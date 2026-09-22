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
    # "gash" has no keyword-index synonym today (task 24): a plain-English "gash on arm" shares no content
    "gash": ("wound", "cut", "laceration", "bleeding"),
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
    # "the water stops", "the heating's stopped": the box says "off", "fails", "failure"
    "stops": ("stopped", "off", "fails", "failure"), "stopped": ("stops", "off", "fails", "failure"), "stop": ("stops", "off"),
    "broke": ("broken", "fails", "failure"), "gone": ("off", "fails", "failure"),
}


# Two words that are one idea: "power cut" is a phrase, not electricity AND a wound. Keyed by the adjacent
# terms as typed; the phrase itself first, then what else it is called.
PHRASES: dict[tuple[str, str], tuple[str, ...]] = {
    ("power", "cut"): ("power cut", "power cuts", "blackout", "outage", "power failure"),
    ("power", "cuts"): ("power cuts", "power cut", "blackout", "outage", "power failure"),
    ("power", "failure"): ("power failure", "power cut", "blackout", "outage"),
    ("carbon", "monoxide"): ("carbon monoxide",),
    ("heart", "attack"): ("heart attack", "cardiac arrest"),
    ("cardiac", "arrest"): ("cardiac arrest", "heart attack"),
    ("first", "aid"): ("first aid",),
    ("food", "poisoning"): ("food poisoning",),
    ("gas", "leak"): ("gas leak",),
    ("chest", "pain"): ("chest pain", "heart attack"),
    ("phone", "signal"): ("phone signal", "mobile signal", "reception", "network"),
    ("mobile", "signal"): ("mobile signal", "phone signal", "reception", "network"),
}


def expand_terms(terms: list[str]) -> list[list[str]]:
    """Each term with its synonyms beside it, the term first, and two adjacent terms that are one idea as
    one group of phrases: the groups an FTS query ORs within and ANDs across."""
    out: list[list[str]] = []
    i = 0
    while i < len(terms):
        pair = (terms[i].lower(), terms[i + 1].lower()) if i + 1 < len(terms) else None
        if pair in PHRASES:
            out.append(list(PHRASES[pair]))
            i += 2
            continue
        t = terms[i]
        out.append([t] + [a for a in SYNONYMS.get(t.lower(), ()) if a != t])
        i += 1
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



# --- Injury intent (task 25, 2026-09-22) -----------------------------------------------------------------------------
# "gash on arm" is an injury (an open wound) and a place on the body (the arm). The keyword query ANDs every idea, so
# a card about wounds that never says "arm" was not a candidate, and the one card that says "arm" five times (Broken
# bones) led. The analysis below reads the raw words, in order and with their stopwords (negation, "my", "himself"
# are what tell a body from a thing), and says which condition is described, where, and how badly -- or that it is
# not an injury at all: a surname ("Sam Gash"), a household phrase ("power cut", "bleeding the brakes"), a book
# request. It is the gate for search's injury policy (`search.py`: condition retrieval, card promotion, the
# unsupported-row penalty), so an ambiguous word ("cut", "burn", "broken", "bleeding") counts only when the rest of
# the sentence makes it bodily. `terms`, `fts` and `kiwix` are untouched by it.

# The canonical conditions: the same ids a quick card's `conditions:` front matter uses (playbooks/schema.json).
CONDITION_IDS: tuple[str, ...] = ("bleeding", "open_wound", "burn", "fracture", "sprain", "head_injury", "eye_injury",
                                  "nosebleed", "bite_sting", "spinal_injury")
# What the keyword index is asked for a condition, with the place on the body left out -- except where the place is
# the condition (a nosebleed, an eye injury, a head injury keep their anatomy). No bare "cut": in this library it is
# the power cut far more often than a wound, so it is asked for only as the phrases a wound is written in.
CONDITION_TERMS: dict[str, tuple[str, ...]] = {
    "bleeding": ("bleeding", "bleed", "haemorrhage", "tourniquet"),
    "open_wound": ("wound", "laceration", "gash", "graze", "cuts and grazes", "a cut", "the cut", "deep cut"),
    "burn": ("burn", "burns", "scald"),
    "fracture": ("fracture", "broken bone", "broken bones", "splint"),
    "sprain": ("sprain", "strain", "twisted ankle"),
    "head_injury": ("head injury", "concussion", "blow to the head"),
    "eye_injury": ("eye injury", "eye", "eyes"),
    "nosebleed": ("nosebleed", "nosebleeds", "nose bleed"),
    "bite_sting": ("bite", "bites", "bitten", "sting", "stings", "stung"),
    "spinal_injury": ("spinal", "spine", "neck injury"),
}
# The order a card for each condition is wanted in when a query names several: the specific place first (a nosebleed
# is not severe bleeding), then what kills first (uncontrolled bleeding), then the rest.
CONDITION_PRIORITY: tuple[str, ...] = ("nosebleed", "eye_injury", "head_injury", "spinal_injury", "bleeding", "burn",
                                       "fracture", "bite_sting", "sprain", "open_wound")

