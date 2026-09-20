"""Regression attacks on search using isolated SQLite, tiny indices and controlled services."""
import asyncio
import json
import os

import httpx
import numpy as np
import pytest

from sos import db, embeddings, kiwix, library, search
from sos.kiwix import KiwixError, KiwixHit


def vector(axis=0):
    v = np.zeros(embeddings.DIMS, dtype=np.float32)
    v[axis] = 1
    return v


class NoKiwix:
    async def search(self, *args, **kwargs):
        return []


@pytest.fixture
def conn(env):
    c = db.connect(env.db_path)
    db.init_schema(c)
    c.executemany(
        "INSERT INTO fts_docs(title,body,doc_id,kind,category,url) VALUES (?,?,?,?,?,?)",
        [("Food", "Keeps for years", "module:food", "module", "playbooks", "/m/food"),
         ("Water", "Boil it", "module:water", "module", "playbooks", "/m/water")])
    c.commit()
    yield c
    c.close()


def publish(env, url):
    embeddings.write_index(env.embeddings_dir, "docs", np.stack([vector()]), [url], {"count": 1})


async def successful_embed(*args, **kwargs):
    return np.stack([vector()])


async def run_search(conn, env, sem=None):
    return await search.search(conn, env, NoKiwix(), "larder", semantic=sem)


def test_cached_query_discovers_a_republished_index(conn, env, monkeypatch):
    clock = {"now": 1000.0}
    monkeypatch.setattr(embeddings.time, "monotonic", lambda: clock["now"])
    publish(env, "/m/food")
    sem = embeddings.Semantic(env)
    monkeypatch.setattr(sem.client, "embed", successful_embed)

    async def scenario():
        for _ in range(3):
            assert (await run_search(conn, env, sem))["results"][0]["url"] == "/m/food"
        publish(env, "/m/water")
        clock["now"] += 31
        assert (await run_search(conn, env, sem))["results"][0]["url"] == "/m/water"
        await sem.client.aclose()

    asyncio.run(scenario())


def test_keyword_only_search_never_reuses_semantic_results(conn, env, monkeypatch):
    publish(env, "/m/food")
    sem = embeddings.Semantic(env)
    monkeypatch.setattr(sem.client, "embed", successful_embed)

    async def scenario():
        assert (await run_search(conn, env, sem))["results"]
        assert (await run_search(conn, env))["results"] == []
        await sem.client.aclose()

    asyncio.run(scenario())


def test_temporary_embedding_failure_does_not_permanently_cache_keyword_fallback(conn, env, monkeypatch):
    clock = {"now": 1000.0}
    monkeypatch.setattr(embeddings.time, "monotonic", lambda: clock["now"])
    publish(env, "/m/food")
    sem = embeddings.Semantic(env)

    async def failing(*args, **kwargs):
        raise embeddings.EmbedError("server restarting")

    monkeypatch.setattr(sem.client, "embed", failing)

    async def scenario():
        for _ in range(3):
            assert (await run_search(conn, env, sem))["results"] == []
        monkeypatch.setattr(sem.client, "embed", successful_embed)
        clock["now"] += 4
        assert (await run_search(conn, env, sem))["results"][0]["url"] == "/m/food"
        await sem.client.aclose()

    asyncio.run(scenario())


def test_kiwix_failure_is_partial_and_retried(conn, env):
    conn.execute("INSERT INTO library_items(id,title,kind,tier,category,dest,available,fts) "
                 "VALUES ('wiki','Wiki','zim','core','reference','zim/wiki.zim',1,1)")
    conn.commit()

    class RestartingKiwix:
        failed = True
        async def search(self, *args):
            if self.failed:
                raise KiwixError("HTTP 503: restarting")
            return [KiwixHit("Larder", "Larder", "Food storage", "wiki")]

    async def scenario():
        kiwix = RestartingKiwix()
        first = await search.search(conn, env, kiwix, "larder")
        assert first["partial"] is True
        kiwix.failed = False
        second = await search.search(conn, env, kiwix, "larder")
        assert second["partial"] is False and second["results"][0]["title"] == "Larder"

    asyncio.run(scenario())


