"""Stage 2: extend subset.json with more random distractors (never targets) so ranks can be read at a larger scale.
Writes scratch books/subset_scale.json (same layout; old keys first, in order).  Plain python."""
import json, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import SCRATCH  # noqa: E402
N_GUT, N_SL = 6000, 3000
sub = json.loads((SCRATCH / "books/subset.json").read_text())
cat = json.loads((SCRATCH / "books/catalogue.json").read_text())
have = set(sub["keys"])
rng = random.Random(sub["seed"] + 1)
g = [x["key"] for x in cat["gutenberg"] if x["in_production_index"] and x["key"] not in have]
s = [x["key"] for x in cat["survivor"] if x["in_production_index"] and x["key"] not in have]
rng.shuffle(g); rng.shuffle(s)
new = g[:N_GUT] + s[:N_SL]
out = dict(sub); out["keys"] = sub["keys"] + new; out["role"] = dict(sub["role"]) | {k: "scale-random" for k in new}
(SCRATCH / "books/subset_scale.json").write_text(json.dumps(out))
print(len(out["keys"]), len(new))