BODY_PARTS: dict[str, str] = {w: canon for canon, words in {
    "arm": "arm arms forearm forearms", "leg": "leg legs", "thigh": "thigh thighs", "shin": "shin shins",
    "calf": "calf calves", "hand": "hand hands palm palms", "finger": "finger fingers fingertip fingertips knuckle knuckles",
    "thumb": "thumb thumbs", "foot": "foot feet sole soles", "heel": "heel heels", "toe": "toe toes",
    "knee": "knee knees kneecap", "ankle": "ankle ankles", "wrist": "wrist wrists", "elbow": "elbow elbows",
    "shoulder": "shoulder shoulders collarbone", "neck": "neck", "head": "head scalp skull", "forehead": "forehead",
    "face": "face cheek cheeks chin jaw", "lip": "lip lips mouth tongue", "ear": "ear ears", "eye": "eye eyes eyeball eyelid",
    "nose": "nose nostril nostrils", "chest": "chest ribs rib", "belly": "belly stomach tummy abdomen", "hip": "hip hips",
    "groin": "groin", "armpit": "armpit armpits", "skin": "skin", "bone": "bone bones", "muscle": "muscle muscles",
    "ligament": "ligament ligaments tendon tendons",
}.items() for w in words.split()}
REFLEXIVE = frozenset("myself himself herself themselves yourself ourselves themself".split())
# Phrases whose ambiguous word is not an injury: consumed before any word is read. A tuple of words in order.
NONMEDICAL_PHRASES: tuple[tuple[str, ...], ...] = tuple(tuple(p.split()) for p in (
    "power cut", "power cuts", "budget cut", "budget cuts", "price cut", "tax cut", "pay cut", "short cut", "hair cut",
    "cut the grass", "cut the power", "cut off the power", "cut corners", "cut and paste", "cut down", "cut a mango",
    "broken link", "broken links", "broken glass", "broken window", "broken bottle", "broken heart", "broken english",
    "broken arrow", "broken down", "break a leg", "break down", "breaking news", "brake bleeding", "bleeding brakes",
    "bleed brakes", "bleed the brakes", "bleeding the brakes", "bleed a radiator", "bleed the radiator",
    "bleed the radiators", "bleeding the radiator", "bleeding the radiators", "bleeding radiators", "bleed radiators",
    "burn a cd", "burn cd", "burn a dvd", "burn dvd", "burn a disc", "burn disc", "burn notice", "burn ban",
    "burn rubbish", "burn wood", "burn calories", "burn fat", "slow burn", "heart burn", "razor burn", "freezer burn",
    "blood pressure", "blood sugar", "blood test", "blood type", "blood group", "blood donor", "wound up",
    "bite to eat", "sound bite", "bite size", "bite sized", "frost bite", "sting operation", "arm wrestling",
    "coat of arms", "arms race", "fire arms", "olympic arms",
))
_WOUND = frozenset("wound wounds wounded laceration lacerations lacerated graze grazes grazed".split())
_WOUND_AMBIGUOUS = frozenset("cut cuts gash gashed gashes slash slashed sliced slit scrape scraped puncture punctured "
                             "stab stabbed stabbing split".split())
_BLEED = frozenset("bleeding bleed bleeds bled blood bloody".split())
_BLEED_ALWAYS = frozenset("haemorrhage hemorrhage haemorrhaging hemorrhaging".split())
_BLEED_SEVERE = frozenset("spurting pouring gushing squirting pumping heavy heavily lots loads alot badly everywhere "
                          "soaking soaked profusely pool puddle losing lost severe serious".split())
_NEGATING = frozenset("wont cant not doesnt wouldnt isnt couldnt never".split())
_BLEED_ELSEWHERE = frozenset("pregnant pregnancy period periods gum gums vaginal miscarriage womb stool poo urine wee "
                             "cough coughing coughed vomit vomiting rectal piles".split())
