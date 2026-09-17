"""Query construction shared by search, suggest and the AI retriever (spec section 8)."""
from __future__ import annotations

import re
from dataclasses import dataclass

STOPWORDS: frozenset[str] = frozenset("""
a about above after again against all also am an and any anyone anything are aren around as at be because been before
being below best between both but by can cannot cant could couldn d did didn do does doesn doing don done down during
each eg either else etc even ever every everyone everything few find for from further get gets give go good got had
hadn has hasn have haven having he hello help her here hers herself hi him himself his how however i ie if im in
into is isn it its itself ive just know let like ll m make many may me mean means might mine more most much must
mustn my myself need neither never no none nor not nothing now of off often ok okay on once one only or other ought
our ours ourselves out over own please re really right s same shall shan she should shouldn show since so some
someone something sometimes still such t tell than thank thanks that thats the their theirs them themselves then
there these they thing things this those though through till to too under until up upon us use used using ve very
versus vs want was wasn way we were weren what whats when where whether which while who whom whose why will with
without won would wouldn yeah yes yet you your yours yourself yourselves
""".split())

_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)

# The household's word beside the box's, for the keyword index of the box's own library: "tinned" finds
# the Food module's "tins" and "canned"; "loo" finds sanitation. Keyed by the word as typed (and its stem),
# small on purpose — a synonym that is not about an emergency pulls in what it should not.
SYNONYMS: dict[str, tuple[str, ...]] = {
    "power": ("electricity", "mains", "blackout", "outage"), "blackout": ("power", "outage"), "outage": ("power", "blackout"),
    "electricity": ("power", "mains"), "tinned": ("canned", "tins", "tin"), "canned": ("tinned", "tins", "tin"), "tins": ("tinned", "canned"),
    "warm": ("heat", "heating", "cold"), "warmth": ("heat", "heating", "warm"), "heating": ("heat", "warm"), "cold": ("warm", "hypothermia"),
    "loo": ("toilet", "sanitation"), "toilet": ("sanitation", "loo", "sewage"), "sewage": ("toilet", "sanitation", "drains"),
    "kid": ("child", "children"), "kids": ("child", "children"), "child": ("children", "baby", "infant"), "children": ("child", "baby"),
    "baby": ("infant", "newborn", "child"), "infant": ("baby", "child"),
    "medicine": ("medication", "medicines", "tablets", "drug"), "medicines": ("medicine", "medication", "tablets"),
    "medication": ("medicine", "medicines", "tablets"), "tablets": ("tablet", "pills", "medicine"), "pills": ("tablets", "medicine"),
    "sick": ("ill", "illness", "unwell", "vomiting"), "ill": ("sick", "illness", "unwell"), "unwell": ("ill", "sick"),
    "bleed": ("bleeding", "blood"), "bleeding": ("bleed", "blood", "haemorrhage"), "blood": ("bleeding",),
    "burn": ("burns", "scald"), "burns": ("burn", "scald"), "scald": ("burn", "burns"),
    "broken": ("fracture", "break"), "fracture": ("broken", "break"), "wound": ("cut", "laceration", "bleeding"), "cut": ("wound", "laceration"),
    "wee": ("urine",), "poo": ("stool", "faeces", "diarrhoea"), "diarrhoea": ("diarrhea", "stool"), "diarrhea": ("diarrhoea",),
    "petrol": ("fuel", "diesel"), "diesel": ("fuel", "petrol"), "fuel": ("petrol", "diesel"),
    "torch": ("light", "lamp"), "torches": ("torch", "light"), "lamp": ("light", "torch"),
    "mobile": ("phone", "signal", "network"), "phone": ("mobile", "landline", "telephone"), "signal": ("mobile", "network", "reception"),
    "radio": ("pmr446", "walkie"), "walkie": ("pmr446", "radio"), "talkie": ("pmr446", "radio"),
    "purify": ("disinfect", "boil", "filter", "purification"), "purification": ("disinfect", "disinfection", "boil", "filter"),
    "disinfect": ("purify", "boil", "disinfection"), "disinfection": ("disinfect", "purify", "boil"), "boil": ("boiling", "disinfect", "purify"),
    "flood": ("flooding", "floods"), "flooding": ("flood", "floods"), "storm": ("storms", "gale", "wind"), "storms": ("storm", "gale"),
    "snow": ("ice", "cold", "blizzard"), "evacuate": ("evacuation", "leave"), "evacuation": ("evacuate", "leave"),
    "nuclear": ("fallout", "radiation"), "fallout": ("nuclear", "radiation"), "radiation": ("nuclear", "fallout", "radioactive"),
    "iodine": ("iodide", "potassium"), "iodide": ("iodine",), "generator": ("generators", "monoxide"),
    "fridge": ("freezer", "refrigerator"), "freezer": ("fridge", "frozen"), "food": ("eat", "meals", "rations"), "eat": ("food", "meals"),
    "cash": ("money", "notes"), "money": ("cash",), "pet": ("pets", "dog", "cat"), "pets": ("pet", "dog", "cat"), "dog": ("pet", "pets"),
    "cat": ("pet", "pets"), "cpr": ("resuscitation", "chest", "compressions"), "resuscitation": ("cpr",),
    "choke": ("choking",), "choking": ("choke",), "unconscious": ("collapsed", "unresponsive"), "collapsed": ("unconscious", "unresponsive"),
    "fever": ("temperature",), "temperature": ("fever",), "stroke": ("fast",), "asthma": ("inhaler", "wheeze"),
    "dehydrated": ("dehydration", "rehydration"), "dehydration": ("rehydration", "dehydrated"), "rehydration": ("dehydration", "ors"),
    "hypothermia": ("cold", "warm"), "frostbite": ("cold", "frost"), "heatstroke": ("heat", "heatwave"), "heatwave": ("heat", "heatstroke"),
}


