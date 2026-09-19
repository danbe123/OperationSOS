"""Semantic search: the passage text, the index, the build, the query prefix, and the fusion into search."""
import asyncio
import hashlib
import json
import logging
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
def test_semantic_query_prefixes_the_query_and_answers_nothing_when_the_server_or_index_is_away(
        env, respx_mock, monkeypatch):
    clock = {"t": 1_000.0}
    monkeypatch.setattr(embeddings.time, "monotonic", lambda: clock["t"])
    sem = embeddings.Semantic(env)
    assert asyncio.run(sem.query("tinned food")) == []          # no index yet
    embeddings.write_index(env.embeddings_dir, "docs", np.stack([unit(1, 0), unit(0, 1)]), ["/m/food", "/m/water"], {})
    clock["t"] += 31                                            # a collection that is away is throttled too
    sent = {}

    def reply(request):
        sent["body"] = json.loads(request.content)
        return httpx.Response(200, json=[{"index": 0, "embedding": [[1.0] + [0.0] * (embeddings.DIMS - 1)]}])

    respx_mock.post(f"{env.embed_url}/embeddings").mock(side_effect=reply)
    hits = asyncio.run(sem.query("tinned food", k=1))
    assert hits == [("/m/food", pytest.approx(1.0))]
    assert sent["body"] == {"input": [embeddings.QUERY_PREFIX + "tinned food"]}
    respx_mock.post(f"{env.embed_url}/embeddings").mock(return_value=httpx.Response(503))
    clock["t"] += 31                                            # past the memo of the words just embedded
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


def test_build_wikipedia_cli_starts_the_server_and_passes_resume_limit_and_workers_through(env, monkeypatch):
    """build_wikipedia_cli mirrors build_cli's own start/stop pattern exactly, but calls
    build_wikipedia_rerank (a no-op here: no wikipedia_en_all_maxi row in library_items) rather than
    build()/build_household(), and threads --limit and --workers through to it."""
    seen_cmds, fake_run = _build_cli_fixture(env, monkeypatch)
    seen_calls = []
    real = embeddings.build_wikipedia_rerank

    def spy(conn, settings, embed, **kw):
        seen_calls.append(kw)
        return real(conn, settings, embed, **kw)

    monkeypatch.setattr(embeddings, "build_wikipedia_rerank", spy)
    rc = embeddings.build_wikipedia_cli(env, out=lambda s: None, run=fake_run, limit=5, workers=4)
    assert rc == 0
    assert len(seen_cmds) == 1 and not seen_cmds[0][0].endswith("llama-server-cuda")
    assert seen_calls == [{"out": seen_calls[0]["out"], "resume": True, "limit": 5, "workers": 4}]


# --- --servers N: several embedding servers side by side ------------------------------------------------
#
# One llama-server's request loop is single-threaded (HTTP, JSON, tokenising, serialising 32x384 floats)
# and is the real ceiling on the GPU builds: measured on the production Wikipedia build, the GPU sits at
# 28-45 W of 220 W while the server's main thread sits at ~70 per cent of one core. These tests use fake
# servers and a fake embed_sync throughout: no port is ever listened on.


class FakeServerProcess:
    def __init__(self, cmd):
        self.cmd = cmd
        self.terminated = False

    @property
    def port(self) -> str:
        return self.cmd[self.cmd.index("--port") + 1]

    def terminate(self):
        self.terminated = True


def _fake_servers(env, monkeypatch, healthy=()):
    """A model file on disk, `/health` answering 200 for the ports in `healthy` (and for every port this
    fake `run` is asked to start, so the wait loop finishes), and a record of what was started."""
    env.embed_model_path.parent.mkdir(parents=True, exist_ok=True)
    env.embed_model_path.write_bytes(b"")
    started: list[FakeServerProcess] = []
    live = {str(p) for p in healthy}

    def fake_get(url, timeout=1.0):
        if url.rsplit(":", 1)[1].partition("/")[0] in live:
            return httpx.Response(200)
        raise httpx.HTTPError("not ready")

    def fake_run(cmd, **kw):
        process = FakeServerProcess(cmd)
        live.add(process.port)
        started.append(process)
        return process

    monkeypatch.setattr(embeddings.httpx, "get", fake_get)
    monkeypatch.setattr(embeddings.time, "sleep", lambda s: None)
    return started, fake_run


def _fake_embed_sync(monkeypatch, seen=None, fails_on=None, barrier=None):
    def fake_embed_sync(url, texts, timeout=120.0, client=None):
        if barrier is not None:
            barrier.wait()      # nothing comes back until every server has been asked: they really overlap
        if seen is not None:
            seen.append((url, list(texts)))
        if fails_on is not None and url.endswith(fails_on):
            raise embeddings.EmbedError("embedding server returned 500")
        return np.stack([unit(1, int(t)) for t in texts])

    monkeypatch.setattr(embeddings, "embed_sync", fake_embed_sync)


def test_several_embedding_servers_split_each_batch_in_order_and_run_at_once(env, monkeypatch):
    import threading

    started, fake_run = _fake_servers(env, monkeypatch)
    seen: list[tuple[str, list[str]]] = []
    _fake_embed_sync(monkeypatch, seen=seen, barrier=threading.Barrier(3, timeout=60))
    texts = [str(i) for i in range(8)]

    with embeddings.embedding_servers(env, out=lambda s: None, run=fake_run, servers=3) as embed:
        vectors = embed(texts)

    assert [p.port for p in started] == ["8091", "8092", "8093"]   # consecutive from settings.embed_url
    assert sorted(seen) == [("http://127.0.0.1:8091", ["0", "1", "2"]),
                            ("http://127.0.0.1:8092", ["3", "4", "5"]),
                            ("http://127.0.0.1:8093", ["6", "7"])]  # contiguous slices, none left out
    # and put back together in the order the caller gave them, not the order the servers answered in
    assert np.allclose(vectors, np.stack([unit(1, i) for i in range(8)]))
    assert all(p.terminated for p in started)


def test_one_embedding_server_sends_the_whole_batch_to_the_one_url(env, monkeypatch):
    """N=1 is what this build has always done: one server, one request, no slicing and no threads."""
    started, fake_run = _fake_servers(env, monkeypatch)
    seen: list[tuple[str, list[str]]] = []
    _fake_embed_sync(monkeypatch, seen=seen)

    with embeddings.embedding_servers(env, out=lambda s: None, run=fake_run, servers=1) as embed:
        embed(["0", "1", "2"])

    assert seen == [(env.embed_url, ["0", "1", "2"])]
    assert [p.port for p in started] == ["8091"] and started[0].terminated


def test_a_server_already_answering_on_its_port_is_reused_rather_than_started_again(env, monkeypatch):
    started, fake_run = _fake_servers(env, monkeypatch, healthy=(8091,))
    _fake_embed_sync(monkeypatch)

    with embeddings.embedding_servers(env, out=lambda s: None, run=fake_run, servers=3) as embed:
        embed(["0", "1", "2"])

    assert [p.port for p in started] == ["8092", "8093"]   # the live one is used, never duplicated
    assert all(p.terminated for p in started)              # and only what we started is stopped again


def test_a_failing_server_raises_embed_error_and_stops_every_server_that_was_started(env, monkeypatch):
    """embed_batch shortens an over-long passage and retries after an EmbedError, so the multi-server
    call has to fail exactly as embed_sync does or that recovery silently stops working."""
    started, fake_run = _fake_servers(env, monkeypatch)
    _fake_embed_sync(monkeypatch, fails_on="8092")

    with pytest.raises(embeddings.EmbedError):
        with embeddings.embedding_servers(env, out=lambda s: None, run=fake_run, servers=3) as embed:
            embed(["0", "1", "2"])
    assert len(started) == 3 and all(p.terminated for p in started)


