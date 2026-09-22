"""How the meaning layer is fused with the words (task 19, 2026-09-21): rank fusion for the box's own passages,
the quick cards meaning may not push out of the first three, and Wikipedia's lift. Each rule on hand-made rows
first, then through search() with a fake meaning layer."""
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


# --- a quick card ---------------------------------------------------------------------------------------------------------

def test_the_kept_cards_are_the_one_the_words_ranked_first_and_the_ones_nearest_in_meaning():
    words_card = row("/medical/card/first", "Choking", kind="card", kw=1.0)
    near_card = row("/medical/card/near", "Burns", kind="card", kw=0.1)
    other = row("/p/other", "Other", kw=0.5)
    results = [other, words_card, near_card]
    kw_pos = search._keyword_positions(results)
    assert kw_pos["/medical/card/first"] == 0
    kept = search._kept_cards(results, kw_pos, ["/medical/card/near"])
    assert urls(kept) == ["/medical/card/first", "/medical/card/near"]
    assert urls(search._kept_cards(results, kw_pos, [])) == ["/medical/card/first"]       # the second one only by meaning
    assert search._kept_cards([other], {"/p/other": 0}, []) == []                          # a page is not a card


def test_a_card_found_only_by_meaning_is_not_the_card_the_words_ranked_first():
    meaning_card = row("/medical/card/m", "Burns", kind="card", score=9.0, via="meaning")
    words = row("/p/words", "Words", kw=1.0)
    results = [meaning_card, words]
    assert search._kept_cards(results, search._keyword_positions(results), []) == []


def test_a_kept_card_replaces_the_lowest_row_in_the_first_three_and_that_row_moves_just_below():
    rows = [row(f"/p/{i}", f"P{i}") for i in range(6)]
    card = row("/medical/card/x", "Card", kind="card")
    out = search._keep_rows(rows[:5] + [card] + rows[5:], [card])
    assert urls(out)[:4] == ["/p/0", "/p/1", "/medical/card/x", "/p/2"]                 # /p/2 stood third
    assert sorted(urls(out)) == sorted(urls(rows + [card]))                                # nothing lost


def test_a_card_already_in_the_first_three_does_not_move():
    card = row("/medical/card/x", "Card", kind="card")
    a, b = row("/a", "A"), row("/b", "B")
    assert urls(search._keep_rows([card, a, b], [card])) == ["/medical/card/x", "/a", "/b"]
    assert urls(search._keep_rows([a, b, card], [card])) == ["/a", "/b", "/medical/card/x"]


def test_two_kept_cards_do_not_displace_each_other_and_a_full_house_of_cards_blocks_a_lift():
    c1, c2, c3, c4 = (row(f"/medical/card/{i}", f"C{i}", kind="card") for i in range(4))
    a, b, c = row("/a", "A"), row("/b", "B"), row("/c", "C")
    out = search._keep_rows([a, b, c, c1, c2], [c1, c2])
    assert set(urls(out)[:3]) >= {"/medical/card/0", "/medical/card/1"} and len(out) == 5
    out = search._keep_rows([c1, c2, c3, c4], [c1, c2, c3, c4])          # the first three are all kept cards already
    assert urls(out) == [f"/medical/card/{i}" for i in range(4)]
    out = search._keep_rows([c1, c2, c3, a], [c1, c2, c3])
    assert urls(out) == ["/medical/card/0", "/medical/card/1", "/medical/card/2", "/a"]


# --- a medicine typed by name -----------------------------------------------------------------------------------------------

