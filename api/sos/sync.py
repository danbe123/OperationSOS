"""`sos sync` (resolve, download, verify, rename, record) and `sos index` (rescan, fts_docs, fts_places)."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import httpx

from sos import db, docs as docs_mod, library, places as places_mod
from sos.config import Settings
from sos.content import KIND_BY_DIR, parse_document
from sos.manifest import Item, load_manifests

OPDS_URL = "https://opds.library.kiwix.org/catalog/v2/entries"
ATOM = "{http://www.w3.org/2005/Atom}"
METALINK = "{urn:ietf:params:xml:ns:metalink}"
CHUNK = 1 << 20
URL_BY_KIND = {"scenario": "/s/", "module": "/m/", "card": "/medical/card/", "page": "/p/"}
FTS_KIND = {"scenario": "playbook", "module": "module", "card": "card", "page": "page"}


class SyncError(RuntimeError):
    pass


class ChecksumError(SyncError):
    pass


@dataclass
class Resolved:
    url: str
    name: str
    size: int | None
    as_at: str | None
    sha256: str | None = None
    mirrors: list[str] = field(default_factory=list)


def parse_opds_entry(text: str) -> Resolved | None:
    root = ET.fromstring(text)
    entry = root.find(f"{ATOM}entry")
    if entry is None:
        return None
    link = next((l for l in entry.findall(f"{ATOM}link") if l.get("type") == "application/x-zim"), None)
    if link is None or not link.get("href"):
        return None
    href = link.get("href", "")
    url = href[:-6] if href.endswith(".meta4") else href
    length = link.get("length") or ""
    updated = entry.findtext(f"{ATOM}updated") or ""
    return Resolved(url=url, name=Path(url).stem, size=int(length) if length.isdigit() else None, as_at=updated[:10] or None)


def parse_meta4(text: str) -> tuple[int | None, str | None, list[str]]:
    root = ET.fromstring(text)
    file_el = root.find(f"{METALINK}file")
    if file_el is None:
        return None, None, []
    size_text = file_el.findtext(f"{METALINK}size") or ""
    sha = next((h.text.strip() for h in file_el.findall(f"{METALINK}hash") if h.get("type") == "sha-256" and h.text), None)
    mirrors = [u.text.strip() for u in file_el.findall(f"{METALINK}url") if u.text]
    return (int(size_text) if size_text.isdigit() else None), sha, mirrors


def resolve_kiwix(name: str, client: httpx.Client) -> Resolved:
    r = client.get(OPDS_URL, params={"name": name, "count": "1"})
    r.raise_for_status()
    resolved = parse_opds_entry(r.text)
    if resolved is None:
        raise SyncError(f"no Kiwix catalogue entry named '{name}'")
    try:
        m = client.get(resolved.url + ".meta4")
        if m.status_code == 200:
            size, sha, mirrors = parse_meta4(m.text)
            resolved.size = size or resolved.size
            resolved.sha256 = sha
            resolved.mirrors = mirrors
    except (httpx.HTTPError, ET.ParseError):
        pass
    return resolved


def resolve_item(item: Item, client: httpx.Client) -> Resolved | None:
    if item.source.type == "kiwix":
        return resolve_kiwix(item.source.name or item.id, client)
    if item.source.type == "url":
        url = item.source.url or ""
        return Resolved(url=url, name=Path(url).stem, size=item.size_bytes or None, as_at=item.as_at,
                        sha256=item.source.sha256, mirrors=list(item.source.mirrors))
    return None


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def stream_download(url: str, target: Path, client: httpx.Client | None = None) -> Path:
    """Built-in downloader with Range resume from an existing partial file."""
    own = client is None
    client = client or httpx.Client(timeout=60, follow_redirects=True)
    try:
        existing = target.stat().st_size if target.exists() else 0
        headers = {"Range": f"bytes={existing}-"} if existing else {}
        with client.stream("GET", url, headers=headers) as r:
            if r.status_code == 416:
                return target
            if r.status_code == 206:
                mode = "ab"
            elif r.status_code == 200:
                mode = "wb"
            else:
                raise SyncError(f"HTTP {r.status_code} for {url}")
            with open(target, mode) as fh:
                for chunk in r.iter_bytes(CHUNK):
                    fh.write(chunk)
    finally:
        if own:
            client.close()
    return target


def aria2c_download(url: str, target: Path, sha256: str | None = None, mirrors=(), run: Callable = subprocess.run) -> Path:
    cmd = ["aria2c", "--continue=true", "--max-connection-per-server=4", "--split=4", "--file-allocation=none",
           "--auto-file-renaming=false", "--allow-overwrite=true", f"--dir={target.parent}", f"--out={target.name}"]
    if sha256:
        cmd.append(f"--checksum=sha-256={sha256}")
    cmd.append(url)
    cmd.extend(mirrors)
    proc = run(cmd, check=False)
    if proc.returncode != 0:
        raise SyncError(f"aria2c failed (exit {proc.returncode}) for {url}")
    return target


def download(url: str, target: Path, sha256: str | None = None, mirrors=(), use_aria2: bool | None = None,
             run: Callable = subprocess.run, client: httpx.Client | None = None) -> Path:
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    if use_aria2 is None:
        use_aria2 = shutil.which("aria2c") is not None
    if use_aria2:
        return aria2c_download(url, target, sha256, mirrors, run)  # aria2c verifies --checksum itself
    stream_download(url, target, client)
    if sha256:
        actual = sha256_file(target)
        if actual != sha256:
            target.unlink(missing_ok=True)
            raise ChecksumError(f"sha256 mismatch for {target.name}: expected {sha256}, got {actual}")
    return target


def _open_db(settings: Settings) -> sqlite3.Connection:
    settings.state.mkdir(parents=True, exist_ok=True)
    conn = db.connect(settings.db_path)
    db.init_schema(conn)
    library.upsert_items(conn, load_manifests(settings.manifests))
    return conn


def record_resolved(conn: sqlite3.Connection, item_id: str, resolved: Resolved) -> None:
    conn.execute("UPDATE library_items SET resolved_name=?, resolved_size=?, resolved_as_at=? WHERE id=?",
                 (resolved.name, resolved.size, resolved.as_at, item_id))
    conn.commit()


def sync(settings: Settings, tier: str, only: list[str] | None = None, dry_run: bool = False, out: Callable = print,
         client: httpx.Client | None = None, run: Callable = subprocess.run, use_aria2: bool | None = None) -> int:
    items = [i for i in load_manifests(settings.manifests) if i.tier == tier]
    if only:
        wanted = set(only)
        for missing in sorted(wanted - {i.id for i in items}):
            out(f"WARN {missing}: not in manifest for tier {tier}")
        items = [i for i in items if i.id in wanted]
    items.sort(key=lambda i: (i.priority, i.id))
    root = settings.tier_root(tier)
    if tier == "extended" and not dry_run and not library.ext_mounted(settings):
        raise SyncError("External drive is not connected")
    own_client = client is None
    client = client or httpx.Client(timeout=60, follow_redirects=True)
    conn = None if dry_run else _open_db(settings)
    failures = 0
    try:
        for item in items:
            target = root / item.dest
            if item.source.type == "build":
                out(f"BUILD {item.id}: run `sos {item.source.tool}` on the PC and copy {item.source.artifact} to {target}")
                continue
            try:
                resolved = resolve_item(item, client)
            except (SyncError, httpx.HTTPError, ET.ParseError) as exc:
                out(f"FAIL {item.id}: {exc}")
                failures += 1
                continue
            assert resolved is not None
            size_txt = f"{resolved.size / 1e9:.2f} GB" if resolved.size else "size unknown"
            if target.exists() and (resolved.size is None or target.stat().st_size == resolved.size):
                out(f"OK   {item.id}: present at {target}")
                if conn is not None:
                    record_resolved(conn, item.id, resolved)
                continue
            if dry_run:
                out(f"GET  {item.id}: {resolved.url} ({size_txt}) -> {target}")
                continue
            out(f"GET  {item.id}: {resolved.url} ({size_txt})")
            part = target.with_name(target.name + ".part")
            try:
                download(resolved.url, part, resolved.sha256, resolved.mirrors, use_aria2, run, client)
            except (SyncError, httpx.HTTPError, OSError) as exc:
                out(f"FAIL {item.id}: {exc}")
                failures += 1
                continue
            os.replace(part, target)
            assert conn is not None
            record_resolved(conn, item.id, resolved)
            out(f"DONE {item.id}: {target}")
    finally:
        if conn is not None:
            conn.close()
        if own_client:
            client.close()
    if not dry_run:
        index(settings, out)
    return 1 if failures else 0


_MD_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_MD_TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$", re.MULTILINE)
_MD_NOISE = re.compile(r"\{\{module:[a-z0-9-]+\}\}|\{#[A-Za-z0-9_/-]+\}|^\s*[-*+] \[[ xX]\]|^\s*#+\s*|[*_`>|]|^\s*-{3,}\s*$", re.MULTILINE)


def strip_markdown(md: str) -> str:
    text = _MD_LINK.sub(r"\1", md or "")
    text = _MD_TABLE_SEP.sub(" ", text)
    text = _MD_NOISE.sub(" ", text)
    return " ".join(text.split())


def index_content(conn: sqlite3.Connection, playbooks_dir: Path) -> int:
    playbooks_dir = Path(playbooks_dir)
    if not playbooks_dir.is_dir():
        return 0
    count = 0
    overlay_scenarios: dict[str, list[str]] = {}
    for dirname, kind in KIND_BY_DIR.items():
        for path in sorted((playbooks_dir / dirname).glob("*.md")):
            try:
                doc = parse_document(path)
            except Exception:
                continue
            base_url = URL_BY_KIND[kind] + doc.id
            scenarios = doc.id if kind == "scenario" else ""
            sections = [(sid, title, md) for sid, title, md in doc.sections if md.strip()] or [("", "", doc.summary)]
            for sid, title, md in sections:
                body = strip_markdown((title + "\n" if title else "") + md)
                url = f"{base_url}#{sid}" if sid else base_url
                conn.execute(
                    "INSERT INTO fts_docs(title, body, doc_id, kind, category, scenarios, page, url) VALUES (?,?,?,?,?,?,?,?)",
                    (doc.title, body, f"{kind}:{doc.id}", FTS_KIND[kind], "playbooks", scenarios, None, url),
                )
                count += 1
            if kind == "scenario":
                for ov in doc.overlays:
                    overlay_scenarios.setdefault(ov, []).append(doc.id)
    db.set_setting(conn, "overlay_scenarios", json.dumps({k: sorted(v) for k, v in sorted(overlay_scenarios.items())}))
    conn.commit()
    return count


def index_titles(conn: sqlite3.Connection) -> int:
    count = 0
    for row in conn.execute("SELECT * FROM library_items ORDER BY priority, id").fetchall():
        conn.execute(
            "INSERT INTO fts_docs(title, body, doc_id, kind, category, scenarios, page, url) VALUES (?,?,?,?,?,?,?,?)",
            (row["title"], row["description"] or "", f"item:{row['id']}", "item", row["category"],
             " ".join(json.loads(row["scenarios_json"] or "[]")), None, f"/library#{row['id']}"),
        )
        count += 1
    conn.commit()
    return count


def notify_api(settings: Settings) -> bool:
    """Ask a running sos-api to rescan so it sees new files. Best effort."""
    try:
        r = httpx.post(f"http://127.0.0.1:{settings.port}/api/system/rescan", timeout=10)
        return r.status_code == 200
    except httpx.HTTPError:
        return False


def index(settings: Settings, out: Callable = print, runner=None) -> dict:
    conn = _open_db(settings)
    try:
        scan = library.rescan(conn, settings)
        out(f"rescan: {scan['available']} of {scan['items']} items available")
        conn.execute("DELETE FROM fts_docs")
        conn.commit()
        n_content = index_content(conn, settings.playbooks)
        n_titles = index_titles(conn)
        n_docs = docs_mod.index_docs(conn, runner)
        imported = places_mod.import_places(conn, places_mod.places_path(settings))
        places_txt = "unchanged" if imported is None else f"{imported} rows"
        out(f"index: {n_content} content rows, {n_titles} title rows, {n_docs} document pages, places {places_txt}")
    finally:
        conn.close()
    notify_api(settings)
    return {"content": n_content, "titles": n_titles, "docs": n_docs, "places": imported, **scan}