def test_cancelling_one_embedding_waiter_does_not_cancel_another(env, monkeypatch):
    async def scenario():
        sem = embeddings.Semantic(env)
        entered, release = asyncio.Event(), asyncio.Event()
        async def embed(*args, **kwargs):
            entered.set()
            await release.wait()
            return np.stack([vector()])
        monkeypatch.setattr(sem.client, "embed", embed)
        owner = asyncio.create_task(sem._query_vector("water"))
        await entered.wait()
        cancelled = asyncio.create_task(sem._query_vector("water"))
        survivor = asyncio.create_task(sem._query_vector("water"))
        await asyncio.sleep(0)
        cancelled.cancel()
        await asyncio.gather(cancelled, return_exceptions=True)
        release.set()
        results = await asyncio.gather(owner, survivor, return_exceptions=True)
        await sem.client.aclose()
        assert all(isinstance(r, np.ndarray) for r in results), results
    asyncio.run(scenario())


def test_generation_change_is_detected_even_when_vector_mtime_is_preserved(env, monkeypatch):
    clock = {"now": 1000.0}
    monkeypatch.setattr(embeddings.time, "monotonic", lambda: clock["now"])
    publish(env, "/m/food")
    sem = embeddings.Semantic(env)
    assert sem.index().keys == ["/m/food"]
    path = env.embeddings_dir / "docs.f16.bin"
    old_stat = path.stat()
    publish(env, "/m/water")
    os.utime(path, ns=(old_stat.st_atime_ns, old_stat.st_mtime_ns))
    clock["now"] += 31
    assert sem.index().keys == ["/m/water"]


def test_indexed_embedding_rows_are_reordered_to_match_the_inputs():
    rows = [{"index": 1, "embedding": vector(1).tolist()},
            {"index": 0, "embedding": vector(0).tolist()}]
    assert np.array_equal(embeddings._vectors_from(rows), np.stack([vector(0), vector(1)]))


@pytest.mark.parametrize("bad", [float('nan'), float('inf'), 0.0, "not a number"])
def test_invalid_embedding_vectors_are_rejected(bad):
    with pytest.raises(embeddings.EmbedError):
        embeddings._vectors_from([{"index": 0, "embedding": [bad] * embeddings.DIMS}])


def test_duplicate_embedding_indices_are_rejected():
    with pytest.raises(embeddings.EmbedError):
        embeddings._vectors_from([{"index": 0, "embedding": vector().tolist()}] * 2)


def test_wrong_embedding_batch_size_is_rejected():
    async def scenario():
        client = embeddings.EmbedClient("http://embed.test")
        await client._client.aclose()
        client._client = httpx.AsyncClient(transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=[{"index": 0, "embedding": vector().tolist()}])))
        try:
            with pytest.raises(embeddings.EmbedError):
                await client.embed(["first passage", "second passage"])
        finally:
            await client.aclose()
    asyncio.run(scenario())


def test_cancelling_the_first_request_keeps_shared_embedding_alive(env, monkeypatch):
    async def scenario():
        sem = embeddings.Semantic(env)
        entered, release = asyncio.Event(), asyncio.Event()
        calls = []
        async def embed(*args, **kwargs):
            calls.append(args)
            entered.set()
            await release.wait()
            return np.stack([vector()])
        monkeypatch.setattr(sem.client, "embed", embed)
        first = asyncio.create_task(sem._query_vector("water"))
        await entered.wait()
        second = asyncio.create_task(sem._query_vector("water"))
        await asyncio.sleep(0)
        first.cancel()
        await asyncio.gather(first, return_exceptions=True)
        release.set()
        result = await second
        assert np.array_equal(result, vector()) and len(calls) == 1
        assert sem.cacheable("water")
        assert sem._embedding == {}
        await sem.client.aclose()
    asyncio.run(scenario())


