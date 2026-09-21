"""Build the ~5,000-book subset: every gold-target book (books.jsonl + books-extra.jsonl) that the production household
index holds, plus hard distractors (same LCC shelf for Gutenberg targets, same Survivor Library category for Survivor
targets) and random distractors, seeded.  Writes scratch books/subset.json.  Plain python."""
import json, random, sys
from collections import Counter, defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import SCRATCH, REPO  # noqa: E402

SEED = 20260921
N_HARD_GUT, N_RANDOM_GUT = 1500, 1300
N_HARD_SL, N_RANDOM_SL = 650, 350

cat = json.loads((SCRATCH / "books/catalogue.json").read_text())
gut = {g["key"]: g for g in cat["gutenberg"] if g["in_production_index"]}
sl = {s["key"]: s for s in cat["survivor"] if s["in_production_index"]}
targets: dict[str, set] = defaultdict(set)   # key -> {gold file}
dropped = Counter()
for name in ("books", "books-extra"):
    for line in (REPO / f"tools/eval/search/{name}.jsonl").read_text().splitlines():
        row = json.loads(line)
        for e in row["expected"]:
            key = f"gutenberg_en_all:{e['gutenberg']}" if "gutenberg" in e else f"survivorlibrary.com_en_all:{e['survivor']}"
            if key in gut or key in sl:
                targets[key].add(name)
            else:
                dropped[name] += 1
rng = random.Random(SEED)
chosen: dict[str, str] = {k: "target" for k in targets}
# hard distractors: same shelf / category as a target, weighted to the targets' own mix
shelf_n = Counter(gut[k]["shelf"] for k in targets if k in gut)
cat_n = Counter(c for k in targets if k in sl for c in sl[k]["categories"])
def pick_hard(pool_by_group, group_weights, n):
    groups = list(group_weights)
    picked = []
    pools = {g: [k for k in pool_by_group[g] if k not in chosen] for g in groups}
    for g in groups:
        rng.shuffle(pools[g])
    total = sum(group_weights.values())
    for g in groups:
        take = max(1, round(n * group_weights[g] / total))
        picked += pools[g][:take]
    rng.shuffle(picked)
    return picked[:n]
by_shelf = defaultdict(list)
for k, g in gut.items(): by_shelf[g["shelf"]].append(k)
by_cat = defaultdict(list)
for k, s in sl.items():
    for c in s["categories"]: by_cat[c].append(k)
for k in pick_hard(by_shelf, shelf_n, N_HARD_GUT): chosen[k] = "hard"
for k in pick_hard(by_cat, cat_n, N_HARD_SL): chosen.setdefault(k, "hard")
rest_g = [k for k in gut if k not in chosen]; rest_s = [k for k in sl if k not in chosen]
rng.shuffle(rest_g); rng.shuffle(rest_s)
for k in rest_g[:N_RANDOM_GUT]: chosen[k] = "random"
for k in rest_s[:N_RANDOM_SL]: chosen[k] = "random"
keys = sorted(chosen, key=lambda k: (k.split(":")[0], int(k.split(":")[1]) if k.startswith("gutenberg") else 0, k))
out = {"seed": SEED, "keys": keys, "role": {k: chosen[k] for k in keys}, "target_in": {k: sorted(v) for k, v in targets.items()},
       "dropped_gold_entries_not_in_index": dict(dropped)}
(SCRATCH / "books/subset.json").write_text(json.dumps(out))
zc = Counter(k.split(":")[0] for k in keys); rc = Counter(chosen[k] for k in keys)
print(len(keys), dict(zc), dict(rc), "dropped gold entries", dict(dropped))
print("targets:", sum(1 for k in targets if k in gut), "gutenberg,", sum(1 for k in targets if k in sl), "survivor")
