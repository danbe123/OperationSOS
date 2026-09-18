# Semantic Search Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the box's own semantic index without its current 1400-character pre-cut; add a second, approximately-indexed "household" meaning-search collection over Project Gutenberg and Survivor Library that can surface new results the way the box's own library does today; add a third, memory-mapped English Wikipedia vector store used only to re-rank Wikipedia's own keyword hits, never to add new ones; and exclude Wiktionary, Welsh Wikipedia and every StackExchange ZIM from all of it.

**Architecture:** `api/sos/embeddings.py`'s single-collection `Index`/`Semantic` becomes multi-collection: the existing brute-force `Index` (renamed to carry a `collection` name, `docs` unchanged) stays for the box's own ~21,000 passages; a new `ApproxIndex` (hnswlib) holds one vector per book across two ZIMs read directly off disk with `python-libzim` (the same approach `api/sos/books.py` already uses for Gutenberg); a new `WikipediaStore` is a `numpy.memmap` keyed lookup, never a nearest-neighbour search, built once from ~7 million article vectors and consulted only for the small number of articles `search()`'s existing Kiwix fan-out already found by keyword. All three PC-side builds run against a second, CUDA-enabled `llama-server` binary built once in this plan; the box's own always-on embedding service and the dev stack are untouched (CPU-only, exactly as today).

**Tech Stack:** `hnswlib` (new dependency, approximate nearest neighbour, builds from source), `python-libzim` (existing dependency since yesterday's Gutenberg work), `numpy.memmap` (standard library via numpy, already a dependency), a second CUDA-enabled `llama-server` build (this plan's own `cmake -DGGML_CUDA=ON` build, kept separate from the Pi-targeted CPU build already documented in the design spec).

