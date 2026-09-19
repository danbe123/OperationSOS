"""Semantic search: the passage text, the index, the build, the query prefix, and the fusion into search."""
import asyncio
import json
import os
import shutil
import time
from pathlib import Path

import httpx
import numpy as np
import pytest
import respx

from sos import db, embeddings, search
from sos.kiwix import KiwixClient

BASE = "http://kiwix.test/kiwix"
FIXTURES = Path(__file__).parent / "fixtures"
REPO = Path(__file__).resolve().parents[2]   # api/tests -> api -> OperationSOS: the real repo manifest lives here
HAS_PDFTOTEXT = shutil.which("pdftotext") is not None


def unit(*values):
    v = np.zeros(embeddings.DIMS, dtype=np.float32)
    for i, x in enumerate(values):
        v[i] = x
    return v / np.linalg.norm(v)


def test_passage_chars_matches_the_real_measured_window():
    """Not a behavioural test of the model itself (that needs the real server, done once in Task 1's own
    Step 2) -- a tripwire so a future edit to this constant is a deliberate decision, not a typo."""
    from sos.embeddings import PASSAGE_CHARS
    assert PASSAGE_CHARS == 2584


def test_passage_text_is_the_title_then_the_words_without_template_tokens_cut_to_the_window():
    text = embeddings.passage_text("Food", "{{#if phones}}Ring first.{{/if}}  Tins keep for years; [[call 999]] never for food.")
    assert text == "Food. Ring first. Tins keep for years; never for food."
    assert len(embeddings.passage_text("T", "x" * 5000)) == embeddings.PASSAGE_CHARS


def test_index_finds_the_nearest_passages_by_cosine_and_survives_a_round_trip(tmp_path):
    keys = ["/p/one", "/p/two", "/p/three"]
    vectors = np.stack([unit(1, 0), unit(0, 1), unit(1, 1)])
    embeddings.write_index(tmp_path, "docs", vectors, keys, {"model": "test", "count": 3})
    index = embeddings.Index.load(tmp_path, "docs")
    assert index is not None and len(index) == 3 and index.meta["model"] == "test"
    hits = index.search(unit(1, 0.1), k=2)
    assert [h[0] for h in hits] == ["/p/one", "/p/three"]
    assert hits[0][1] > hits[1][1] > 0.5
    # nothing to load: no index, not an error
    assert embeddings.Index.load(tmp_path / "nowhere", "docs") is None
    # a vectors file that does not match its keys is refused rather than misread
    (tmp_path / "docs.ids").write_text("/p/one\n")
    assert embeddings.Index.load(tmp_path, "docs") is None


def test_index_load_and_write_are_scoped_by_collection_name(tmp_path):
    vectors = np.random.rand(2, embeddings.DIMS).astype(np.float32)
    embeddings.write_index(tmp_path, "household", vectors, ["book:1", "book:2"], {"count": 2})
    assert (tmp_path / "household.f16.bin").exists() and (tmp_path / "household.ids").exists()
    assert not (tmp_path / "docs.f16.bin").exists()
    idx = embeddings.Index.load(tmp_path, "household")
    assert idx is not None and len(idx) == 2
    assert embeddings.Index.load(tmp_path, "docs") is None  # a different collection name, nothing written for it


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


def test_vectors_from_reads_both_reply_shapes_and_normalises():
    flat = embeddings._vectors_from([{"index": 0, "embedding": [3.0] + [0.0] * (embeddings.DIMS - 1)}])
    nested = embeddings._vectors_from({"data": [{"embedding": [[0.0, 4.0] + [0.0] * (embeddings.DIMS - 2)]}]})
    assert flat.shape == nested.shape == (1, embeddings.DIMS)
    assert np.linalg.norm(flat[0]) == pytest.approx(1.0) and nested[0][1] == pytest.approx(1.0)
    with pytest.raises(embeddings.EmbedError):
        embeddings._vectors_from({"data": [{"embedding": [1.0, 2.0]}]})


def test_build_embeds_every_passage_but_the_catalogue_entries_and_never_prefixes_them(env, tmp_path):
    conn = db.connect(env.db_path)
    db.init_schema(conn)
    rows = [("Water", "Boil it for a minute.", "module:water", "module", "playbooks", "", None, "/m/water"),
            ("NRR", "Risks.", "nrr#p1", "doc", "uk-official", "", 1, "/doc/nrr#page=1"),
            ("Wikipedia", "An encyclopaedia.", "item:wiki", "item", "reference", "", None, "/library#wiki")]
    conn.executemany("INSERT INTO fts_docs(title, body, doc_id, kind, category, scenarios, page, url) VALUES (?,?,?,?,?,?,?,?)", rows)
    conn.commit()
    seen: list[str] = []

    def fake_embed(texts):
        seen.extend(texts)
        return np.stack([unit(1, i) for i in range(len(texts))])

    lines = []
    meta = embeddings.build(conn, env, fake_embed, out=lines.append)
    assert seen == ["Water. Boil it for a minute.", "NRR. Risks."]   # the catalogue entry is not a passage
    assert all(not t.startswith(embeddings.QUERY_PREFIX) for t in seen)
    assert meta["count"] == 2 and meta["prefix"] == embeddings.QUERY_PREFIX
    index = embeddings.Index.load(env.embeddings_dir, "docs")
    assert index is not None and index.keys == ["/m/water", "/doc/nrr#page=1"]
    assert any(line.startswith("wrote 2 vectors") for line in lines)


@respx.mock
def test_semantic_query_prefixes_the_query_and_answers_nothing_when_the_server_or_index_is_away(env, respx_mock):
    sem = embeddings.Semantic(env)
    assert asyncio.run(sem.query("tinned food")) == []          # no index yet
    embeddings.write_index(env.embeddings_dir, "docs", np.stack([unit(1, 0), unit(0, 1)]), ["/m/food", "/m/water"], {})
    sent = {}

    def reply(request):
        sent["body"] = json.loads(request.content)
        return httpx.Response(200, json=[{"index": 0, "embedding": [[1.0] + [0.0] * (embeddings.DIMS - 1)]}])

    respx_mock.post(f"{env.embed_url}/embeddings").mock(side_effect=reply)
    hits = asyncio.run(sem.query("tinned food", k=1))
    assert hits == [("/m/food", pytest.approx(1.0))]
    assert sent["body"] == {"input": [embeddings.QUERY_PREFIX + "tinned food"]}
    respx_mock.post(f"{env.embed_url}/embeddings").mock(return_value=httpx.Response(503))
    assert asyncio.run(sem.query("tinned food")) == []


class FakeSemantic:
    def __init__(self, hits, household_hits=None):
        self.hits = hits
        self.household_hits = household_hits or []

    async def query(self, q, k=20):
        return self.hits

    async def query_household(self, q, k=20):
        return self.household_hits


