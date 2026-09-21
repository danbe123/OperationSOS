"""How the meaning layer is fused with the words (task 19, 2026-09-21): rank fusion for the box's own passages,
the rows meaning may not push down (a title the query names, a quick card near the query), and Wikipedia's lift.
Each rule on hand-made rows first, then through search() with a fake meaning layer."""
import asyncio

import httpx
import pytest
import respx

from sos import db, query as query_mod, search
from sos.kiwix import KiwixClient

BASE = "http://kiwix.test/kiwix"
ROW_SQL = "INSERT INTO fts_docs(title, body, doc_id, kind, category, scenarios, page, url) VALUES (?,?,?,?,?,?,?,?)"


def row(url, title, kind="page", score=1.0, kw=None, via=None, source="playbooks"):
    r = {"url": url, "title": title, "kind": kind, "score": score, "source": source, "snippet": "", "_cat": source}
    if via:
        r["via"] = via
    else:
        r["_kw"] = score if kw is None else kw
    return r


def urls(results):
    return [r["url"] for r in results]


# --- rank fusion -------------------------------------------------------------------------------------------------

def test_the_nth_nearest_passage_is_worth_a_keyword_hit_at_rank_n_times_the_dense_weight():
    assert search.dense_bonus(1, 1.6) == pytest.approx(search.DENSE_WEIGHT * search.score(1.6, 1))
    assert search.dense_bonus(4, 1.0) == pytest.approx(search.DENSE_WEIGHT * search.score(1.0, 4))
    assert search.dense_bonus(1, 1.0) > search.dense_bonus(2, 1.0) > search.dense_bonus(20, 1.0)
    # a converted document's page is worth DENSE_DOC_SHARE of that
    assert search.dense_bonus(3, 1.0, doc=True) == pytest.approx(search.DENSE_DOC_SHARE * search.dense_bonus(3, 1.0))


def test_the_household_books_keep_the_distance_bonus():
    assert search.semantic_bonus(search.SEMANTIC_CEIL, 0.6) == pytest.approx(search.SEMANTIC_WEIGHT * 0.6)
    assert search.semantic_bonus(search.SEMANTIC_MIN, 0.6) == 0.0
    assert search.semantic_bonus(0.71, 0.6) < search.semantic_bonus(0.80, 0.6)


def test_the_floors_only_ask_more_of_a_page_the_words_missed():
    floor = search.SEMANTIC_FLOOR
    assert floor[(True, False)] < floor[(False, False)] < floor[(False, True)]
    assert floor[(True, False)] <= floor[(True, True)] <= floor[(False, True)]
    assert search.SEMANTIC_MIN == min(*floor.values(), *search.HOUSEHOLD_FLOOR.values())


# --- the words' own positions --------------------------------------------------------------------------------------

def test_keyword_positions_are_the_order_the_words_gave_with_meaning_taken_away():
    results = [row("/m/found-by-meaning", "Meaning", score=9.0, via="meaning"),
               row("/p/second", "Second", score=5.0, kw=0.2),
               row("/p/first", "First", score=1.0, kw=0.9)]
    assert search._keyword_positions(results) == {"/p/first": 0, "/p/second": 1}


# --- a title the query names ------------------------------------------------------------------------------------------

def test_a_row_titled_as_the_query_or_nearly_is_kept_where_the_words_put_it():
    terms = query_mod.reduce_query("paracetamol adult dose").terms
    results = [row("/a", "Something else", kw=0.9), row("/nhs", "Paracetamol dose", kind="article", kw=0.5),
               row("/b", "Unrelated", kw=0.4), row("/exact", "Paracetamol adult dose", kw=0.3),
               row("/m", "Paracetamol", via="meaning")]
    kw_pos = search._keyword_positions(results)
    titles, cards = search._kept_rows(results, kw_pos, terms, "paracetamol adult dose", [])
    assert {r["url"]: i for r, i in titles} == {"/nhs": 1, "/exact": 3}     # two of three words, and the whole title
    assert cards == []                                                        # nor the meaning-only row