**Spec:** `docs/superpowers/specs/2026-09-18-search-precision-and-semantic-design.md` section 3 (the system this plan extends) and `docs/superpowers/specs/2026-09-14-gutenberg-library-design.md` section 8 (the original phase-2 sketch this superseded once the real ZIM's layout and scale were known). Read both. This plan's four decisions were given directly by the project owner (verified against this real environment before this plan was written, not re-litigated here): rebuild the docs collection at its real safe length; embed Gutenberg and Survivor Library as an approximate-index "household" collection with full add-rows retrieval; embed English Wikipedia only to re-rank its own keyword hits; exclude Wiktionary, Welsh Wikipedia and every StackExchange site from both paths.

## Global Constraints

- British English in every user-facing string and comment: "licence" not "license", "colour" not "color".
- Never write "NOMAD" anywhere.
- No network access from unit tests: every ZIM read goes through a fake `ZimReader`/`open_zim` (the existing `Protocol` in `api/sos/books.py`) or a fixture file, never a real multi-GB ZIM or a real embedding server.
- The box's own `install/systemd/sos-embed.service` and `api/sos/ai_runtime.py`-style dev-profile launcher stay CPU-only (`-ngl` never appears in the always-on box/dev command). GPU offload is a PC-build-only code path, used solely by `sos build-embeddings`'s bulk-build variants.
- Every embedding build writes its output via the existing `write_index`-style rename(2) pattern (`.part` files, `os.replace` into place) — a build that dies partway must never leave a half-written index the API could load.
- A collection's build must be a no-op, not an error, when its source ZIM is absent or unreadable — `sos build-embeddings` (and `sos index`, for anything it touches) must keep going through its other steps either way, exactly as `index_books`/`index_docs` already do.
- `EXCLUDED_ZIMS` (this plan's new exclusion list: `wiktionary_en_all_nopic`, `wikipedia_cy_all_maxi`, and every manifest item id ending `.stackexchange.com_en_all`) must never appear as a source for any embedding collection built by this plan, checked by a real test against the real manifest, not just a hand-written short list that could drift from the manifest.
- Every new manifest item (the household and Wikipedia indices, and the CUDA-build marker if one is recorded) follows the existing `manifest/schema.json` shape: `kind` from its enum, `dest` under the tier root as `<something>/…`, `source.type: "build"`.
- Real, multi-hundred-GB-to-multi-hour operations (the Survivor Library download, the household build, the Wikipedia build) are exercised for real only in this plan's own acceptance task and its own dedicated download/verification steps — every other task's tests run against small fixtures and a fake embedding function, matching the existing `api/tests/test_books.py`/`test_embeddings.py`-style conventions (read whichever of those already exists before writing a new test file, and match its fixture patterns).

---

## File structure

| File | Responsibility |
|---|---|
| `api/sos/embeddings.py` | Tasks 1, 3, 4, 6, 8: full-length passage rebuild, multi-collection `Index`, `ApproxIndex` (hnswlib), `WikipediaStore` (memmap), `EXCLUDED_ZIMS`, the three `build_*` functions |
| `api/sos/cli.py` | Task 2, 6, 8: `build-embeddings` CLI gains the collections it builds, and a `--cuda` (or equivalent) PC-build-time server variant |
| `install/build-llama-cuda.sh` (new) | Task 2: builds the second, CUDA-enabled `llama-server` binary once |
| `manifest/core.json` | Tasks 5, 6, 8: `survivorlibrary.com_en_all` already core (Task 1 of the Gutenberg plan promoted it); new `embeddings-household` and `embeddings-wikipedia` items |
| `api/sos/search.py` | Tasks 7, 9: household fusion (mirrors the existing docs fusion), Wikipedia rerank-only fusion (a new, smaller code path) |
| `api/tests/test_embeddings.py` | Every task: read it first if it exists (it should, from yesterday's build) and extend it; if it does not exist yet, create it matching `test_books.py`'s conventions |
| `api/pyproject.toml` | Task 4: add `hnswlib` |

---

### Task 1: Rebuild the docs collection at its real safe length

**Files:**
- Modify: `api/sos/embeddings.py` (`PASSAGE_CHARS`)
- Test: `api/tests/test_embeddings.py`

**Interfaces:**
- Produces: `PASSAGE_CHARS` set to the real, empirically-determined value (not assumed). No new function signatures — this task is a constant change plus a real rebuild, and exists on its own because it is real, immediate value with zero architecture risk, unlike every later task in this plan.

- [ ] **Step 1: Read the current file in full**

Read `api/sos/embeddings.py` in full (not just the excerpt below) — in particular `passage_text`, `PASSAGE_CHARS`, `SHORTEST_CHARS`, and `embed_batch`'s reactive-shortening fallback, so this task's change is made with the real current code in view, not a paraphrase.

- [ ] **Step 2: Start the real embedding server and determine the real window**

```bash
llama-server -m /home/dan/sos-content/models/embed/bge-small-en-v1.5-q8_0.gguf --embedding --pooling cls -c 512 -ub 512 -b 512 --host 127.0.0.1 --port 8091 -t 4 --no-webui &
sleep 3
```

Then, from a Python shell (`cd api && .venv/bin/python`), embed strings of increasing length built from real passage text (pull a handful of real, long `fts_docs` rows via `sqlite3`, or use any long English prose) and find the length at which the returned vector visibly stops changing as more text is appended (bge-small silently truncates past its window rather than erroring — this is the real signal to look for, not an HTTP error):

```python
import httpx
url = "http://127.0.0.1:8091/embeddings"
base = "The full text of a long document page repeated to build a realistic sample. " * 60
for n in (1200, 1600, 1800, 2000, 2200, 2600, 3000):
    r = httpx.post(url, json={"input": [base[:n]]}, timeout=30).json()
    v = r["data"][0]["embedding"] if isinstance(r, dict) else r[0]["embedding"]
    print(n, v[:3])
```

Record where the first three components of the vector stop changing between consecutive lengths — that is the real character length the model actually reads before silently truncating. Kill the server (`kill %1` in the same shell, or `pgrep -f 'llama-server.*8091'` then `kill <pid>` in a separate command — never put the literal `llama-server` command text in the same shell call as a `pkill`/`kill` targeting it, which matches this project's own already-learned lesson about killing the shell that typed the command).

- [ ] **Step 3: Set `PASSAGE_CHARS` to the real value and update the comment**

In `api/sos/embeddings.py`, change:

```python
PASSAGE_CHARS = 1400      # bge-small reads 512 tokens; a document page averages 2,100 characters, and a
                          # passage heavy with numbers tokenises long, so the cut is well inside the window
```

to the real determined value (write the actual number Step 2 found, and replace the comment's reasoning with what was actually measured, e.g. "bge-small silently truncates past N characters on this build, measured by embedding increasingly long real passages and watching the vector stop changing (see docs/superpowers/plans/2026-09-18-semantic-search-expansion.md Task 1) — this is the real window, not a token:char estimate").

- [ ] **Step 4: Add a regression test pinning the real value**

```python
def test_passage_chars_matches_the_real_measured_window():
    """Not a behavioural test of the model itself (that needs the real server, done once in Task 1's own
    Step 2) -- a tripwire so a future edit to this constant is a deliberate decision, not a typo."""
    from sos.embeddings import PASSAGE_CHARS
    assert PASSAGE_CHARS == <the real value from Step 2>  # replace with the literal number, not a variable
```

- [ ] **Step 5: Run the existing embeddings test suite**

Run: `cd api && .venv/bin/python -m pytest tests/test_embeddings.py -v`
Expected: PASS, including any existing `passage_text` length tests (read them — a test asserting the *old* 1400 cut on a long fixture string needs its expected length updated to the new constant).

- [ ] **Step 6: Rebuild the real docs index**

```bash
export MAMBA_ROOT_PREFIX=$HOME/micromamba && eval "$(micromamba shell hook --shell bash)" 2>/dev/null || true
cd /home/dan/OperationSOS
SOS_CORE=/home/dan/sos-content SOS_STATE=.dev/state api/.venv/bin/sos build-embeddings
```

Expected: `wrote <N> vectors to /home/dan/sos-content/embeddings` where `N` matches the existing ~21,000 passage count (this task changes passage *length*, not which rows are embedded — the count should be unchanged from before this task).

- [ ] **Step 7: Commit**

```bash
git add api/sos/embeddings.py api/tests/test_embeddings.py
git commit -m "feat(embeddings): rebuild the docs index at its real measured window, not a 1400-char guess"
```

---

### Task 2: A second, CUDA-enabled `llama-server` for PC-side bulk embedding

**Files:**
- Create: `install/build-llama-cuda.sh`
- Modify: `api/sos/embeddings.py` (`server_command` gains a PC-build variant)
- Test: `api/tests/test_embeddings.py`

**Interfaces:**
- Produces: `server_command(settings: Settings, cuda: bool = False) -> list[str]` — the existing signature gains one keyword argument, defaulting to today's exact CPU-only behaviour (`cuda=False`) so every existing caller (the box's systemd unit generation, `ai_runtime`-style dev launch, if either calls this function — check) is unaffected. `cuda=True` adds `-ngl 99` and points `-m`/the binary at the CUDA build. A new `CUDA_LLAMA_SERVER` path constant (or a `Settings` field, whichever this file's existing convention favours — check `config.py` for how `embed_model_path`-style computed paths are expressed) at `~/.local/bin/llama-server-cuda` (a name distinct from the plain `llama-server` already on PATH, so neither shadows the other).

- [ ] **Step 1: Confirm the plain binary really has no CUDA support**

```bash
llama-server --version
ldd "$(which llama-server)" | grep -i cuda
```

Expected: version string with no CUDA mention, and no `libcuda`/`libcudart` in the linked libraries — confirms a second binary is genuinely needed, not redundant. (Already confirmed once while writing this plan; re-confirm as the first real step of implementing it, since the installed binary could have changed.)

- [ ] **Step 2: Write the CUDA build script**

```bash
#!/usr/bin/env bash
# Builds a second, CUDA-enabled llama-server for PC-side bulk embedding builds only (sos build-embeddings's
# household/Wikipedia collections). The box's own build stays the existing CPU-only native-ARM one -- this
# script never touches /usr/local/bin/llama-server or the systemd unit.
set -euo pipefail
SRC=${LLAMA_CPP_SRC:-$HOME/llama.cpp}
OUT=$HOME/.local/bin/llama-server-cuda
if [ ! -d "$SRC" ]; then
  echo "build-llama-cuda: cloning llama.cpp (see install/versions.env for the pinned tag)" >&2
  git clone --depth 1 --branch "$(grep '^LLAMA_CPP_TAG=' /home/dan/OperationSOS/install/versions.env | cut -d= -f2)" \
    https://github.com/ggml-org/llama.cpp "$SRC"
fi
cmake -S "$SRC" -B "$SRC/build-cuda" -DGGML_CUDA=ON -DLLAMA_BUILD_TESTS=OFF -DCMAKE_BUILD_TYPE=Release
cmake --build "$SRC/build-cuda" --config Release -j"$(nproc)" --target llama-server
mkdir -p "$(dirname "$OUT")"
cp "$SRC/build-cuda/bin/llama-server" "$OUT"
echo "build-llama-cuda: built $OUT"
"$OUT" --version
```

- [ ] **Step 3: Run it**

Run: `bash install/build-llama-cuda.sh`
Expected: builds successfully (a CUDA-capable `nvcc` toolchain must be present — if `cmake` fails to find CUDA, this environment needs the CUDA toolkit installed first; check `nvcc --version` before running, and if absent, install it via whatever this environment's own package manager convention already is — do not attempt a sudo-less workaround, ask if genuinely blocked here) and prints a version string; then `~/.local/bin/llama-server-cuda --version` runs standalone.

- [ ] **Step 4: Confirm real GPU offload**

```bash
~/.local/bin/llama-server-cuda -m /home/dan/sos-content/models/embed/bge-small-en-v1.5-q8_0.gguf --embedding --pooling cls -c 512 -ngl 99 --host 127.0.0.1 --port 8092 --no-webui &
sleep 3
nvidia-smi --query-compute-apps=pid,used_memory --format=csv
curl -s http://127.0.0.1:8092/health
```

Expected: the `llama-server-cuda` process appears in `nvidia-smi`'s compute-apps list with nonzero VRAM, and `/health` returns 200. Stop it (`pgrep -f 'llama-server-cuda.*8092'`, then `kill <pid>` as its own command).

- [ ] **Step 5: Write the failing test**

```python
def test_server_command_cuda_variant_adds_gpu_layers_and_the_cuda_binary(ai_settings):
    from sos.embeddings import server_command
    cpu_cmd = server_command(ai_settings)
    assert "-ngl" not in cpu_cmd  # today's exact behaviour, unchanged
    gpu_cmd = server_command(ai_settings, cuda=True)
    assert "-ngl" in gpu_cmd and gpu_cmd[gpu_cmd.index("-ngl") + 1] == "99"
    assert str(gpu_cmd[gpu_cmd.index("-m") - 1] if False else gpu_cmd[0]).endswith("llama-server-cuda")
```

(Clean up the odd `if False else` placeholder above before finishing this step — it was a slip while drafting; the real assertion should simply check `gpu_cmd[0]` is the CUDA binary path, since `server_command`'s existing return shape puts the binary first per the code already read in Task 1 Step 1 — confirm the exact index against the real function before finalising this test.)

- [ ] **Step 6: Implement**

In `api/sos/embeddings.py`, change `server_command`'s signature and body to accept `cuda: bool = False`, returning the CUDA binary path and appending `"-ngl", "99"` when true, otherwise identical to today's return value. Add the path constant near the top of the file alongside the other module constants:

```python
CUDA_LLAMA_SERVER = Path.home() / ".local" / "bin" / "llama-server-cuda"
```

- [ ] **Step 7: Run the test**

Run: `cd api && .venv/bin/python -m pytest tests/test_embeddings.py -k cuda -v`
Expected: PASS.

- [ ] **Step 8: Run the full backend suite**

Run: `cd api && .venv/bin/python -m pytest -q`
Expected: all pass, no regressions to the existing `server_command`/`build_cli` callers.

- [ ] **Step 9: Commit**

```bash
git add install/build-llama-cuda.sh api/sos/embeddings.py api/tests/test_embeddings.py
git commit -m "feat(embeddings): a second, CUDA-enabled llama-server for PC-side bulk embedding builds"
```

---

### Task 3: Multi-collection `Index`

**Files:**
- Modify: `api/sos/embeddings.py` (`Index`, `write_index`, `Index.load`)
- Test: `api/tests/test_embeddings.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `Index.load(folder: Path, collection: str) -> Optional[Index]` (was `Index.load(folder)`, implicitly always `"docs"`); `write_index(folder: Path, collection: str, vectors, keys, meta)` (was `write_index(folder, vectors, keys, meta)`). File names become `f"{collection}.f16.bin"` etc. — `collection="docs"` reproduces today's exact `docs.f16.bin`/`docs.ids`/`docs.meta.json` names, so the existing on-disk index at `/home/dan/sos-content/embeddings/` keeps working with zero migration. Later tasks (4, 6, 8) add `collection="household"` and the Wikipedia store (which does not use this class at all — see Task 8).

- [ ] **Step 1: Read the current `Index`/`write_index`/`build` in full**

Already read once while planning this (the file is short, 323 lines) — re-read it now as the first real step of this task, since Tasks 1 and 2 have already changed two of its constants and one of its functions.

- [ ] **Step 2: Write the failing test**

```python
def test_index_load_and_write_are_scoped_by_collection_name(tmp_path):
    from sos.embeddings import Index, write_index
    import numpy as np
    vectors = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float32)
    write_index(tmp_path, "household", vectors, ["book:1", "book:2"], {"count": 2})
    assert (tmp_path / "household.f16.bin").exists() and (tmp_path / "household.ids").exists()
    assert not (tmp_path / "docs.f16.bin").exists()
    idx = Index.load(tmp_path, "household")
    assert idx is not None and len(idx) == 2
    assert Index.load(tmp_path, "docs") is None  # a different collection name, nothing written for it
```

Note: `DIMS` is a module constant (384) that the real `Index.load` uses to validate the vector-file size against the key count — the test above uses 3-dimensional vectors for brevity, which will fail that validation as written. Either monkeypatch `sos.embeddings.DIMS` to `3` for the duration of this test, or use real 384-dimensional arrays (`np.random.rand(2, 384).astype(np.float32)`) — read `Index.load`'s real validation line before choosing, and prefer whichever keeps the test fast and clear.

- [ ] **Step 3: Run to verify failure**

Run: `cd api && .venv/bin/python -m pytest tests/test_embeddings.py -k collection_name -v`
Expected: FAIL — `write_index() missing 1 required positional argument: 'collection'` (or similar, depending on argument order chosen).

- [ ] **Step 4: Implement**

In `api/sos/embeddings.py`:

```python
def write_index(folder: Path, collection: str, vectors: np.ndarray, keys: list[str], meta: dict) -> None:
    """The three files for one named collection, written beside their finals and moved into place
    together, so a build that dies halfway leaves the old index whole."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    parts = []
    for name, data in ((f"{collection}.f16.bin", np.asarray(vectors, dtype=np.float16).tobytes()),
                       (f"{collection}.ids", ("\n".join(keys) + "\n").encode("utf-8")),
                       (f"{collection}.meta.json", json.dumps(meta, indent=1).encode("utf-8"))):
        part = folder / (name + ".part")
        part.write_bytes(data)
        parts.append((part, folder / name))
    for part, final in parts:
        os.replace(part, final)
```

Delete the old module-level `VECTORS = "docs.f16.bin"` / `KEYS = "docs.ids"` / `META = "docs.meta.json"` constants (Task 6 will need equivalent per-collection names, but as computed strings, not fixed constants) and update `Index.load` to take `collection: str` and build the three paths the same way `write_index` now does:

```python
@classmethod
def load(cls, folder: Path, collection: str) -> Optional["Index"]:
    folder = Path(folder)
    vec_path, key_path, meta_path = folder / f"{collection}.f16.bin", folder / f"{collection}.ids", folder / f"{collection}.meta.json"
    if not (vec_path.is_file() and key_path.is_file()):
        return None
    keys = [line for line in key_path.read_text(encoding="utf-8").split("\n") if line]
    raw = np.fromfile(vec_path, dtype=np.float16)
    if len(keys) == 0 or raw.size != len(keys) * DIMS:
        log.warning("embeddings: %s does not match %s (%d keys, %d values)", vec_path.name, key_path.name, len(keys), raw.size)
        return None
    meta = {}
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except ValueError:
            meta = {}
    return cls(raw.reshape(len(keys), DIMS), keys, meta)
```

Update every call site this file's own `build()` and `Semantic.index()` make to `write_index(...)`/`Index.load(...)` to pass `"docs"` explicitly (grep the file for `write_index(` and `Index.load(` after this change — there should be exactly the two call sites already in `build()` and `Semantic.index()`).

- [ ] **Step 5: Run the test**

Run: `cd api && .venv/bin/python -m pytest tests/test_embeddings.py -k collection_name -v`
Expected: PASS.

- [ ] **Step 6: Run the full suite**

Run: `cd api && .venv/bin/python -m pytest -q`
Expected: all pass — in particular `Semantic.index()`'s existing behaviour (loading the `"docs"` collection) must be bit-for-bit unchanged from before this task; the real on-disk `/home/dan/sos-content/embeddings/docs.f16.bin` written by Task 1 must still load.

- [ ] **Step 7: Commit**

```bash
git add api/sos/embeddings.py api/tests/test_embeddings.py
git commit -m "refactor(embeddings): Index/write_index are scoped by collection name, docs unchanged on disk"
```

---

### Task 4: `ApproxIndex` (hnswlib) for the household collection

**Files:**
- Modify: `api/pyproject.toml` (add `hnswlib`)
- Modify: `api/sos/embeddings.py` (new `ApproxIndex` class)
- Test: `api/tests/test_embeddings.py`

**Interfaces:**
- Produces: `ApproxIndex` with the same public shape `Index` already has where it matters to a caller: `__len__`, `.search(query: np.ndarray, k: int) -> list[tuple[str, float]]`, plus `ApproxIndex.build(vectors: np.ndarray, keys: list[str]) -> "ApproxIndex"` and `ApproxIndex.save(folder: Path, collection: str)` / `ApproxIndex.load(folder: Path, collection: str) -> Optional["ApproxIndex"]`. `search()`'s return score is a cosine similarity in `[-1, 1]` exactly like `Index.search`'s, so `Semantic`/`search.py` can treat either kind of index identically once Task 6 wires it in.

- [ ] **Step 1: Add the dependency**

In `api/pyproject.toml`, add `"hnswlib>=0.8"` to the dependencies list (matching Task 4 of the Gutenberg plan's pattern for adding `ijson`). Run: `cd api && .venv/bin/pip install "hnswlib>=0.8"` — this builds from source (confirmed earlier: no prebuilt wheel for this platform), so it needs a C++ compiler; if it fails, install build-essential (or this environment's equivalent) first rather than working around the failure.

- [ ] **Step 2: Write the failing test**

```python
def test_approx_index_round_trips_and_finds_the_nearest_neighbour(tmp_path):
    from sos.embeddings import ApproxIndex
    import numpy as np
    rng = np.random.default_rng(0)
    vectors = rng.normal(size=(50, 384)).astype(np.float32)
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    keys = [f"book:{i}" for i in range(50)]
    idx = ApproxIndex.build(vectors, keys)
    assert len(idx) == 50
    hits = idx.search(vectors[7], k=1)
    assert hits[0][0] == "book:7" and hits[0][1] > 0.99  # a vector is its own nearest neighbour
    idx.save(tmp_path, "household")
    assert (tmp_path / "household.hnsw").exists() and (tmp_path / "household.ids").exists()
    reloaded = ApproxIndex.load(tmp_path, "household")
    assert reloaded is not None and len(reloaded) == 50
    assert reloaded.search(vectors[7], k=1)[0][0] == "book:7"


def test_approx_index_load_returns_none_when_absent(tmp_path):
    from sos.embeddings import ApproxIndex
    assert ApproxIndex.load(tmp_path, "household") is None
```

- [ ] **Step 3: Run to verify failure**

Run: `cd api && .venv/bin/python -m pytest tests/test_embeddings.py -k approx_index -v`
Expected: FAIL — `ImportError` or `AttributeError: module 'sos.embeddings' has no attribute 'ApproxIndex'`.

- [ ] **Step 4: Implement**

```python
class ApproxIndex:
    """One vector per book/article across the household collection (Gutenberg, Survivor Library):
    tens of thousands of vectors, an approximate (not exact) nearest-neighbour search via hnswlib,
    because the collection is expected to keep growing and a brute-force scan is the wrong shape for
    that even though it would still be fast today at this size. cosine similarity, matching Index's
    contract exactly, so search.py's fusion code does not need to know which kind of index it has."""

    def __init__(self, hnsw, keys: list[str]):
        self._hnsw = hnsw
        self.keys = keys

    def __len__(self) -> int:
        return len(self.keys)

    @classmethod
    def build(cls, vectors: np.ndarray, keys: list[str], ef_construction: int = 200, m: int = 16) -> "ApproxIndex":
        import hnswlib
        vectors = np.asarray(vectors, dtype=np.float32)
        hnsw = hnswlib.Index(space="cosine", dim=DIMS)
        hnsw.init_index(max_elements=len(keys), ef_construction=ef_construction, M=m)
        hnsw.add_items(vectors, np.arange(len(keys)))
        hnsw.set_ef(max(50, ef_construction // 2))
        return cls(hnsw, keys)

    def save(self, folder: Path, collection: str) -> None:
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        hnsw_part = folder / f"{collection}.hnsw.part"
        self._hnsw.save_index(str(hnsw_part))
        ids_part = folder / f"{collection}.ids.part"
        ids_part.write_text("\n".join(self.keys) + "\n", encoding="utf-8")
        os.replace(hnsw_part, folder / f"{collection}.hnsw")
        os.replace(ids_part, folder / f"{collection}.ids")

    @classmethod
    def load(cls, folder: Path, collection: str) -> Optional["ApproxIndex"]:
        import hnswlib
        folder = Path(folder)
        hnsw_path, ids_path = folder / f"{collection}.hnsw", folder / f"{collection}.ids"
        if not (hnsw_path.is_file() and ids_path.is_file()):
            return None
        keys = [line for line in ids_path.read_text(encoding="utf-8").split("\n") if line]
        hnsw = hnswlib.Index(space="cosine", dim=DIMS)
        hnsw.load_index(str(hnsw_path), max_elements=len(keys))
        hnsw.set_ef(max(50, len(keys) // 2) if len(keys) < 100 else 100)
        return cls(hnsw, keys)

    def search(self, query: np.ndarray, k: int = 20) -> list[tuple[str, float]]:
        if len(self.keys) == 0:
            return []
        k = max(1, min(k, len(self.keys)))
        labels, distances = self._hnsw.knn_query(np.asarray(query, dtype=np.float32).reshape(1, -1), k=k)
        # hnswlib's "cosine" space returns a distance (1 - cosine); this class's contract is a similarity.
        return [(self.keys[i], float(1.0 - d)) for i, d in zip(labels[0], distances[0])]
```

- [ ] **Step 5: Run the tests**

Run: `cd api && .venv/bin/python -m pytest tests/test_embeddings.py -k approx_index -v`
Expected: PASS.

- [ ] **Step 6: Run the full suite**

Run: `cd api && .venv/bin/python -m pytest -q`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add api/pyproject.toml api/sos/embeddings.py api/tests/test_embeddings.py
git commit -m "feat(embeddings): ApproxIndex, an hnswlib-backed collection for the household shelf"
```

---

### Task 5: Fetch Survivor Library; check both ZIMs' real per-book text

**Files:**
- Modify: nothing in `api/` (a diagnostic and a download, mirroring Task 2 of the Gutenberg plan)
- Modify: `docs/app-completion.md` (record the real finding)

**Interfaces:**
- Produces: the real Survivor Library ZIM at `/home/dan/sos-content/zim/survivorlibrary.com_en_all.zim`, checksum-verified; and a settled answer to "does each ZIM's `.html`/`.epub`/text entry actually carry readable text this plan can embed, or is a meaningful fraction of Survivor Library's 'scanned pre-1920s books' image-only with no OCR text layer inside the ZIM?" — Task 6 is written against whichever answer this task finds. If a real fraction of Survivor Library has no usable text, Task 6 must skip those books (a no-op per book, not a build failure), exactly as `sos.buildbooks.convert_one` already skips a PDF with zero extractable text elsewhere in this codebase.

- [ ] **Step 1: Resolve and download the real ZIM**

```bash
curl -s "https://opds.library.kiwix.org/catalog/v2/entries?name=survivorlibrary.com_en_all&count=1" | grep -A1 "<link rel=\"http://opds-spec.org/acquisition"
```

Read the `href` and `length` attributes from the result (mirroring exactly how the Gutenberg ZIM was resolved earlier this session: an OPDS entry pointing at a `.zim.meta4` metalink). Fetch that `.meta4`, extract its real mirror `<url>` entries and `sha-256` hash (same approach as before: `grep -A2 "<url"` and `grep "sha-256"` on the metalink XML), then:

```bash
mkdir -p /home/dan/sos-content/zim
nohup /home/dan/micromamba/envs/sos-maps/bin/aria2c -x 8 -s 8 -k 1M -c --auto-file-renaming=false --allow-overwrite=true \
  --checksum=sha-256=<the real hash from the meta4> \
  -d /home/dan/sos-content/zim -o survivorlibrary.com_en_all.zim \
  <mirror-url-1> <mirror-url-2> \
  > /tmp/survivorlibrary-download.log 2>&1 &
disown
```

This is a ~252GB download; it will take a real, possibly multi-hour amount of time depending on real mirror throughput (the Gutenberg download earlier this session ran at roughly 17-26 MiB/s against its mirrors — expect a comparable order of magnitude here, but do not assume a specific duration; check the aria2c log's own ETA once it has been running a few minutes). Let it run in the background while later steps of this task (and, once this task is otherwise done, later tasks that do not need this specific file) continue.

- [ ] **Step 2: Check the real per-book text in the Gutenberg ZIM (already downloaded)**

```bash
zimdump list /home/dan/sos-content/zim/gutenberg_en_all.zim 2>&1 | grep '\.html$' | head -5
zimdump show --url /home/dan/sos-content/zim/gutenberg_en_all.zim --path "<one real .html path from above>" 2>&1 | head -c 2000
```

Confirm the `.html` entry for a real book contains actual prose (not just a cover image or a stub page) — this is the entry `api/sos/books.py`'s `LibzimReader`/`open_zim` pattern already reads successfully for the catalogue (per yesterday's work, per the `gutenberg-zim-layout` finding: `<Title>.<id>.html` is a real entry name in this ZIM's actual old-JS layout). Record the real HTML-to-plain-text approach this plan will reuse: `api/sos/kiwix.py`'s `extract_text(html_text: str) -> list[str]` (already used elsewhere in this codebase for Kiwix HTML) — confirm by running it against the real fetched HTML in a Python shell and checking the output looks like real prose, not boilerplate.

- [ ] **Step 3: Check the real per-book text in Survivor Library once the download completes**

Wait for Step 1's download to finish and its checksum to verify (poll `tail -f /tmp/survivorlibrary-download.log` or check periodically — do not block this task indefinitely on it if other tasks are ready to proceed; come back to this step once the file is confirmed complete). Then:

```bash
sha256sum /home/dan/sos-content/zim/survivorlibrary.com_en_all.zim   # must match the real hash from Step 1
zimdump list /home/dan/sos-content/zim/survivorlibrary.com_en_all.zim 2>&1 | head -30
```

Identify the real entry-naming convention for this ZIM (it may differ from Gutenberg's — do not assume the same `<Title>.<id>.html` shape). Pick 5-10 real entries at random across the list and inspect their content the same way as Step 2. Specifically check whether any of them are page-image-only (a `.jpg`/`.png`-heavy entry with little or no extractable text) — "scanned pre-1920s books" in this ZIM's own manifest description is a real signal this might be common; confirm or rule it out by looking at real entries, not by assuming.

- [ ] **Step 4: Record the finding**

Append to `docs/app-completion.md` (dated today): the real Survivor Library ZIM's entry-naming convention, whether its books carry real extractable text or are commonly image-only (and if the latter, roughly what fraction of the sample checked in Step 3 was affected), and confirmation that Gutenberg's `.html` entries are real prose. This is the reference Task 6 is implemented against.

- [ ] **Step 5: Commit**

```bash
git add docs/app-completion.md
git commit -m "docs: record the real Survivor Library ZIM layout and both collections' text availability"
```

---

### Task 6: The household embedding build

**Files:**
- Modify: `api/sos/embeddings.py` (`build_household`, `HOUSEHOLD_ZIMS`)
- Modify: `api/sos/cli.py` (`cmd_build_embeddings` builds both collections)
- Modify: `manifest/core.json` (`embeddings-household` item)
- Test: `api/tests/test_embeddings.py`, fixture ZIM reader

**Interfaces:**
- Consumes: `ApproxIndex.build`/`.save` (Task 4), `LibzimReader`/`open_zim`/the `ZimReader` `Protocol` (existing, `api/sos/books.py` — import it, do not redefine it), `embed_batch`/`embed_sync` (existing).
- Produces: `HOUSEHOLD_ZIMS = ("gutenberg_en_all", "survivorlibrary.com_en_all")`; `build_household(conn, settings, embed, out=print) -> dict` — same shape as the existing `build()` (renamed nowhere; a second, parallel top-level function, since the two collections read from entirely different sources — a SQL table for docs, ZIMs directly for household), writing the `"household"` collection via `ApproxIndex`.

- [ ] **Step 1: Write the fixture ZIM reader and books**

Read `api/tests/test_books.py`'s existing fake-`ZimReader` pattern (it already fakes `open_zim` for `index_books`'s tests) and reuse the identical style. Add to `api/tests/test_embeddings.py`:

```python
class FakeHouseholdZim:
    """A tiny fake ZIM: a few books with real prose, one with no usable text (an image-only scan)."""

    def __init__(self, books: dict[str, str]):
        self._books = books

    def read(self, path: str) -> bytes | None:
        text = self._books.get(path)
        return text.encode("utf-8") if text is not None else None

    def has(self, path: str) -> bool:
        return path in self._books


GUTENBERG_BOOKS = {
    "Pride and Prejudice.1.html": "<html><body><h1>Pride and Prejudice</h1><p>It is a truth universally "
        "acknowledged, that a single man in possession of a good fortune, must be in want of a wife.</p></body></html>",
    "Moby-Dick.2.html": "<html><body><h1>Moby-Dick</h1><p>Call me Ishmael. Some years ago, having little or "
        "no money in my purse, I thought I would sail about a little.</p></body></html>",
}
SURVIVOR_BOOKS = {
    "Blacksmithing.10.html": "<html><body><h1>Blacksmithing</h1><p>The forge must be built of firebrick, "
        "and the bellows arranged so that a steady draught reaches the coals.</p></body></html>",
    "Scanned Plate 12.11.html": "<html><body><img src=\"page.jpg\"/></body></html>",  # no real text -- skip it
}
```

- [ ] **Step 2: Write the failing test**

```python
def test_build_household_embeds_real_text_and_skips_image_only_entries(tmp_path):
    from sos.embeddings import build_household, ApproxIndex

    def fake_open_zim(path):
        return FakeHouseholdZim(GUTENBERG_BOOKS if "gutenberg" in str(path) else SURVIVOR_BOOKS)

    def fake_embed(texts):
        import numpy as np
        return np.eye(len(texts), 384, dtype=np.float32)[:, :384]  # deterministic, distinct per row

    class FakeSettings:
        embeddings_dir = tmp_path

    result = build_household(
        conn=None, settings=FakeSettings(), embed=fake_embed,
        zim_paths={"gutenberg_en_all": tmp_path / "g.zim", "survivorlibrary.com_en_all": tmp_path / "s.zim"},
        open_zim=fake_open_zim, out=lambda *a: None)
    assert result["count"] == 3  # two Gutenberg books + one real Survivor Library book, the image-only one skipped
    idx = ApproxIndex.load(tmp_path, "household")
    assert idx is not None and len(idx) == 3
    assert any("Blacksmithing" in k for k in idx.keys)
    assert not any("Scanned Plate" in k for k in idx.keys)
```

The exact `zim_paths`/`open_zim` parameter shape above is this task's own design choice — a real implementation needs to get each collection's real ZIM path from `library_items.local_path` the way `index_books` already does (read that function again, in `api/sos/books.py`, for the exact query), rather than a hand-passed dict; adjust this test to match once `build_household`'s real signature is written in Step 4, keeping the same *behaviour* (fake ZIMs in, no real network or real 200+GB file touched).

- [ ] **Step 3: Run to verify failure**

Run: `cd api && .venv/bin/python -m pytest tests/test_embeddings.py -k build_household -v`
Expected: FAIL — `ImportError`.

- [ ] **Step 4: Implement `build_household`**

```python
HOUSEHOLD_ZIMS = ("gutenberg_en_all", "survivorlibrary.com_en_all")
HOUSEHOLD_TEXT_CHARS = PASSAGE_CHARS  # the same real safe window Task 1 measured -- one model, one window


def _household_entries(reader, zim_id: str) -> list[tuple[str, str, str]]:
    """(key, title, text) for every real-text entry this ZIM's reader can list. Reuses whatever real entry
    enumeration api/sos/books.py's LibzimReader/Archive wrapper already exposes for walking a ZIM's entries
    -- read that file's real Archive-iteration code (used by index_books to walk 70,000+ entries) before
    writing this, rather than inventing a second way to list a ZIM's paths."""
    raise NotImplementedError  # replaced by the real body once Task 5's real entry-naming finding is in hand


def build_household(conn, settings: Settings, embed: Callable[[list[str]], np.ndarray],
                    open_zim=None, out: Callable = print) -> dict:
    from sos.books import open_zim as real_open_zim
    open_zim = open_zim or real_open_zim
    keys: list[str] = []
    chunks: list[np.ndarray] = []
    t0 = time.perf_counter()
    total_seen = total_skipped = 0
    for zim_id in HOUSEHOLD_ZIMS:
        row = conn.execute("SELECT available, local_path FROM library_items WHERE id=?", (zim_id,)).fetchone()
        if row is None or not row["available"] or not row["local_path"]:
            out(f"household: {zim_id} is not on the box; skipped")
            continue
        reader = open_zim(Path(row["local_path"]))
        entries = _household_entries(reader, zim_id)
        for start in range(0, len(entries), BATCH):
            batch = entries[start:start + BATCH]
            texts, batch_keys = [], []
            for key, title, text in batch:
                total_seen += 1
                plain = " ".join(_extract_plain_text(text))[:HOUSEHOLD_TEXT_CHARS]
                if len(plain) < SHORTEST_CHARS:
                    total_skipped += 1
                    continue
                texts.append(f"{title}. {plain}")
                batch_keys.append(key)
            if not texts:
                continue
            chunks.append(embed_batch(embed, texts))
            keys.extend(batch_keys)
        out(f"household: {zim_id} done, {len(keys)} books so far")
    vectors = np.concatenate(chunks) if chunks else np.zeros((0, DIMS), dtype=np.float32)
    if keys:
        idx = ApproxIndex.build(vectors, keys)
        idx.save(settings.embeddings_dir, "household")
    meta = {"model": settings.embed_model, "dims": DIMS, "count": len(keys), "seen": total_seen,
            "skipped_no_text": total_skipped, "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    (Path(settings.embeddings_dir) / "household.meta.json.part").write_text(json.dumps(meta, indent=1))
    os.replace(Path(settings.embeddings_dir) / "household.meta.json.part", Path(settings.embeddings_dir) / "household.meta.json")
    out(f"household: wrote {len(keys)} vectors ({time.perf_counter() - t0:.0f}s, {total_skipped} skipped for no usable text)")
    return meta
```

Two things in the sketch above are deliberately left for the real implementation, not placeholders to skip: `_household_entries` must be written against Task 5's real finding of how each ZIM's entries are actually named and enumerated (read `api/sos/books.py`'s real `Archive`-walking code — `LibzimReader` wraps `libzim.reader.Archive`, which has its own real iteration API; use it, do not invent a parallel one), and `_extract_plain_text` should simply be `api/sos/kiwix.py`'s existing `extract_text` (import it) unless Task 5 found real reasons it needs adapting for these ZIMs' specific HTML shape.

- [ ] **Step 5: Run the test**

Run: `cd api && .venv/bin/python -m pytest tests/test_embeddings.py -k build_household -v`
Expected: PASS after `_household_entries` is filled in for real.

- [ ] **Step 6: Wire into `sos build-embeddings`**

In `api/sos/cli.py`'s `cmd_build_embeddings`, after the existing `build(...)` call for the docs collection, add a call to `build_household(conn, settings, embed_fn)` using the same embed function/connection already in scope (read the function's current body first — do not open a second connection or start a second server).

- [ ] **Step 7: Add the manifest item**

In `manifest/core.json`, add a new line (matching the file's one-object-per-line convention, and `embeddings-docs`'s real shape read earlier) for `embeddings-household`, `kind: "dir"`, `category: "ai"`, `dest: "embeddings"` is already used by `embeddings-docs` — check whether `dest` needs to be a distinct subpath (e.g. the household files live in the same `core/embeddings/` folder as `docs.f16.bin`, so `dest: "embeddings"` for both may be correct as a shared directory item, or each collection may need its own manifest entry pointing at its own specific files — read `manifest/schema.json`'s `dest`-uniqueness rule and `sos.manifest.validate_manifests`'s duplicate-dest check before deciding; if `dest` must be unique per item, use `dest: "embeddings/household.hnsw"` naming the primary file, following whatever convention least confuses `sos sync`'s existing dest-resolution for a multi-file `dir`-kind item).

- [ ] **Step 8: Run the manifest validator and full suite**

Run: `SOS_PLAYBOOKS_DIR=playbooks SOS_MANIFEST_DIR=manifest api/.venv/bin/sos validate-playbooks --all-scenarios` and `cd api && .venv/bin/python -m pytest -q`
Expected: both pass.

- [ ] **Step 9: Commit**

```bash
git add api/sos/embeddings.py api/sos/cli.py manifest/core.json api/tests/test_embeddings.py
git commit -m "feat(embeddings): build_household embeds Gutenberg and Survivor Library into an hnswlib index"
```

---

### Task 7: Household fusion in search

**Files:**
- Modify: `api/sos/search.py`
- Modify: `api/sos/embeddings.py` (`Semantic` gains the household collection)
- Test: `api/tests/test_search.py`

**Interfaces:**
- Consumes: `ApproxIndex.load`/`.search` (Task 4), the existing `Semantic.query`-style pattern.
- Produces: `Semantic` exposes a second query method (or an optional `collection` parameter on the existing one — pick whichever keeps `search.py`'s call sites clearest, and be consistent with Task 9's Wikipedia addition, which needs its own distinct code path regardless since it is rerank-only, not add-rows). Search results with `source: "household"` when a household book is surfaced by meaning alone or lifted because the words already found it.

- [ ] **Step 1: Extend `Semantic` to load the household collection**

In `api/sos/embeddings.py`'s `Semantic` class, add a second cached index (mirroring `self._index`/`self._stamp`/`self._checked` for `"docs"`) for `"household"`, loaded via `ApproxIndex.load` instead of `Index.load`. Add `async def query_household(self, q: str, k: int = 20) -> list[tuple[str, float]]`, identical in shape to the existing `query` but against the household index. Bump `self.generation` on either collection's reload, matching today's cache-invalidation contract (`search.py`'s cache keys on `Semantic.generation` as a whole, so either collection changing should still invalidate it).

- [ ] **Step 2: Write the failing test**

Read `api/tests/test_search.py`'s existing semantic-fusion tests (there should be at least one exercising the docs collection's add-rows behaviour, from yesterday's build) and mirror its fixture-setup style exactly for this test:

```python
def test_search_household_book_found_by_meaning_gets_the_books_group_via_meaning(client, monkeypatch):
    # Mirror whatever fixture/mock this file's existing docs-semantic test uses to fake Semantic.query's
    # return value and the household books table's rows, adapted to household/ApproxIndex instead.
    ...
    r = client.get("/api/search", params={"q": "a whaling voyage"})
    hits = [x for x in r.json()["results"] if x["source"] == "household"]
    assert hits and hits[0].get("via") == "meaning"
```

Fill in the fixture setup by reading the real existing docs-semantic test first — this plan does not repeat its exact mechanics here because they must match that test's real, current fixture shape (a `monkeypatch`/`unittest.mock` on `Semantic.query`, or a fake embed server — whichever the existing test already uses) rather than a second, divergent style.

- [ ] **Step 3: Run to verify failure**

Run: `cd api && .venv/bin/python -m pytest tests/test_search.py -k household -v`
Expected: FAIL.

- [ ] **Step 4: Add the household fusion block to `search()`**

Read the existing docs-collection fusion block in `api/sos/search.py` (already quoted in full while planning this, the block starting `if semantic is not None:` through the `for url, cos in near:` loop) and add a second, parallel block immediately after it, querying `books`/the household ZIM ids instead of `fts_docs`:

```python
if semantic is not None:
    try:
        household_near = await semantic.query_household(q, SEMANTIC_K)
    except Exception:
        household_near = []
    household_near = [(key, cos) for key, cos in household_near if cos >= SEMANTIC_MIN]
    if household_near:
        by_key = {r["url"]: r for r in results if r["source"] == "household"}
        for key, cos in household_near:
            zim, _, book_id = key.partition(":")
            row = conn.execute("SELECT title, author FROM books WHERE zim=? AND id=?", (zim, book_id)).fetchone()
            if row is None or cos < SEMANTIC_FLOOR[(key in by_key, False)]:
                continue
            url = f"/book/gutenberg/{book_id}" if zim == "gutenberg_en_all" else f"/read/{zim}/{key}"
            if key in by_key:
                by_key[key]["score"] += SEMANTIC_WEIGHT * min(1.0, (cos - SEMANTIC_MIN) / (SEMANTIC_CEIL - SEMANTIC_MIN))
                continue
            results.append({"source": "household", "badge": "Books", "title": row["title"],
                            "snippet": row["author"] or "", "url": url,
                            "score": SEMANTIC_WEIGHT * min(1.0, (cos - SEMANTIC_MIN) / (SEMANTIC_CEIL - SEMANTIC_MIN)),
                            "kind": "book", "_cat": "household", "via": "meaning"})
```

The `zim, _, book_id = key.partition(":")` line assumes `ApproxIndex`'s keys are written as `"<zim>:<id>"` — confirm this matches the real key format `build_household` actually writes in Task 6 (adjust either this parsing or that writing so they agree; they must use the same separator and field order). The `SEMANTIC_FLOOR` dict's existing keys are `(found_by_words, is_doc_page)` tuples (read its real current definition in `search.py`) — a household book is never a "doc page" in the existing sense, so `False` is right for the second element, but confirm `SEMANTIC_FLOOR` actually has an entry for `(False, False)` and `(True, False)` (it should, from the existing docs-collection code path also using `False` for non-document rows) rather than assuming.

Add `CLASS_TITLES` (or wherever `"Books"` is already defined as a badge title from the Gutenberg plan's search-integration work) — reuse the existing `"books"`-badge constant rather than a new literal string, if `search.py` already has one from Task 7 of the Gutenberg plan.

- [ ] **Step 5: Run the tests**

Run: `cd api && .venv/bin/python -m pytest tests/test_search.py -k household -v`
Expected: PASS.

- [ ] **Step 6: Run the full suite**

Run: `cd api && .venv/bin/python -m pytest -q`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add api/sos/embeddings.py api/sos/search.py api/tests/test_search.py
git commit -m "feat(search): household books can be found by meaning, fused like the box's own library"
```

---

### Task 8: The Wikipedia rerank-only vector store

**Files:**
- Modify: `api/sos/embeddings.py` (`WikipediaStore`, `build_wikipedia_rerank`)
- Modify: `api/sos/cli.py`
- Modify: `manifest/core.json` (`embeddings-wikipedia` item)
- Test: `api/tests/test_embeddings.py`

**Interfaces:**
- Produces: `WikipediaStore` — a `numpy.memmap`-backed, key-to-row lookup (not a nearest-neighbour index; there is no `.search()` on this class, only `.vector_for(key: str) -> Optional[np.ndarray]`). `build_wikipedia_rerank(conn, settings, embed, open_zim=None, out=print, resume=True) -> dict` — a resumable build: it writes progress checkpoints (a small JSON recording the last completed batch index) so a restart continues rather than re-embedding from the start.

- [ ] **Step 1: Determine the real article count**

```bash
zimdump list /home/dan/sos-content/zim/wikipedia_en_all_maxi.zim > /tmp/wiki-entries.txt
wc -l /tmp/wiki-entries.txt   # 27,199,904 total entries, confirmed earlier -- includes redirects, images, css, js
grep -c '\.html$' /tmp/wiki-entries.txt   # a first approximation of real articles
```

Real Wikipedia ZIMs also carry redirect entries that resolve to another `.html` page rather than having their own content — check a real sample of `.html`-suffixed entries for whether the entry itself has a body or is a bare redirect marker (`zimdump show --url ... --path <entry>` on a handful, looking for suspiciously tiny output). Record the real final article count this plan will actually embed in `docs/app-completion.md` (dated today) alongside the `wc -l`/`grep -c` figures, and recompute the expected on-disk size (`real_count × 384 × 2` bytes) rather than trusting this plan's own upfront "~7 million, ~5.4GB" estimate — note the delta if there is one.

- [ ] **Step 2: Write `WikipediaStore`**

```python
class WikipediaStore:
    """~7 million article vectors, memory-mapped, never loaded whole: an 8GB Pi running kiwix-serve, the
    kiosk, sos-api and the chat model cannot afford a 5GB dict of Python strings and float arrays in RAM.
    Keys are sorted once at build time so a lookup is a binary search over a modest in-memory list of
    strings (a few hundred MB for millions of short keys -- real, but affordable, unlike materialising
    every vector too); only the one row actually asked for is paged in from disk."""

    def __init__(self, mmap: np.memmap, keys: list[str]):
        self._mmap = mmap
        self.keys = keys  # sorted

    def __len__(self) -> int:
        return len(self.keys)

    @classmethod
    def load(cls, folder: Path, collection: str = "wikipedia") -> Optional["WikipediaStore"]:
        folder = Path(folder)
        vec_path, key_path = folder / f"{collection}.f16.bin", folder / f"{collection}.ids"
        if not (vec_path.is_file() and key_path.is_file()):
            return None
        keys = [line for line in key_path.read_text(encoding="utf-8").split("\n") if line]
        if not keys:
            return None
        mmap = np.memmap(vec_path, dtype=np.float16, mode="r", shape=(len(keys), DIMS))
        return cls(mmap, keys)

    def vector_for(self, key: str) -> Optional[np.ndarray]:
        import bisect
        i = bisect.bisect_left(self.keys, key)
        if i == len(self.keys) or self.keys[i] != key:
            return None
        return np.asarray(self._mmap[i], dtype=np.float32)
```

- [ ] **Step 3: Write the failing test**

```python
def test_wikipedia_store_memory_maps_and_looks_up_by_key(tmp_path):
    from sos.embeddings import WikipediaStore
    import numpy as np
    vectors = np.random.default_rng(1).normal(size=(5, 384)).astype(np.float16)
    keys = sorted(["Aardvark", "Berlin", "Canoe", "Drought", "Ember"])
    (tmp_path / "wikipedia.ids").write_text("\n".join(keys) + "\n")
    vectors.tofile(tmp_path / "wikipedia.f16.bin")
    store = WikipediaStore.load(tmp_path)
    assert store is not None and len(store) == 5
    v = store.vector_for("Canoe")
    assert v is not None and v.shape == (384,)
    assert np.allclose(v, vectors[keys.index("Canoe")], atol=0.01)
    assert store.vector_for("Not There") is None
    assert isinstance(store._mmap, np.memmap)  # a real requirement of this task, not incidental
```

- [ ] **Step 4: Run to verify failure, then run to pass**

Run: `cd api && .venv/bin/python -m pytest tests/test_embeddings.py -k wikipedia_store -v`
Expected: FAIL, then PASS after Step 2's class exists.

- [ ] **Step 5: Write the resumable build**

```python
CHECKPOINT_BATCHES = 200  # write a resume checkpoint every this-many batches -- frequent enough that an
                          # interrupted multi-hour build loses minutes, not hours, of already-done work


def build_wikipedia_rerank(conn, settings: Settings, embed: Callable[[list[str]], np.ndarray],
                           open_zim=None, out: Callable = print, resume: bool = True) -> dict:
    """One vector per real English Wikipedia article, for rerank-only lookup (WikipediaStore), never
    for nearest-neighbour retrieval. Resumable: a checkpoint file records the sorted key list and how
    many have vectors so far; a restart skips straight to the first unembedded key rather than
    re-embedding articles this process (or an earlier, interrupted one) already finished."""
    from sos.books import open_zim as real_open_zim
    open_zim = open_zim or real_open_zim
    row = conn.execute("SELECT available, local_path FROM library_items WHERE id='wikipedia_en_all_maxi'").fetchone()
    if row is None or not row["available"] or not row["local_path"]:
        out("wikipedia: not on the box; skipped")
        return {"count": 0}
    reader = open_zim(Path(row["local_path"]))
    checkpoint_path = Path(settings.embeddings_dir) / "wikipedia.checkpoint.json"
    all_keys = sorted(_wikipedia_article_keys(reader))  # every real article path, sorted once, up front
    done = 0
    vectors = np.zeros((len(all_keys), DIMS), dtype=np.float16)
    if resume and checkpoint_path.is_file():
        state = json.loads(checkpoint_path.read_text())
        if state.get("keys") == all_keys:  # the ZIM has not changed under us mid-build
            done = state["done"]
            existing = np.memmap(Path(settings.embeddings_dir) / "wikipedia.f16.bin.part", dtype=np.float16,
                                 mode="r", shape=(len(all_keys), DIMS)) if (Path(settings.embeddings_dir) / "wikipedia.f16.bin.part").is_file() else None
            if existing is not None:
                vectors[:done] = existing[:done]
            out(f"wikipedia: resuming from {done} of {len(all_keys)}")
    part_path = Path(settings.embeddings_dir) / "wikipedia.f16.bin.part"
    part_path.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    for start in range(done, len(all_keys), BATCH):
        batch_keys = all_keys[start:start + BATCH]
        texts = [_wikipedia_article_text(reader, k) for k in batch_keys]
        vecs = embed_batch(embed, texts)
        vectors[start:start + len(batch_keys)] = vecs.astype(np.float16)
        if (start // BATCH) % CHECKPOINT_BATCHES == 0 or start + BATCH >= len(all_keys):
            vectors.tofile(part_path)
            checkpoint_path.write_text(json.dumps({"keys": all_keys, "done": start + len(batch_keys)}))
            elapsed = time.perf_counter() - t0
            rate = (start + len(batch_keys) - done) / max(elapsed, 0.001)
            remaining_s = (len(all_keys) - start - len(batch_keys)) / max(rate, 0.001)
            out(f"wikipedia: {start + len(batch_keys)} of {len(all_keys)} "
                f"({elapsed:.0f}s elapsed, ~{remaining_s / 3600:.1f}h remaining at this rate)")
    os.replace(part_path, Path(settings.embeddings_dir) / "wikipedia.f16.bin")
    (Path(settings.embeddings_dir) / "wikipedia.ids").write_text("\n".join(all_keys) + "\n")
    checkpoint_path.unlink(missing_ok=True)
    meta = {"model": settings.embed_model, "dims": DIMS, "count": len(all_keys),
            "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    (Path(settings.embeddings_dir) / "wikipedia.meta.json").write_text(json.dumps(meta, indent=1))
    return meta
```

`_wikipedia_article_keys(reader)` and `_wikipedia_article_text(reader, key)` are this task's own real implementation, written against Step 1's real finding of which entries are real articles versus redirects/media — a real article's text should go through `api/sos/kiwix.py`'s `extract_text` the same way `build_household` does, cut to `HOUSEHOLD_TEXT_CHARS`/`PASSAGE_CHARS`. Skip `EXCLUDED_ZIMS` items entirely here too, even though this function is scoped to a single ZIM id already — Task 9 adds the general-purpose check other call sites need; this function's own single-ZIM scope makes it trivially compliant already (Wikipedia is never in `EXCLUDED_ZIMS`), but say so in a comment so a future editor does not add a second ZIM to `build_wikipedia_rerank` without re-checking.

- [ ] **Step 6: Write a resumability test**

```python
def test_build_wikipedia_rerank_resumes_after_a_simulated_interruption(tmp_path):
    from sos.embeddings import build_wikipedia_rerank
    import numpy as np, sqlite3
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE library_items (id TEXT, available INTEGER, local_path TEXT)")
    conn.execute("INSERT INTO library_items VALUES ('wikipedia_en_all_maxi', 1, 'fake.zim')")
    calls = {"n": 0}

    def flaky_embed(texts):
        calls["n"] += 1
        if calls["n"] == 3:
            raise RuntimeError("simulated interruption")
        return np.random.default_rng(calls["n"]).normal(size=(len(texts), 384)).astype(np.float32)

    class FakeSettings:
        embeddings_dir = tmp_path
        embed_model = "test"

    fake_reader = ...  # a fake with enough entries to span at least 3 BATCH-sized groups; reuse this
    # task's own fixture-building helper once BATCH's real value (read from embeddings.py) is known.
    try:
        build_wikipedia_rerank(conn, FakeSettings(), flaky_embed, open_zim=lambda p: fake_reader, resume=False)
    except RuntimeError:
        pass
    result = build_wikipedia_rerank(conn, FakeSettings(), flaky_embed, open_zim=lambda p: fake_reader, resume=True)
    assert result["count"] > 0
    assert not (tmp_path / "wikipedia.checkpoint.json").exists()  # cleaned up on real completion
```

- [ ] **Step 7: Run the tests**

Run: `cd api && .venv/bin/python -m pytest tests/test_embeddings.py -k wikipedia -v`
Expected: PASS.

- [ ] **Step 8: Wire into `sos build-embeddings` and add the manifest item**

Add a `--wikipedia` flag (or a separate `build-embeddings-wikipedia` subcommand, given how long this specific build genuinely takes versus the other two — read `cli.py`'s existing subcommand style and pick whichever fits better) so this multi-hour build is not accidentally triggered by every routine `sos build-embeddings` run. Add `embeddings-wikipedia` to `manifest/core.json` following the same pattern as Task 6's `embeddings-household` item.

- [ ] **Step 9: Run the full suite**

Run: `cd api && .venv/bin/python -m pytest -q`
Expected: all pass.

- [ ] **Step 10: Commit**

```bash
git add api/sos/embeddings.py api/sos/cli.py manifest/core.json api/tests/test_embeddings.py
git commit -m "feat(embeddings): a resumable, memory-mapped Wikipedia vector store for rerank-only lookups"
```

---

### Task 9: Wikipedia rerank-only fusion; the exclusion list

**Files:**
- Modify: `api/sos/search.py`
- Modify: `api/sos/embeddings.py` (`EXCLUDED_ZIMS`)
- Test: `api/tests/test_search.py`, `api/tests/test_embeddings.py`

**Interfaces:**
- Consumes: `WikipediaStore.vector_for` (Task 8).
- Produces: `EXCLUDED_ZIMS: frozenset[str]` in `api/sos/embeddings.py`, checked by both `build_household` (Task 6, retrofit a check even though today's `HOUSEHOLD_ZIMS` tuple happens not to include any excluded id) and any future collection; a rerank step in `search()` that adjusts (never adds) Wikipedia's own keyword-hit scores.

- [ ] **Step 1: Write the exclusion list against the real manifest**

```python
def _stackexchange_ids() -> frozenset[str]:
    """Every *.stackexchange.com_en_all id in the real manifest, computed rather than hand-listed, so this
    set can never silently drift from the manifest as StackExchange sites are added or removed."""
    from sos.manifest import load_manifests
    from sos.config import get_settings
    ids = {i.id for i in load_manifests(get_settings().manifests) if i.id.endswith(".stackexchange.com_en_all")}
    return frozenset(ids)


EXCLUDED_ZIMS = frozenset({"wiktionary_en_all_nopic", "wikipedia_cy_all_maxi"}) | _stackexchange_ids()
```

Computing `_stackexchange_ids()` at import time couples this module to a working `Settings`/manifest at import — check whether that is safe in this codebase's existing import order (does anything import `sos.embeddings` before settings/manifests are loadable, e.g. at CLI startup before env vars are set?) by running the full test suite after this change; if import-time manifest loading causes any failure, make `EXCLUDED_ZIMS` a function (`excluded_zims(settings) -> frozenset[str]`) computed lazily where it is used instead of a module constant, and update every reference in this task accordingly.

- [ ] **Step 2: Write the failing test**

```python
def test_excluded_zims_contains_every_real_stackexchange_id_and_the_two_named_exclusions():
    from sos.embeddings import EXCLUDED_ZIMS  # or excluded_zims(settings), matching Step 1's final shape
    assert "wiktionary_en_all_nopic" in EXCLUDED_ZIMS
    assert "wikipedia_cy_all_maxi" in EXCLUDED_ZIMS
    assert "ham.stackexchange.com_en_all" in EXCLUDED_ZIMS
    assert "homebrew.stackexchange.com_en_all" in EXCLUDED_ZIMS
    assert len([z for z in EXCLUDED_ZIMS if z.endswith(".stackexchange.com_en_all")]) >= 20  # the real current count


def test_household_zims_never_overlap_excluded_zims():
    from sos.embeddings import HOUSEHOLD_ZIMS, EXCLUDED_ZIMS
    assert not (set(HOUSEHOLD_ZIMS) & EXCLUDED_ZIMS)
```

- [ ] **Step 3: Run, implement, re-run**

Run: `cd api && .venv/bin/python -m pytest tests/test_embeddings.py -k excluded -v`
Expected: FAIL, then PASS once Step 1's code is in place.

- [ ] **Step 4: Wikipedia rerank fusion in `search()`**

Add, after the existing Kiwix-class fan-out loop in `search()` (the block that already produces `results` entries with `source` derived from `classify(row)` for each `library_items` ZIM), a small rerank pass over just the Wikipedia entries already in `results`:

```python
wiki_store = semantic.wikipedia_store() if semantic is not None else None  # a cached loader, mirroring
# Semantic.index()'s stat-and-reload-on-change pattern -- add this method to Semantic in this same task.
if wiki_store is not None:
    wiki_hits = [r for r in results if r.get("_cat") == "reference" and r["source"] == "wikipedia_en_all_maxi"]
    # confirm the real source/_cat value Wikipedia's own hits carry today by reading classify()'s real
    # current bucket for wikipedia_en_all_maxi (category "reference" per its manifest entry -- check) --
    # this filter must match that real value exactly, not the guess written here.
    if wiki_hits:
        try:
            qvec = (await semantic.client.embed([QUERY_PREFIX + q], timeout=Semantic.QUERY_TIMEOUT_S))[0]
        except EmbedError:
            qvec = None
        if qvec is not None:
            for r in wiki_hits:
                key = r["url"].rsplit("/", 1)[-1]  # confirm this really is the Wikipedia article key
                # WikipediaStore's keys use (built in Task 8) -- adjust to match exactly, they must agree
                vec = wiki_store.vector_for(key)
                if vec is not None:
                    cos = float(np.dot(qvec, vec) / (np.linalg.norm(qvec) * np.linalg.norm(vec) + 1e-9))
                    r["score"] *= 0.7 + 0.6 * max(0.0, cos)  # a keyword hit is never zeroed by this, only
                    # nudged up to 1.3x for a real semantic match and down toward 0.7x for a weak one --
                    # tune this multiplier against real queries in Task 10's acceptance step, not by theory
```

Add `wikipedia_store()` to `Semantic`, mirroring `index()`'s existing stat-mtime-reload pattern exactly, but loading a `WikipediaStore` instead of an `Index`.

- [ ] **Step 5: Write the failing test, then implement, then pass**

```python
def test_search_wikipedia_hits_are_rescored_by_meaning_never_added(client, monkeypatch):
    # As with Task 7's test, mirror whatever fake-Semantic mechanism this file's existing semantic tests
    # already use, extended with a fake WikipediaStore.vector_for returning a known vector for one of the
    # Wikipedia hits a keyword search already produces in this test's fixtures, and asserting: (a) the
    # rescored hit's score changed, (b) no NEW source="wikipedia_en_all_maxi" row appeared beyond what the
    # keyword search itself returned.
    ...
```

Run: `cd api && .venv/bin/python -m pytest tests/test_search.py -k wikipedia_rerank -v`
Expected: FAIL, then PASS.

- [ ] **Step 6: Retrofit the exclusion check into `build_household`**

In `api/sos/embeddings.py`'s `build_household` (Task 6), add a one-line assertion at the top of the loop over `HOUSEHOLD_ZIMS`: `assert zim_id not in EXCLUDED_ZIMS, f"{zim_id} is excluded from meaning search"` — a defensive check, not expected to ever fire given `HOUSEHOLD_ZIMS`'s fixed two entries, but it means a future edit that accidentally adds an excluded id to that tuple fails loudly in CI rather than silently embedding a dictionary.

- [ ] **Step 7: Run the full suite**

Run: `cd api && .venv/bin/python -m pytest -q`
Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add api/sos/embeddings.py api/sos/search.py api/tests/test_search.py api/tests/test_embeddings.py
git commit -m "feat(search): Wikipedia's own keyword hits are re-ranked by meaning, never added to by it"
```

---

### Task 10: Acceptance

**Files:**
- Modify: `docs/app-completion.md`, `docs/hardware-checklist.md`, `docs/superpowers/specs/2026-09-18-search-precision-and-semantic-design.md` (a new subsection recording what this plan added)
- Test: real builds, not fixtures

**Interfaces:**
- Produces: real, measured facts recorded in the docs above — no new code.

- [ ] **Step 1: Confirm the CUDA build and real full-length rebuild are both real and current**

```bash
~/.local/bin/llama-server-cuda --version
sha256sum /home/dan/sos-content/embeddings/docs.f16.bin   # exists, from Task 1's real rebuild
cat /home/dan/sos-content/embeddings/docs.meta.json       # count matches the pre-Task-1 count; built_at is recent
```

- [ ] **Step 2: Run the real household build, measuring real throughput**

```bash
SOS_CORE=/home/dan/sos-content SOS_STATE=.dev/state api/.venv/bin/sos build-embeddings --cuda
```

(`--cuda` here stands for whatever flag Task 2/6 actually wired up — use the real one.) This embeds real books from both real ZIMs (Gutenberg's confirmed 60,366, plus however many of Survivor Library's real entries Task 5 found had usable text). Record real wall-clock duration and the real final `count`/`skipped_no_text` from the meta file in `docs/app-completion.md`.

- [ ] **Step 3: Measure real Wikipedia throughput on a real, bounded sample first**

Before committing to the full multi-million-article run, measure real throughput on a real but small slice:

```bash
SOS_CORE=/home/dan/sos-content SOS_STATE=.dev/state api/.venv/bin/sos build-embeddings-wikipedia --cuda --limit 5000
```

(Add a `--limit N` flag to Task 8's build wiring if one does not already exist, purely for this measurement — embed only the first `N` real article keys, still through the real resumable code path, so this measurement exercises the real thing rather than a separate code path.) Record the real articles-per-second rate, then compute and record a real extrapolated total duration for all real articles found in Task 8 Step 1 — do not assert a specific number of hours anywhere in this plan's own text; only this step, using a real measurement, gets to state one.

- [ ] **Step 4: Start the real full Wikipedia build in the background**

```bash
nohup env SOS_CORE=/home/dan/sos-content SOS_STATE=.dev/state api/.venv/bin/sos build-embeddings-wikipedia --cuda > /tmp/wikipedia-embed.log 2>&1 &
disown
```

Given Step 3's real extrapolated duration, this may still be running well after this task's other steps are done — that is expected and correct; do not block the rest of this task, or this plan being considered complete, on its finish. Record in `docs/app-completion.md` that it was started, its real starting throughput, and its real extrapolated completion time, plus a reminder that `WikipediaStore.load` returning `None` (the vector file not existing yet) is already the correct, tested "off" behaviour from Task 8/9 — nothing breaks while this build is still running.

- [ ] **Step 5: A real search exercising both new fusion paths**

Once Task 6's household build (Step 2, which is fast enough to finish within this task) is complete and the API is running against real data:

```bash
curl -s "http://127.0.0.1:8000/api/search?q=a+whaling+voyage+in+the+age+of+sail" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print([(r['source'], r.get('via')) for r in d['results']])
"
```

Expected: at least one `("household", "meaning")` entry (Moby-Dick or a similarly-themed real Gutenberg book, found by meaning rather than an exact keyword match). If the real Wikipedia build (Step 4) has not progressed far enough yet for a query's Wikipedia hits to have precomputed vectors, confirm the rerank path degrades correctly (the keyword-found Wikipedia hits still appear, un-reranked, exactly as `WikipediaStore.vector_for` returning `None` per-key is already specified to do) rather than erroring.

- [ ] **Step 6: Confirm the exclusions hold against real search results**

```bash
curl -s "http://127.0.0.1:8000/api/search?q=define+the+word+forge" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print([r['source'] for r in d['results']])
print('via' in str(d))
" | grep -i wiktionary
```

Expected: no output (Wiktionary may still appear as a plain keyword hit if the query happens to match it — that is fine and unrelated to this plan, which only excludes it from *meaning* search — but no result should carry `"via": "meaning"` alongside a Wiktionary/StackExchange/Welsh-Wikipedia source).

- [ ] **Step 7: Update the design spec and hardware checklist**

Add a new subsection to `docs/superpowers/specs/2026-09-18-search-precision-and-semantic-design.md`'s section 3 recording: the real full-length `PASSAGE_CHARS` value, the household collection's real book count, the real Wikipedia article count and real measured build throughput/extrapolated duration, and the exclusion list. Add a `docs/hardware-checklist.md` entry (matching the existing checklist's phrasing style) for the owner's own hardware-side verification: a search on the touchscreen surfaces a household book by meaning for a query with no matching words, and a StackExchange/Wiktionary hit never carries a "related" (meaning) badge.

- [ ] **Step 8: Full-suite final check**

Run: `cd api && .venv/bin/python -m pytest -q`, `cd web && pnpm vitest run`, `SOS_PLAYBOOKS_DIR=playbooks SOS_MANIFEST_DIR=manifest api/.venv/bin/sos validate-playbooks --all-scenarios`
Expected: all green (the still-running background Wikipedia build does not touch anything these check).

- [ ] **Step 9: Commit**

```bash
git add docs/app-completion.md docs/hardware-checklist.md docs/superpowers/specs/2026-09-18-search-precision-and-semantic-design.md
git commit -m "docs: record the real semantic-search expansion acceptance (household, Wikipedia rerank)"
```

---

## Self-review

**Spec coverage:** Directive 1 (full-length rebuild) → Task 1. Directive 2 (household, approximate index, add-rows) → Tasks 4, 5, 6, 7. Directive 3 (Wikipedia, rerank-only, memory-mapped, ~5.4GB) → Tasks 8, 9. Directive 4 (exclusions) → Task 9, retrofitted defensively into Task 6. The GPU-build prerequisite both large builds need → Task 2. The multi-collection architecture both new collections need → Task 3.

**Placeholder scan:** `_household_entries` (Task 6) and `_wikipedia_article_keys`/`_wikipedia_article_text` (Task 8) are left for the real implementation rather than invented against a paraphrase, because their real shape depends on Task 5's and Task 8 Step 1's own real findings about each ZIM's entry layout — this is the same pattern the Gutenberg plan used for its own `_household_entries`-shaped gap (there, "confirm with `zimdump list` after the sha256 matches, then write the importer against the layout found"), not an unfilled TBD. Every other function in this plan has a complete, real body.

**Type consistency:** `Index.search`/`ApproxIndex.search` both return `list[tuple[str, float]]` with a cosine-similarity score (not a distance) — `WikipediaStore` deliberately has no `.search()` at all, only `.vector_for`, since Task 8/9's whole point is that Wikipedia is never searched by meaning, only looked up. `EXCLUDED_ZIMS` (Task 9) and `HOUSEHOLD_ZIMS` (Task 6) are both real, checkable sets of manifest item ids, cross-tested against each other in Task 9 Step 2. `write_index`/`Index.load`'s `collection` parameter (Task 3) and `ApproxIndex.save`/`.load`'s `collection` parameter (Task 4) use the same naming convention (`f"{collection}.<suffix>"`) so a future collection needs no new file-naming logic, only a new call site.

**A note on task ordering an implementer should not disturb:** Task 5's Survivor Library download is started early and deliberately left running across several later tasks (3, 4, and the early parts of 6) that do not need it — those tasks work entirely against fixtures. Do not block on the download finishing before starting Task 3 or Task 4; do check it has finished and checksum-verified before Task 6 Step 4 needs the real file for anything beyond its own fixture-driven tests (the real acceptance build in Task 10 is the first point this plan actually requires the real Survivor Library file to be present and correct).

---

**Plan complete and saved to `docs/superpowers/plans/2026-09-18-semantic-search-expansion.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