def test_embedding_servers_rejects_a_nonpositive_count(env, monkeypatch):
    started, fake_run = _fake_servers(env, monkeypatch)
    with pytest.raises(ValueError, match="servers"):
        with embeddings.embedding_servers(env, out=lambda s: None, run=fake_run, servers=0):
            pass
    assert started == []


@pytest.mark.parametrize("build, kwargs", [("build_cli", {"collection": "docs"}),
                                           ("build_wikipedia_cli", {})])
def test_both_builds_run_the_servers_they_were_asked_for_and_stop_them(env, monkeypatch, build, kwargs):
    conn = db.connect(env.db_path)
    db.init_schema(conn)
    conn.close()
    started, fake_run = _fake_servers(env, monkeypatch)
    _fake_embed_sync(monkeypatch)
    rc = getattr(embeddings, build)(env, out=lambda s: None, run=fake_run, servers=3, **kwargs)
    assert rc == 0
    assert [p.port for p in started] == ["8091", "8092", "8093"]
    assert all(p.terminated for p in started)


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
    # The real ZIM's own duplicate shapes for a book that already has its article above (measured against
    # gutenberg_en_all.zim: 60,359 "<slug>_cover.<id>" pages of about 330 characters, and 16,455 ids with a
    # second, differently-named page -- very often the author's name). Both match `<something>.<id>`, both
    # are long enough to embed, and both would key on the same book id.
    "Pride and Prejudice_cover.1": b"<html><body><h1>Pride and Prejudice</h1><p>Read this book online or "
        b"download it as an EPUB, a Kindle file or a plain text file from Project Gutenberg, the oldest "
        b"digital library of free electronic books, founded in 1971 by Michael Hart. Cover image courtesy "
        b"of the Project Gutenberg collection. Language: English. Downloads this month: 31,415.</p></body></html>",
    "Jane Austen.1": b"<html><body><h1>Jane Austen</h1><p>It is a truth universally acknowledged, that a "
        b"single man in possession of a good fortune, must be in want of a wife. However little known the "
        b"feelings or views of such a man may be on his first entering a neighbourhood, this truth is so "
        b"well fixed in the minds of the surrounding families.</p></body></html>",
    # a real article-shaped entry for an id the catalogue does not carry at all (3,794 of these on the real
    # ZIM): never a book the box can open, so never a vector
    "Unlisted Pamphlet.999": b"<html><body><h1>Unlisted Pamphlet</h1><p>This entry looks exactly like a "
        b"real book article and is long enough to embed, but no row of the Gutenberg catalogue mentions "
        b"book 999 at all, so the box has no title, no author and no way to open it for a reader.</p></body></html>",
    "covers/1_cover_image.jpg": b"JPEG",              # not a bare "<slug>.<id>": never mistaken for a book
    "full_by_popularity.js": b"var json_data = [];",  # Gutenberg's catalogue entry: not a book either
}
# (id, title, author, html_path) -- what `sos index` (books.index_books) leaves in the `books` table for the
# ZIM above: the two real books, one of them with no author, and a third the ZIM has no HTML for at all.
GUTENBERG_CATALOGUE = [
    (1, "Pride and Prejudice", "Jane Austen", "Pride and Prejudice.1"),
    (2, "Moby-Dick; Or, The Whale", None, "Moby-Dick.2"),
    (3, "A Book This ZIM Has No HTML For", "Anon", None),
]
SURVIVOR_BOOKS = {
    # a real PDF with real, if short, extractable text -- pdftotext genuinely runs against it in this test
    "www.survivorlibrary.com/library/blacksmithing.pdf": _REAL_PDF_BYTES,
    # a pure page-image scan (or here, simply a malformed PDF): pdftotext fails and it is skipped, not a crash
    "www.survivorlibrary.com/library/scanned-plate-12.pdf": b"%PDF-1.4\nnot a real pdf body",
    "_zim_static/theme/style.css": b"body{}",          # the zimit crawl's own noise: never under /library/
}


def fake_household_open_zim(path):
    return FakeHouseholdZim(GUTENBERG_BOOKS if "gutenberg" in str(path) else SURVIVOR_BOOKS)


def _household_conn(tmp_path, catalogue=GUTENBERG_CATALOGUE):
    """Both household ZIMs on the box, and whatever `sos index` would have left in `books` for Gutenberg."""
    conn = db.connect(tmp_path / "sos.db")
    db.init_schema(conn)
    conn.execute("INSERT INTO library_items (id, title, kind, tier, category, dest, priority, available, local_path) "
                 "VALUES ('gutenberg_en_all', 'Project Gutenberg', 'zim', 'core', 'books', 'zim/g.zim', 100, 1, ?)",
                 (str(tmp_path / "gutenberg_en_all.zim"),))
    conn.execute("INSERT INTO library_items (id, title, kind, tier, category, dest, priority, available, local_path) "
                 "VALUES ('survivorlibrary.com_en_all', 'Survivor Library', 'zim', 'core', 'books', 'zim/s.zim', 100, 1, ?)",
                 (str(tmp_path / "survivorlibrary.com_en_all.zim"),))
    conn.executemany("INSERT INTO books (zim, id, title, author, shelf, popularity, epub_path, html_path, cover_path) "
                     "VALUES ('gutenberg_en_all', ?, ?, ?, NULL, 0, NULL, ?, NULL)", catalogue)
    conn.commit()
    return conn


def test_build_household_embeds_real_text_and_skips_image_only_entries(tmp_path, monkeypatch):
    from sos.embeddings import ApproxIndex, build_household

    # this test is about the extraction/skip logic, not the exclusion list, so build_household's Task 9
    # excluded_zims(settings) assertion is stubbed out rather than coupling it to the real manifest.
    monkeypatch.setattr(embeddings, "excluded_zims", lambda settings: frozenset())
    fake_open_zim = fake_household_open_zim

    def fake_embed(texts):
        return np.eye(len(texts), embeddings.DIMS, dtype=np.float32)   # deterministic, distinct per row

    conn = _household_conn(tmp_path)

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


def test_build_household_embeds_one_vector_per_catalogue_book_with_its_author(tmp_path, monkeypatch):
    """The correctness bug this build had: driven by a path scan, the real ZIM's cover pages and
    author-named alias pages gave several vectors the same `gutenberg_en_all:<id>` key (which search()
    then lifted once per copy), and ids the catalogue has never heard of were embedded too. Driven by the
    catalogue there is exactly one vector per book, its text is the catalogue's own title and author, and
    a book the catalogue has no HTML for is not embedded at all."""
    monkeypatch.setattr(embeddings, "excluded_zims", lambda settings: frozenset())
    seen: list[str] = []

    def fake_embed(texts):
        seen.extend(texts)
        return np.eye(len(texts), embeddings.DIMS, dtype=np.float32)

    conn = _household_conn(tmp_path)
    result = embeddings.build_household(conn, embeddings_settings(tmp_path), fake_embed,
                                        open_zim=fake_household_open_zim, out=lambda s: None)

    gutenberg = [t for t in seen if not t.startswith("blacksmithing")]
    assert len(gutenberg) == 2                      # one per catalogue book, not one per matching entry
    # the catalogue's title (not the entry name "Moby-Dick") and its author, which the path scan never had
    assert gutenberg[0].startswith("Pride and Prejudice by Jane Austen. ")
    assert "It is a truth universally acknowledged" in gutenberg[0]
    assert gutenberg[1].startswith("Moby-Dick; Or, The Whale. ")   # no author in the catalogue, none embedded
    assert "Call me Ishmael" in gutenberg[1] and " by " not in gutenberg[1].split(". ")[0]
    assert not any("Cover image courtesy" in t for t in seen)        # the cover page is not a book
    assert not any("Unlisted Pamphlet" in t for t in seen)           # nor is an id the catalogue lacks
    assert not any("A Book This ZIM Has No HTML For" in t for t in seen)
    keys = embeddings.ApproxIndex.load(tmp_path, "household").keys
    assert sorted(keys) == ["gutenberg_en_all:1", "gutenberg_en_all:2",
                            "survivorlibrary.com_en_all:blacksmithing"]
    assert len(set(keys)) == len(keys) == result["count"]