def test_search_fuses_the_nearest_passages_lifting_a_keyword_hit_and_adding_one_the_words_missed(env):
    conn = db.connect(env.db_path)
    db.init_schema(conn)
    rows = [("Food", "Keeps for years past the date on the label.", "module:food", "module", "playbooks", "", None, "/m/food"),
            ("Food storage", "How long tinned food lasts and how to rotate it.", "page:food-storage", "page", "playbooks", "", None, "/p/food-storage"),
            ("Water", "Boil it.", "module:water", "module", "playbooks", "", None, "/m/water")]
    conn.executemany("INSERT INTO fts_docs(title, body, doc_id, kind, category, scenarios, page, url) VALUES (?,?,?,?,?,?,?,?)", rows)
    conn.commit()
    with respx.mock(base_url=BASE, assert_all_called=False) as m:
        m.get("/search").mock(return_value=httpx.Response(200, text="<rss><channel></channel></rss>"))
        # neither "canned" nor "goods" is a word in the Food module (nor a synonym of one); the meaning is
        sem = FakeSemantic([("/m/food", 0.82), ("/p/food-storage", 0.7), ("/m/water", 0.2)])
        resp = asyncio.run(search.search(conn, env, KiwixClient(BASE), "canned goods", use_cache=False, semantic=sem))
    urls = [r["url"] for r in resp["results"]]
    assert "/m/food" in urls and "/p/food-storage" in urls and "/m/water" not in urls   # under the floor: not near enough
    food = next(r for r in resp["results"] if r["url"] == "/m/food")
    storage = next(r for r in resp["results"] if r["url"] == "/p/food-storage")
    # the page was found by its words ("tinned" is a synonym of "canned") and lifted; the module only by meaning
    assert storage.get("via") is None
    assert food["via"] == "meaning" and food["snippet"].startswith("Keeps for years")
    assert resp["results"][0]["url"] in ("/m/food", "/p/food-storage")


def test_search_fuses_household_books_lifting_a_matched_gutenberg_book_and_surfacing_a_slug_titled_survivor_library_pdf(env):
    conn = db.connect(env.db_path)
    db.init_schema(conn)
    # a Gutenberg book the words already found (fts_books), so its household hit must lift the same row
    conn.execute("INSERT INTO library_items (id, available) VALUES ('gutenberg_en_all', 1)")
    conn.execute("INSERT INTO books (zim, id, title, author, shelf, popularity, epub_path, html_path, cover_path) "
                 "VALUES ('gutenberg_en_all', 2701, 'Whaling Voyage', 'Herman Melville', 'PS', 3, NULL, NULL, NULL)")
    conn.execute("INSERT INTO fts_books(fts_books) VALUES('rebuild')")
    conn.execute("INSERT INTO library_items (id, available) VALUES ('survivorlibrary.com_en_all', 1)")
    conn.commit()
    sem = FakeSemantic([], household_hits=[
        ("gutenberg_en_all:2701", 0.75),                    # the same book the words already found: lifted, not duplicated
        ("survivorlibrary.com_en_all:canning-meat", 0.70),  # meaning alone; no catalogue row exists for Survivor Library at all
    ])
    resp = _search(conn, env, "whaling voyage", sem, use_cache=False)
    books = [r for r in resp["results"] if r["source"] == "books"]
    assert len(books) == 2   # the Gutenberg hit joined its keyword row rather than adding a second one

    gutenberg = next(r for r in books if r["url"] == "/book/gutenberg/2701")
    assert gutenberg["title"] == "Whaling Voyage" and gutenberg.get("via") is None   # the keyword row survives, just boosted
    expected_gutenberg_score = search.score(search.BOOK_WEIGHT, 1) + search.semantic_bonus(0.75, search.BOOK_WEIGHT)
    assert gutenberg["score"] == pytest.approx(expected_gutenberg_score)

    survivor = next(r for r in books if r["url"] != "/book/gutenberg/2701")
    assert survivor["title"] == "Canning Meat" and survivor["snippet"] == ""        # slug-derived, no author to show
    assert survivor["url"] == "/kiwix/content/survivorlibrary.com_en_all/www.survivorlibrary.com/library/canning-meat.pdf"
    assert survivor["via"] == "meaning"
    # the bonus genuinely carries BOOK_WEIGHT: dropping it would let this outscore the box's own survival guidance
    assert survivor["score"] == pytest.approx(search.semantic_bonus(0.70, search.BOOK_WEIGHT))
    assert search.semantic_bonus(0.70, search.BOOK_WEIGHT) != pytest.approx(search.semantic_bonus(0.70, 1.0))


class RerankSemantic:
    """Just enough of Semantic for the Wikipedia rerank pass (Task 9): no docs or household collections at
    all (a real Semantic reports empty for both when no index has been built), and a scripted
    rerank_wikipedia that records every call it receives so a test can check the real keys it was asked
    to score, not merely that a score came back."""

    def __init__(self, wikipedia_scores: dict[str, float]):
        self.wikipedia_scores = wikipedia_scores
        self.rerank_calls: list[tuple[str, list[str]]] = []

    async def query(self, q, k=20):
        return []

    async def query_household(self, q, k=20):
        return []

    async def rerank_wikipedia(self, q, keys):
        self.rerank_calls.append((q, list(keys)))
        return {k: v for k, v in self.wikipedia_scores.items() if k in keys}


@pytest.mark.parametrize("encoded,decoded", [("A/Some_Article", "A/Some_Article"),
                                               ("A/Caf%C3%A9%25", "A/Café%")])
def test_search_wikipedia_hits_are_rescored_by_meaning_never_added(env, encoded, decoded):
    """The one behaviour this whole task exists to guarantee. WikipediaStore has no `.search()` at all
    (Task 8) -- only `vector_for(key)` -- so there is structurally no way for the rerank pass to introduce
    a Wikipedia row the keyword search itself did not already find; this proves search.py's fusion code
    genuinely respects that rather than accidentally reintroducing a "find by meaning" path for Wikipedia."""
    conn = db.connect(env.db_path)
    db.init_schema(conn)
    conn.execute("INSERT INTO library_items (id, title, kind, tier, category, dest, priority, available, fts) VALUES "
                 "('wikipedia_en_all_maxi', 'Wikipedia', 'zim', 'core', 'reference', 'zim/w.zim', 50, 1, 1)")
    conn.execute("INSERT INTO library_items (id, title, kind, tier, category, dest, priority, available, fts) VALUES "
                 "('nhs_uk', 'NHS', 'zim', 'core', 'medical', 'zim/n.zim', 10, 1, 1)")
    conn.commit()

    # Wikipedia's real ZIM path is namespaced ("A/Some_Article"): the keyword hit's url must carry that
    # internal slash through to /read/wikipedia_en_all_maxi/A/Some_Article intact, exactly as a real Kiwix
    # search result would (kiwix.py's _split_content_link partitions on only the FIRST slash after the book).
    def kiwix_reply(request):
        books = request.url.params.get_list("books.name")
        if "wikipedia_en_all_maxi" in books:
            xml = ("<rss><channel><item><title>Some Article</title>"
                   f"<link>/kiwix/content/wikipedia_en_all_maxi/{encoded}</link>"
                   "<description>An encyclopaedia article.</description></item></channel></rss>")
        else:
            xml = ("<rss><channel><item><title>Bleeding</title>"
                   "<link>/kiwix/content/nhs_uk/conditions/bleeding</link>"
                   "<description>NHS guidance on bleeding.</description></item></channel></rss>")
        return httpx.Response(200, text=xml)

    def run(sem):
        with respx.mock(base_url=BASE, assert_all_called=False) as m:
            m.get("/search").mock(side_effect=kiwix_reply)
            return asyncio.run(search.search(conn, env, KiwixClient(BASE), "wikipedia article",
                                             use_cache=False, semantic=sem))

    baseline = run(RerankSemantic({}))   # no vector for the real key: never rescored, but still present
    wiki_before = [r for r in baseline["results"] if r["url"].startswith("/read/wikipedia_en_all_maxi/")]
    assert [r["url"] for r in wiki_before] == [f"/read/wikipedia_en_all_maxi/{encoded}"]
    baseline_score = wiki_before[0]["score"]
    other_before = [r["url"] for r in baseline["results"] if not r["url"].startswith("/read/wikipedia_en_all_maxi/")]
    assert other_before == ["/read/nhs_uk/conditions/bleeding"]

    cos = 0.9   # chosen so the multiplier (0.7 + 0.6 * cos = 1.24) is genuinely not 1.0 -- a real change
    sem = RerankSemantic({decoded: cos})
    resp = run(sem)

    # (a) the rescored hit's score genuinely changed by the expected multiplier, computed explicitly here
    wiki_after = [r for r in resp["results"] if r["url"].startswith("/read/wikipedia_en_all_maxi/")]
    assert len(wiki_after) == 1
    expected_score = baseline_score * (search.WIKIPEDIA_RERANK_BASE + search.WIKIPEDIA_RERANK_SPAN * cos)
    assert wiki_after[0]["score"] == pytest.approx(expected_score)
    assert wiki_after[0]["score"] != pytest.approx(baseline_score)                 # it really did change
    assert sem.rerank_calls == [("wikipedia article", [decoded])]          # the real key, slash intact

    # (b) THE WHOLE POINT: no new row was added by meaning alone
    assert len(wiki_after) == len(wiki_before)
    other_after = [r["url"] for r in resp["results"] if not r["url"].startswith("/read/wikipedia_en_all_maxi/")]
    assert other_after == other_before   # the NHS hit, found by keyword alone, is untouched by this rerank


