"""Check that api/sos/embeddings.py's opt-in "meta-opening" household text is byte-identical to the lab's c0 representation on
real books (100 of the subset's Gutenberg books, read from the real ZIM).  API venv, PYTHONPATH=<worktree>/api."""
import json, pathlib, sqlite3, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import SCRATCH, DB_PATH   # noqa: E402
from sos import embeddings            # noqa: E402
from sos.books import open_zim, SHELF_NAMES   # noqa: E402
from reps import rep_texts            # noqa: E402

B = SCRATCH / "books"
sub = json.loads((B / "subset.json").read_text()); cat = json.loads((B / "catalogue.json").read_text())
rows = {g["key"]: g for g in cat["gutenberg"]}
keys = [k for k in sub["keys"] if k.startswith("gutenberg")][::35][:100]
recs = {}
with open(B / "texts.jsonl", encoding="utf-8") as fh:
    for line in fh:
        if line.startswith('{"key": "gutenberg'):
            r = json.loads(line)
            if r["key"] in keys:
                recs[r["key"]] = r
src = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True); src.row_factory = sqlite3.Row
mem = sqlite3.connect(":memory:"); mem.row_factory = sqlite3.Row
mem.execute("create table books (zim text,id int,title text,author text,shelf text,html_path text)")
for k in keys:
    mem.execute("insert into books values (?,?,?,?,?,?)", tuple(src.execute("select zim,id,title,author,shelf,html_path from books where id=?", (int(k.split(":")[1]),)).fetchone()))
reader = open_zim(pathlib.Path("/home/dan/sos-content/zim/gutenberg_en_all.zim"))
same = diff = 0
for key, heading, text in embeddings._household_entries(reader, "gutenberg_en_all", mem, "meta-opening"):
    mine = f"{heading}. {text}"[:embeddings.HOUSEHOLD_TEXT_CHARS].strip()      # the lab strips the ends; the tokenizer ignores them anyway
    lab = rep_texts(rows[key], recs[key], SHELF_NAMES)["c0"]
    if mine == lab:
        same += 1
    else:
        diff += 1
        i = next((n for n, (a, b) in enumerate(zip(mine, lab)) if a != b), min(len(mine), len(lab)))
        if diff < 4:
            print(i, len(mine), len(lab), repr(mine[max(0, i - 40):i + 40]), repr(lab[max(0, i - 40):i + 40]))
print("identical", same, "different", diff)
