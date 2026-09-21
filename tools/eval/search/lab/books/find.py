"""Grep the catalogue: find.py sl|gut REGEX [-c CATEGORY_REGEX] [-n LIMIT]  (title, and Survivor category / Gutenberg author+shelf)."""
import argparse, json, re, sys
sys.path.insert(0, "..")
from common import SCRATCH  # noqa
ap = argparse.ArgumentParser(); ap.add_argument("kind"); ap.add_argument("rx"); ap.add_argument("-c", default=""); ap.add_argument("-n", type=int, default=40)
ap.add_argument("-a", default="")
a = ap.parse_args()
cat = json.loads((SCRATCH / "books/catalogue.json").read_text())
rx = re.compile(a.rx, re.I)
rows = []
if a.kind == "sl":
    for s in cat["survivor"]:
        if (rx.search(s["title"]) or (a.c and False)) and (not a.c or any(re.search(a.c, c, re.I) for c in s["categories"])):
            rows.append(f"{s['slug']}  [{', '.join(s['categories'])}]")
        elif not a.rx and a.c and any(re.search(a.c, c, re.I) for c in s["categories"]):
            rows.append(f"{s['slug']}  [{', '.join(s['categories'])}]")
else:
    for g in cat["gutenberg"]:
        if rx.search(g["title"]) and (not a.a or re.search(a.a, g["author"], re.I)) and (not a.c or re.search(a.c, g["shelf"])):
            rows.append(f"{g['id']}  {g['title'][:90]} | {g['author'][:30]} | {g['shelf']}")
print(len(rows), "matches")
print("\n".join(rows[: a.n]))
