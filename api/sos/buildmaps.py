"""`sos build-maps`: the PC-only map pipeline (spec section 9 and 13; plan 04)."""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

from sos.mapbuild.common import (BuildError, Context, MICROMAMBA_HINT, check_tools, log, read_versions,
                                 repo_root)

STEP_IDS = ("base", "os", "contours", "hillshade", "overlays", "places", "packs", "styles", "verify")


def all_steps() -> list:
    """Registry in pipeline order. Later tasks append their step here."""
    from sos.mapbuild.base import BaseStep
    from sos.mapbuild.contours import ContoursStep
    from sos.mapbuild.hillshade import HillshadeStep
    from sos.mapbuild.osdata import OsZoomstackStep
    from sos.mapbuild.overlays import OverlaysStep
    from sos.mapbuild.packs import PacksStep
    from sos.mapbuild.places import PlacesStep
    from sos.mapbuild.styles import StylesStep
    return [BaseStep(), OsZoomstackStep(), ContoursStep(), HillshadeStep(), OverlaysStep(), PlacesStep(), PacksStep(), StylesStep()]


def select_steps(ids: list[str] | None) -> list:
    """Steps in registry order: all registered steps if `ids` is falsy, else just the named ones."""
    registry = all_steps()
    if not ids:
        return list(registry)
    known = {step.id for step in registry}
    missing = [i for i in ids if i not in known]
    if missing:
        raise BuildError(f"step(s) not available: {', '.join(missing)} (registered: {', '.join(sorted(known))})")
    wanted = set(ids)
    return [step for step in registry if step.id in wanted]


def run_steps(ctx: Context, ids: list[str] | None) -> None:
    for step in select_steps(ids):
        outputs = [ctx.out / name for name in step.outputs(ctx)]
        if outputs and all(p.exists() for p in outputs) and not ctx.force:
            log.info("[%s] up to date, skipping (use --force to rebuild)", step.id)
            continue
        started = time.monotonic()
        log.info("[%s] start", step.id)
        step.run(ctx)
        missing = [str(p) for p in outputs if not p.exists()]
        if missing:
            raise BuildError(f"[{step.id}] did not produce: {', '.join(missing)}")
        log.info("[%s] done in %.0fs", step.id, time.monotonic() - started)


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--out", type=Path, default=None,
                        help="output directory (default ~/sos-content/maps; with --fixture api/tests/fixtures/maps)")
    parser.add_argument("--steps", nargs="+", choices=STEP_IDS, default=None,
                        help="steps to run in registry order (default: all)")
    parser.add_argument("--build", default=None, help="Protomaps build YYYYMMDD (default PROTOMAPS_BUILD from install/versions.env)")
    parser.add_argument("--fixture", action="store_true", help="build the 0.1 degree Southampton fixture instead of the full extract")
    parser.add_argument("--force", action="store_true", help="rebuild steps whose outputs already exist")


def run(args: argparse.Namespace) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stderr)
    missing = check_tools()
    if missing:
        print(f"build-maps: missing tools: {', '.join(missing)}\n{MICROMAMBA_HINT}", file=sys.stderr)
        return 2
    try:
        repo = repo_root()
        versions = read_versions(repo / "install" / "versions.env")
        build = args.build or versions.get("PROTOMAPS_BUILD", "")
        if not build:
            raise BuildError("no Protomaps build: pass --build YYYYMMDD or set PROTOMAPS_BUILD in install/versions.env")
        default_out = repo / "api" / "tests" / "fixtures" / "maps" if args.fixture else Path.home() / "sos-content" / "maps"
        out = Path(args.out).resolve() if args.out else default_out
        src = Path(os.environ.get("SOS_MAPS_SRC") or Path.home() / "sos-content" / "maps-src")
        out.mkdir(parents=True, exist_ok=True)
        src.mkdir(parents=True, exist_ok=True)
        ctx = Context(out=out, src=src, fixture=args.fixture, force=args.force, build=build, versions=versions, repo=repo)
        log.info("build-maps out=%s src=%s fixture=%s build=%s", out, src, args.fixture, build)
        run_steps(ctx, args.steps)
    except BuildError as exc:
        print(f"build-maps: {exc}", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sos build-maps")
    add_arguments(parser)
    return run(parser.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
