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