def expand_terms(terms: list[str]) -> list[list[str]]:
    """Each term with its synonyms beside it, the term first: the groups an FTS query ORs within and ANDs across."""
    out: list[list[str]] = []
    for t in terms:
        alts = [t] + [a for a in SYNONYMS.get(t.lower(), ()) if a != t]
        out.append(alts)
    return out


def fts_match_expanded(terms: list[str], mode: str = "and") -> str:
    """`("tinned" OR "canned" OR "tins") "food"`: the keyword query for the box's own library, widened by
    the synonyms. A term without synonyms is itself."""
    if mode not in ("and", "or"):
        raise ValueError("mode must be 'and' or 'or'")
    groups = []
    for alts in expand_terms(terms):
        quoted = ['"' + a.replace('"', '""') + '"' for a in alts]
        groups.append(quoted[0] if len(quoted) == 1 else "(" + " OR ".join(quoted) + ")")
    return (" OR " if mode == "or" else " AND ").join(groups)
POSTCODE_RE = re.compile(r"^[A-Z]{1,2}\d[A-Z\d]? ?\d[A-Z]{2}$", re.IGNORECASE)
DISTRICT_RE = re.compile(r"^[A-Z]{1,2}\d[A-Z\d]?$", re.IGNORECASE)


def tokenise(q: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for tok in _TOKEN_RE.findall((q or "").lower()):
        if tok not in seen:
            seen.add(tok)
            out.append(tok)
    return out


def content_terms(q: str) -> list[str]:
    tokens = tokenise(q)
    terms = [t for t in tokens if t not in STOPWORDS]
    return terms or tokens


def fts5_match(tokens: list[str]) -> str:
    return " ".join(f'"{t}"' for t in tokens)


def fts_match(tokens: list[str], mode: str = "and") -> str:
    if mode not in ("and", "or"):
        raise ValueError("mode must be 'and' or 'or'")
    return (" OR " if mode == "or" else " ").join('"' + t.replace('"', '""') + '"' for t in tokens)


def kiwix_pattern(tokens: list[str]) -> str:
    return " ".join(tokens)


def is_postcode(s: str) -> bool:
    return bool(POSTCODE_RE.match((s or "").strip()))


def is_district(s: str) -> bool:
    return bool(DISTRICT_RE.match((s or "").strip()))


def place_candidates(q: str) -> list[str]:
    norm = " ".join((q or "").split())
    if not norm:
        return []
    cands = [norm]
    words = norm.split(" ")
    if len(words) > 1 and words[0].lower() in ("near", "in"):
        cands.append(" ".join(words[1:]))
    if len(words) > 1 and words[-1].lower() in ("near", "in"):
        cands.append(" ".join(words[:-1]))
    out: list[str] = []
    for c in cands:
        if c and c not in out:
            out.append(c)
    return out


@dataclass(frozen=True)
class Query:
    raw: str
    tokens: list[str]
    terms: list[str]
    fts: str
    kiwix: str


def reduce_query(q: str) -> Query:
    tokens = tokenise(q)
    terms = content_terms(q) if tokens else []
    return Query(raw=q, tokens=tokens, terms=terms, fts=fts5_match(terms), kiwix=kiwix_pattern(terms))
