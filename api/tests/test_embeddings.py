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
    rc = embeddings.build_cli(env, out=lambda s: None, run=fake_run)
    assert rc == 0
    assert len(seen_cmds) == 1
    expected_binary = shutil.which("llama-server") or "/usr/local/bin/llama-server"
    assert seen_cmds[0][0] == expected_binary
    assert not seen_cmds[0][0].endswith("llama-server-cuda")
    assert "-ngl" not in seen_cmds[0]


def test_build_cli_starts_the_cuda_binary_when_cuda_is_true(env, monkeypatch):
    seen_cmds, fake_run = _build_cli_fixture(env, monkeypatch)
    rc = embeddings.build_cli(env, out=lambda s: None, run=fake_run, cuda=True)
    assert rc == 0
    assert len(seen_cmds) == 1
    assert seen_cmds[0][0].endswith("llama-server-cuda")
    assert seen_cmds[0][0] == str(embeddings.CUDA_LLAMA_SERVER)
    assert "-ngl" in seen_cmds[0] and seen_cmds[0][seen_cmds[0].index("-ngl") + 1] == "99"


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


def test_build_household_embeds_real_text_and_skips_image_only_entries(tmp_path):
    from sos.embeddings import ApproxIndex, build_household

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
    """A bare stand-in for Settings carrying only what build_household reads: embeddings_dir and embed_model."""
    class FakeSettings:
        embeddings_dir = tmp_path
        embed_model = "bge-small-en-v1.5-q8_0.gguf"
    return FakeSettings()


def test_build_household_is_a_noop_for_a_zim_not_on_the_box(tmp_path):
    from sos.embeddings import build_household

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
