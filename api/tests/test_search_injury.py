"""The injury policy of search (task 25, 2026-09-22): a query read as an injury described ("gash on arm") finds the
cards about that condition though they never say "arm", leads with the right one by what the card is about (its
`conditions` and `aliases`), keeps a card that only shares the body word (Broken bones) below them, and puts down a
row whose only overlap is a body word or an ambiguous spelling (Sam Gash, Olympic Arms, bleeding bicycle brakes) --
with the meaning layer or without it. A name, a household phrase or a book request is searched as before."""
import asyncio
import json

import httpx
import pytest
import respx

from sos import db, search
from sos.kiwix import KiwixClient

BASE = "http://kiwix.test/kiwix"
ROW_SQL = ("INSERT INTO fts_docs(title, body, doc_id, kind, category, scenarios, page, url, aliases) "
           "VALUES (?,?,?,?,?,?,?,?,?)")

CARDS = {
    # slug: (title, conditions, aliases, {section: body})
    "severe-bleeding": ("Severe bleeding", ["bleeding", "open_wound"], ["heavy bleeding", "won't stop bleeding", "deep wound"], {
        "when-to-use": "When to use Blood is flowing or spurting, soaking through cloth, or pooling.",
        "steps": "Steps Press hard on the wound with a pad. For a limb wound that will not stop, put a tourniquet above the wound.",
    }),
    "wound-cleaning": ("Wound cleaning", ["open_wound"], ["cut", "gash", "graze", "laceration"], {
        "when-to-use": "When to use Any cut, graze, puncture or open wound once the bleeding is under control.",
        "steps": "Steps Rinse the wound under clean running water. Cover with a dressing.",
    }),
    "wound-closure": ("Closing a wound", ["open_wound"], ["gaping cut", "deep cut", "stitches"], {
        "when-to-use": "When to use A cut whose edges gape, once the bleeding is controlled and it is clean.",
        "steps": "Steps Stop the bleeding first. Close only if it is clean. Strips pull the edges together.",
    }),
    "broken-bones": ("Broken bones", ["fracture"], ["broken arm", "broken leg", "fracture"], {
        "when-to-use": "When to use Pain, swelling, a limb bent the wrong way after an injury.",
        "steps": "Steps Support the arm in a sling. Support the arm above and below. A broken arm: keep the arm still. "
                 "Do not straighten the arm.",
        "warnings": "Warnings An open fracture with a wound: cover the wound, control bleeding.",
    }),
    "burns": ("Burns and scalds", ["burn"], ["scald", "scalded", "hot liquid spill"], {
        "when-to-use": "When to use Skin is burned by heat, steam, hot liquid, chemicals or electricity.",
        "steps": "Steps Cool the burn under cool running water for 20 minutes. Cover with cling film.",
    }),
    "heat-stroke": ("Heat stroke", [], [], {
        "when-to-use": "When to use Hot, dry or sweating skin, confusion after heat. Boiling hot weather.",
        "steps": "Steps Move them somewhere cool, spray the skin with water and fan them.",
    }),
}


class FakeSemantic:
    def __init__(self, near=()):
        self.near = list(near)

    async def query(self, q, k=20):
        return self.near[:k]

    async def query_household(self, q, k=20):
        return []

    async def rerank_wikipedia(self, q, keys):
        return {}


class Down(FakeSemantic):
    async def query(self, q, k=20):
        raise RuntimeError("the embedding server is not there")

    async def query_household(self, q, k=20):
        raise RuntimeError("the embedding server is not there")

    async def rerank_wikipedia(self, q, keys):
        raise RuntimeError("the embedding server is not there")