@pytest.mark.parametrize("file", ["ids", "meta.json"])
def test_nonvector_file_changes_invalidate_a_loaded_index(env, monkeypatch, file):
    clock = {"now": 1000.0}
    monkeypatch.setattr(embeddings.time, "monotonic", lambda: clock["now"])
    publish(env, "/m/food")
    sem = embeddings.Semantic(env)
    assert sem.index().keys == ["/m/food"]
    (env.embeddings_dir / f"docs.{file}").write_text(
        "/m/water\n" if file == "ids" else '{"dims": 768, "count": 1}')
    clock["now"] += 31
    result = sem.index()
    assert result is None if file == "meta.json" else result.keys == ["/m/water"]


def test_corrupt_optional_index_does_not_break_keyword_search(conn, env):
    folder = env.embeddings_dir
    folder.mkdir()
    (folder / "household.hnsw").write_bytes(b"not an index")
    (folder / "household.ids").write_text("gutenberg_en_all:1\n")
    sem = embeddings.Semantic(env)
    async def scenario():
        result = await search.search(conn, env, NoKiwix(), "water", semantic=sem)
        assert result["results"][0]["url"] == "/m/water"
        await sem.client.aclose()
    asyncio.run(scenario())


def test_cache_fields_cannot_be_confused_with_delimiters():
    assert search.SearchCache.key("water|books", ["docs"], 40) != search.SearchCache.key(
        "water", ["books|docs"], 40)


@pytest.mark.parametrize("payload", ["not json", {"data": []},
    [{"embedding": [[1] * embeddings.DIMS, [2] * embeddings.DIMS]}],
    [{"index": -1, "embedding": vector().tolist()}],
    [{"index": True, "embedding": vector().tolist()}]])
def test_malformed_embeddings_fail_consistently(payload):
    with pytest.raises(embeddings.EmbedError):
        embeddings._vectors_from(payload)


@pytest.mark.parametrize("q", ["' OR 1=1 --", '"water" NOT (food)', 'NEAR(water food, 1)',
                               '😀', '\x00', '"; DROP TABLE books; --', 'AND OR NOT',
                               'water* OR title:food', '水 水 水', 'a' * 512])
def test_query_syntax_is_data_not_sql(conn, env, q):
    result = asyncio.run(search.search(conn, env, NoKiwix(), q, use_cache=False))
    assert isinstance(result["results"], list)
    assert conn.execute("SELECT count(*) FROM fts_docs").fetchone()[0] == 2


def test_multilingual_library_is_not_grouped_with_english_only_books(conn, env, tmp_path):
    xml = tmp_path / "library.xml"
    xml.write_text('<library><book path="/english.zim" language="eng" tags="_ftindex:yes"/>'
                   '<book path="/multilingual.zim" language="eng,fra" tags="_ftindex:yes"/></library>')
    info = library.parse_library_xml(xml)
    db.set_setting(conn, "zim_languages", json.dumps({k: v["language"] for k, v in info.items()}))
    for name in info:
        conn.execute("INSERT INTO library_items(id,title,kind,tier,category,dest,available,fts) "
                     "VALUES (?,?,'zim','core','survival',?,1,1)", (name, name, f"zim/{name}.zim"))
    conn.commit()

    class LanguageCheckingKiwix:
        async def search(self, names, *args):
            if len(names) != 1:
                raise KiwixError("HTTP 400: Two or more books in different languages")
            name = names[0]
            return [KiwixHit(f"Water {name}", "Water", "Water supply", name)]

    result = asyncio.run(search.search(conn, env, LanguageCheckingKiwix(), "water"))
    assert result["partial"] is False
    assert {r["url"] for r in result["results"] if r["kind"] == "article"} == {
        "/read/english/Water", "/read/multilingual/Water"}


def test_catalog_retains_every_language_used_by_kiwix_search():
    xml = '<feed xmlns="http://www.w3.org/2005/Atom"><entry><name>multi</name>' \
          '<language>eng,fra</language><tags>_ftindex:yes</tags></entry></feed>'
    assert kiwix.parse_catalog_xml(xml)[0].language == "eng,fra"