def test_search_is_unhurt_by_a_semantic_layer_that_raises(env):
    conn = db.connect(env.db_path)
    db.init_schema(conn)
    conn.execute("INSERT INTO fts_docs(title, body, doc_id, kind, category, scenarios, page, url) VALUES (?,?,?,?,?,?,?,?)",
                 ("Water", "Boil it.", "module:water", "module", "playbooks", "", None, "/m/water"))
    conn.commit()

    class Broken:
        async def query(self, q, k=20):
            raise RuntimeError("boom")

    with respx.mock(base_url=BASE, assert_all_called=False) as m:
        m.get("/search").mock(return_value=httpx.Response(200, text="<rss><channel></channel></rss>"))
        resp = asyncio.run(search.search(conn, env, KiwixClient(BASE), "water", use_cache=False, semantic=Broken()))
    assert [r["url"] for r in resp["results"]] == ["/m/water"]


def test_server_command_is_the_embedding_server_on_its_own_port(env):
    cmd = embeddings.server_command(env)
    assert cmd[0] == "llama-server" and "--embedding" in cmd and "--pooling" in cmd
    assert cmd[cmd.index("--port") + 1] == env.embed_url.rsplit(":", 1)[1]
    assert cmd[cmd.index("-m") + 1] == str(env.embed_model_path)


def test_server_command_cuda_variant_adds_gpu_layers_and_the_cuda_binary(env):
    cpu_cmd = embeddings.server_command(env)
    assert "-ngl" not in cpu_cmd  # today's exact behaviour, unchanged
    gpu_cmd = embeddings.server_command(env, cuda=True)
    assert "-ngl" in gpu_cmd and gpu_cmd[gpu_cmd.index("-ngl") + 1] == "99"
    assert gpu_cmd[0].endswith("llama-server-cuda")
    assert gpu_cmd[0] == str(embeddings.CUDA_LLAMA_SERVER)


def _build_cli_fixture(env, monkeypatch):
    """A model file, an initialised (empty) db, and a `httpx.get` fake that reports the server not-ready
    once (so build_cli starts one) then ready -- so build_cli's own polling loop exits on its first check,
    with `time.sleep` stubbed out so the test does not actually wait."""
    conn = db.connect(env.db_path)
    db.init_schema(conn)
    conn.close()
    env.embed_model_path.parent.mkdir(parents=True, exist_ok=True)
    env.embed_model_path.write_bytes(b"")

    calls = {"get": 0}

    def fake_get(url, timeout=1.0):
        calls["get"] += 1
        if calls["get"] == 1:
            raise httpx.HTTPError("not ready")
        return httpx.Response(200)

    monkeypatch.setattr(embeddings.httpx, "get", fake_get)
    monkeypatch.setattr(embeddings.time, "sleep", lambda s: None)

    class FakeProcess:
        def terminate(self):
            pass

    seen_cmds: list[list[str]] = []

    def fake_run(cmd, **kw):
        seen_cmds.append(cmd)
        return FakeProcess()

    return seen_cmds, fake_run


def test_build_cli_starts_the_plain_binary_when_cuda_is_not_asked_for(env, monkeypatch):
    import shutil

    seen_cmds, fake_run = _build_cli_fixture(env, monkeypatch)
    # build_cli's own build_household() call runs the Task 9 exclusion check (excluded_zims); this test is
    # about the server command line, not the exclusion list, so the check is stubbed out entirely rather
    # than coupling this test to the real repository manifest's StackExchange entries.
    monkeypatch.setattr(embeddings, "excluded_zims", lambda settings: frozenset())
    rc = embeddings.build_cli(env, out=lambda s: None, run=fake_run)
    assert rc == 0
    assert len(seen_cmds) == 1
    expected_binary = shutil.which("llama-server") or "/usr/local/bin/llama-server"
    assert seen_cmds[0][0] == expected_binary
    assert not seen_cmds[0][0].endswith("llama-server-cuda")
    assert "-ngl" not in seen_cmds[0]


def test_build_cli_starts_the_cuda_binary_when_cuda_is_true(env, monkeypatch):
    seen_cmds, fake_run = _build_cli_fixture(env, monkeypatch)
    # as above: this test is about the CUDA command line, not the exclusion list.
    monkeypatch.setattr(embeddings, "excluded_zims", lambda settings: frozenset())
    rc = embeddings.build_cli(env, out=lambda s: None, run=fake_run, cuda=True)
    assert rc == 0
    assert len(seen_cmds) == 1
    assert seen_cmds[0][0].endswith("llama-server-cuda")
    assert seen_cmds[0][0] == str(embeddings.CUDA_LLAMA_SERVER)
    assert "-ngl" in seen_cmds[0] and seen_cmds[0][seen_cmds[0].index("-ngl") + 1] == "99"


def test_build_wikipedia_cli_starts_the_server_and_passes_resume_and_limit_through(env, monkeypatch):
    """build_wikipedia_cli mirrors build_cli's own start/stop pattern exactly, but calls
    build_wikipedia_rerank (a no-op here: no wikipedia_en_all_maxi row in library_items) rather than
    build()/build_household(), and threads --limit through to it."""
    seen_cmds, fake_run = _build_cli_fixture(env, monkeypatch)
    seen_calls = []
    real = embeddings.build_wikipedia_rerank

    def spy(conn, settings, embed, **kw):
        seen_calls.append(kw)
        return real(conn, settings, embed, **kw)

    monkeypatch.setattr(embeddings, "build_wikipedia_rerank", spy)
    rc = embeddings.build_wikipedia_cli(env, out=lambda s: None, run=fake_run, limit=5)
    assert rc == 0
    assert len(seen_cmds) == 1 and not seen_cmds[0][0].endswith("llama-server-cuda")
    assert seen_calls == [{"out": seen_calls[0]["out"], "resume": True, "limit": 5}]


# --- excluded_zims: the ZIM ids meaning search must never touch (Task 9) -------------------------------------


class _RealManifestSettings:
    """A bare stand-in carrying only what excluded_zims reads: the real repository manifest directory,
    never the fixtures one (env's SOS_MANIFEST_DIR points at tests/fixtures/manifest, which deliberately
    carries no StackExchange entries at all) -- this must be checked against the real manifest, per the
    task's own global constraint, not a hand-written short list."""
    manifests = REPO / "manifest"


