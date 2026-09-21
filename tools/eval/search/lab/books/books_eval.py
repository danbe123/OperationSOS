"""Score every representation on the gold queries: rank of the right book among the subset's books, hit@5/@10, MRR@10, with
paired bootstrap intervals (lab/common.py).  usage: books_eval.py <tag> [<tag> ...]  -> results/books/eval_<tag>.json (+ printed tables)
Query strata: known (books.jsonl Gutenberg plot descriptions), sl (books.jsonl Survivor topics), extras split by a stable hash into a
dev half (tuned on, together with the two above) and a held-out half (never looked at until the choice was made)."""
import hashlib, json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import SCRATCH, RESULTS, REPO, m_rr, m_hit   # noqa: E402

B = SCRATCH / "books"
sub = json.loads((B / "subset.json").read_text())
keys = sub["keys"]; kidx = {k: i for i, k in enumerate(keys)}
N = len(keys)
is_gut = np.array([k.startswith("gutenberg") for k in keys])


def load_queries():
    qs = []
    for name in ("books", "books-extra"):
        for line in (REPO / f"tools/eval/search/{name}.jsonl").read_text().splitlines():
            r = json.loads(line)
            rel = set()
            for e in r["expected"]:
                key = f"gutenberg_en_all:{e['gutenberg']}" if "gutenberg" in e else f"survivorlibrary.com_en_all:{e['survivor']}"
                if key in kidx:
                    rel.add(kidx[key])
            qs.append({"id": r["id"], "query": r["query"], "set": r["set"], "group": r["group"], "rel": sorted(rel)})
    # strata
    extras = sorted([q for q in qs if q["set"] == "books-extra"], key=lambda q: (q["group"], hashlib.md5(q["id"].encode()).hexdigest()))
    pos = {}
    for g in ("both", "gutenberg", "survivor"):
        for j, q in enumerate([q for q in extras if q["group"] == g]):
            pos[q["id"]] = "extra-dev" if j % 2 == 0 else "extra-heldout"
    for i, q in enumerate(qs):
        q["qi"] = i
        q["stratum"] = ("known" if q["group"] == "gutenberg" else "sl") if q["set"] == "books" else pos[q["id"]]
    return [q for q in qs if q["rel"]], qs


QS, ALLQ = load_queries()
STRATA = {"known": ["known"], "sl": ["sl"], "extra-dev": ["extra-dev"], "extra-heldout": ["extra-heldout"],
          "dev (tuning pool)": ["known", "sl", "extra-dev"], "extras (all 58)": ["extra-dev", "extra-heldout"],
          "everyday dev+heldout excl. plots": ["sl", "extra-dev", "extra-heldout"], "ALL": ["known", "sl", "extra-dev", "extra-heldout"]}


def unit(x):
    return x / np.clip(np.linalg.norm(x, axis=-1, keepdims=True), 1e-9, None)


def systems(V):
    """name -> score matrix [nq_all, N] (float32)."""
    Q = V["Q"].astype(np.float32)
    S = {}
    for rep in ("a", "b1", "b2", "c0", "c1", "c2"):
        S[rep] = Q @ V[rep].astype(np.float32).T
    n = V["n_dt"].astype(int)
    for tag, arr in (("dt", V["dt"]), ("dp", V["dp"])):
        W = arr.astype(np.float32)                       # [N, 10, D]
        sc = np.einsum("qd,nwd->qnw", Q, W)              # [nq, N, 10]
        for kname, idx in (("k3", [0, 5, 9]), ("k5", [0, 2, 5, 7, 9]), ("k10", list(range(10)))):
            sel = np.array(idx)
            valid = (sel[None, :] < n[:, None])          # [N, k]
            s = sc[:, :, sel]                            # [nq, N, k]
            s_max = np.where(valid[None], s, -9).max(-1)
            cnt = np.maximum(valid.sum(1), 1)
            s_mean = np.where(valid[None], s, 0).sum(-1) / cnt[None]
            top2 = np.sort(np.where(valid[None], s, -9), axis=-1)[..., -2:]
            top2 = np.where(top2 < -8, s_max[..., None], top2).mean(-1)
            m = np.where(valid[:, :, None], W[:, sel], 0).sum(1) / cnt[:, None]
            S[f"{tag}-{kname}-max"] = s_max; S[f"{tag}-{kname}-mean"] = s_mean; S[f"{tag}-{kname}-top2"] = top2
            S[f"{tag}-{kname}-pool"] = Q @ unit(m).T
    b2 = S["b2"]
    S["b2+dt10-max"] = np.maximum(b2, S["dt-k10-max"])
    S["b2+dt10-avg(max)"] = 0.5 * (b2 + S["dt-k10-max"])
    S["b2+dt10-avg(mean)"] = 0.5 * (b2 + S["dt-k10-mean"])
    mvec = unit(V["b2"].astype(np.float32) + unit(V["dt"].astype(np.float32).sum(1) / np.maximum(n, 1)[:, None]))
    S["b2+dt10-pooledvec"] = Q @ mvec.T
    S["b2+dt10-top2avg"] = 0.5 * (b2 + S["dt-k10-top2"])
    S["c1+dt10-avg(max)"] = 0.5 * (S["c1"] + S["dt-k10-max"])
    return S