@pytest.fixture
def conn(env):
    c = db.connect(env.db_path)
    db.init_schema(c)
    for slug, (title, conditions, aliases, sections) in CARDS.items():
        for sid, body in sections.items():
            c.execute(ROW_SQL, (title, body, f"card:{slug}", "card", "playbooks", "", None, f"/medical/card/{slug}#{sid}",
                                " ; ".join(aliases) if sid == "when-to-use" and aliases else None))
        if conditions:
            c.execute("INSERT INTO card_subjects(page, title, conditions, aliases) VALUES (?,?,?,?)",
                      (f"/medical/card/{slug}", title, json.dumps(conditions), json.dumps(aliases)))
    c.executemany(ROW_SQL, [
        ("The essentials, printed", "Printed first aid: an arm in a sling, a wound pad, a tourniquet for an arm or leg, "
         "the arm and the leg. Arm yourself with the essentials.", "page:rebuild-essentials-printed", "page", "playbooks", "",
         None, "/p/rebuild-essentials-printed#first-aid", None),
        ("Power", "In a power cut, a torch in every room. After a power cut the freezer stays cold for a day.",
         "module:power", "module", "playbooks", "", None, "/m/power#power-cut", None),
        ("Self-defence law", "Being armed is not self-defence; an arm raised is not a weapon.",
         "page:knife-firearms-law", "page", "playbooks", "", None, "/p/knife-firearms-law#law", None),
    ])
    for zim, title, cat in (("wikipedia_en_all_maxi", "Wikipedia", "reference"), ("mdwiki_en_all", "MDWiki", "medical"),
                            ("bicycles.stackexchange.com_en_all", "Bicycles", "practical")):
        c.execute("INSERT INTO library_items (id, title, kind, tier, category, dest, priority, available, fts) VALUES "
                  "(?, ?, 'zim', 'core', ?, ?, 50, 1, 1)", (zim, title, cat, f"zim/{zim}.zim"))
    c.commit()
    yield c
    c.close()


KIWIX = {
    "wikipedia_en_all_maxi": {
        "gash": [("Sam Gash", "Sam_Gash", "<b>Sam</b> <b>Gash</b> (born 1986) is an English footballer who played for <b>Gash</b> town"),
                 ("Olympic Arms", "Olympic_Arms", "<b>Olympic</b> <b>Arms</b> was an American manufacturer of rifles and <b>arms</b>")],
        "sam": [("Sam Gash", "Sam_Gash", "<b>Sam</b> <b>Gash</b> (born 1986) is an English footballer")],
    },
    "mdwiki_en_all": {"gash": [("Falling (accident)", "Falling_(accident)", "a fall onto an outstretched <b>arm</b>")]},
    "bicycles.stackexchange.com_en_all": {
        "gash": [("How do I bleed hydraulic brakes?", "q/1", "the lever <b>arm</b> and the brake bleeding kit")]},
}


def run(conn, env, q, sem=None):
    def reply(request):
        names = request.url.params.get_list("books.name")
        pattern = request.url.params.get("pattern", "")
        items = ""
        for zim in names:
            for key, hits in KIWIX.get(zim, {}).items():
                if key in pattern.split():
                    for title, path, snip in hits:
                        items += (f"<item><title>{title}</title><link>/kiwix/content/{zim}/A/{path}</link>"
                                  f"<description>{snip}</description></item>")
                    break
        return httpx.Response(200, text=f"<rss><channel>{items}</channel></rss>")

    with respx.mock(base_url=BASE, assert_all_called=False) as m:
        m.get("/search").mock(side_effect=reply)
        return asyncio.run(search.search(conn, env, KiwixClient(BASE), q, use_cache=False, semantic=sem))["results"]


def pages(results):
    return [r["url"].split("#", 1)[0] for r in results]


def card(slug):
    return f"/medical/card/{slug}"


WOUND_CARDS = {card("severe-bleeding"), card("wound-cleaning"), card("wound-closure")}


@pytest.mark.parametrize("sem", [None, FakeSemantic(), Down()], ids=["no-meaning-layer", "meaning-layer", "embedding-down"])
def test_gash_on_arm_leads_with_a_wound_card_and_broken_bones_is_below_every_wound_card(conn, env, sem):
    got = pages(run(conn, env, "gash on arm", sem))
    assert got[0] in WOUND_CARDS, got
    assert WOUND_CARDS <= set(got)
    last_wound = max(got.index(p) for p in WOUND_CARDS)
    assert card("broken-bones") not in got or got.index(card("broken-bones")) > last_wound, got
    assert got[0] == card("wound-cleaning")          # the card whose own alias the query uses ("gash")
    assert got[1] in WOUND_CARDS                     # a second relevant card inside the first KEPT_TOP


def test_without_the_injury_policy_the_body_word_wins(conn, env, monkeypatch):
    """The control: with the analysis off, the search is what shipped, and the one card that says "arm" leads."""
    monkeypatch.setattr(search, "INJURY_INTENT", False)
    got = pages(run(conn, env, "gash on arm"))
    assert got[0] not in WOUND_CARDS, got