def test_the_kept_medicines_are_nhs_rows_the_words_ranked_high_whose_title_has_the_query():
    terms = query_mod.reduce_query("paracetamol").terms
    wiki = row("/w", "Paracetamol", kind="article", kw=1.0, source="medical")
    nhs_top = row("/nhs1", "Common questions about paracetamol for adults - NHS", kind="article", kw=0.8, source="nhs")
    nhs_other = row("/nhs2", "Ibuprofen for adults - NHS", kind="article", kw=0.7, source="nhs")
    nhs_low = row("/nhs3", "Paracetamol for children - NHS", kind="article", kw=0.1, source="nhs")
    meaning = row("/m", "Paracetamol", kind="article", score=5.0, via="meaning", source="nhs")
    results = [wiki, nhs_top, nhs_other, meaning, nhs_low]
    kw_pos = search._keyword_positions(results)
    assert urls(search._kept_medicines(results, kw_pos, terms)) == ["/nhs1"]     # not Wikipedia, not another medicine, not below the third, not found by meaning


def test_a_medicine_is_lifted_into_the_first_three_and_the_nearest_cards_are_not_kept_beside_it():
    a, b, c = row("/a", "A"), row("/b", "B"), row("/c", "C")
    nhs = row("/nhs", "Paracetamol - NHS", kind="article", source="nhs")
    out = search._keep_rows([a, b, c, nhs], [nhs])
    assert urls(out) == ["/a", "/b", "/nhs", "/c"]


# --- a book (task 22: the household's good matches were "outscored", ranked below the tenth place by BOOK_WEIGHT
# against the page's own rows, for the single largest share of 272 book gold queries traced against the shipped
# index) -----------------------------------------------------------------------------------------------------------

def book_row(url, title, score):
    return {"url": url, "title": title, "kind": "book", "source": "books", "badge": "Books", "snippet": "",
            "score": score, "_cat": "books"}


def test_the_kept_books_are_the_best_scoring_book_rows():
    a = row("/a", "A", score=5.0)
    books = [book_row(f"/book/gutenberg/{i}", f"B{i}", score=0.30 - i * 0.03) for i in range(8)]
    kept = search._kept_books([a] + books)
    assert urls(kept) == urls(books[: search.BOOKS_GUARANTEE])   # the best BOOKS_GUARANTEE, not the first BOOKS_GUARANTEE
    assert search._kept_books([a]) == []                          # nothing to keep when there is no book row


def test_a_kept_book_is_brought_into_the_first_books_top_below_where_cards_and_medicines_are_protected():
    pages = [row(f"/p/{i}", f"P{i}") for i in range(14)]
    book = book_row("/book/gutenberg/9", "Book", score=0.02)   # scores below every page: it needs the rule, not the score
    ordered = pages[:12] + [book] + pages[12:]
    out = search._keep_rows(ordered, search._kept_books(ordered), top=search.BOOKS_TOP, protect=search.KEPT_TOP)
    assert urls(out)[: search.KEPT_TOP] == [f"/p/{i}" for i in range(search.KEPT_TOP)]   # the protected rows never move
    assert out[search.BOOKS_TOP - 1] is book                                              # kept at the foot of the window
    assert sorted(urls(out)) == sorted(urls(pages + [book]))                              # nothing lost, one displaced by one place


def test_a_book_already_inside_books_top_is_left_alone():
    pages = [row(f"/p/{i}", f"P{i}") for i in range(9)]
    book = book_row("/book/gutenberg/9", "Book", score=0.02)
    ordered = pages[:5] + [book] + pages[5:]
    out = search._keep_rows(ordered, search._kept_books(ordered), top=search.BOOKS_TOP, protect=search.KEPT_TOP)
    assert out == ordered


def test_the_household_floor_no_longer_asks_more_of_a_book_the_words_missed():
    """Task 19's 0.66 "not found by words" floor was tuned on the box's own dense passages, whose neighbourhood
    is far denser with plausible strangers than 70,558 one-vector-per-book entries; task 22 found 19 of 272 book
    gold queries with an acceptable book at 0.607-0.657, never a row because of it."""
    assert search.HOUSEHOLD_FLOOR[True] == search.HOUSEHOLD_FLOOR[False] == search.SEMANTIC_MIN