def test_excluded_zims_contains_every_real_stackexchange_id_and_the_two_named_exclusions():
    from sos.embeddings import excluded_zims

    result = excluded_zims(_RealManifestSettings())
    assert "wiktionary_en_all_nopic" in result
    assert "wikipedia_cy_all_maxi" in result
    assert "ham.stackexchange.com_en_all" in result
    assert "homebrew.stackexchange.com_en_all" in result
    assert len([z for z in result if z.endswith(".stackexchange.com_en_all")]) >= 20  # the real current count


def test_household_zims_never_overlap_excluded_zims():
    from sos.embeddings import HOUSEHOLD_ZIMS, excluded_zims

    assert not (set(HOUSEHOLD_ZIMS) & excluded_zims(_RealManifestSettings()))


def test_excluded_zims_raises_loudly_rather_than_silently_under_excluding_on_a_wrong_manifest_dir(tmp_path):
    """Ruling 9's own point: load_manifests() glob()s a directory that may not exist and returns [] without
    raising -- a manifest directory that is simply wrong must not be allowed to look like "no StackExchange
    ZIMs today", since a caller could never tell the two apart otherwise. excluded_zims() must fail loudly
    instead of quietly handing back a dangerously small set."""
    from sos.embeddings import excluded_zims

    class EmptySettings:
        manifests = tmp_path / "does-not-exist"

    with pytest.raises(RuntimeError, match="zero"):
        excluded_zims(EmptySettings())


def test_excluded_zims_is_cached_and_does_not_re_read_the_manifest_directory_on_every_call(monkeypatch):
    """The lazy function must still only load_manifests() once per real settings.manifests path -- the
    whole reason it is cached rather than simply called fresh every time, since load_manifests() re-reads
    and re-parses every manifest JSON file from disk."""
    from sos import manifest as manifest_mod
    from sos.embeddings import excluded_zims

    calls = {"n": 0}
    real_load = manifest_mod.load_manifests

    def counting_load(dir):
        calls["n"] += 1
        return real_load(dir)

    monkeypatch.setattr(manifest_mod, "load_manifests", counting_load)
    excluded_zims(_RealManifestSettings())
    excluded_zims(_RealManifestSettings())
    assert calls["n"] <= 1  # already cached from an earlier test's call, or exactly one call from this test


# --- build_household: one vector per book across Gutenberg and Survivor Library -----------------------------

_REAL_PDF_BYTES = (FIXTURES / "docs" / "sos-test.pdf").read_bytes()   # a tiny, real, on-disk PDF -- no network


class FakeHouseholdZim:
    """A tiny fake ZIM reader: real book entries plus, for Survivor Library, one whose PDF has no
    usable text at all -- Task 5's real finding that about a fifth of that collection is a pure
    page-image scan with no text layer, which pdftotext cannot read either."""

    def __init__(self, books: dict[str, bytes]):
        self._books = books

    def read(self, path: str) -> bytes | None:
        return self._books.get(path)

    def has(self, path: str) -> bool:
        return path in self._books

    def paths(self):
        return iter(self._books)


GUTENBERG_BOOKS = {
    "Pride and Prejudice.1": b"<html><body><h1>Pride and Prejudice</h1><p>It is a truth universally "
        b"acknowledged, that a single man in possession of a good fortune, must be in want of a wife. "
        b"However little known the feelings or views of such a man may be on his first entering a "
        b"neighbourhood, this truth is so well fixed in the minds of the surrounding families.</p></body></html>",
    "Moby-Dick.2": b"<html><body><h1>Moby-Dick</h1><p>Call me Ishmael. Some years ago, having little or "
        b"no money in my purse, and nothing particular to interest me on shore, I thought I would sail "
        b"about a little and see the watery part of the world. It is a way I have of driving off the "
        b"spleen and regulating the circulation.</p></body></html>",
    "covers/1_cover_image.jpg": b"JPEG",              # not a bare "<slug>.<id>": never mistaken for a book
    "full_by_popularity.js": b"var json_data = [];",  # Gutenberg's catalogue entry: not a book either
}
SURVIVOR_BOOKS = {
    # a real PDF with real, if short, extractable text -- pdftotext genuinely runs against it in this test
    "www.survivorlibrary.com/library/blacksmithing.pdf": _REAL_PDF_BYTES,
    # a pure page-image scan (or here, simply a malformed PDF): pdftotext fails and it is skipped, not a crash
    "www.survivorlibrary.com/library/scanned-plate-12.pdf": b"%PDF-1.4\nnot a real pdf body",
    "_zim_static/theme/style.css": b"body{}",          # the zimit crawl's own noise: never under /library/
}


def test_build_household_embeds_real_text_and_skips_image_only_entries(tmp_path, monkeypatch):
    from sos.embeddings import ApproxIndex, build_household

    # this test is about the extraction/skip logic, not the exclusion list, so build_household's Task 9
    # excluded_zims(settings) assertion is stubbed out rather than coupling it to the real manifest.
    monkeypatch.setattr(embeddings, "excluded_zims", lambda settings: frozenset())

    def fake_open_zim(path):
        return FakeHouseholdZim(GUTENBERG_BOOKS if "gutenberg" in str(path) else SURVIVOR_BOOKS)

    def fake_embed(texts):
        return np.eye(len(texts), embeddings.DIMS, dtype=np.float32)   # deterministic, distinct per row

    conn = db.connect(tmp_path / "sos.db")
    db.init_schema(conn)
    conn.execute("INSERT INTO library_items (id, title, kind, tier, category, dest, priority, available, local_path) "
                 "VALUES ('gutenberg_en_all', 'Project Gutenberg', 'zim', 'core', 'books', 'zim/g.zim', 100, 1, ?)",
                 (str(tmp_path / "gutenberg_en_all.zim"),))
    conn.execute("INSERT INTO library_items (id, title, kind, tier, category, dest, priority, available, local_path) "
                 "VALUES ('survivorlibrary.com_en_all', 'Survivor Library', 'zim', 'core', 'books', 'zim/s.zim', 100, 1, ?)",
                 (str(tmp_path / "survivorlibrary.com_en_all.zim"),))
    conn.commit()

    lines = []
    result = build_household(conn, embeddings_settings(tmp_path), fake_embed, open_zim=fake_open_zim, out=lines.append)

    assert result["count"] == 3   # two Gutenberg books + one real Survivor Library book; the scan skipped
    assert result["seen"] == 4 and result["skipped_no_text"] == 1   # both /library/ PDFs seen; the corrupt one skipped
    idx = ApproxIndex.load(tmp_path, "household")
    assert idx is not None and len(idx) == 3
    assert set(idx.keys) == {"gutenberg_en_all:1", "gutenberg_en_all:2", "survivorlibrary.com_en_all:blacksmithing"}
    assert not any("scanned-plate" in k for k in idx.keys)
    assert any("household: gutenberg_en_all done, 2 books" in line for line in lines)
    assert any("household: survivorlibrary.com_en_all done, 1 books" in line for line in lines)


def embeddings_settings(tmp_path):
    """A bare stand-in for Settings carrying only what build_household and build_wikipedia_rerank read:
    embeddings_dir and embed_model. Deliberately has no `manifests` attribute: build_household's
    excluded_zims(settings) assertion is stubbed out by whichever caller needs it (via
    monkeypatch.setattr(embeddings, "excluded_zims", ...)) rather than this stand-in carrying a real
    manifest path, so tests that do not care about the exclusion list stay uncoupled from its content."""
    class FakeSettings:
        embeddings_dir = tmp_path
        embed_model = "bge-small-en-v1.5-q8_0.gguf"
    return FakeSettings()