def test_a_title_sharing_less_than_the_share_of_the_words_is_not_kept():
    terms = query_mod.reduce_query("paracetamol adult dose overdose").terms
    results = [row("/nhs", "Paracetamol dose", kw=0.5)]
    titles, _ = search._kept_rows(results, search._keyword_positions(results), terms, "paracetamol adult dose overdose", [])
    assert titles == []                                                       # a half


def test_places_and_catalogue_books_are_never_kept_by_title():
    results = [row("/map?x", "Oxford", kind="place", source="places", kw=1.0), row("/book/gutenberg/1", "Oxford", kind="book", source="books", kw=0.9)]
    titles, cards = search._kept_rows(results, search._keyword_positions(results), ["oxford"], "oxford", [])
    assert titles == [] and cards == []


def test_a_kept_title_is_lifted_to_its_place_but_not_above_a_card_in_the_first_three():
    a, b, c, d = row("/a", "A"), row("/b", "B"), row("/c", "C"), row("/kept", "Kept")
    assert urls(search._lift_titles([a, b, c, d], [(d, 0)])) == ["/kept", "/a", "/b", "/c"]
    assert urls(search._lift_titles([a, b, c, d], [(d, 1)])) == ["/a", "/kept", "/b", "/c"]
    assert urls(search._lift_titles([a, b, c, d], [(a, 3)])) == ["/a", "/b", "/c", "/kept"]      # already above: stays
    card = row("/medical/card/x", "Card", kind="card")
    assert urls(search._lift_titles([card, a, b, d], [(d, 0)])) == ["/medical/card/x", "/kept", "/a", "/b"]
    assert urls(search._lift_titles([a, b, card, d], [(d, 0)])) == ["/a", "/b", "/medical/card/x", "/kept"]


# --- a quick card ---------------------------------------------------------------------------------------------------------

def test_a_card_the_words_ranked_first_and_the_nearest_cards_are_kept_in_the_first_three():
    words_card = row("/medical/card/first", "Choking", kind="card", kw=1.0)
    near_card = row("/medical/card/near", "Burns", kind="card", kw=0.1)
    other = row("/p/other", "Other", kw=0.5)
    results = [other, words_card, near_card]
    kw_pos = search._keyword_positions(results)
    assert kw_pos["/medical/card/first"] == 0
    titles, cards = search._kept_rows(results, kw_pos, ["boiling", "water"], "boiling water", ["/medical/card/near"])
    assert {r["url"] for r, _ in cards} == {"/medical/card/first", "/medical/card/near"}
    assert all(index == search.KEPT_TOP - 1 for _, index in cards) and titles == []


def test_a_kept_card_replaces_the_lowest_row_in_the_first_three_that_nothing_keeps():
    rows = [row(f"/p/{i}", f"P{i}") for i in range(6)]
    card = row("/medical/card/x", "Card", kind="card")
    out = search._lift_cards(rows[:5] + [card] + rows[5:], [(card, 2)], [])
    assert urls(out)[:3] == ["/p/0", "/p/1", "/medical/card/x"] and urls(out)[3] == "/p/2"      # /p/2 stood third
    assert sorted(urls(out)) == sorted(urls(rows + [card]))                                        # nothing lost


def test_a_card_already_in_the_first_three_does_not_move_and_a_full_house_of_kept_rows_blocks_a_lift():
    card = row("/medical/card/x", "Card", kind="card")
    a, b = row("/a", "A"), row("/b", "B")
    assert urls(search._lift_cards([card, a, b], [(card, 2)], [])) == ["/medical/card/x", "/a", "/b"]
    kept_a, kept_b, kept_c = row("/ka", "A"), row("/kb", "B"), row("/kc", "C")
    out = search._lift_cards([kept_a, kept_b, kept_c, card], [(card, 2)], [(kept_a, 0), (kept_b, 1), (kept_c, 2)])
    assert urls(out) == ["/ka", "/kb", "/kc", "/medical/card/x"]


# --- through search() -----------------------------------------------------------------------------------------------------------