def test_household_is_asked_deeper_than_the_boxs_own_passages(conn, env):
    """A book's neighbourhood is thin: task 22 found the acceptable book beyond vector rank 20 for 27 of 272
    book gold queries. HOUSEHOLD_K governs only the household lookup, so the box's own dense passages (and
    every guardrail that depends on them) are unaffected."""
    sem = FakeSemantic()
    run(conn, env, "canning meat", sem)
    assert sem.household_k_calls == [search.HOUSEHOLD_K]
    assert search.HOUSEHOLD_K > search.SEMANTIC_K


def test_a_book_the_words_never_found_is_still_shown_in_the_first_books_top(conn, env):
    """A Survivor Library book the words never found, confidently near in meaning (past BOOKS_PROMOTE_COS) and
    ranked well below the tenth place by the fusion alike, is still guaranteed a place in the first BOOKS_TOP
    results: the books group's own promise, not a competition against the page's rank fusion row for row
    (task 22). The control (BOOKS_GUARANTEE 0, the rule off) shows the same book left out, so the test fails
    for the right reason if it ever does."""
    conn.execute("INSERT INTO library_items (id, available) VALUES ('survivorlibrary.com_en_all', 1)")
    conn.executemany(ROW_SQL, [
        (f"Extra page {i}", f"Extra page {i} about kettles and water storage.", f"page:extra{i}", "page",
         "playbooks", "", None, f"/p/extra{i}#kettle") for i in range(12)
    ])
    conn.commit()
    near = [(f"/p/extra{i}#kettle", 0.80 - i * 0.01) for i in range(12)]
    household = [("survivorlibrary.com_en_all:canning-meat", search.BOOKS_PROMOTE_COS + 0.01)]  # confident, but
    # still scored below the twelve competing pages on its own -- the "without" control below must show it
    # staying out naturally, or the test would not tell the rule's doing from a coincidence of scores.
    book_url = "/kiwix/content/survivorlibrary.com_en_all/www.survivorlibrary.com/library/canning-meat.pdf"

    out = run(conn, env, "kettle water storage", FakeSemantic(near, household=household))
    assert book_url in urls(out)[: search.BOOKS_TOP]

    monkey = pytest.MonkeyPatch()
    monkey.setattr(search, "BOOKS_GUARANTEE", 0)
    try:
        without = run(conn, env, "kettle water storage", FakeSemantic(near, household=household))
    finally:
        monkey.undo()
    assert book_url not in urls(without)[: search.BOOKS_TOP]


def test_a_household_match_that_only_just_cleared_the_floor_is_a_row_but_is_not_promoted(conn, env):
    """The gate a live regression found (task 22): "who do I phone if the water supply stops" pulled in five
    Survivor Library waterworks books at cosine 0.601-0.611 -- past HOUSEHOLD_FLOOR but barely -- and their
    promotion pushed the real answer, found by the words and unrelated to meaning, from the 7th place to the
    12th. A book meaning barely put over the floor is still a row (the group is not hidden) but is not owed a
    place in the first BOOKS_TOP over pages the words ranked ahead of it."""
    conn.execute("INSERT INTO library_items (id, available) VALUES ('survivorlibrary.com_en_all', 1)")
    conn.executemany(ROW_SQL, [
        (f"Extra page {i}", f"Extra page {i} about kettles and water storage.", f"page:extra{i}", "page",
         "playbooks", "", None, f"/p/extra{i}#kettle") for i in range(12)
    ])
    conn.commit()
    near = [(f"/p/extra{i}#kettle", 0.80 - i * 0.01) for i in range(12)]
    weak = [("survivorlibrary.com_en_all:canning-meat", search.BOOKS_PROMOTE_COS - 0.02)]   # a row, not a confident one
    book_url = "/kiwix/content/survivorlibrary.com_en_all/www.survivorlibrary.com/library/canning-meat.pdf"

    out = run(conn, env, "kettle water storage", FakeSemantic(near, household=weak))
    assert book_url in urls(out)                          # still shown: the group is not hidden
    assert book_url not in urls(out)[: search.BOOKS_TOP]  # but not promoted over the pages the words ranked ahead of it