def test_build_household_skips_gutenberg_when_the_catalogue_has_not_been_built(tmp_path, monkeypatch):
    """No catalogue means no titles, no authors and no way to tell a book's article from its cover page:
    say so and leave Gutenberg alone rather than falling back to the path scan this build just left."""
    monkeypatch.setattr(embeddings, "excluded_zims", lambda settings: frozenset())
    conn = _household_conn(tmp_path, catalogue=[])
    lines: list[str] = []
    result = embeddings.build_household(conn, embeddings_settings(tmp_path),
                                        lambda texts: np.eye(len(texts), embeddings.DIMS, dtype=np.float32),
                                        open_zim=fake_household_open_zim, out=lines.append)
    assert result["count"] == 1   # the Survivor Library book only
    assert embeddings.ApproxIndex.load(tmp_path, "household").keys == ["survivorlibrary.com_en_all:blacksmithing"]
    assert any("sos index" in line for line in lines)


def test_build_household_refuses_to_build_an_index_with_duplicate_keys(tmp_path, monkeypatch):
    """A last line of defence: two vectors under one key silently double-count that book in search(), so
    a duplicate must never reach ApproxIndex.build however it got into the entry stream."""
    monkeypatch.setattr(embeddings, "excluded_zims", lambda settings: frozenset())
    monkeypatch.setattr(embeddings, "_household_entries",
                        lambda reader, zim_id, conn=None: iter(
                            [(f"{zim_id}:7", "Twice Over", "Useful words. " * 40)] * 2))
    conn = _household_conn(tmp_path)
    with pytest.raises(ValueError, match="gutenberg_en_all:7"):
        embeddings.build_household(conn, embeddings_settings(tmp_path),
                                   lambda texts: np.eye(len(texts), embeddings.DIMS, dtype=np.float32),
                                   open_zim=fake_household_open_zim, out=lambda s: None)
    assert embeddings.ApproxIndex.load(tmp_path, "household") is None


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


# --- publishing the household collection: never a quietly smaller index, never a meta of its own ------------


def _household_embed(texts):
    return np.eye(len(texts), embeddings.DIMS, dtype=np.float32)


def _published_household(folder) -> dict[str, bytes]:
    """Every byte a reader of the published household collection can see, generation and all."""
    folder = Path(folder)
    generation = embeddings._collection_folder(folder, "household")
    seen = {name: (generation / f"household.{name}").read_bytes() for name in ("hnsw", "ids")}
    seen["meta.json"] = (folder / "household.meta.json").read_bytes()
    seen["current"] = os.readlink(folder / "household.current").encode("utf-8")
    return seen


def test_household_meta_counts_the_books_each_zim_gave_and_rides_in_the_same_generation(tmp_path, monkeypatch):
    """The meta has to be published with the vectors it describes, in the one generation directory the
    `.current` symlink swings to, or a reader that resolves both between the index rename and the meta
    rename sees a new index described by an old meta."""
    monkeypatch.setattr(embeddings, "excluded_zims", lambda settings: frozenset())
    conn = _household_conn(tmp_path)
    meta = embeddings.build_household(conn, embeddings_settings(tmp_path), _household_embed,
                                      open_zim=fake_household_open_zim, out=lambda s: None)
    assert meta["by_zim"] == {"gutenberg_en_all": 2, "survivorlibrary.com_en_all": 1}
    assert sum(meta["by_zim"].values()) == meta["count"] == 3

    generation = embeddings._collection_folder(tmp_path, "household")
    assert generation != tmp_path                                   # a real published generation
    assert json.loads((generation / "household.meta.json").read_text())["by_zim"] == meta["by_zim"]
    assert (tmp_path / "household.meta.json").resolve().parent == (tmp_path / "household.hnsw").resolve().parent


def test_a_partial_household_rebuild_refuses_to_publish_a_smaller_index(tmp_path, monkeypatch):
    """The real failure: with both collections published, a rebuild run while only Gutenberg was mounted
    quietly published a Gutenberg-only index and meta, and Survivor Library was simply gone from search.
    A ZIM that had books in the published index and none in this run means something is wrong with the
    box, not with the library, so nothing is published at all until an operator says otherwise."""
    monkeypatch.setattr(embeddings, "excluded_zims", lambda settings: frozenset())
    conn = _household_conn(tmp_path)
    settings = embeddings_settings(tmp_path)
    embeddings.build_household(conn, settings, _household_embed, open_zim=fake_household_open_zim,
                               out=lambda s: None)
    before = _published_household(tmp_path)

    conn.execute("UPDATE library_items SET available=0 WHERE id='survivorlibrary.com_en_all'")
    conn.commit()
    lines: list[str] = []
    result = embeddings.build_household(conn, settings, _household_embed, open_zim=fake_household_open_zim,
                                        out=lines.append)
    said = "\n".join(lines)
    assert "survivorlibrary.com_en_all" in said and "refus" in said
    assert "household.*" in said and "delete" in said              # how to go ahead deliberately
    assert _published_household(tmp_path) == before                # byte for byte, generation and all
    assert result["count"] == 2 and result["by_zim"]["survivorlibrary.com_en_all"] == 0


def test_a_first_household_build_with_only_one_collection_present_still_publishes(tmp_path, monkeypatch):
    """Nothing published yet means nothing to lose: a box that has Gutenberg and not Survivor Library
    must still get a Gutenberg index, and the refusal above must not turn into a build that never runs."""
    monkeypatch.setattr(embeddings, "excluded_zims", lambda settings: frozenset())
    conn = _household_conn(tmp_path)
    conn.execute("UPDATE library_items SET available=0 WHERE id='survivorlibrary.com_en_all'")
    conn.commit()
    result = embeddings.build_household(conn, embeddings_settings(tmp_path), _household_embed,
                                        open_zim=fake_household_open_zim, out=lambda s: None)
    assert result["by_zim"] == {"gutenberg_en_all": 2, "survivorlibrary.com_en_all": 0}
    assert embeddings.ApproxIndex.load(tmp_path, "household").keys == ["gutenberg_en_all:1", "gutenberg_en_all:2"]


def test_a_partial_rebuild_is_refused_against_a_published_index_written_before_by_zim_existed(tmp_path, monkeypatch):
    """The index already on the box was published by the old code and its meta has no by_zim at all. The
    published keys are "<zim id>:<book id>", so they say which collections were in it just as well."""
    monkeypatch.setattr(embeddings, "excluded_zims", lambda settings: frozenset())
    conn = _household_conn(tmp_path)
    embeddings.ApproxIndex.build(np.stack([unit(1, 0), unit(0, 1)]),
                                 ["gutenberg_en_all:1", "survivorlibrary.com_en_all:blacksmithing"]
                                 ).save(tmp_path, "household")
    (tmp_path / "household.meta.json").write_text('{"count": 2}')
    before = _published_household(tmp_path)
    conn.execute("UPDATE library_items SET available=0 WHERE id='survivorlibrary.com_en_all'")
    conn.commit()
    lines: list[str] = []
    embeddings.build_household(conn, embeddings_settings(tmp_path), _household_embed,
                               open_zim=fake_household_open_zim, out=lines.append)
    assert "survivorlibrary.com_en_all" in "\n".join(lines)
    assert _published_household(tmp_path) == before


def test_build_household_refuses_an_excluded_zim_with_a_real_check_not_an_assert(tmp_path, monkeypatch):
    """`python -O` throws assert statements away, and this is the only live use of the exclusion
    machinery: under an optimised interpreter the old assertion would have let a build embed a ZIM
    search must never touch. A real raise, of something that is not AssertionError."""
    monkeypatch.setattr(embeddings, "excluded_zims", lambda settings: frozenset({"gutenberg_en_all"}))
    conn = _household_conn(tmp_path)
    with pytest.raises(ValueError, match="gutenberg_en_all is excluded from meaning search"):
        embeddings.build_household(conn, embeddings_settings(tmp_path),
                                   lambda texts: pytest.fail("must not embed"),
                                   open_zim=fake_household_open_zim, out=lambda s: None)


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


