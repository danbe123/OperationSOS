"""Apply extras_spec.SPEC to the catalogue: print each query's acceptable books for review, and write books-extra.jsonl
with --write.  Only books the production household index really holds are acceptable (so today's representation is
not blamed for a book it never embedded).  Run with any python; needs catalogue.json (catalogue.py)."""
import argparse, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import SCRATCH, REPO   # noqa: E402
from extras_spec import SPEC       # noqa: E402

ap = argparse.ArgumentParser(); ap.add_argument("--write", action="store_true"); ap.add_argument("--only", default=""); ap.add_argument("-n", type=int, default=12)
args = ap.parse_args()
cat = json.loads((SCRATCH / "books/catalogue.json").read_text())
gut = [g for g in cat["gutenberg"] if g["in_production_index"]]
sl = [s for s in cat["survivor"] if s["in_production_index"]]
rows = []
for rid, query, spec in SPEC:
    exp, notes = [], []
    if spec.get("gut"):
        rx, nx, sh = re.compile(spec["gut"], re.I), (re.compile(spec["gut_not"], re.I) if spec.get("gut_not") else None), spec.get("gut_shelf")
        hits = [g for g in gut if rx.search(g["title"]) and not (nx and nx.search(g["title"])) and (not sh or re.match(f"(?:{sh})", g["shelf"]))]
        exp += [{"gutenberg": g["id"], "title": g["title"]} for g in hits]
        notes.append(f"{len(hits)} Gutenberg")
    if spec.get("sl"):
        rx = re.compile(spec["sl"], re.I)
        nxs = re.compile(spec["sl_not"], re.I) if spec.get("sl_not") else None
        hits_s = [s for s in sl if rx.search(s["title"]) and not (nxs and nxs.search(s["title"]))]
        exp += [{"survivor": s["slug"]} for s in hits_s]
        notes.append(f"{len(hits_s)} Survivor Library")
    group = "both" if spec.get("gut") and spec.get("sl") else "gutenberg" if spec.get("gut") else "survivor"
    rows.append({"id": f"book-x-{rid}", "query": query, "expected": exp, "set": "books-extra", "group": group,
                 "tags": ["everyday"], "notes": "every book whose title clearly covers the topic (title-level judgement, no page reading): " + ", ".join(notes)})
    if not args.only or args.only in rid:
        print(f"\n## {rid}: {query}  ->  {len(exp)}")
        for e in exp[: args.n]:
            print("   ", e.get("title") or e["survivor"])
if args.write:
    bad = [r["id"] for r in rows if not r["expected"]]
    assert not bad, bad
    out = REPO / "tools/eval/search/books-extra.jsonl"
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print("wrote", out, len(rows))