def test_a_book_the_words_found_too_is_only_lifted_once_not_promoted_a_second_time(conn, env):
    """A Gutenberg book both the catalogue search and the household vectors found is one row (task 5's rule);
    the books rule must not add a second entry for it when it brings the group into the window."""
    conn.execute("INSERT INTO library_items (id, available) VALUES ('gutenberg_en_all', 1)")
    conn.execute("INSERT INTO books (zim, id, title, author, shelf, popularity, epub_path, html_path, cover_path) "
                 "VALUES ('gutenberg_en_all', 2701, 'Whaling Voyage', 'Herman Melville', 'PS', 3, NULL, NULL, NULL)")
    conn.execute("INSERT INTO fts_books(fts_books) VALUES('rebuild')")
    conn.commit()
    household = [("gutenberg_en_all:2701", 0.65)]
    out = run(conn, env, "whaling voyage", FakeSemantic(household=household))
    assert urls(out).count("/book/gutenberg/2701") == 1


# --- through search() -----------------------------------------------------------------------------------------------------------

class FakeSemantic:
    def __init__(self, near=(), wiki=None, household=()):
        self.near, self.wiki, self.rerank_calls = list(near), wiki or {}, []
        self.household, self.household_k_calls = list(household), []

    async def query(self, q, k=20):
        return self.near[:k]

    async def query_household(self, q, k=20):
        self.household_k_calls.append(k)
        return self.household[:k]

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


def test_a_medicine_named_in_the_query_keeps_its_nhs_page_in_the_first_three(conn, env):
    conn.executemany(ROW_SQL, [
        ("Lethal pandemic", "Paracetamol and fever in a pandemic.", "playbook:pandemic", "playbook", "playbooks", "", None, "/s/pandemic#first-72-hours"),
        ("Survival medicine", "Paracetamol, aspirin and ibuprofen.", "page:rebuild-medicine", "page", "playbooks", "", None, "/p/rebuild-medicine#drugs"),
        ("Medical", "Paracetamol and other medicine.", "module:medical", "module", "playbooks", "", None, "/m/medical#what-to-do")])
    conn.execute("INSERT INTO library_items (id, title, kind, tier, category, dest, priority, available, fts) VALUES "
                 "('nhs_medicines', 'NHS medicines', 'zim', 'core', 'medical', 'zim/n.zim', 10, 1, 1)")
    conn.commit()

    def reply(request):
        if "nhs_medicines" in request.url.params.get_list("books.name"):
            return httpx.Response(200, text="<rss><channel><item><title>Common questions about paracetamol for adults - NHS</title>"
                                  "<link>/kiwix/content/nhs_medicines/www.nhs.uk/medicines/paracetamol-for-adults/common-questions/</link>"
                                  "<description>x</description></item></channel></rss>")
        return httpx.Response(200, text="<rss><channel></channel></rss>")

    near = [("/s/pandemic#first-72-hours", 0.78), ("/p/rebuild-medicine#drugs", 0.77), ("/m/medical#what-to-do", 0.76),
            ("/medical/card/poisoning#steps", 0.75)]
    with respx.mock(base_url=BASE, assert_all_called=False) as m:
        m.get("/search").mock(side_effect=reply)
        out = asyncio.run(search.search(conn, env, KiwixClient(BASE), "paracetamol", use_cache=False, semantic=FakeSemantic(near)))["results"]
        with_rule = urls(out)
        monkey = pytest.MonkeyPatch()
        monkey.setattr(search, "MEDICINE_TOP", 0)
        try:
            without = urls(asyncio.run(search.search(conn, env, KiwixClient(BASE), "paracetamol", use_cache=False, semantic=FakeSemantic(near)))["results"])
        finally:
            monkey.undo()
    nhs = "/read/nhs_medicines/www.nhs.uk/medicines/paracetamol-for-adults/common-questions/"
    assert nhs in with_rule[:search.KEPT_TOP]
    assert nhs not in without[:search.KEPT_TOP]                                    # the control: the rule is what puts it there


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