def ranks_of(S, qs, mask=None):
    """rank of best relevant book (1-based) per query in qs; mask = boolean over books usable as candidates."""
    out = {}
    for q in qs:
        s = S[q["qi"]].copy()
        if mask is not None:
            s = np.where(mask, s, -9)
        best = s[q["rel"]].max()
        out[q["id"]] = int((s > best).sum() + 1)
    return out


def summarise(ranks, ids):
    r = [ranks[i] for i in ids]
    n = len(r)
    if not n:
        return None
    return {"n": n, "hit@1": float(np.mean([m_hit(x, 1) for x in r])), "hit@5": float(np.mean([m_hit(x, 5) for x in r])),
            "hit@10": float(np.mean([m_hit(x, 10) for x in r])), "mrr@10": float(np.mean([m_rr(x) for x in r])),
            "median_rank": float(np.median(r))}


def boot_ci(vals, n_boot=4000, seed=7):
    v = np.asarray(vals, dtype=float)
    rng = np.random.default_rng(seed)
    means = v[rng.integers(0, len(v), size=(n_boot, len(v)))].mean(axis=1)
    return [round(float(np.percentile(means, 2.5)), 4), round(float(np.percentile(means, 97.5)), 4)]


def paired(ra, rb, ids, metric, n_boot=4000, seed=7):
    d = np.array([metric(rb[i]) - metric(ra[i]) for i in ids], dtype=float)
    return {"n": len(ids), "diff": round(float(d.mean()), 4), "ci95": boot_ci(d, n_boot, seed), "wins": int((d > 1e-12).sum()),
            "losses": int((d < -1e-12).sum())}


def ids_of(strata):
    want = set(STRATA[strata])
    return [q["id"] for q in QS if q["stratum"] in want]


if __name__ == "__main__":
    for tag in sys.argv[1:]:
        V = np.load(B / f"V_{tag}.npz")
        S = systems(V)
        res = {"tag": tag, "n_queries": {k: len(ids_of(k)) for k in STRATA}, "systems": {}}
        RK = {}
        for name, mat in S.items():
            RK[name] = ranks_of(mat, QS)
            res["systems"][name] = {st: summarise(RK[name], ids_of(st)) for st in STRATA}
            res["systems"][name]["ranks"] = RK[name]
        (RESULTS / "books").mkdir(parents=True, exist_ok=True)
        (RESULTS / "books" / f"eval_{tag}.json").write_text(json.dumps(res))
        print(f"\n== {tag}: queries { {k: len(ids_of(k)) for k in STRATA} }")
        cols = ["known", "sl", "extra-dev", "extra-heldout", "dev (tuning pool)"]
        print(f"{'system':22s} " + " | ".join(f"{c[:14]:>14s} mrr h@5 h@10" for c in cols[:0]) )
        for name in S:
            row = [f"{res['systems'][name][c]['mrr@10']:.3f}/{res['systems'][name][c]['hit@5']:.2f}/{res['systems'][name][c]['hit@10']:.2f}" for c in cols]
            print(f"{name:22s} " + "  ".join(f"{c[:9]}:{r}" for c, r in zip(cols, row)))