_BURN_ALWAYS = frozenset("scald scalds scalded scalding".split())
_BURN = frozenset("burn burns burned burnt".split())
_BURN_CUES = frozenset("blister blisters blistering blistered stove hob oven iron kettle boiling hot fire flame flames "
                       "steam oil fat cooker pan saucepan chemical acid bonfire candle barbecue bbq".split())
_HOT = frozenset("boiling hot scalding".split())
_LIQUID = frozenset("water tea coffee oil fat soup liquid milk kettle pan saucepan steam".split())
_SPILL = frozenset("spilled spilt spill spills splashed splash splashes poured knocked pulled tipped went onto".split())
_FRACTURE_ALWAYS = frozenset("fracture fractures fractured".split())
_FRACTURE = frozenset("broken broke break breaks snapped cracked".split())
_SPRAIN_ALWAYS = frozenset("sprain sprains sprained".split())
_SPRAIN = frozenset("twisted twist twisting rolled strain strains strained pulled".split())
_JOINTS = frozenset("ankle wrist knee elbow shoulder finger thumb toe muscle ligament calf hip neck foot".split())
_HEAD_CUES = frozenset("hit hits banged bang bumped bump knocked knock blow fell fall fallen smacked whacked struck "
                       "injury injured hurt cracked dent concussion".split())
_EYE_CUES = frozenset("something stuck grit dust sand splash splashed chemical bleach poked poke scratched scratch hit "
                      "punched punch black injury injured hurt glass metal splinter blow".split())
_BITE = frozenset("bite bites bitten stung sting stings".split())
_ANIMALS = frozenset("dog dogs cat cats snake snakes adder adders spider spiders tick ticks bat bats bee bees wasp wasps "
                     "hornet hornets insect insects horse fox rat rats jellyfish human person midge midges mosquito "
                     "mosquitoes".split())
# Adder bites and ticks are the "Ticks and adders" page's, not the Bites and stings card's (the card says so itself):
# no card leads for them, and the search stays the one that shipped.
_BITE_ELSEWHERE = frozenset("adder adders snake snakes snakebite viper vipers tick ticks".split())
_CARE_CUES = frozenset("treat treating treated treatment dress dressing bandage heal healing infected infection clean "
                       "cleaning cool cooling stitches stitch sore hurts painful swollen swelling blister first aid".split())
_MODIFIERS = frozenset("deep deeper shallow bad badly nasty big large huge small minor tiny gaping open infected dirty "
                       "severe serious heavy heavily".split())
# A single word that is an injury on its own ("gash" typed alone is a wound, "cut" alone is not).
_STANDALONE = frozenset("gash gashes wound wounds laceration graze grazes bleeding bleed burn burns scald scalds "
                        "fracture sprain nosebleed concussion".split())
# A sign of another, graver emergency beside the injury ("throat swelling up after a wasp sting ... epipen" is
# anaphylaxis, not a sting to clean): the injury policy stands aside and the search is the one that shipped.
_OTHER_EMERGENCY = frozenset("anaphylaxis anaphylactic epipen adrenaline allergic allergy hives cpr unconscious "
                             "unresponsive seizure seizures fitting convulsing choking breathless".split())
_BOOK = frozenset("book books novel novels textbook poem poems poetry author".split())
_LOOKUP = frozenset("film movie album song tv series episode biography meaning definition etymology wikipedia history".split())


# Every word the analysis reads as the injury itself, a place or a qualifier: what is left of a query's terms ("adder",
# "stove", "kettle") is still a word to find, and search's weighted coverage counts it as one idea of its own.
INJURY_VOCAB = frozenset(set(BODY_PARTS) | _WOUND | _WOUND_AMBIGUOUS | _BLEED | _BLEED_ALWAYS | _BLEED_SEVERE | _NEGATING
                         | {"stop", "stopping", "burning", "bit", "nosebleed", "nosebleeds", "concussion", "concussed",
                            "spinal", "spine"} | _BURN | _BURN_ALWAYS | _FRACTURE | _FRACTURE_ALWAYS | _SPRAIN
                         | _SPRAIN_ALWAYS | _BITE | _MODIFIERS)


