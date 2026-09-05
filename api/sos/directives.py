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
# one token at a time, so blocks may nest to any depth: an open tag, an {{else}}, or a close tag
_TOKEN = re.compile(r"\{\{#(if|unless)\s+([\w:-]+)\s*\}\}|\{\{(else)\}\}|\{\{/(if|unless)\}\}")
_INLINE_CALL = re.compile(r"\[\[call\s+(999|112|111|105|101|0800[\d ]+|0345[\d ]+|0300[\d ]+)\]\]")
NO_PHONES_TEXT = "{n} will not connect while the phones are down: [get help without phones](page:no-phones)"


class DirectiveError(ValueError):
    pass


def flag_names(md_text: str) -> set[str]:
    """Every flag a document refers to, at any depth, for validation and for cache keys."""
    return {m.group(2) for m in _TOKEN.finditer(md_text or "") if m.group(2)}


def check_flags(names: Iterable[str]) -> list[str]:
    bad = []
    for n in names:
        if n in FLAG_IDS or n.startswith("scenario:"):
            continue
        bad.append(n)
    return bad


class _Block:
    """One `{{#if}}` … `{{else}}` … `{{/if}}`, with whatever is inside it (text or more blocks)."""

    __slots__ = ("kind", "name", "then", "otherwise")

    def __init__(self, kind: str, name: str) -> None:
        self.kind, self.name = kind, name
        self.then: list = []
        self.otherwise: list | None = None


def _parse(md_text: str) -> list:
    """The document as a tree of text and blocks. Nesting is handled by a stack, not by a regex."""
    text = md_text or ""
    root: list = []
    current = root
    stack: list[tuple[_Block, list]] = []
    pos = 0
    for m in _TOKEN.finditer(text):
        current.append(text[pos:m.start()])
        pos = m.end()
        if m.group(1):
            block = _Block(m.group(1), m.group(2))
            stack.append((block, current))
            current = block.then
        elif m.group(3):
            if not stack:
                raise DirectiveError("{{else}} outside a {{#if}} block")
            block = stack[-1][0]
            if block.otherwise is not None:
                raise DirectiveError(f"two {{{{else}}}} in one {{{{#{block.kind} {block.name}}}}} block")
            block.otherwise = []
            current = block.otherwise
        else:
            if not stack:
                raise DirectiveError("unbalanced {{#if}} / {{/if}} directive")
            block, parent = stack.pop()
            if block.kind != m.group(4):
                raise DirectiveError(f"{{{{#{block.kind} {block.name}}}}} closed by {{{{/{m.group(4)}}}}}")
            parent.append(block)
            current = parent
    current.append(text[pos:])
    if stack:
        raise DirectiveError("unbalanced {{#if}} / {{/if}} directive")
    return root


def _walk(nodes: list):
    for node in nodes:
        if isinstance(node, _Block):
            yield node
            yield from _walk(node.then)
            yield from _walk(node.otherwise or [])


def _render(nodes: list, lookup) -> str:
    out = []
    for node in nodes:
        if isinstance(node, _Block):
            value = lookup(node.name)
            if node.kind == "unless":
                value = not value
            out.append(_render(node.then if value else (node.otherwise or []), lookup))
        else:
            out.append(node)
    return "".join(out)


def resolve(md_text: str, flags: dict[str, bool]) -> str:
    """Apply the directives. Blocks may nest to any depth, and an {{else}} belongs to its own block."""

    def lookup(name: str) -> bool:
        if name in flags:
            return bool(flags[name])
        if name.startswith("scenario:"):
            return bool(flags.get(name, False))
        raise DirectiveError(f"unknown condition flag '{name}'")

    tree = _parse(md_text)
    for block in _walk(tree):          # a typo in a branch nobody is reading is still a mistake
        lookup(block.name)
    text = _render(tree, lookup)
    phones = flags.get("phones", True)
    return _INLINE_CALL.sub(lambda m: f"call {m.group(1)}" if phones else NO_PHONES_TEXT.format(n=m.group(1)), text)


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