@pytest.mark.parametrize("body", ['not json', '{}', '[null]', '[{"kind":"path","path":3}]'])
def test_malformed_suggestions_do_not_take_down_local_suggestions(conn, env, body):
    conn.execute("INSERT INTO library_items(id,title,kind,tier,category,dest,available,suggest) "
                 "VALUES ('wiki','Wiki','zim','core','reference','zim/wiki.zim',1,1)")
    conn.commit()
    async def scenario():
        client = kiwix.KiwixClient("http://kiwix.test")
        await client._client.aclose()
        client._client = httpx.AsyncClient(transport=httpx.MockTransport(
            lambda request: httpx.Response(200, text=body)))
        try:
            result = await search.suggest(conn, env, client, "Fo")
            assert [r["url"] for r in result] == ["/m/food"]
        finally:
            await client.aclose()
    asyncio.run(scenario())


def test_malformed_search_count_is_a_recoverable_service_error():
    xml = '<rss xmlns:op="http://a9.com/-/spec/opensearch/1.1/"><channel>' \
          '<op:totalResults>not a number</op:totalResults></channel></rss>'
    with pytest.raises(KiwixError):
        kiwix.parse_search_xml(xml)


@pytest.mark.parametrize("endpoint", ["search", "suggest"])
def test_unbounded_search_input_is_rejected_before_backend_work(client, endpoint):
    response = client.get(f"/api/{endpoint}", params={"q": " ".join(f"term{i}" for i in range(1200))})
    assert response.status_code == 422


class RefreshFails:
    """A semantic layer whose refresh() raises: the fault the cache-on path met outside every guard."""
    generation = 0

    def __init__(self, exc):
        self.exc = exc

    def refresh(self):
        raise self.exc

    async def query(self, q, k=20):
        return []

    async def query_household(self, q, k=20):
        return []


def cached_rows(conn):
    return conn.execute("SELECT count(*) FROM search_cache").fetchone()[0]


FAULTS = [MemoryError("out of memory"), TypeError("bad argument"), KeyError("missing")]


@pytest.mark.parametrize("exc", FAULTS, ids=lambda e: type(e).__name__)
def test_a_semantic_refresh_that_raises_is_keyword_search_and_is_not_cached(conn, env, exc):
    result = asyncio.run(search.search(conn, env, NoKiwix(), "water", semantic=RefreshFails(exc)))
    assert [r["url"] for r in result["results"]] == ["/m/water"]
    assert cached_rows(conn) == 0


@pytest.mark.parametrize("exc", FAULTS, ids=lambda e: type(e).__name__)
def test_an_index_that_fails_to_load_is_keyword_search_and_is_not_cached(conn, env, monkeypatch, exc):
    publish(env, "/m/food")
    sem = embeddings.Semantic(env)

    def fail(*args, **kwargs):
        raise exc

    monkeypatch.setattr(embeddings.Index, "load", staticmethod(fail))

    async def scenario():
        result = await search.search(conn, env, NoKiwix(), "water", semantic=sem)
        await sem.client.aclose()
        return result

    result = asyncio.run(scenario())
    assert [r["url"] for r in result["results"]] == ["/m/water"]
    assert cached_rows(conn) == 0


def test_a_failing_refresh_is_logged_once_per_distinct_error(conn, env, caplog):
    search._refresh_fault.clear()

    def warnings():
        return [r for r in caplog.records if r.levelname == "WARNING" and "refresh" in r.getMessage()]

    async def scenario():
        for exc in (TypeError("bad argument"),) * 3 + (KeyError("missing"),) * 2:
            await search.search(conn, env, NoKiwix(), "water", semantic=RefreshFails(exc))

    with caplog.at_level("WARNING", logger="sos.search"):
        asyncio.run(scenario())
    assert len(warnings()) == 2
    assert "bad argument" in warnings()[0].getMessage() and "missing" in warnings()[1].getMessage()