@dataclass(frozen=True)
class InjuryIntent:
    """What `analyse_injury` read: the conditions in `CONDITION_PRIORITY` order, the canonical body parts, the
    qualifiers, how sure (`none`, `possible` -- an injury word with nothing bodily about it -- or `confirmed`), and
    what for (`care`, `book`, `lookup`). `confirmed` is care intent confirmed: what search's injury policy needs."""
    conditions: tuple[str, ...] = ()
    locations: tuple[str, ...] = ()
    modifiers: tuple[str, ...] = ()
    confidence: str = "none"
    purpose: str = "care"
    matched_rules: tuple[str, ...] = ()

    @property
    def confirmed(self) -> bool:
        return self.confidence == "confirmed" and self.purpose == "care" and bool(self.conditions)


NO_INJURY = InjuryIntent()


def _raw_tokens(raw: str) -> list[str]:
    """The words in order, repeats and stopwords kept, apostrophes closed up ("won't" is "wont", "kid's" "kids")."""
    return _TOKEN_RE.findall(re.sub(r"['’]", "", (raw or "").lower()))


# Every nonmedical phrase as one pattern, longest first, its words apart by anything that is not a word: taken out of
# a text before its words are read. One C-speed pass, cheap enough for a passage's whole body as well as a query.
_NONMEDICAL_RE = re.compile(r"(?<![^\W_])(?:" + "|".join(
    r"[\W_]+".join(map(re.escape, p)) for p in sorted(NONMEDICAL_PHRASES, key=len, reverse=True)) + r")(?![^\W_])")


def free_tokens(text: str) -> list[str]:
    """The lower-case words of a text in order, apostrophes closed up, with every nonmedical phrase ("power cut",
    "brake bleeding") left out: the words search reads as evidence of an injury (task 25)."""
    return _TOKEN_RE.findall(_NONMEDICAL_RE.sub(" ", re.sub(r"['\u2019]", "", (text or "").lower())))


