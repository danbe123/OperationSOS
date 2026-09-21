"""Cross-model paired comparisons and the scaling extrapolation, from results/books/eval_<tag>.json.
usage: BOOKS_SUBSET=subset_scale books_cross.py <bge tag> <e5 tag>"""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import RESULTS, m_rr, m_hit   # noqa: E402
import books_eval as be                    # noqa: E402
from books_report import boot              # noqa: E402

bge = json.load(open(RESULTS / "books" / f"eval_{sys.argv[1]}.json")); e5 = json.load(open(RESULTS / "books" / f"eval_{sys.argv[2]}.json"))
STR = ["known", "sl", "extra-dev", "extra-heldout", "everyday dev+heldout excl. plots", "dev (tuning pool)", "ALL"]
PAIRS = [("e5 a vs bge a (model swap only)", (bge, "a"), (e5, "a")),
         ("bge c0 vs bge a", (bge, "a"), (bge, "c0")), ("bge b2+dt10-pooledvec vs bge a", (bge, "a"), (bge, "b2+dt10-pooledvec")),
         ("e5 c0 vs e5 a", (e5, "a"), (e5, "c0")), ("e5 b2+dt10-pooledvec vs e5 a", (e5, "a"), (e5, "b2+dt10-pooledvec")),
         ("e5 b2+dt10-pooledvec vs bge a (both changes)", (bge, "a"), (e5, "b2+dt10-pooledvec")),
         ("e5 c0 vs bge a (model + free text change)", (bge, "a"), (e5, "c0")),
         ("bge c0-gut-only vs bge a", (bge, "a"), (bge, "c0-gut-only")), ("e5 c0-gut-only vs e5 a", (e5, "a"), (e5, "c0-gut-only")),
         ("e5 c0-gut-only vs bge a", (bge, "a"), (e5, "c0-gut-only")), ("e5 pooled-gut-only vs bge a", (bge, "a"), (e5, "pooled-gut-only")),
         ("e5 b2+dt10-pooledvec vs e5 c0", (e5, "c0"), (e5, "b2+dt10-pooledvec")),
         ("e5 b2+dt10-pooledvec vs e5 b2+dt10-avg(max)", (e5, "b2+dt10-avg(max)"), (e5, "b2+dt10-pooledvec"))]
for metric, f in (("MRR@10", m_rr), ("hit@10", lambda r: m_hit(r, 10)), ("hit@5", lambda r: m_hit(r, 5))):
    print(f"\n{metric}, B minus A (95% interval; W/L = queries B does better/worse on)\n")
    print("| comparison | " + " | ".join(STR) + " |\n|---|" + "---|" * len(STR))
    for label, (ra, sa), (rb, sb) in PAIRS:
        cells = []
        for st in STR:
            ids = be.ids_of(st)
            d, lo, hi, w, l = boot([f(rb["systems"][sb]["ranks"][i]) - f(ra["systems"][sa]["ranks"][i]) for i in ids])
            cells.append(f"{d:+.3f} [{lo:+.3f}, {hi:+.3f}]{'*' if lo > 0 or hi < 0 else ''} {w}/{l}")
        print(f"| {label} | " + " | ".join(cells) + " |")
print("\nScaling extrapolation (least-squares line of metric on log10 pool size, pools 1,500 to the whole set; 70,558 = the real library):\n")
for name, res in (("bge", bge), ("e5", e5)):
    for sysn in ("a", "c0", "b2+dt10-pooledvec"):
        for g in ("known", "everyday"):
            for m in ("mrr@10", "hit@10"):
                xs, ys = [], []
                for size, d in res["scaling"].items():
                    xs.append(np.log10(int(size))); ys.append(d[sysn][g][m])
                k, b = np.polyfit(xs, ys, 1)
                print(f"{name} {sysn:20s} {g:9s} {m:7s} at 1.5k {ys[0]:.3f} 5k {ys[2]:.3f} 14k {ys[-1]:.3f} -> 70.5k (extrapolated) {max(0, k*np.log10(70558)+b):.3f}")
