"""Read the subset's books out of the two ZIMs and keep only what the representations need (run with the API venv, needs
libzim and pdftotext; resumable, one JSON line per book in scratch books/texts.jsonl):
  today   the production household text: the first HOUSEHOLD_TEXT_CHARS of extract text / pdftotext output
  prose   the first ~1500 characters of real prose after the title page, contents list and licence boilerplate
  windows 10 windows of ~1500 characters at 5%, 15% ... 95% of the book's text
  subjects, creator (Gutenberg dc.* metadata of the page head), nchars, and the seconds each step took."""
from __future__ import annotations
import argparse, html, json, os, re, subprocess, sys, tempfile, time
from multiprocessing import Pool
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "api"))
from common import SCRATCH  # noqa: E402

GUT_ZIM = "/home/dan/sos-content/zim/gutenberg_en_all.zim"
SL_ZIM = "/home/dan/sos-content/zim/survivorlibrary.com_en_all.zim"
NWIN, WIN = 10, 1500
TODAY = 2584
_archives: dict = {}
_WS = re.compile(r"\s+")
_HEAD = re.compile(r"<head.*?</head>|<style.*?</style>|<script.*?</script>", re.S | re.I)
_TAGS = re.compile(r"<[^>]+>")
_META = re.compile(r'<meta content="([^"]*)" name="(dc\.[a-z]+)"')
_BOILER = re.compile(r"project gutenberg|gutenberg-tm|copyright|all rights reserved|transcriber|produced by|printed in|printed by|published by|"
                     r"table of contents|illustrations?\b|e-?text|this ebook|release date|http|www\.", re.I)


def archive(path):
    if path not in _archives:
        from libzim.reader import Archive
        _archives[path] = Archive(path)
    return _archives[path]


def plain_from_html(raw: bytes) -> str:
    t = raw.decode("utf-8", "replace")
    t = _HEAD.sub(" ", t)
    t = _TAGS.sub(" ", t)
    return _WS.sub(" ", html.unescape(t)).strip()


def windows(text: str) -> list[str]:
    n = len(text)
    out = []
    for i in range(NWIN):
        pos = int(n * (i + 0.5) / NWIN)
        seg = text[pos: pos + WIN + 400]
        m = re.search(r"[.!?] (?=[A-Z\"'“‘])", seg[:300])
        if m:
            seg = seg[m.end():]
        seg = seg[:WIN]
        sp = seg.rfind(" ")
        out.append(seg[: sp if sp > WIN * 0.7 else len(seg)].strip())
    return out


def prose_score(par: str) -> bool:
    words = par.split()
    if len(words) < 30:
        return False
    letters = sum(c.isalpha() for c in par)
    if letters < 0.7 * len(par):
        return False
    upper = sum(c.isupper() for c in par)
    if upper > 0.25 * letters:
        return False
    if not re.search(r"[a-z]{3,} [a-z]{2,} [a-z]{2,}", par):
        return False
    if len(re.findall(r"[.!?]", par)) < 2 and len(re.findall(r",", par)) < 2:
        return False
    if len(re.findall(r"\bCHAPTER\b|\bChapter\b|\bPART\b", par)) >= 3 or _BOILER.search(par):
        return False
    return True


def opening_prose(paragraphs: list[str]) -> str:
    got, total = [], 0
    for par in paragraphs[:4000]:
        if prose_score(par):
            got.append(par)
            total += len(par) + 1
            if total >= WIN:
                break
        elif got:
            continue
    return " ".join(got)[:WIN]


def work(key: str) -> dict:
    zim, ident = key.split(":", 1)
    rec = {"key": key}
    t0 = time.perf_counter()
    try:
        if zim == "gutenberg_en_all":
            from sos.embeddings import _gutenberg_text
            from sos.kiwix import extract_text
            arc = archive(GUT_ZIM)
            row = json.loads(Path(SCRATCH / "books/gut_paths.json").read_text()) if False else None
            path = GUT_PATHS[ident]
            raw = bytes(arc.get_entry_by_path(path).get_item().content)
            rec["t_read"] = time.perf_counter() - t0
            t1 = time.perf_counter()
            today = _gutenberg_text(raw)[:TODAY]
            rec["t_today"] = time.perf_counter() - t1
            t1 = time.perf_counter()
            head = raw[:60000].decode("utf-8", "replace")
            meta = _META.findall(head)
            rec["subjects"] = [html.unescape(v) for v, n in meta if n == "dc.subject"]
            rec["creator"] = next((html.unescape(v) for v, n in meta if n == "dc.creator"), "")
            paras = extract_text(raw.decode("utf-8", "replace"), max_chars=90000)
            rec["prose"] = opening_prose(paras)
            text = plain_from_html(raw)
            rec["nchars"] = len(text)
            rec["windows"] = windows(text)
            rec["t_extra"] = time.perf_counter() - t1
        else:
            from sos.embeddings import _pdf_text
            arc = archive(SL_ZIM)
            raw = bytes(arc.get_entry_by_path(SL_PATHS[ident]).get_item().content)
            rec["t_read"] = time.perf_counter() - t0
            rec["pdf_bytes"] = len(raw)
            t1 = time.perf_counter()
            text = _pdf_text(raw)
            rec["t_pdftotext"] = time.perf_counter() - t1
            t1 = time.perf_counter()
            rec["today"] = text[:TODAY]
            flat = _WS.sub(" ", re.sub(r"-\n(?=[a-z])", "", text)).strip()
            rec["nchars"] = len(flat)
            rec["prose"] = opening_prose([p for p in re.split(r"\n\s*\n", text) if p.strip()] and
                                         [_WS.sub(" ", p).strip() for p in re.split(r"\n\s*\n", re.sub(r"-\n(?=[a-z])", "", text))])
            rec["windows"] = windows(flat) if len(flat) > 200 else []
            rec["t_extra"] = time.perf_counter() - t1
            return rec
        rec["today"] = today
    except Exception as exc:   # a book that cannot be read is recorded, not fatal
        rec["error"] = f"{type(exc).__name__}: {exc}"
    return rec


GUT_PATHS: dict[str, str] = {}
SL_PATHS: dict[str, str] = {}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--procs", type=int, default=6)
    ap.add_argument("--out", default="texts.jsonl")
    a = ap.parse_args()
    sub = json.loads((SCRATCH / "books/subset.json").read_text())
    cat = json.loads((SCRATCH / "books/catalogue.json").read_text())
    GUT_PATHS.update({str(g["id"]): g["html_path"] for g in cat["gutenberg"] if g["html_path"]})
    SL_PATHS.update({s["slug"]: s["path"] for s in cat["survivor"]})
    out = SCRATCH / "books" / a.out
    done = set()
    if out.exists():
        done = {json.loads(l)["key"] for l in out.read_text().splitlines() if l.strip()}
    keys = [k for k in sub["keys"] if k not in done]
    if a.limit:
        keys = keys[: a.limit]
    print(f"{len(done)} done, {len(keys)} to do", flush=True)
    t0 = time.perf_counter()
    with open(out, "a", encoding="utf-8") as fh, Pool(a.procs, initializer=_init, initargs=(GUT_PATHS, SL_PATHS)) as pool:
        for i, rec in enumerate(pool.imap_unordered(work, keys, chunksize=4), 1):
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if i % 200 == 0:
                fh.flush()
                print(f"{i}/{len(keys)} {time.perf_counter() - t0:.0f}s", flush=True)
    print("finished", time.perf_counter() - t0)


def _init(g, s):
    GUT_PATHS.update(g); SL_PATHS.update(s)


if __name__ == "__main__":
    main()