def test_build_household_is_a_noop_for_a_zim_not_on_the_box(tmp_path, monkeypatch):
    from sos.embeddings import build_household

    # build_household's excluded_zims(settings) assertion runs at the top of its loop for every zim_id,
    # before the "not on the box" no-op check below is ever reached; this test is about the no-op path,
    # not the exclusion list, so the check is stubbed out rather than coupling it to the real manifest.
    monkeypatch.setattr(embeddings, "excluded_zims", lambda settings: frozenset())

    conn = db.connect(tmp_path / "sos.db")
    db.init_schema(conn)
    conn.commit()   # neither gutenberg_en_all nor survivorlibrary.com_en_all is in library_items at all

    lines = []
    result = build_household(conn, embeddings_settings(tmp_path), lambda texts: np.zeros((len(texts), embeddings.DIMS)),
                             open_zim=lambda p: (_ for _ in ()).throw(AssertionError("never opened")), out=lines.append)
    assert result["count"] == 0
    assert embeddings.ApproxIndex.load(tmp_path, "household") is None
    assert sum("is not on the box; skipped" in line for line in lines) == 2


@pytest.mark.skipif(not HAS_PDFTOTEXT, reason="pdftotext not installed")
def test_pdf_text_reads_a_real_pdf_and_returns_empty_on_a_corrupt_one():
    """The Survivor Library PDF-extraction path in isolation, against a tiny real PDF on disk (not the
    206 GiB Survivor Library ZIM): confirms the tempfile-plus-run_pdftotext plumbing genuinely works,
    separately from the fuller fixture-ZIM test above (which also exercises it, end to end)."""
    text = embeddings._pdf_text(_REAL_PDF_BYTES)
    assert "Boil water for one minute" in text and "Severe bleeding" in text
    assert embeddings._pdf_text(b"%PDF-1.4\nnot a real pdf body") == ""
    assert embeddings._pdf_text(b"") == ""


# --- WikipediaStore and build_wikipedia_rerank: a third, memory-mapped, rerank-only vector store --------------


def test_wikipedia_store_memory_maps_and_looks_up_by_key(tmp_path):
    from sos.embeddings import WikipediaStore
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


def test_wikipedia_store_load_returns_none_when_absent(tmp_path):
    from sos.embeddings import WikipediaStore
    assert WikipediaStore.load(tmp_path) is None


class FakeWikipediaZim:
    """A tiny fake ZIM reader for Wikipedia's own build: a hundred real article entries, one asset entry
    (never a real article, dropped by path alone -- `_assets_/` is the real prefix Task 8's own
    investigation against the live ZIM found holds every image, thumbnail and SVG) and one "soft
    redirect" stub (a real, non-structural-redirect entry whose body is just its title said twice, in
    under a hundred characters -- the real shape Task 8's spot check against the live ZIM found in 7 of
    40 sampled real entries). The same fixture pattern FakeHouseholdZim already establishes above for the
    household collection's own build."""

    def __init__(self, entries: dict[str, bytes]):
        self._entries = dict(entries)

    def read(self, path: str) -> bytes | None:
        return self._entries.get(path)

    def has(self, path: str) -> bool:
        return path in self._entries

    def paths(self):
        return iter(self._entries)


def _wiki_article_html(i: int) -> bytes:
    body = (f"This is the real body text of Wikipedia article number {i}, with enough distinct words in "
            f"it that every article's own real vector should differ from every other one once it is "
            f"embedded for real. Article {i} says so twice: article {i}, article {i}, article {i}.")
    return f"<html><body><h1>Article {i}</h1><p>{body}</p></body></html>".encode()


WIKI_ARTICLES = {f"Article_{i:03d}": _wiki_article_html(i) for i in range(100)}
WIKI_ARTICLES["_assets_/thumb/a1b2c3/Some_Picture.jpg"] = b"\xff\xd8\xff\xe0not a real article"
WIKI_ARTICLES["Soft_Redirect_Stub"] = b"<html><body><p>Soft Redirect Stub Soft Redirect Stub</p></body></html>"


def test_wikipedia_article_keys_drops_asset_entries_but_keeps_everything_else():
    from sos.embeddings import _wikipedia_article_keys
    keys = set(_wikipedia_article_keys(FakeWikipediaZim(WIKI_ARTICLES)))
    assert "_assets_/thumb/a1b2c3/Some_Picture.jpg" not in keys      # the one non-article entry, dropped
    assert "Article_000" in keys and "Soft_Redirect_Stub" in keys   # a stub is still a real article path
    assert len(keys) == len(WIKI_ARTICLES) - 1


def test_wikipedia_article_text_is_short_for_a_soft_redirect_stub_and_long_for_a_real_article():
    from sos.embeddings import SHORTEST_CHARS, _wikipedia_article_text
    reader = FakeWikipediaZim(WIKI_ARTICLES)
    stub_text = _wikipedia_article_text(reader, "Soft_Redirect_Stub")
    real_text = _wikipedia_article_text(reader, "Article_000")
    assert len(stub_text) < SHORTEST_CHARS      # the exact mechanism build_wikipedia_rerank skips it by
    assert len(real_text) >= SHORTEST_CHARS
    assert real_text.startswith("Article 000.")


def test_build_wikipedia_rerank_is_a_noop_for_a_zim_not_on_the_box(tmp_path):
    from sos.embeddings import build_wikipedia_rerank
    conn = db.connect(tmp_path / "sos.db")
    db.init_schema(conn)
    conn.commit()   # wikipedia_en_all_maxi is not in library_items at all

    lines = []
    result = build_wikipedia_rerank(
        conn, embeddings_settings(tmp_path), lambda texts: (_ for _ in ()).throw(AssertionError("never embedded")),
        open_zim=lambda p: (_ for _ in ()).throw(AssertionError("never opened")), out=lines.append)
    assert result == {"count": 0}
    assert any("not on the box; skipped" in line for line in lines)


def _insert_wikipedia_zim_row(conn, tmp_path) -> None:
    conn.execute("INSERT INTO library_items (id, title, kind, tier, category, dest, priority, available, local_path) "
                 "VALUES ('wikipedia_en_all_maxi', 'Wikipedia', 'zim', 'core', 'reference', 'zim/w.zim', 50, 1, ?)",
                 (str(tmp_path / "wikipedia_en_all_maxi.zim"),))
    conn.commit()


def test_wikipedia_store_treats_a_stubs_zero_vector_as_no_vector_at_all(tmp_path):
    """build_wikipedia_rerank itself leaves a soft-redirect stub as the zero vector its fixed-size
    vectors array was already zero-initialised to (never embedded, exactly like build_household skips a
    near-empty book) -- that part of the build is correct and unchanged. But every REAL embedded vector
    in this store is L2-normalised to unit norm, so a genuine cosine similarity against a real article
    lands somewhere in [-1, 1], and a real, dissimilar article can and does score below 0.0 -- the zero
    vector is not that range's floor, it is its orthogonal midpoint. Handing a stub's zero row back as a
    real vector would therefore rank it as an artificially middling match for every query, rather than
    correctly signalling "no real vector here", the same as a genuinely absent key. WikipediaStore.
    vector_for() must translate the build's zero row into None for exactly this reason -- the key stays
    present and countable (that contract does not change), it just has no vector."""
    from sos.embeddings import WikipediaStore, build_wikipedia_rerank

    conn = db.connect(tmp_path / "sos.db")
    db.init_schema(conn)
    _insert_wikipedia_zim_row(conn, tmp_path)
    reader = FakeWikipediaZim(WIKI_ARTICLES)

    def fake_embed(texts):
        return np.stack([unit(1, i) for i in range(len(texts))])

    result = build_wikipedia_rerank(conn, embeddings_settings(tmp_path), fake_embed,
                                    open_zim=lambda p: reader, out=lambda s: None)
    assert result["count"] == len(WIKI_ARTICLES) - 1    # every real, non-asset key, the stub included
    assert result["skipped_no_text"] == 1
    store = WikipediaStore.load(tmp_path)
    assert store is not None and len(store) == result["count"]
    assert "Soft_Redirect_Stub" in store.keys           # still present and countable, just no real vector
    assert store.vector_for("Soft_Redirect_Stub") is None   # no vector, not a middling zero-vector match
    real_vec = store.vector_for("Article_050")
    assert real_vec is not None and not np.allclose(real_vec, 0.0)


