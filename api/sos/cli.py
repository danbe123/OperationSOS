"""`sos` command line: sync, index, storage-event, validate-playbooks, build-maps, build-nhs, eval, pin, status."""
from __future__ import annotations

import argparse
import getpass
import json
import sys
import time
from pathlib import Path

import httpx

from sos import buildmaps, db, library, system
from sos.config import Settings, get_settings
from sos.content import KIND_BY_DIR, validate_tree
from sos.manifest import load_manifests


def _api(settings: Settings) -> str:
    return f"http://127.0.0.1:{settings.port}/api"


def cmd_sync(settings: Settings, args) -> int:
    from sos.sync import SyncError, sync

    only = [s for s in (args.only or "").split(",") if s] or None
    try:
        return sync(settings, args.tier, only=only, dry_run=args.dry_run)
    except SyncError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def cmd_index(settings: Settings, args) -> int:
    from sos.sync import index

    index(settings)
    return 0


def post_rescan(settings: Settings) -> bool:
    try:
        r = httpx.post(f"{_api(settings)}/system/rescan", timeout=30)
        print(f"rescan: {r.status_code} {r.text.strip()}")
        return r.status_code == 200
    except httpx.HTTPError as exc:
        print(f"rescan failed: {exc}", file=sys.stderr)
        return False


def _is_mounted(path: Path) -> bool:
    try:
        return any(line.split()[1] == str(path) for line in Path("/proc/mounts").read_text().splitlines())
    except OSError:
        return False


def cmd_storage_event(settings: Settings, args) -> int:
    if args.event == "remove":
        settings.state.mkdir(parents=True, exist_ok=True)
        conn = db.connect(settings.db_path)
        try:
            db.init_schema(conn)
            library.write_library_xml(conn, settings, include_ext=False)
        finally:
            conn.close()
        time.sleep(1.0)  # let kiwix-serve --monitorLibrary drop the books before the unmount
    ok = post_rescan(settings)
    if args.event == "remove":
        if not settings.dev and _is_mounted(settings.ext):
            system.sudo(["umount", "-l", str(settings.ext)], settings)
        return 0
    return 0 if ok else 1


def cmd_validate(settings: Settings, args) -> int:
    items = load_manifests(settings.manifests) if settings.manifests.is_dir() else []
    overlay_ids = {i.overlay.id for i in items if i.overlay}
    kiwix_check = doc_check = None
    if args.deep:
        client = httpx.Client(timeout=10, follow_redirects=True)

        def kiwix_check(book: str, path: str) -> bool:
            try:
                return client.get(f"{settings.kiwix_url}/raw/{book}/content/{path}").status_code == 200
            except httpx.HTTPError:
                return False

        def doc_check(item) -> bool:
            return (settings.tier_root(item.tier) / item.dest).exists()

    problems = validate_tree(settings.playbooks, items, overlay_ids, kiwix_check=kiwix_check, doc_check=doc_check,
                             require_all_scenarios=args.all_scenarios)
    for line in problems:
        print(line)
    errors = [p for p in problems if not p.startswith("warning: ")]
    if errors:
        print(f"FAILED {len(errors)} error{'s' if len(errors) != 1 else ''}")
        return 1
    count = sum(len(list((settings.playbooks / d).glob("*.md"))) for d in KIND_BY_DIR) if settings.playbooks.is_dir() else 0
    print(f"OK {count} documents")
    return 0


def cmd_pin(settings: Settings, args) -> int:
    settings.state.mkdir(parents=True, exist_ok=True)
    conn = db.connect(settings.db_path)
    try:
        db.init_schema(conn)
        if args.action == "reset":
            system.clear_pin(conn)
            print("PIN cleared")
            return 0
        pin = args.pin or getpass.getpass("New admin PIN (4 to 12 digits): ")
        try:
            system.set_pin(conn, pin)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print("PIN set")
        return 0
    finally:
        conn.close()


def cmd_status(settings: Settings, args) -> int:
    try:
        r = httpx.get(f"{_api(settings)}/status", timeout=10)
        r.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"sos-api not reachable: {exc}", file=sys.stderr)
        return 1
    for key, value in r.json().items():
        print(f"{key}: {json.dumps(value) if isinstance(value, (dict, list)) else value}")
    return 0


def cmd_build_maps(settings: Settings, args) -> int:
    return buildmaps.run(args)


def cmd_build_nhs(settings: Settings, args) -> int:
    from sos import buildnhs

    return buildnhs.main(args.out)


def cmd_eval(settings: Settings, args) -> int:
    from sos import evalrun

    return evalrun.run_from_namespace(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sos", description="Operation SOS command line")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("sync", help="resolve, download, verify and index a content tier")
    p.add_argument("--tier", choices=["core", "extended"], required=True)
    p.add_argument("--only", help="comma-separated item ids")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_sync)
    p = sub.add_parser("index", help="rescan, rebuild fts_docs, import places if changed")
    p.set_defaults(func=cmd_index)
    p = sub.add_parser("storage-event", help="external drive plugged in or removed")
    p.add_argument("event", choices=["add", "remove"])
    p.set_defaults(func=cmd_storage_event)
    p = sub.add_parser("validate-playbooks", help="validate authored content")
    p.add_argument("--deep", action="store_true", help="also request every kiwix: path and check every doc: file")
    p.add_argument("--all-scenarios", action="store_true", help="require all 20 scenario playbooks")
    p.set_defaults(func=cmd_validate)
    p = sub.add_parser("build-maps", help="PC only: build map tiles, styles, overlays, places and phone packs")
    buildmaps.add_arguments(p)
    p.set_defaults(func=cmd_build_maps)
    p = sub.add_parser("build-nhs", help="PC only: zimit crawl of nhs.uk")
    p.add_argument("--out")
    p.set_defaults(func=cmd_build_nhs)
    p = sub.add_parser("eval", help="AI evaluation (plan 05)")
    p.add_argument("--retrieval-only", action="store_true")
    p.add_argument("--out")
    p.set_defaults(func=cmd_eval)
    p.add_argument("--questions", help="evaluation question file")
    p = sub.add_parser("pin", help="admin PIN")
    p.add_argument("action", choices=["reset", "set"])
    p.add_argument("pin", nargs="?")
    p.set_defaults(func=cmd_pin)
    p = sub.add_parser("status", help="print /api/status")
    p.set_defaults(func=cmd_status)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = get_settings()
    try:
        return args.func(settings, args)
    except NotImplementedError as exc:
        print(f"not available: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