def _insert_wikipedia_zim_row(conn, tmp_path, zim_path: Path | None = None) -> None:
    conn.execute("INSERT INTO library_items (id, title, kind, tier, category, dest, priority, available, local_path) "
                 "VALUES ('wikipedia_en_all_maxi', 'Wikipedia', 'zim', 'core', 'reference', 'zim/w.zim', 50, 1, ?)",
                 (str(zim_path or tmp_path / "wikipedia_en_all_maxi.zim"),))
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


# --- build_wikipedia_rerank(workers=N): article extraction in a pool of worker processes ------------------
#
# The parallel path opens a real ZIM in each worker (a spawned process cannot be handed the parent's
# libzim handle, nor a fixture reader object), so these tests build a tiny REAL ZIM in the maxi
# Wikipedia layout rather than using FakeWikipediaZim.


@pytest.fixture(scope="module")
def wikipedia_zim(tmp_path_factory) -> Path:
    """A real, tiny ZIM shaped like the maxi Wikipedia one: 300 article entries, an `_assets_/` image
    entry (dropped by path alone) and one "soft redirect" stub whose extracted text is under
    SHORTEST_CHARS. 301 real keys is ten BATCH-sized chunks: enough for a sliding window to be visible."""
    from libzim.writer import Creator, Hint, Item, StringProvider

    class _Item(Item):
        def __init__(self, path: str, content: str, mimetype: str):
            super().__init__()
            self._path, self._content, self._mimetype = path, content, mimetype

        def get_path(self):
            return self._path

        def get_title(self):
            return self._path

        def get_mimetype(self):
            return self._mimetype

        def get_contentprovider(self):
            return StringProvider(self._content)

        def get_hints(self):
            return {Hint.FRONT_ARTICLE: False}

    path = tmp_path_factory.mktemp("wikizim") / "wikipedia_en_all_maxi.zim"
    with Creator(str(path)).config_indexing(False, "eng") as creator:
        creator.set_mainpath("Article_000")
        for i in range(300):
            body = (f"This is the real body text of Wikipedia article number {i}, with enough distinct "
                    f"words in it that every article's own vector differs from every other article's "
                    f"once it has been embedded, and comfortably more characters than SHORTEST_CHARS so "
                    f"that it is never mistaken for a stub. Article {i} says so several times over: "
                    f"article {i}, article {i}, article {i}, article {i}.")
            creator.add_item(_Item(f"Article_{i:03d}",
                                   f"<html><body><h1>Article {i}</h1><p>{body}</p></body></html>", "text/html"))
        creator.add_item(_Item("_assets_/thumb/a1b2c3/Some_Picture.jpg", "not a real article", "image/jpeg"))
        creator.add_item(_Item("Soft_Redirect_Stub",
                               "<html><body><p>Soft Redirect Stub Soft Redirect Stub</p></body></html>", "text/html"))
    return path


def _text_seeded_embed(calls_log: list | None = None, fail_at: int | None = None):
    """A deterministic fake embed whose vector depends only on the text, never on call order or batch
    composition -- so two runs that scheduled their extraction differently are still expected to produce
    byte-identical vectors, and a difference means a real difference in what was embedded."""
    def embed(texts):
        if calls_log is not None:
            calls_log.append(list(texts))
            if fail_at is not None and len(calls_log) == fail_at:
                raise RuntimeError("simulated interruption")
        rows = []
        for text in texts:
            seed = int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big")
            v = np.random.default_rng(seed).normal(size=embeddings.DIMS).astype(np.float32)
            rows.append(v / np.linalg.norm(v))
        return np.stack(rows)
    return embed


def _wikipedia_conn(folder: Path, zim_path: Path):
    conn = db.connect(folder / "sos.db")
    db.init_schema(conn)
    _insert_wikipedia_zim_row(conn, folder, zim_path)
    return conn


def _store_bytes(folder: Path) -> tuple[bytes, bytes]:
    return (folder / "wikipedia.f16.bin").read_bytes(), (folder / "wikipedia.ids").read_bytes()


def test_parallel_and_serial_wikipedia_builds_are_byte_identical(tmp_path, wikipedia_zim):
    """The whole point of the worker pool is that it only changes WHERE the article text is extracted,
    never what ends up in the store: same keys, same order, same vectors, same counts."""
    from sos.embeddings import build_wikipedia_rerank

    results, folders = [], []
    for workers in (1, 3):
        folder = tmp_path / f"w{workers}"
        folder.mkdir()
        conn = _wikipedia_conn(folder, wikipedia_zim)
        results.append(build_wikipedia_rerank(conn, embeddings_settings(folder), _text_seeded_embed(),
                                              out=lambda s: None, workers=workers))
        conn.close()
        folders.append(folder)

    assert results[0]["count"] == 301 and results[0]["skipped_no_text"] == 1   # the stub, left a zero row
    for field in ("count", "seen", "skipped_no_text", "dims"):
        assert results[0][field] == results[1][field], field
    assert _store_bytes(folders[0]) == _store_bytes(folders[1])


def test_wikipedia_build_resumes_across_a_change_of_worker_count(tmp_path, monkeypatch, wikipedia_zim):
    """`workers` is a scheduling choice, never part of the checkpoint's identity: a build interrupted on
    three workers resumes on two, from the batch it was interrupted on, and finishes byte-identical to a
    build that was never interrupted at all."""
    from sos.embeddings import BATCH, build_wikipedia_rerank

    monkeypatch.setattr(embeddings, "CHECKPOINT_BATCHES", 1)   # a checkpoint every batch: fast, still real

    folder = tmp_path / "interrupted"
    folder.mkdir()
    conn = _wikipedia_conn(folder, wikipedia_zim)

    calls_1: list = []
    with pytest.raises(RuntimeError, match="simulated interruption"):
        build_wikipedia_rerank(conn, embeddings_settings(folder), _text_seeded_embed(calls_1, fail_at=3),
                               out=lambda s: None, resume=False, workers=3)
    assert len(calls_1) == 3
    state = json.loads((folder / "wikipedia.checkpoint.json").read_text())
    assert state["done"] == 2 * BATCH               # only the two genuinely finished batches were saved
    assert not (folder / "wikipedia.f16.bin").exists()

    calls_2: list = []
    result = build_wikipedia_rerank(conn, embeddings_settings(folder), _text_seeded_embed(calls_2),
                                    out=lambda s: None, resume=True, workers=2)
    conn.close()
    # the proof it resumed rather than silently restarting: the second run's first embed call is given the
    # interrupted batch's own texts, not batch 1's -- and the worker count it resumed on is irrelevant.
    assert calls_2[0] == calls_1[2] and calls_2[0] != calls_1[0]
    assert not (folder / "wikipedia.checkpoint.json").exists()

    clean = tmp_path / "clean"
    clean.mkdir()
    conn2 = _wikipedia_conn(clean, wikipedia_zim)
    uninterrupted = build_wikipedia_rerank(conn2, embeddings_settings(clean), _text_seeded_embed(),
                                           out=lambda s: None, workers=3)
    conn2.close()
    assert result["count"] == uninterrupted["count"] == 301
    assert result["skipped_no_text"] == uninterrupted["skipped_no_text"] == 1
    assert _store_bytes(folder) == _store_bytes(clean)