def analyse_injury(raw: str) -> InjuryIntent:
    """Read `raw` as an injury described, or not. See the block comment above."""
    tokens = _raw_tokens(raw)
    if not tokens:
        return NO_INJURY
    words = free_tokens(raw)
    have = set(words)
    content = [t for t in tokens if t not in STOPWORDS]
    locations = tuple(dict.fromkeys(BODY_PARTS[t] for t in words if t in BODY_PARTS))
    places = set(locations) - {"bone", "muscle", "ligament"}
    bodily = bool(places) or bool(have & REFLEXIVE)
    single = len(content) == 1
    conditions: set[str] = set()
    rules: list[str] = []
    ambiguous_seen = False

    def found(cond: str, rule: str) -> None:
        conditions.add(cond)
        rules.append(rule)

    def near_negated_stop() -> bool:
        return any(w == "stop" or w == "stopping" for w in words) and bool(have & _NEGATING)

    phrase = " ".join(words)
    # the places that are the condition
    if have & {"nosebleed", "nosebleeds"} or "nose bleed" in phrase or ("nose" in places and have & (_BLEED | _BLEED_ALWAYS)):
        found("nosebleed", "nose+bleed")
    if "eye" in places and (have & _EYE_CUES or have & (_WOUND | _WOUND_AMBIGUOUS | _BURN)):
        found("eye_injury", "eye+cue")
    if have & {"concussion", "concussed"} or "knocked out" in phrase or ("head" in places and have & _HEAD_CUES):
        found("head_injury", "head+impact")
    if have & {"spinal", "spine", "vertebra", "vertebrae", "paralysed", "paralyzed"} or (
            ("neck" in places or "back" in have) and have & (_FRACTURE | {"injury", "injured"})):
        found("spinal_injury", "spine")
    # bleeding: a nosebleed has taken it; a bleed in pregnancy, from the gums, in urine is not this card's
    bleed_words = have & _BLEED
    if "nosebleed" not in conditions and not have & _BLEED_ELSEWHERE:
        if have & _BLEED_ALWAYS:
            found("bleeding", "haemorrhage")
        elif bleed_words and (have & _BLEED_SEVERE or near_negated_stop()):
            found("bleeding", "bleed+severity")
        elif bleed_words and single and have & {"bleeding", "bleed"}:
            found("bleeding", "standalone")
        elif bleed_words - {"blood", "bloody"} and bodily:
            found("bleeding", "bleed+body")
        elif bleed_words:
            ambiguous_seen = True
    # burns: scald always; burn when bodily, with a burn's cause, cared for, or alone; hot liquid over a person
    if have & _BURN_ALWAYS:
        found("burn", "scald")
    elif have & _BURN:
        if (bodily and "chest" not in places) or have & _BURN_CUES or have & _CARE_CUES or single:
            found("burn", "burn+support")
        else:
            ambiguous_seen = True
    elif "burning" in have and have & _BURN_CUES:
        found("burn", "burning+cause")
    if "burn" not in conditions and have & _HOT and have & _LIQUID and (have & _SPILL or bodily):
        found("burn", "hot-liquid")
    # fractures
    if have & _FRACTURE_ALWAYS or "wrong way" in phrase or "sticking out" in phrase and "bone" in locations:
        found("fracture", "fracture")
    elif have & _FRACTURE:
        if places - {"eye", "neck"} or "bone" in locations:   # a broken neck is the spine card's
            found("fracture", "broken+body")
        else:
            ambiguous_seen = True
    # sprains
    if have & _SPRAIN_ALWAYS:
        found("sprain", "sprain")
    elif have & _SPRAIN and (set(locations) & _JOINTS or have & _JOINTS) and "fracture" not in conditions:
        found("sprain", "twist+joint")
    # bites and stings
    if have & _BITE or ("bit" in have and have & _ANIMALS):
        if have & _BITE_ELSEWHERE:
            ambiguous_seen = True
        elif have & _ANIMALS or bodily or "bitten" in have or "stung" in have:
            found("bite_sting", "bite")
        else:
            ambiguous_seen = True
    # open wounds: unambiguous words, or a cut/gash that is bodily, qualified, cared for, or typed alone
    if have & _WOUND:
        found("open_wound", "wound")
    elif have & _WOUND_AMBIGUOUS:
        if bodily or have & _CARE_CUES or (have & _MODIFIERS and have & {"cut", "gash", "cuts", "gashes"}) or (
                single and have & _STANDALONE):
            found("open_wound", "cut+support")
        else:
            ambiguous_seen = True
    if "bleeding" in conditions and bleed_words and bodily and "open_wound" not in conditions:
        found("open_wound", "bleed+body")
    if single and not conditions and have & _STANDALONE:
        for cond, terms in (("open_wound", _WOUND | {"gash", "gashes"}), ("burn", _BURN), ("fracture", {"fracture"}),
                            ("sprain", {"sprain"}), ("head_injury", {"concussion"})):
            if have & terms:
                found(cond, "standalone")

    if conditions & {"eye_injury"} and "open_wound" in conditions and not have & _WOUND:
        conditions.discard("open_wound")   # a cut or scratch to the eye is the eye card's
    ordered = tuple(c for c in CONDITION_PRIORITY if c in conditions)
    purpose = "book" if have & _BOOK else "lookup" if (have & _LOOKUP or tokens[:2] in (["who", "is"], ["who", "was"])) else "care"
    confidence = "confirmed" if ordered else "possible" if ambiguous_seen else "none"
    if ordered and (have & _OTHER_EMERGENCY or "not breathing" in phrase or "cant breathe" in phrase):
        confidence, rules = "possible", rules + ["other-emergency"]
    modifiers = tuple(dict.fromkeys(t for t in words if t in _MODIFIERS))
    return InjuryIntent(conditions=ordered, locations=locations, modifiers=modifiers, confidence=confidence,
                        purpose=purpose, matched_rules=tuple(rules))


def fts_match_conditions(intent: InjuryIntent) -> str:
    """`"wound" OR "laceration" OR "gash" ...`: the keyword query for an injury's conditions alone, every condition's
    words ORed (a passage about one of two injuries is still a candidate), the place on the body left out. Empty
    when there is no confirmed injury."""
    if not intent.confirmed:
        return ""
    words = list(dict.fromkeys(w for c in intent.conditions for w in CONDITION_TERMS[c]))
    return " OR ".join('"' + w.replace('"', '""') + '"' for w in words)


@dataclass(frozen=True)
class Query:
    raw: str
    tokens: list[str]
    terms: list[str]
    fts: str
    kiwix: str
    injury: InjuryIntent = NO_INJURY    # what analyse_injury read in the raw words (task 25)


def reduce_query(q: str) -> Query:
    tokens = tokenise(q)
    terms = content_terms(q) if tokens else []
    return Query(raw=q, tokens=tokens, terms=terms, fts=fts5_match(terms), kiwix=kiwix_pattern(terms),
                 injury=analyse_injury(q) if tokens else NO_INJURY)