def test_the_noise_that_shares_only_a_body_word_or_a_spelling_is_put_down(conn, env):
    got = run(conn, env, "gash on arm")
    urls = [r["url"] for r in got]
    wiki = "/read/wikipedia_en_all_maxi/A/Sam_Gash"
    assert wiki in urls                                                   # put down, not out
    assert all(urls.index(wiki) > urls.index(u) for u in urls if u.split("#")[0] in WOUND_CARDS)
    scores = {r["url"]: r["score"] for r in got}
    for noise in ("/read/wikipedia_en_all_maxi/A/Olympic_Arms", "/read/bicycles.stackexchange.com_en_all/A/q/1"):
        assert noise not in scores or scores[noise] < min(scores[u] for u in urls if u.split("#")[0] in WOUND_CARDS)


def test_the_penalty_is_what_puts_the_noise_down(conn, env, monkeypatch):
    factor = search.MEDICAL_UNSUPPORTED_FACTOR
    assert factor < 1.0
    on = {r["url"]: r["score"] for r in run(conn, env, "gash on arm")}
    monkeypatch.setattr(search, "MEDICAL_UNSUPPORTED_FACTOR", 1.0)
    off = {r["url"]: r["score"] for r in run(conn, env, "gash on arm")}
    wiki = "/read/wikipedia_en_all_maxi/A/Sam_Gash"
    assert on[wiki] == pytest.approx(off[wiki] * factor)


def test_sam_gash_as_its_own_query_still_finds_the_biography_first(conn, env):
    got = run(conn, env, "Sam Gash")
    assert got[0]["url"] == "/read/wikipedia_en_all_maxi/A/Sam_Gash"
    got = run(conn, env, "sam gash", FakeSemantic())
    assert got[0]["url"] == "/read/wikipedia_en_all_maxi/A/Sam_Gash"


def test_a_query_that_is_not_an_injury_is_searched_exactly_as_before(conn, env, monkeypatch):
    for q in ("power cut", "Sam Gash", "a book about treating gunshot wounds"):
        with_policy = [r["url"] for r in run(conn, env, q)]
        monkeypatch.setattr(search, "INJURY_INTENT", False)
        without = [r["url"] for r in run(conn, env, q)]
        monkeypatch.setattr(search, "INJURY_INTENT", True)
        assert with_policy == without, q


def test_spilled_boiling_water_leads_with_burns_and_heat_stroke_is_not_promoted(conn, env):
    """Heat stroke is nearer in meaning (live: cosine 0.64 against Burns' 0.63) and shares "hot", "skin", "boiling";
    the injury read is a burn, so Burns leads and Heat stroke is owed nothing."""
    near = [(card("heat-stroke") + "#when-to-use", 0.66), (card("burns") + "#when-to-use", 0.63)]
    got = pages(run(conn, env, "spilled boiling water on my leg", FakeSemantic(near)))
    assert got[0] == card("burns"), got
    assert card("heat-stroke") not in got[:1]


def test_the_condition_route_finds_a_card_that_never_says_the_body_word(conn, env, monkeypatch):
    """Retrieval alone, with nothing else to rescue it (no OR fallback): the AND of the condition's words and
    "arm" finds no wound card; the condition-only query does."""
    monkeypatch.setattr(search, "FTS_OR_BELOW", 0)
    monkeypatch.setattr(search, "INJURY_PROMOTION", False)
    assert card("wound-cleaning") in pages(run(conn, env, "gash on arm"))
    monkeypatch.setattr(search, "INJURY_RETRIEVAL", False)
    assert card("wound-cleaning") not in pages(run(conn, env, "gash on arm"))


def test_without_the_card_subjects_broken_bones_is_not_mistaken_for_a_wound_card(conn, env, monkeypatch):
    """Broken bones' warnings say "wound" and "bleeding"; only its curated subject (fracture) says it is not a
    wound card. The subjects are what keep it out of a wound query's promotion."""
    got = pages(run(conn, env, "gash on arm"))
    assert got.index(card("broken-bones")) > 2 if card("broken-bones") in got else True
    rows = conn.execute("SELECT page FROM card_subjects").fetchall()
    assert rows                                       # the fixture has them: the control below removes them
    conn.execute("DELETE FROM card_subjects")
    conn.commit()
    got = pages(run(conn, env, "gash on arm"))
    assert got[0] in WOUND_CARDS                      # the fallback reads a card's title: still a wound card first


def test_deep_cut_leg_leads_with_a_wound_card(conn, env):
    got = pages(run(conn, env, "deep cut leg"))
    assert got[0] in WOUND_CARDS and len(WOUND_CARDS & set(got[:3])) >= 2, got


def test_the_analysis_makes_the_query_medical(conn, env):
    from sos import query
    assert search.is_medical_intent(["gash", "arm"], query.analyse_injury("gash on arm"))
    assert not search.is_medical_intent(["sam", "gash"], query.analyse_injury("Sam Gash"))