def test_build_wikipedia_rerank_limit_genuinely_caps_the_keys_embedded(tmp_path):
    """`limit` exists for a fast, real, small-scale throughput measurement against the full ZIM
    (`sos build-embeddings-wikipedia --limit N`) without doing the full multi-hour build. The only other
    test exercising it goes through build_wikipedia_cli against an empty database (no wikipedia_en_all_maxi
    row at all), so it short-circuits at the "not on the box" no-op before the real truncation
    (`all_keys = all_keys[:limit]`) is ever reached. This test calls build_wikipedia_rerank directly,
    against the same populated FakeWikipediaZim/WIKI_ARTICLES fixture the stub test above uses (101 real
    candidate keys, well more than N), and proves the cap is genuinely honoured -- not merely threaded
    through unused -- by checking the resulting store really only has N keys, all of them the first N in
    sorted order."""
    from sos.embeddings import WikipediaStore, _wikipedia_article_keys, build_wikipedia_rerank

    conn = db.connect(tmp_path / "sos.db")
    db.init_schema(conn)
    _insert_wikipedia_zim_row(conn, tmp_path)
    reader = FakeWikipediaZim(WIKI_ARTICLES)

    all_keys = sorted(_wikipedia_article_keys(reader))
    N = 10
    assert len(all_keys) > N   # genuinely more real candidate keys than the cap, or this proves nothing

    def fake_embed(texts):
        return np.stack([unit(1, i) for i in range(len(texts))])

    result = build_wikipedia_rerank(conn, embeddings_settings(tmp_path), fake_embed,
                                    open_zim=lambda p: reader, out=lambda s: None, limit=N)
    assert result["count"] == N
    assert WikipediaStore.load(tmp_path) is None
    store = WikipediaStore.load(tmp_path / "wikipedia-sample")
    assert store is not None and len(store) == N
    assert store.keys == all_keys[:N]   # the first N in sorted order, not an arbitrary N-sized subset


def _tracking_embed(calls_log: list, fail_at: int | None = None):
    """Wraps a deterministic fake embed call so a test can inspect exactly which texts each call received
    (Ruling 12: proving resumption genuinely skipped finished work, not just that a count came back). The
    text is logged *before* the simulated failure, so a caller can still see what an interrupted call was
    given -- exactly the batch resumption must return to, not re-embed from the start."""
    def embed(texts):
        calls_log.append(list(texts))
        if fail_at is not None and len(calls_log) == fail_at:
            raise RuntimeError("simulated interruption")
        return np.stack([unit(1, i) for i in range(len(texts))])
    return embed


def test_build_wikipedia_rerank_resumes_after_a_simulated_interruption(tmp_path, monkeypatch):
    """The one behaviour this whole task exists to deliver: a restart after an interruption must pick up
    exactly where it left off, never re-embedding a batch that already finished. Proved here by literally
    comparing which texts each run's embed calls received, not merely that a final count came back (a
    build that silently restarted from zero would produce the same final count and the same absent
    checkpoint file, so neither on its own tells resumed-correctly apart from restarted-from-scratch)."""
    from sos.embeddings import BATCH, WikipediaStore, _wikipedia_article_keys, build_wikipedia_rerank

    monkeypatch.setattr(embeddings, "CHECKPOINT_BATCHES", 1)   # a checkpoint every batch: fast, still real

    conn = db.connect(tmp_path / "sos.db")
    db.init_schema(conn)
    _insert_wikipedia_zim_row(conn, tmp_path)
    reader = FakeWikipediaZim(WIKI_ARTICLES)
    all_keys = sorted(_wikipedia_article_keys(reader))
    assert len(all_keys) == 101 and len(all_keys) > 3 * BATCH   # spans at least 3 BATCH-sized groups

    checkpoint_path = tmp_path / "wikipedia.checkpoint.json"
    part_path = tmp_path / "wikipedia.f16.bin.part"
    final_path = tmp_path / "wikipedia.f16.bin"

    calls_1: list = []
    # two full batches (64 keys) succeed and are checkpointed; the third call -- the interrupted batch --
    # is logged (so the test can see exactly what it was given) and then raises, same as a real crash.
    try:
        build_wikipedia_rerank(conn, embeddings_settings(tmp_path), _tracking_embed(calls_1, fail_at=3),
                               open_zim=lambda p: reader, out=lambda s: None, resume=False)
        assert False, "the simulated interruption should have propagated"
    except RuntimeError as exc:
        assert "simulated interruption" in str(exc)

    assert len(calls_1) == 3                       # batch 1, batch 2, then the interrupted batch 3
    assert checkpoint_path.is_file()
    state = json.loads(checkpoint_path.read_text())
    assert state["done"] == 2 * BATCH               # only the two genuinely finished batches were saved
    assert part_path.is_file()
    assert not final_path.is_file()                 # the build never reached its atomic handoff

    calls_2: list = []
    result = build_wikipedia_rerank(conn, embeddings_settings(tmp_path), _tracking_embed(calls_2, fail_at=None),
                                    open_zim=lambda p: reader, out=lambda s: None, resume=True)

    # the proof: the second run's very first embed call is given the interrupted batch's own texts again
    # (calls_1's third, un-returned call) -- not batch 1's texts, which would mean a silent restart.
    assert calls_2[0] == calls_1[2]
    assert calls_2[0] != calls_1[0]

    assert result["count"] == len(all_keys) == 101
    assert result["skipped_no_text"] == 1
    assert not checkpoint_path.exists()             # cleaned up on real completion
    assert final_path.is_file() and not part_path.exists()

    store = WikipediaStore.load(tmp_path)
    assert store is not None and len(store) == 101
    # the first key's vector was embedded in the *first* run (batch 1, never touched again) and survived
    # into the finished store untouched -- resume copied it forward rather than the second run recreating
    # it from scratch, which a fresh, differently-seeded embed would have made numerically different.
    assert np.allclose(store.vector_for(all_keys[0]), unit(1, 0), atol=0.01)
    assert "Soft_Redirect_Stub" in store.keys           # still present and countable, just no real vector
    assert store.vector_for("Soft_Redirect_Stub") is None


ROW_SQL = "INSERT INTO fts_docs(title, body, doc_id, kind, category, scenarios, page, url) VALUES (?,?,?,?,?,?,?,?)"


def _search(conn, env, q, sem, **kw):
    with respx.mock(base_url=BASE, assert_all_called=False) as m:
        m.get("/search").mock(return_value=httpx.Response(200, text="<rss><channel></channel></rss>"))
        return asyncio.run(search.search(conn, env, KiwixClient(BASE), q, semantic=sem, **kw))