def test_parallel_extraction_keeps_a_bounded_sliding_window(tmp_path, monkeypatch, wikipedia_zim):
    """Bounded memory is the reason this is a hand-rolled window and not Executor.map: the pool must never
    hold the whole key list's worth of extracted text at once. Counted here by watching submissions run
    ahead of consumption -- one progress line per consumed chunk, with CHECKPOINT_BATCHES pinned to 1."""
    from concurrent.futures import ProcessPoolExecutor

    from sos.embeddings import BATCH, WORKER_WINDOW_CHUNKS, build_wikipedia_rerank

    monkeypatch.setattr(embeddings, "CHECKPOINT_BATCHES", 1)
    workers = 2
    window = workers * WORKER_WINDOW_CHUNKS
    seen = {"submitted": 0, "consumed": 0, "ahead": 0}

    class CountingPool(ProcessPoolExecutor):
        def submit(self, fn, /, *args, **kwargs):
            seen["submitted"] += 1
            seen["ahead"] = max(seen["ahead"], seen["submitted"] - seen["consumed"])
            return super().submit(fn, *args, **kwargs)

    monkeypatch.setattr(embeddings, "ProcessPoolExecutor", CountingPool)

    folder = tmp_path / "windowed"
    folder.mkdir()
    conn = _wikipedia_conn(folder, wikipedia_zim)
    chunks = -(-301 // BATCH)
    assert chunks > window + 1   # more chunks than the window, or a bound on the window proves nothing

    def out(line):
        if " of " in line:
            seen["consumed"] += 1

    result = build_wikipedia_rerank(conn, embeddings_settings(folder), _text_seeded_embed(),
                                    out=out, workers=workers)
    conn.close()
    assert result["count"] == 301
    assert seen["submitted"] == chunks and seen["consumed"] == chunks   # every chunk, exactly once
    # at most a full window in flight, plus the one chunk just taken out of it and being embedded
    assert seen["ahead"] <= window + 1
    assert seen["ahead"] > WORKER_WINDOW_CHUNKS   # and it really does run ahead: extraction overlaps embedding


def test_a_worker_that_cannot_open_the_zim_fails_the_build_clearly_and_leaves_no_children(tmp_path, monkeypatch,
                                                                                          wikipedia_zim):
    """A worker that dies must stop the run with an error that says so, take the pool down with it, and
    leave the last checkpoint intact so the build is still resumable. Provoked here the way it would
    really happen -- the workers cannot open the ZIM at the path the library row gives -- by deleting it
    once the parent has enumerated its keys: the parent's own archive survives an unlink (it holds the
    file open), a worker starting afterwards has nothing to open. An `open_zim` override cannot be used
    for this: the workers never see it, which is exactly why workers > 1 now refuses one."""
    import multiprocessing
    import shutil as shutil_mod
    from concurrent.futures.process import BrokenProcessPool

    from sos.embeddings import build_wikipedia_rerank

    folder = tmp_path / "broken"
    folder.mkdir()
    doomed = folder / "wikipedia_en_all_maxi.zim"
    shutil_mod.copy(wikipedia_zim, doomed)
    conn = db.connect(folder / "sos.db")
    db.init_schema(conn)
    _insert_wikipedia_zim_row(conn, folder, doomed)
    real_keys = embeddings._wikipedia_article_keys

    def enumerate_then_delete(reader):
        keys = list(real_keys(reader))
        doomed.unlink()
        return iter(keys)

    monkeypatch.setattr(embeddings, "_wikipedia_article_keys", enumerate_then_delete)
    with pytest.raises(RuntimeError) as exc:
        build_wikipedia_rerank(conn, embeddings_settings(folder), _text_seeded_embed(),
                               out=lambda s: None, workers=2)
    conn.close()
    assert "worker" in str(exc.value).lower()
    assert isinstance(exc.value.__cause__, BrokenProcessPool)
    assert multiprocessing.active_children() == []   # the pool was shut down, not orphaned


def test_an_embedding_failure_mid_build_leaves_no_worker_processes_behind(tmp_path, wikipedia_zim):
    """The pool lives inside a context manager whose `finally` is the only thing that stops the workers:
    if the main process gives up on the embedding side -- the part of the build most likely to fail --
    every extraction worker must go with it. Removing that shutdown makes this test fail (checked against
    a copy of the module with it taken out); the earlier "no orphaned processes" test did not notice."""
    import multiprocessing

    from sos.embeddings import build_wikipedia_rerank

    folder = tmp_path / "embed-fails"
    folder.mkdir()
    conn = _wikipedia_conn(folder, wikipedia_zim)
    calls: list = []
    with pytest.raises(RuntimeError, match="simulated interruption"):
        build_wikipedia_rerank(conn, embeddings_settings(folder), _text_seeded_embed(calls, fail_at=3),
                               out=lambda s: None, workers=3)
    conn.close()
    assert len(calls) == 3
    assert multiprocessing.active_children() == []


def test_a_wedged_worker_times_out_with_a_clear_resumable_error(tmp_path, monkeypatch, wikipedia_zim):
    """Without a timeout on future.result() a worker that never answers hangs the whole build in silence.
    The real ceiling is generous (half an hour for one chunk of 32 articles); it is pinned to zero here so
    a chunk that is merely still in flight trips it."""
    import multiprocessing

    from sos.embeddings import build_wikipedia_rerank

    assert embeddings.CHUNK_TIMEOUT_S == 30 * 60
    monkeypatch.setattr(embeddings, "CHUNK_TIMEOUT_S", 0)
    folder = tmp_path / "wedged"
    folder.mkdir()
    conn = _wikipedia_conn(folder, wikipedia_zim)
    with pytest.raises(RuntimeError) as exc:
        build_wikipedia_rerank(conn, embeddings_settings(folder), _text_seeded_embed(),
                               out=lambda s: None, workers=2)
    conn.close()
    message = str(exc.value)
    assert "worker" in message.lower() and "resumed from its last checkpoint" in message
    assert isinstance(exc.value.__cause__, TimeoutError)
    assert multiprocessing.active_children() == []


def test_long_lived_workers_are_recycled_without_changing_the_store(tmp_path, monkeypatch, wikipedia_zim):
    """A real build hands one worker a quarter of a million chunks; max_tasks_per_child retires each of
    them long before any leak in libzim or the parser can matter. Pinned to one task per child here so a
    300-article ZIM shows the recycling, and the store it produces is still byte-identical to a serial
    build's."""
    from concurrent.futures import ProcessPoolExecutor

    from sos.embeddings import build_wikipedia_rerank

    assert embeddings.MAX_TASKS_PER_CHILD == 2000
    monkeypatch.setattr(embeddings, "MAX_TASKS_PER_CHILD", 1)
    monkeypatch.setattr(embeddings, "CHECKPOINT_BATCHES", 1)
    pids: set[int] = set()
    pools: list = []

    class PidWatchingPool(ProcessPoolExecutor):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            pools.append(self)

        def submit(self, fn, /, *args, **kwargs):
            future = super().submit(fn, *args, **kwargs)
            pids.update(p.pid for p in self._processes.values())
            return future

    monkeypatch.setattr(embeddings, "ProcessPoolExecutor", PidWatchingPool)

    recycled = tmp_path / "recycled"
    recycled.mkdir()
    conn = _wikipedia_conn(recycled, wikipedia_zim)

    def out(line):
        if pools:   # `_processes` is None once the pool has been shut down
            pids.update(p.pid for p in (pools[0]._processes or {}).values())

    result = build_wikipedia_rerank(conn, embeddings_settings(recycled), _text_seeded_embed(),
                                    out=out, workers=2)
    conn.close()
    assert pools[0]._max_tasks_per_child == 1
    assert len(pids) > 2          # more processes than workers: they really were retired and replaced

    serial = tmp_path / "serial"
    serial.mkdir()
    conn = _wikipedia_conn(serial, wikipedia_zim)
    plain = build_wikipedia_rerank(conn, embeddings_settings(serial), _text_seeded_embed(),
                                   out=lambda s: None, workers=1)
    conn.close()
    assert result["count"] == plain["count"] == 301
    assert _store_bytes(recycled) == _store_bytes(serial)


def test_build_wikipedia_rerank_refuses_an_open_zim_override_on_several_workers(tmp_path, wikipedia_zim):
    """The workers always open the real file at library_items.local_path: an override the parent alone
    honours meant the two sides read different archives, and a store of nothing but zero rows came out of
    it with no error at all."""
    from sos.embeddings import build_wikipedia_rerank

    conn = _wikipedia_conn(tmp_path, wikipedia_zim)
    with pytest.raises(ValueError, match="open_zim"):
        build_wikipedia_rerank(conn, embeddings_settings(tmp_path), _text_seeded_embed(),
                               open_zim=lambda p: None, out=lambda s: None, workers=2)
    conn.close()


_SIGTERM_DRIVER = '''
"""A real `sos build-embeddings-wikipedia --workers 3` run, far enough along to have its workers, which
then waits in the embedding call until this process is signalled. Everything is under the main guard: a
spawned worker re-imports this file, and must not repeat the setup."""
import multiprocessing
import sys
import time
from pathlib import Path

import httpx

from sos import db, embeddings


def never_answers(url, texts, **kwargs):
    print(" ".join(str(p.pid) for p in multiprocessing.active_children()), flush=True)
    while True:
        time.sleep(0.05)


if __name__ == "__main__":
    folder, zim = Path(sys.argv[1]), sys.argv[2]
    conn = db.connect(folder / "sos.db")
    db.init_schema(conn)
    conn.execute("INSERT INTO library_items (id, title, kind, tier, category, dest, priority, available, "
                 "local_path) VALUES ('wikipedia_en_all_maxi', 'Wikipedia', 'zim', 'core', 'reference', "
                 "'zim/w.zim', 50, 1, ?)", (zim,))
    conn.commit()
    conn.close()
    model = folder / "model.gguf"
    model.write_bytes(b"")

    class FakeSettings:
        embeddings_dir = folder
        embed_model = "test"
        embed_model_path = model
        embed_url = "http://127.0.0.1:8099"
        db_path = folder / "sos.db"

    embeddings.httpx.get = lambda url, timeout=1.0: httpx.Response(200)   # a server is up: start none
    embeddings.embed_sync = never_answers
    sys.exit(embeddings.build_wikipedia_cli(FakeSettings(), out=lambda s: None, workers=3))
'''


def test_sigterm_to_the_build_stops_its_workers_instead_of_orphaning_them(tmp_path, wikipedia_zim):
    """Python's default SIGTERM kills the process outright: the `finally` that shuts the extraction pool
    down never runs, and every worker is left behind for good (measured: three workers still alive a
    minute after the parent was signalled). A real run, a real SIGTERM, real child processes."""
    import os
    import select
    import signal
    import subprocess
    import sys

    driver = tmp_path / "driver.py"
    driver.write_text(_SIGTERM_DRIVER)
    env = dict(os.environ, PYTHONPATH=str(REPO / "api"), PYTHONUNBUFFERED="1")
    proc = subprocess.Popen([sys.executable, str(driver), str(tmp_path), str(wikipedia_zim)],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    try:
        assert select.select([proc.stdout], [], [], 120)[0], "the build never reached its first embedding call"
        children = [int(pid) for pid in proc.stdout.readline().split()]
        assert len(children) == 3
        for pid in children:
            os.kill(pid, 0)                      # every worker really is running before the signal

        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=120)                   # the parent stops rather than ignoring the signal

        deadline = time.monotonic() + 60
        alive = children
        while alive and time.monotonic() < deadline:
            alive = [pid for pid in alive if _is_alive(pid)]
            if alive:
                time.sleep(0.2)
        assert alive == [], f"workers orphaned by SIGTERM: {alive}"
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.stdout.close()
        proc.stderr.close()


def _is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    return True


def test_build_wikipedia_rerank_rejects_a_nonpositive_worker_count(tmp_path):
    from sos.embeddings import build_wikipedia_rerank

    conn = db.connect(tmp_path / "sos.db")
    db.init_schema(conn)
    conn.commit()
    with pytest.raises(ValueError, match="workers"):
        build_wikipedia_rerank(conn, embeddings_settings(tmp_path), lambda texts: None,
                               out=lambda s: None, workers=0)


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


def test_semantic_generation_counts_each_load_of_the_index(env, monkeypatch):
    clock = {"t": 1_000.0}
    monkeypatch.setattr(embeddings.time, "monotonic", lambda: clock["t"])
    sem = embeddings.Semantic(env)
    assert sem.generation == 0 and sem.index() is None
    embeddings.write_index(env.embeddings_dir, "docs", np.stack([unit(1, 0)]), ["/m/food"], {})
    clock["t"] += 31                                                 # the not-loaded state is throttled too
    assert sem.index() is not None and sem.generation == 1
    clock["t"] += 31
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


def test_household_entries_extract_lazily(tmp_path):
    class Reader(FakeHouseholdZim):
        def read(self, path):
            if path == 'second.2':
                raise AssertionError('read ahead of the consumer')
            return b'<p>' + b'Useful words. ' * 30 + b'</p>'
    conn = _household_conn(tmp_path, catalogue=[(1, 'First', 'A Writer', 'first.1'),
                                                (2, 'Second', None, 'second.2')])
    entries = embeddings._household_entries(Reader({'first.1': b'', 'second.2': b''}), 'gutenberg_en_all', conn)
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


# --- one embedding per search, not one per collection ------------------------------------------------------


class CountingEmbedClient:
    """Stands in for EmbedClient and records every real request the Semantic layer makes."""

    def __init__(self, fail: bool = False, delay: float = 0.0):
        self.calls: list[tuple[list[str], float]] = []
        self.fail = fail
        self.delay = delay

    async def embed(self, texts, timeout=None):
        self.calls.append((list(texts), timeout))
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.fail:
            raise embeddings.EmbedError("no embedding server")
        return np.stack([unit(1, 0)])


def _every_collection(folder: Path) -> None:
    embeddings.write_index(folder, "docs", np.stack([unit(1, 0)]), ["/m/food"], {})
    embeddings.ApproxIndex.build(np.stack([unit(1, 0)]), ["gutenberg_en_all:1"]).save(folder, "household")
    embeddings.write_index(folder, "wikipedia", np.stack([unit(1, 0)]), ["Water_purification"], {"count": 1})


def _semantic_with(env, client) -> "embeddings.Semantic":
    sem = embeddings.Semantic(env)
    sem.client = client
    return sem


async def _one_search(sem, q: str):
    return (await sem.query(q), await sem.query_household(q),
            await sem.rerank_wikipedia(q, ["Water_purification"]))


def test_one_search_embeds_the_query_once_for_all_three_collections(env):
    """The three collections used to embed the same words three times over, each with its own 0.6 s
    timeout: up to 1.8 s of a loaded box's search, and triple the work for the Pi's single-threaded
    sos-embed.service (MemoryMax=600M)."""
    _every_collection(Path(env.embeddings_dir))
    client = CountingEmbedClient()
    docs, books, wiki = asyncio.run(_one_search(_semantic_with(env, client), "tinned food"))
    assert docs and books and wiki                                  # every collection really answered
    assert len(client.calls) == 1
    assert client.calls[0] == ([embeddings.QUERY_PREFIX + "tinned food"], embeddings.Semantic.QUERY_TIMEOUT_S)


def test_a_down_embedding_server_costs_one_timeout_a_search_rather_than_three(env):
    _every_collection(Path(env.embeddings_dir))
    client = CountingEmbedClient(fail=True)
    assert asyncio.run(_one_search(_semantic_with(env, client), "tinned food")) == ([], [], {})
    assert len(client.calls) == 1


def test_a_different_query_is_embedded_again_and_the_memo_expires(env, monkeypatch):
    clock = {"t": 10_000.0}
    monkeypatch.setattr(embeddings.time, "monotonic", lambda: clock["t"])
    _every_collection(Path(env.embeddings_dir))
    client = CountingEmbedClient()
    sem = _semantic_with(env, client)
    assert asyncio.run(sem.query("tinned food")) and asyncio.run(sem.query("boiling water"))
    assert len(client.calls) == 2
    assert asyncio.run(sem.query("tinned food"))
    assert len(client.calls) == 2                                   # still the same words, still fresh
    clock["t"] += 31
    assert asyncio.run(sem.query("tinned food"))
    assert len(client.calls) == 3                                   # the memo is short on purpose


def test_two_searches_for_the_same_words_at_once_embed_it_once(env):
    _every_collection(Path(env.embeddings_dir))
    client = CountingEmbedClient(delay=0.05)
    sem = _semantic_with(env, client)

    async def at_the_same_time():
        return await asyncio.gather(sem.query("tinned food"), sem.query_household("tinned food"))

    docs, books = asyncio.run(at_the_same_time())
    assert docs and books and len(client.calls) == 1


def test_an_empty_query_still_embeds_nothing_at_all(env):
    _every_collection(Path(env.embeddings_dir))
    client = CountingEmbedClient()
    sem = _semantic_with(env, client)
    assert asyncio.run(_one_search(sem, "   ")) == ([], [], {})
    assert client.calls == []


# --- loading a store: the throttle, the generation names, the pruning and the metadata check ---------------


def _wikipedia_ids(folder: Path, count: int) -> None:
    (folder / "wikipedia.ids").write_text("".join(f"Article_{i}\n" for i in range(count)), encoding="utf-8")


def _touch(path: Path, when: float) -> None:
    os.utime(path, (when, when))


def test_a_store_still_being_copied_is_tried_once_a_throttle_window_not_once_a_search(env, monkeypatch):
    """A vector file being copied onto the box grows, so its mtime moves on every request. Only a loaded
    store used to be throttled, so every search re-read the whole key list (8.4 million of them: about
    1.8 s and 700 MB) and bumped `generation`, which throws search's own results cache away each time."""
    clock = {"t": 5_000.0}
    monkeypatch.setattr(embeddings.time, "monotonic", lambda: clock["t"])
    folder = Path(env.embeddings_dir)
    folder.mkdir(parents=True, exist_ok=True)
    _wikipedia_ids(folder, 100)
    attempts = {"n": 0}
    real_load = embeddings.WikipediaStore.load.__func__

    def counting(cls, *args, **kwargs):
        attempts["n"] += 1
        return real_load(cls, *args, **kwargs)

    monkeypatch.setattr(embeddings.WikipediaStore, "load", classmethod(counting))
    sem = embeddings.Semantic(env)
    for i in range(1, 6):
        (folder / "wikipedia.f16.bin").write_bytes(b"\0" * (i * 10 * embeddings.DIMS * 2))
        _touch(folder / "wikipedia.f16.bin", 1_000 + i)
        assert sem.wikipedia_store() is None
        clock["t"] += 0.2                                   # five searches inside one throttle window
    assert attempts["n"] == 1
    assert sem.generation == 0                              # a failed attempt is not a new generation

    clock["t"] += 31
    assert sem.wikipedia_store() is None and attempts["n"] == 2 and sem.generation == 0

    (folder / "wikipedia.f16.bin").write_bytes(np.zeros((100, embeddings.DIMS), dtype=np.float16).tobytes())
    _touch(folder / "wikipedia.f16.bin", 2_000)
    clock["t"] += 31
    store = sem.wikipedia_store()
    assert store is not None and len(store) == 100 and sem.generation == 1


def test_the_docs_and_household_caches_wait_out_their_throttle_when_nothing_is_loaded(env, monkeypatch):
    clock = {"t": 1_000.0}
    monkeypatch.setattr(embeddings.time, "monotonic", lambda: clock["t"])
    sem = embeddings.Semantic(env)
    assert sem.index() is None and sem.household_index() is None and sem.generation == 0
    embeddings.write_index(env.embeddings_dir, "docs", np.stack([unit(1, 0)]), ["/m/food"], {})
    embeddings.ApproxIndex.build(np.stack([unit(1, 0)]), ["book:1"]).save(env.embeddings_dir, "household")
    assert sem.index() is None and sem.household_index() is None and sem.generation == 0
    clock["t"] += 31
    assert sem.index() is not None and sem.household_index() is not None and sem.generation == 2


def test_the_wikipedia_key_list_is_not_opened_when_the_meta_count_already_rules_the_file_out(tmp_path, monkeypatch):
    """The whole point of the size check: 8.4 million keys cost about 1.8 s and 700 MB to materialise,
    so a file that is still growing must be ruled out before any of that. The meta says how many keys
    there are, so nothing need be read at all."""
    _wikipedia_ids(tmp_path, 1000)
    (tmp_path / "wikipedia.meta.json").write_text(json.dumps({"count": 1000, "dims": embeddings.DIMS}))
    (tmp_path / "wikipedia.f16.bin").write_bytes(b"\0" * (17 * embeddings.DIMS * 2))
    real_open = Path.open

    def no_opening(self, *args, **kwargs):
        assert self.name != "wikipedia.ids", "the key list was opened although the count already rules it out"
        return real_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", no_opening)
    assert embeddings.WikipediaStore.load(tmp_path) is None


def test_a_wikipedia_key_list_with_no_meta_is_counted_without_being_decoded(tmp_path, monkeypatch):
    """No meta to ask, so the keys have to be counted -- by streaming the bytes, never by building the
    8.4 million strings that are the very cost the check exists to avoid."""
    _wikipedia_ids(tmp_path, 1000)
    (tmp_path / "wikipedia.f16.bin").write_bytes(b"\0" * (17 * embeddings.DIMS * 2))
    real_open = Path.open

    def watching(self, mode="r", *args, **kwargs):
        assert self.name != "wikipedia.ids" or "b" in mode, "the key list was decoded although the sizes cannot match"
        return real_open(self, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", watching)
    assert embeddings.WikipediaStore.load(tmp_path) is None


def test_a_new_generation_survives_an_ordinary_copy_that_skips_dot_names(tmp_path):
    """`cp -a core/embeddings/* dest/`, `scp -r dir/*` and a file manager all leave a dot-prefixed
    directory behind, and what arrives is a `*.current` symlink pointing at nothing -- semantic search
    silently degrades to the keyword search. New generations are named so an ordinary copy takes them."""
    embeddings.write_index(tmp_path / "src", "docs", np.stack([unit(1, 0)]), ["/m/food"], {})
    generation = embeddings._collection_folder(tmp_path / "src", "docs")
    assert generation.parent == tmp_path / "src" and not generation.name.startswith(".")
    shutil.copytree(tmp_path / "src", tmp_path / "dest", symlinks=True,
                    ignore=lambda where, names: [n for n in names if n.startswith(".")])
    assert embeddings.Index.load(tmp_path / "dest", "docs").keys == ["/m/food"]


def test_a_dot_prefixed_generation_from_an_earlier_build_still_loads(tmp_path):
    """Whatever new builds are named, the generations already published on the box must keep loading:
    the resolver follows the relative `*.current` symlink, never the directory's name."""
    generation = tmp_path / ".docs-0123456789abcdef0123456789abcdef"
    generation.mkdir()
    (generation / "docs.f16.bin").write_bytes(unit(1, 0).astype(np.float16).tobytes())
    (generation / "docs.ids").write_text("/m/food\n", encoding="utf-8")
    (tmp_path / "docs.current").symlink_to(generation.name, target_is_directory=True)
    (tmp_path / "docs.f16.bin").symlink_to("docs.current/docs.f16.bin")
    (tmp_path / "docs.ids").symlink_to("docs.current/docs.ids")
    assert embeddings.Index.load(tmp_path, "docs").keys == ["/m/food"]


def test_a_dangling_current_symlink_is_said_once_rather_than_on_every_search(env, monkeypatch, caplog):
    folder = Path(env.embeddings_dir)
    embeddings.write_index(folder, "docs", np.stack([unit(1, 0)]), ["/m/food"], {})
    shutil.rmtree(embeddings._collection_folder(folder, "docs"))     # the copy that left the generation behind
    clock = {"t": 1_000.0}
    monkeypatch.setattr(embeddings.time, "monotonic", lambda: clock["t"])
    sem = embeddings.Semantic(env)
    with caplog.at_level(logging.WARNING, logger="sos.embeddings"):
        for _ in range(3):
            assert sem.index() is None
            clock["t"] += 31
    said = [r.getMessage() for r in caplog.records if "docs.current" in r.getMessage()]
    assert len(said) == 1 and "copy" in said[0]


def test_publishing_keeps_the_current_and_previous_generations_and_removes_the_rest(tmp_path):
    """A retained Wikipedia generation is 6.47 GB. Deleting the one before last is safe while a reader
    still has it memory-mapped: on Linux the inode outlives the name it was opened by."""
    published = []
    for i in range(4):
        embeddings.write_index(tmp_path, "docs", np.stack([unit(1, i + 1)]), [f"/m/{i}"], {"count": 1})
        published.append(embeddings._collection_folder(tmp_path, "docs"))
    assert published[3].is_dir() and published[2].is_dir()
    assert not published[0].exists() and not published[1].exists()
    assert embeddings.Index.load(tmp_path, "docs").keys == ["/m/3"]


def test_pruning_knows_both_naming_schemes_and_leaves_everything_else_alone(tmp_path):
    legacy = tmp_path / ".docs-0123456789abcdef0123456789abcdef"     # published by an earlier build
    legacy.mkdir()
    (legacy / "docs.f16.bin").write_bytes(unit(1, 0).astype(np.float16).tobytes())
    (legacy / "docs.ids").write_text("/m/legacy\n", encoding="utf-8")
    (tmp_path / "docs.current").symlink_to(legacy.name, target_is_directory=True)
    household = tmp_path / ".household-0123456789abcdef0123456789abcdef"
    household.mkdir()
    notes = tmp_path / "docs-notes.txt"
    notes.write_text("not a generation")

    embeddings.write_index(tmp_path, "docs", np.stack([unit(0, 1)]), ["/m/new"], {})
    first = embeddings._collection_folder(tmp_path, "docs")
    assert legacy.is_dir()                                           # the immediately previous generation
    embeddings.write_index(tmp_path, "docs", np.stack([unit(1, 1)]), ["/m/newer"], {})
    assert not legacy.exists() and first.is_dir()                    # one older than that: gone
    assert embeddings._collection_folder(tmp_path, "docs").is_dir()
    assert household.is_dir() and notes.is_file()                    # another collection, and a plain file


def test_pruning_never_removes_a_generation_any_collection_points_at(tmp_path):
    """Belt and braces: whatever the names say, a directory a live `*.current` resolves to is in use."""
    borrowed = tmp_path / ".docs-0123456789abcdef0123456789abcdef"
    borrowed.mkdir()
    (tmp_path / "household.current").symlink_to(borrowed.name, target_is_directory=True)
    for i in range(3):
        embeddings.write_index(tmp_path, "docs", np.stack([unit(1, i + 1)]), [f"/m/{i}"], {})
    assert borrowed.is_dir()


def test_a_store_built_with_other_dimensions_refuses_to_load(tmp_path, caplog):
    embeddings.write_index(tmp_path, "docs", np.stack([unit(1, 0)]), ["/m/food"],
                           {"model": "some-other-model", "dims": 768, "count": 1})
    with caplog.at_level(logging.WARNING, logger="sos.embeddings"):
        assert embeddings.Index.load(tmp_path, "docs", model="bge-small-en-v1.5-q8_0.gguf") is None
    assert any("768" in r.getMessage() for r in caplog.records)


def test_a_store_built_by_another_build_of_the_same_model_loads_and_says_so_once(tmp_path, caplog):
    """The Wikipedia vectors are deliberately built by bge-small-en-v1.5-fp16-torch while the box queries
    with the q8_0 GGUF of the same model: measured mean cosine 0.9998 and 98 per cent top-10 overlap, so
    this is expected, worth one line in the log, and never a refusal."""
    embeddings.write_index(tmp_path, "wikipedia", np.stack([unit(1, 0)]), ["Water_purification"],
                           {"model": "bge-small-en-v1.5-fp16-torch", "dims": embeddings.DIMS, "count": 1})
    with caplog.at_level(logging.INFO, logger="sos.embeddings"):
        for _ in range(3):
            assert embeddings.WikipediaStore.load(tmp_path, model="bge-small-en-v1.5-q8_0.gguf") is not None
    assert len([r for r in caplog.records if "fp16-torch" in r.getMessage()]) == 1


def test_a_store_with_no_meta_at_all_still_loads(tmp_path):
    (tmp_path / "docs.f16.bin").write_bytes(unit(1, 0).astype(np.float16).tobytes())
    (tmp_path / "docs.ids").write_text("/m/food\n", encoding="utf-8")
    assert embeddings.Index.load(tmp_path, "docs", model="bge-small-en-v1.5-q8_0.gguf") is not None


# --- the model file is what starts a server, so it is only needed when one must be started ----------------
#
# A server may be up already and be nothing to do with settings.embed_model: tools/embed_server_torch.py
# serves bge-small from Hugging Face in fp16 and has no GGUF on disk at all. Both builds used to refuse
# before they ever looked at /health, so that server could not be used.


def _no_model_fixture(env, monkeypatch, healthy):
    """An initialised (empty) db, no model file anywhere, and a /health that answers as `healthy` says."""
    conn = db.connect(env.db_path)
    db.init_schema(conn)
    conn.close()
    assert not env.embed_model_path.exists()

    def fake_get(url, timeout=1.0):
        if healthy:
            return httpx.Response(200)
        raise httpx.HTTPError("nothing there")

    monkeypatch.setattr(embeddings.httpx, "get", fake_get)
    monkeypatch.setattr(embeddings.time, "sleep", lambda s: None)
    _fake_embed_sync(monkeypatch)
    started = []
    return started, lambda cmd, **kw: pytest.fail(f"no server may be started: {cmd}") if healthy else started.append(cmd)


@pytest.mark.parametrize("build, kwargs", [("build_cli", {"collection": "docs"}),
                                           ("build_wikipedia_cli", {})])
def test_a_healthy_server_is_used_even_with_no_model_file_on_disk(env, monkeypatch, build, kwargs):
    _, run = _no_model_fixture(env, monkeypatch, healthy=True)
    said = []
    rc = getattr(embeddings, build)(env, out=said.append, run=run, **kwargs)
    assert rc == 0
    assert not any("the embedding model is not at" in line for line in said)


@pytest.mark.parametrize("build, kwargs", [("build_cli", {"collection": "docs"}),
                                           ("build_wikipedia_cli", {})])
def test_no_server_and_no_model_file_still_fails_the_way_it_always_has(env, monkeypatch, build, kwargs):
    started, run = _no_model_fixture(env, monkeypatch, healthy=False)
    said = []
    rc = getattr(embeddings, build)(env, out=said.append, run=run, **kwargs)
    assert rc == 1
    assert said == [f"FAIL the embedding model is not at {env.embed_model_path} (manifest item bge-small-en-v1.5)"]
    assert started == []


def test_the_model_file_is_required_when_any_one_of_several_servers_must_be_started(env, monkeypatch):
    """`--servers 3` with only the first port answering still has two to start, so the file is needed."""
    conn = db.connect(env.db_path)
    db.init_schema(conn)
    conn.close()
    monkeypatch.setattr(embeddings.httpx, "get",
                        lambda url, timeout=1.0: httpx.Response(200) if url.startswith("http://127.0.0.1:8091")
                        else (_ for _ in ()).throw(httpx.HTTPError("nothing there")))
    said = []
    rc = embeddings.build_cli(env, out=said.append, run=lambda cmd, **kw: pytest.fail("must not start"),
                              collection="docs", servers=3)
    assert rc == 1
    assert said == [f"FAIL the embedding model is not at {env.embed_model_path} (manifest item bge-small-en-v1.5)"]
