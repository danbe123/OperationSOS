"""Condition directives in authored Markdown (situation spec section 5).

`{{#if phones}} … {{else}} … {{/if}}`, `{{#unless power}} … {{/unless}}` and the inline `[[call 999]]` are resolved
against a flag set before Markdown rendering. Flags are plain booleans keyed by condition id (`power`, `water`,
`mobile`, `landline`, `internet`, `gas`, `heating`, `roads`, `shops`, `sewage`), plus `phones` (any phone route
working), `dark`, and `scenario:<slug>`. Unknown flags are errors so a typo never silently hides advice."""
from __future__ import annotations

import re
from itertools import product
from typing import Iterable

FLAG_IDS = ("power", "water", "mobile", "landline", "internet", "gas", "heating", "roads", "shops", "sewage", "phones", "dark")
_BLOCK = re.compile(r"\{\{#(if|unless)\s+([\w:-]+)\s*\}\}(.*?)(?:\{\{else\}\}(.*?))?\{\{/\1\}\}", re.S)
_INLINE_CALL = re.compile(r"\[\[call\s+(999|112|111|105|101|0800[\d ]+|0345[\d ]+|0300[\d ]+)\]\]")
_ANY = re.compile(r"\{\{[#/]?(if|unless|else)[^}]*\}\}")
NO_PHONES_TEXT = "{n} will not connect while the phones are down: [get help without phones](page:no-phones)"


class DirectiveError(ValueError):
    pass


def flag_names(md_text: str) -> set[str]:
    """Every flag a document refers to, for validation and for cache keys."""
    return {m.group(2) for m in _BLOCK.finditer(md_text or "")}


def check_flags(names: Iterable[str]) -> list[str]:
    bad = []
    for n in names:
        if n in FLAG_IDS or n.startswith("scenario:"):
            continue
        bad.append(n)
    return bad


def resolve(md_text: str, flags: dict[str, bool]) -> str:
    """Apply the directives. Nested blocks resolve inside out because the regex is non-greedy and we loop."""
    text = md_text or ""

    def lookup(name: str) -> bool:
        if name in flags:
            return bool(flags[name])
        if name.startswith("scenario:"):
            return bool(flags.get(name, False))
        raise DirectiveError(f"unknown condition flag '{name}'")

    def replace(m: re.Match) -> str:
        kind, name, yes, no = m.group(1), m.group(2), m.group(3), m.group(4) or ""
        value = lookup(name)
        if kind == "unless":
            value = not value
        return yes if value else no

    previous = None
    while previous != text:
        previous = text
        text = _BLOCK.sub(replace, text)
    if _ANY.search(text):
        raise DirectiveError("unbalanced {{#if}} / {{/if}} directive")
    phones = flags.get("phones", True)
    text = _INLINE_CALL.sub(lambda m: f"call {m.group(1)}" if phones else NO_PHONES_TEXT.format(n=m.group(1)), text)
    return text


def signature(flags: dict[str, bool], used: Iterable[str]) -> str:
    """A short cache key: only the flags the document actually uses, in a fixed order."""
    names = sorted(set(used) | ({"phones"} if "[[call" in "" else set()))
    return ",".join(f"{n}={'1' if flags.get(n, True) else '0'}" for n in names)


def branch_flag_sets(md_text: str) -> list[dict[str, bool]]:
    """Every combination of the flags a document uses (plus `phones` when it has inline calls), for validation.
    Documents use few flags, so this stays small; a document using more than six is refused by the validator."""
    names = sorted(flag_names(md_text))
    if _INLINE_CALL.search(md_text or ""):
        names = sorted(set(names) | {"phones"})
    if len(names) > 6:
        raise DirectiveError(f"too many condition flags in one document ({len(names)}); split it")
    if not names:
        return [{}]
    return [dict(zip(names, values)) for values in product((True, False), repeat=len(names))]


def default_flags() -> dict[str, bool]:
    """Everything working, daylight, no scenario: what a document shows with no situation set."""
    return {n: True for n in FLAG_IDS if n != "dark"} | {"dark": False}


def has_inline_calls(md_text: str) -> bool:
    """Whether a document contains `[[call 999]]`, which makes its rendering depend on the `phones` flag."""
    return bool(_INLINE_CALL.search(md_text or ""))