def test_a_document_page_found_by_meaning_alone_needs_a_nearer_match_than_the_box_s_own_page(env):
    conn = db.connect(env.db_path)
    db.init_schema(conn)
    conn.executemany(ROW_SQL, [
        ("Approved Document L", "Renewable systems and their controls.", "adl#p69", "doc", "uk-official", "", 69, "/doc/ad-l1#page=69"),
        ("Mains electricity", "A generator or battery system, and where to put it.", "page:mains", "page", "playbooks", "", None, "/p/mains#generators"),
    ])
    conn.commit()
    # the building regulation is the nearest stranger at 0.71: not near enough for a document's page on its own
    sem = FakeSemantic([("/doc/ad-l1#page=69", 0.71), ("/p/mains#generators", 0.68)])
    urls = [r["url"] for r in _search(conn, env, "running a genset in the house", sem, use_cache=False)["results"]]
    assert urls == ["/p/mains#generators"]
    # nearer, it is an answer
    sem = FakeSemantic([("/doc/ad-l1#page=69", 0.76)])
    urls = [r["url"] for r in _search(conn, env, "running a genset in the house", sem, use_cache=False)["results"]]
    assert urls == ["/doc/ad-l1#page=69"]


def test_search_asks_the_or_when_the_and_finds_too_little_and_ranks_its_rows_after(env):
    conn = db.connect(env.db_path)
    db.init_schema(conn)
    conn.executemany(ROW_SQL, [
        ("Carbon monoxide", "Never run a generator indoors.", "card:co", "card", "playbooks", "", None, "/medical/card/co#steps"),
        ("Mains electricity", "A generator or battery system. Petrol is kept outside.", "page:mains", "page", "playbooks", "", None, "/p/mains#generators"),
        ("Water", "Boil it.", "module:water", "module", "playbooks", "", None, "/m/water"),
    ])
    conn.commit()
    urls = [r["url"] for r in _search(conn, env, "generator indoors", None, use_cache=False)["results"]]
    assert urls == ["/medical/card/co#steps", "/p/mains#generators"]   # both words first, then one of them; Water never


def test_search_drops_its_cache_when_the_semantic_index_changes(env):
    conn = db.connect(env.db_path)
    db.init_schema(conn)
    conn.executemany(ROW_SQL, [
        ("Food", "Keeps for years.", "module:food", "module", "playbooks", "", None, "/m/food"),
        ("Water", "Boil it.", "module:water", "module", "playbooks", "", None, "/m/water"),
    ])
    conn.commit()
    sem = FakeSemantic([("/m/food", 0.8)])
    sem.generation = 1
    assert [r["url"] for r in _search(conn, env, "larder", sem)["results"]] == ["/m/food"]
    sem.hits = [("/m/water", 0.8)]
    assert [r["url"] for r in _search(conn, env, "larder", sem)["results"]] == ["/m/food"]      # served from the cache
    sem.generation = 2                                                                            # a new index: forgotten
    assert [r["url"] for r in _search(conn, env, "larder", sem)["results"]] == ["/m/water"]


def test_semantic_generation_counts_each_load_of_the_index(env):
    sem = embeddings.Semantic(env)
    assert sem.generation == 0 and sem.index() is None
    embeddings.write_index(env.embeddings_dir, "docs", np.stack([unit(1, 0)]), ["/m/food"], {})
    assert sem.index() is not None and sem.generation == 1
    sem._checked = 0.0
    assert sem.index() is not None and sem.generation == 1                                       # unchanged: no new generation


def test_household_index_has_its_own_throttle_clock_not_shared_with_the_docs_index(env, monkeypatch):
    """search.py always calls query() (-> index()) before query_household() (-> household_index()) on
    every request. index() unconditionally resets its own throttle timestamp whenever it runs its real
    stat() check. If household_index() checked against that same timestamp, then once both collections
    have loaded, the docs check running microseconds ahead of the household one would always look "fresh"
    to the household guard, and household_index() would never run its own stat() check again -- a later
    `sos build-embeddings` rewriting household.hnsw would be silently ignored forever. household_index()
    must throttle against its own clock instead."""
    from sos.embeddings import ApproxIndex

    clock = {"t": 1_000.0}
    monkeypatch.setattr(embeddings.time, "monotonic", lambda: clock["t"])

    sem = embeddings.Semantic(env)
    embeddings.write_index(env.embeddings_dir, "docs", np.stack([unit(1, 0)]), ["/m/food"], {})
    ApproxIndex.build(np.stack([unit(1, 0)]), ["book:1"]).save(env.embeddings_dir, "household")
    assert sem.index() is not None and sem.household_index() is not None
    assert sem.generation == 2

    clock["t"] += 31                                              # both 30s throttles have now elapsed

    # a later `sos build-embeddings` run rewrites household.hnsw with new content and a fresh mtime
    hnsw_path = env.embeddings_dir / "household.hnsw"
    stamp = hnsw_path.stat().st_mtime
    ApproxIndex.build(np.stack([unit(1, 0), unit(0, 1)]), ["book:1", "book:2"]).save(env.embeddings_dir, "household")
    os.utime(hnsw_path, (stamp + 5, stamp + 5))

    sem.index()                                                   # the docs check search.py always runs first
    clock["t"] += 0.001                                           # microseconds later, as in a real request
    reloaded = sem.household_index()
    assert reloaded is not None and len(reloaded) == 2            # the rebuilt index, not the stale 1-book one
    assert sem.generation == 3                                    # so search.py's results cache invalidates too


def test_passage_text_drops_the_section_heading_and_build_skips_the_link_lists(env):
    assert embeddings.passage_text("Water", "What to do 1. Fill every container.", "/m/water#what-to-do") == "Water. 1. Fill every container."
    conn = db.connect(env.db_path)
    db.init_schema(conn)
    conn.executemany(ROW_SQL, [
        ("Water", "What to do 1. Fill it.", "module:water", "module", "playbooks", "", None, "/m/water#what-to-do"),
        ("Water", "Go deeper - Water outdoors - Food", "module:water", "module", "playbooks", "", None, "/m/water#go-deeper"),
        ("Shock", "Source - NHS - Resuscitation Council", "card:shock", "card", "playbooks", "", None, "/medical/card/shock#source"),
    ])
    conn.commit()
    seen: list[str] = []

    def fake_embed(texts):
        seen.extend(texts)
        return np.stack([unit(1, i) for i in range(len(texts))])

    meta = embeddings.build(conn, env, fake_embed, out=lambda s: None)
    assert seen == ["Water. 1. Fill it."] and meta["count"] == 1


def test_household_entries_extract_lazily():
    class Reader(FakeHouseholdZim):
        def read(self, path):
            if path == 'second.2':
                raise AssertionError('read ahead of the consumer')
            return b'<p>' + b'Useful words. ' * 30 + b'</p>'
    entries = embeddings._household_entries(Reader({'first.1': b'', 'second.2': b''}), 'gutenberg_en_all')
    assert next(entries)[0] == 'gutenberg_en_all:1'