class FakeSemantic:
    def __init__(self, near=(), wiki=None):
        self.near, self.wiki, self.rerank_calls = list(near), wiki or {}, []

    async def query(self, q, k=20):
        return self.near[:k]

    async def query_household(self, q, k=20):
        return []

    async def rerank_wikipedia(self, q, keys):
        self.rerank_calls.append(list(keys))
        return {k: v for k, v in self.wiki.items() if k in keys}


@pytest.fixture
def conn(env):
    c = db.connect(env.db_path)
    db.init_schema(c)
    c.executemany(ROW_SQL, [
        ("Burns and scalds", "Cool the burn under running water for twenty minutes.", "card:burns", "card", "playbooks", "", None, "/medical/card/burns#steps"),
        ("Choking", "Back blows and abdominal thrusts.", "card:choking", "card", "playbooks", "", None, "/medical/card/choking#steps"),
        ("Water", "Store and purify water, boil it for a minute.", "module:water", "module", "playbooks", "", None, "/m/water#store"),
        ("Fire", "Lighting and keeping a fire.", "module:fire", "module", "playbooks", "", None, "/m/fire#light"),
        ("Cooking on a fire", "Cooking over a camp fire and boiling a kettle.", "page:cook", "page", "playbooks", "", None, "/p/cook#kettle"),
        ("Field manual", "Kettle and stove.", "fm#p1", "doc", "survival", "", 1, "/doc/fm#page=1"),
        ("Field manual", "Stoves.", "fm#p2", "doc", "survival", "", 2, "/doc/fm#page=2"),
        ("Field manual", "Camp cooking.", "fm#p3", "doc", "survival", "", 3, "/doc/fm#page=3"),
    ])
    c.execute("INSERT INTO library_items (id, title, kind, tier, category, dest, priority, available, fts) VALUES "
              "('wikipedia_en_all_maxi', 'Wikipedia', 'zim', 'core', 'reference', 'zim/w.zim', 50, 1, 1)")
    c.commit()
    yield c
    c.close()


def run(conn, env, q, sem, wiki_hit=None):
    def reply(request):
        if wiki_hit and "wikipedia_en_all_maxi" in request.url.params.get_list("books.name"):
            return httpx.Response(200, text="<rss><channel><item><title>" + wiki_hit[0] + "</title>"
                                  f"<link>/kiwix/content/wikipedia_en_all_maxi/A/{wiki_hit[1]}</link>"
                                  "<description>x</description></item></channel></rss>")
        return httpx.Response(200, text="<rss><channel></channel></rss>")

    with respx.mock(base_url=BASE, assert_all_called=False) as m:
        m.get("/search").mock(side_effect=reply)
        return asyncio.run(search.search(conn, env, KiwixClient(BASE), q, use_cache=False, semantic=sem))["results"]


def test_a_card_a_household_words_it_their_own_way_for_is_in_the_first_three(conn, env):
    """No word of the question is in the card; the documents outrank it by rank, and the card is kept anyway."""
    near = [("/doc/fm#page=1", 0.75), ("/doc/fm#page=2", 0.74), ("/doc/fm#page=3", 0.73), ("/m/water#store", 0.72),
            ("/p/cook#kettle", 0.71), ("/medical/card/burns#steps", 0.66)]
    out = run(conn, env, "spilled the kettle on my daughters arm", FakeSemantic(near))
    assert "/medical/card/burns" in [u.split("#")[0] for u in urls(out)[:3]]


def test_without_the_card_rule_the_documents_do_outrank_the_card(conn, env, monkeypatch):
    """The control for the test above: it fails for the right reason."""
    monkeypatch.setattr(search, "CARD_COS", 2.0)
    near = [("/doc/fm#page=1", 0.75), ("/doc/fm#page=2", 0.74), ("/doc/fm#page=3", 0.73), ("/m/water#store", 0.72),
            ("/p/cook#kettle", 0.71), ("/medical/card/burns#steps", 0.66)]
    out = run(conn, env, "spilled the kettle on my daughters arm", FakeSemantic(near))
    assert "/medical/card/burns#steps" not in urls(out)[:3]


def test_a_card_less_near_than_the_card_cosine_is_not_promoted(conn, env):
    near = [("/doc/fm#page=1", 0.75), ("/doc/fm#page=2", 0.74), ("/doc/fm#page=3", 0.73), ("/m/water#store", 0.72),
            ("/p/cook#kettle", 0.71), ("/medical/card/burns#steps", search.CARD_COS - 0.01)]
    out = run(conn, env, "spilled the kettle on my daughters arm", FakeSemantic(near))
    assert "/medical/card/burns#steps" not in urls(out)[:3]


def test_a_card_is_kept_only_for_the_nearest_two(conn, env):
    near = [("/medical/card/burns#steps", 0.80), ("/medical/card/choking#steps", 0.75), ("/doc/fm#page=1", 0.74)]
    out = run(conn, env, "something quite unrelated", FakeSemantic(near))
    assert urls(out)[:2] == ["/medical/card/burns#steps", "/medical/card/choking#steps"]
    near = [("/m/water#store", 0.80), ("/m/fire#light", 0.79), ("/p/cook#kettle", 0.78), ("/medical/card/burns#steps", 0.77),
            ("/medical/card/choking#steps", 0.76), ("/doc/fm#page=1", 0.75)]
    out = run(conn, env, "something quite unrelated", FakeSemantic(near))
    kept = [u for u in urls(out)[:3] if "/medical/card/" in u]
    assert len(kept) == search.CARDS_KEPT


def test_a_search_with_no_meaning_layer_at_all_is_the_keyword_search(conn, env):
    keyword = urls(run(conn, env, "water fire", None))
    assert keyword and urls(run(conn, env, "water fire", FakeSemantic())) == keyword          # a layer with nothing to say

    class Down:
        async def query(self, q, k=20):
            raise RuntimeError("the embedding server is not there")

        async def query_household(self, q, k=20):
            raise RuntimeError("the embedding server is not there")

        async def rerank_wikipedia(self, q, keys):
            raise RuntimeError("the embedding server is not there")

    assert urls(run(conn, env, "water fire", Down(), wiki_hit=("Water", "Water"))) == \
        urls(run(conn, env, "water fire", None, wiki_hit=("Water", "Water")))


def test_wikipedia_is_lifted_by_meaning_but_not_for_a_medical_query(conn, env):
    wiki_key = "A/Kettle"
    near = []
    lifted = FakeSemantic(near, wiki={wiki_key: 0.85})
    plain = run(conn, env, "kettle stove", lifted, wiki_hit=("Kettle", "Kettle"))
    unlifted = run(conn, env, "kettle stove", FakeSemantic(near, wiki={wiki_key: 0.60}), wiki_hit=("Kettle", "Kettle"))
    score = lambda rows: next(r["score"] for r in rows if r["url"].startswith("/read/"))
    assert score(plain) > score(unlifted)                                   # a near article gains, a far one does not
    medical = FakeSemantic(near, wiki={"A/Bleeding": 0.9})
    run(conn, env, "severe bleeding", medical, wiki_hit=("Bleeding", "Bleeding"))
    assert medical.rerank_calls == []                                       # a medical query never asks
    assert lifted.rerank_calls == [[wiki_key]]


def test_wikipedia_lift_is_a_ramp_between_its_two_cosines():
    assert search.wikipedia_lift(search.WIKIPEDIA_LIFT_FROM) == 0.0
    assert search.wikipedia_lift(0.2) == 0.0 and search.wikipedia_lift(-0.3) == 0.0
    assert search.wikipedia_lift(search.WIKIPEDIA_LIFT_TO) == pytest.approx(search.WIKIPEDIA_LIFT)
    assert search.wikipedia_lift(0.99) == pytest.approx(search.WIKIPEDIA_LIFT)
    middle = (search.WIKIPEDIA_LIFT_FROM + search.WIKIPEDIA_LIFT_TO) / 2
    assert search.wikipedia_lift(middle) == pytest.approx(search.WIKIPEDIA_LIFT / 2)