@pytest.mark.parametrize('damage', ['missing', 'truncated', 'corrupt_checkpoint'])
def test_wikipedia_bad_checkpoint_reembeds_instead_of_publishing_zero_rows(tmp_path, monkeypatch, damage):
    monkeypatch.setattr(embeddings, 'CHECKPOINT_BATCHES', 1)
    conn = db.connect(tmp_path / 'sos.db')
    db.init_schema(conn)
    _insert_wikipedia_zim_row(conn, tmp_path)
    reader = FakeWikipediaZim(WIKI_ARTICLES)
    first = []
    with pytest.raises(RuntimeError, match='simulated interruption'):
        embeddings.build_wikipedia_rerank(conn, embeddings_settings(tmp_path), _tracking_embed(first, fail_at=2),
                                         open_zim=lambda p: reader, out=lambda s: None)
    part = tmp_path / 'wikipedia.f16.bin.part'
    if damage == 'missing':
        part.unlink()
    elif damage == 'truncated':
        part.write_bytes(b'bad')
    else:
        (tmp_path / 'wikipedia.checkpoint.json').write_text('{')
    second = []
    result = embeddings.build_wikipedia_rerank(conn, embeddings_settings(tmp_path), _tracking_embed(second),
                                              open_zim=lambda p: reader, out=lambda s: None)
    assert second[0] == first[0]
    assert result['seen'] == 101
    assert embeddings.WikipediaStore.load(tmp_path).vector_for('Article_000') is not None


def test_wikipedia_resumption_preserves_skipped_counts(tmp_path, monkeypatch):
    monkeypatch.setattr(embeddings, 'CHECKPOINT_BATCHES', 1)
    conn = db.connect(tmp_path / 'sos.db')
    db.init_schema(conn)
    _insert_wikipedia_zim_row(conn, tmp_path)
    reader = FakeWikipediaZim({'AAA_stub': b'<p>stub</p>', **WIKI_ARTICLES})
    with pytest.raises(RuntimeError, match='simulated interruption'):
        embeddings.build_wikipedia_rerank(conn, embeddings_settings(tmp_path), _tracking_embed([], fail_at=2),
                                         open_zim=lambda p: reader, out=lambda s: None)
    result = embeddings.build_wikipedia_rerank(conn, embeddings_settings(tmp_path), _tracking_embed([]),
                                              open_zim=lambda p: reader, out=lambda s: None)
    assert result['seen'] == 102 and result['skipped_no_text'] == 2


@pytest.mark.parametrize('collection', ['household', 'wikipedia'])
def test_unreadable_zim_is_a_noop(tmp_path, monkeypatch, collection):
    monkeypatch.setattr(embeddings, 'excluded_zims', lambda settings: frozenset())
    conn = db.connect(tmp_path / 'sos.db')
    db.init_schema(conn)
    zim = embeddings.WIKIPEDIA_ZIM if collection == 'wikipedia' else embeddings.HOUSEHOLD_ZIMS[0]
    conn.execute('INSERT INTO library_items(id, available, local_path) VALUES (?, 1, ?)', (zim, 'bad.zim'))
    def unreadable(path):
        raise RuntimeError('invalid ZIM')
    build = embeddings.build_wikipedia_rerank if collection == 'wikipedia' else embeddings.build_household
    assert build(conn, embeddings_settings(tmp_path), lambda texts: pytest.fail('must not embed'),
                 open_zim=unreadable, out=lambda s: None)['count'] == 0


def test_publication_interruption_keeps_the_previous_generation(tmp_path, monkeypatch):
    embeddings.write_index(tmp_path, 'docs', np.stack([unit(1, 0)]), ['old'], {'count': 1})
    replace = os.replace
    def interrupted(src, dst):
        if Path(dst).name == 'docs.current':
            raise OSError('interrupted publication')
        return replace(src, dst)
    monkeypatch.setattr(os, 'replace', interrupted)
    with pytest.raises(OSError, match='interrupted publication'):
        embeddings.write_index(tmp_path, 'docs', np.stack([unit(0, 1)]), ['new'], {'count': 1})
    index = embeddings.Index.load(tmp_path, 'docs')
    assert index.keys == ['old']
    assert np.allclose(index.vectors[0], unit(1, 0))


def test_search_drops_unknown_or_unavailable_household_sources(env):
    conn = db.connect(env.db_path)
    db.init_schema(conn)
    conn.execute("INSERT INTO library_items(id, available) VALUES ('gutenberg_en_all', 0)")
    sem = FakeSemantic([], household_hits=[('wiktionary_en_all_nopic:forge', .9),
                                          ('gutenberg_en_all:2701', .9)])
    response = _search(conn, env, 'whaling voyage', sem, use_cache=False)
    assert not [r for r in response['results'] if r.get('via') == 'meaning']


def test_wikipedia_measurement_preserves_live_index_and_full_checkpoint(tmp_path):
    conn = db.connect(tmp_path / 'sos.db')
    db.init_schema(conn)
    _insert_wikipedia_zim_row(conn, tmp_path)
    embeddings.write_index(tmp_path, 'wikipedia', np.stack([unit(1, 0)]), ['Live'], {'count': 1})
    checkpoint = tmp_path / 'wikipedia.checkpoint.json'
    checkpoint.write_text('full build checkpoint')
    (tmp_path / 'wikipedia.f16.bin.part').write_bytes(b'full build work')
    reader = FakeWikipediaZim(WIKI_ARTICLES)
    embeddings.build_wikipedia_rerank(conn, embeddings_settings(tmp_path), _tracking_embed([]),
                                     open_zim=lambda p: reader, out=lambda s: None, limit=10)
    assert embeddings.WikipediaStore.load(tmp_path).keys == ['Live']
    assert checkpoint.read_text() == 'full build checkpoint'
    assert (tmp_path / 'wikipedia.f16.bin.part').read_bytes() == b'full build work'
    assert len(embeddings.WikipediaStore.load(tmp_path / 'wikipedia-sample')) == 10


def test_missing_household_archives_preserve_published_index_and_metadata(tmp_path, monkeypatch):
    monkeypatch.setattr(embeddings, 'excluded_zims', lambda settings: frozenset())
    conn = db.connect(tmp_path / 'sos.db')
    db.init_schema(conn)
    embeddings.ApproxIndex.build(np.stack([unit(1, 0)]), ['book:1']).save(tmp_path, 'household')
    meta = tmp_path / 'household.meta.json'
    meta.write_text('{"count": 1}')
    embeddings.build_household(conn, embeddings_settings(tmp_path), _tracking_embed([]), out=lambda s: None)
    assert embeddings.ApproxIndex.load(tmp_path, 'household').keys == ['book:1']
    assert json.loads(meta.read_text())['count'] == 1


@pytest.mark.parametrize("html", [
    '<p>Opening words. </p>' * 1000,
    '<p>Page furniture. </p>' * 1000 + '<main><p>Actual text. </p>' * 1000 + '</main>',
    '<p>Page furniture. </p>' * 1000 + '<div id="maincontent"><p>Actual text. </p>' * 1000 + '</div>',
    '<script>' + 'ignored; ' * 1000 + '</script><p>' + 'A long paragraph. ' * 1000 + '</p>',
])
def test_bounded_html_extraction_preserves_the_full_extraction_prefix(html):
    from sos.kiwix import extract_text
    limit = embeddings.HOUSEHOLD_TEXT_CHARS
    assert ' '.join(extract_text(html, max_chars=limit))[:limit] == ' '.join(extract_text(html))[:limit]


def test_household_only_cli_does_not_rebuild_docs(env, monkeypatch):
    _, run = _build_cli_fixture(env, monkeypatch)
    monkeypatch.setattr(embeddings, 'build', lambda *a, **k: pytest.fail('docs must stay unchanged'))
    called = []
    monkeypatch.setattr(embeddings, 'build_household', lambda *a, **k: called.append(True))
    assert embeddings.build_cli(env, run=run, out=lambda s: None, collection='household') == 0
    assert called == [True]
