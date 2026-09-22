"""HTTP client for kiwix-serve and the parsers for its XML/JSON responses.
Book names in every URL are ZIM filename stems, which equal manifest item ids."""
from __future__ import annotations

import asyncio
import html
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from html.parser import HTMLParser

import httpx

OPENSEARCH = "{http://a9.com/-/spec/opensearch/1.1/}"
ATOM = "{http://www.w3.org/2005/Atom}"


class KiwixError(RuntimeError):
    """`status` is the HTTP status kiwix-serve answered with; None when there was no such answer to
    speak of (a reply that would not parse, say)."""

    def __init__(self, message: str = "", status: int | None = None) -> None:
        super().__init__(message)
        self.status = status

    @property
    def permanent(self) -> bool:
        """A refusal that asking again will not change: a 4xx, bar the two that mean "not now"."""
        return self.status is not None and 400 <= self.status < 500 and self.status not in (408, 429)


@dataclass(frozen=True)
class Book:
    name: str
    fts: bool
    language: str
    title: str


@dataclass(frozen=True)
class KiwixHit:
    title: str
    path: str
    snippet: str
    book: str


_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def strip_tags(text: str) -> str:
    # Unescape first: some feeds (kiwix's suggest JSON) double-encode tags as "&lt;b&gt;" rather than
    # emitting them literally, so stripping tags before unescaping would miss them entirely.
    return _WS_RE.sub(" ", _TAG_RE.sub("", html.unescape(text or ""))).strip()


def _element_text(el: "ET.Element | None") -> str:
    """Every bit of text an element carries, tags and all -- unlike `Element.findtext`, which returns only
    the text immediately after the opening tag and silently drops anything inside or after a child element.
    Kiwix's search `<description>` marks its matched words with an inline `<b>…</b>` (real XML, not escaped
    text), so `findtext("description")` was truncating every snippet with a highlight to whatever text came
    before the *first* match -- losing the matched word and everything after it (task 24, 2026-09-22: this
    silently starved `relevance()`'s snippet-evidence check of the very evidence a keyword hit's highlight is
    supposed to be)."""
    if el is None:
        return ""
    parts = [el.text or ""]
    for child in el:
        parts.append(ET.tostring(child, encoding="unicode"))
        parts.append(child.tail or "")
    return "".join(parts)


def _split_content_link(link: str) -> tuple[str, str]:
    marker = "/content/"
    idx = link.find(marker)
    rest = link[idx + len(marker):] if idx >= 0 else link.lstrip("/")
    book, _, path = rest.partition("/")
    return book, path


def parse_search_xml(text: str) -> tuple[int, list[KiwixHit]]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise KiwixError(f"bad search XML: {exc}") from exc
    if root.tag == "error":
        raise KiwixError(strip_tags(text))
    channel = root.find("channel")
    if channel is None:
        raise KiwixError("no channel in search response")
    total_el = channel.find(f"{OPENSEARCH}totalResults")
    try:
        total = int((total_el.text or "0").replace(",", "")) if total_el is not None else 0
    except ValueError as exc:
        raise KiwixError("invalid totalResults in search response") from exc
    hits: list[KiwixHit] = []
    for item in channel.findall("item"):
        link = (item.findtext("link") or "").strip()
        book, path = _split_content_link(link)
        snippet = strip_tags(_element_text(item.find("description")))
        snippet = snippet.strip(". ").strip()
        hits.append(KiwixHit(title=(item.findtext("title") or "").strip(), path=path, snippet=snippet, book=book))
    return total, hits


def parse_catalog_xml(text: str) -> list[Book]:
    root = ET.fromstring(text)
    books: list[Book] = []
    for entry in root.findall(f"{ATOM}entry"):
        name = None
        for link in entry.findall(f"{ATOM}link"):
            if link.get("type") == "text/html" and link.get("href"):
                name = link.get("href").rstrip("/").rsplit("/", 1)[-1]
        if not name:
            name = entry.findtext(f"{ATOM}name") or ""
        tags = (entry.findtext(f"{ATOM}tags") or "").split(";")
        books.append(Book(
            name=name,
            fts="_ftindex:yes" in tags,
            language=entry.findtext(f"{ATOM}language") or "eng",
            title=entry.findtext(f"{ATOM}title") or name,
        ))
    return books


def parse_suggest_json(text: str) -> list[dict]:
    out = []
    try:
        entries = json.loads(text)
    except ValueError as exc:
        raise KiwixError("invalid suggestion JSON") from exc
    if not isinstance(entries, list):
        raise KiwixError("expected a list of suggestions")
    for entry in entries:
        if not isinstance(entry, dict):
            raise KiwixError("invalid suggestion entry")
        if entry.get("kind") != "path" or not entry.get("path"):
            continue
        if any(not isinstance(entry.get(field, ""), str) for field in ("path", "value", "label")):
            raise KiwixError("suggestion paths and labels must be strings")
        out.append({"value": entry.get("value", ""), "label": strip_tags(entry.get("label", "")), "path": entry["path"]})
    return out


_DROP_TAGS = {"nav", "header", "footer", "aside", "script", "style", "noscript", "template", "svg"}
_DROP_CLASSES = ("nhsuk-header", "nhsuk-footer", "nhsuk-skip-link")
_BLOCK_TAGS = {"p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "div", "td", "th", "tr", "br", "section", "article",
               "dd", "dt", "blockquote", "pre", "figcaption", "summary", "ul", "ol", "table"}
_VOID = {"br", "img", "input", "hr", "meta", "link", "area", "base", "col", "embed", "source", "track", "wbr"}


class _TextExtractor(HTMLParser):
    """Paragraph extractor implementing spec section 12 step 3: keep <main> or #maincontent when present,
    drop nav/header/footer/aside/script/style/noscript, [role=navigation] and the NHS chrome classes."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.all_paras: list[str] = []
        self.main_paras: list[str] = []
        self.buf: list[str] = []
        self.skip_stack: list[str] = []
        self.main_depth = 0
        self.main_stack: list[str] = []
        self.has_main = False

    def _flush(self) -> None:
        text = _WS_RE.sub(" ", "".join(self.buf)).strip()
        self.buf = []
        if len(text) < 2:
            return
        self.all_paras.append(text)
        if self.main_depth > 0:
            self.main_paras.append(text)

    @staticmethod
    def _is_dropped(tag: str, attrs: list[tuple[str, str | None]]) -> bool:
        if tag in _DROP_TAGS:
            return True
        a = dict(attrs)
        if (a.get("role") or "") == "navigation":
            return True
        cls = a.get("class") or ""
        return any(c in cls for c in _DROP_CLASSES)

    def handle_starttag(self, tag, attrs):
        if tag in _BLOCK_TAGS:
            self._flush()
        if self._is_dropped(tag, attrs):
            if tag not in _VOID:
                self.skip_stack.append(tag)
            return
        if self.skip_stack:
            return
        a = dict(attrs)
        if tag == "main" or (a.get("id") == "maincontent"):
            self.has_main = True
            self.main_depth += 1
            self.main_stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        if tag in _BLOCK_TAGS:
            self._flush()

    def handle_endtag(self, tag):
        if tag in _BLOCK_TAGS:
            self._flush()
        if self.skip_stack:
            if tag == self.skip_stack[-1]:
                self.skip_stack.pop()
            return
        if self.main_stack and tag == self.main_stack[-1]:
            self._flush()
            self.main_stack.pop()
            self.main_depth -= 1

    def handle_data(self, data):
        if self.skip_stack:
            return
        self.buf.append(data)

    def result(self) -> list[str]:
        self._flush()
        return self.main_paras if self.has_main else self.all_paras


def extract_text(html_text: str, *, max_chars: int | None = None) -> list[str]:
    parser = _TextExtractor()
    if max_chars is None:
        parser.feed(html_text)
    else:
        # Meaning search only reads an opening passage. Avoid parsing a whole novel for it.
        # A main element can occur after long page furniture: wait for it when present.
        expects_main = bool(re.search(r"<main(?:\s|>)|\bid\s*=\s*['\"]?maincontent(?:['\"]|\s|>)",
                                      html_text, re.I))
        for start in range(0, len(html_text), 4096):
            parser.feed(html_text[start:start + 4096])
            paragraphs = parser.main_paras if parser.has_main else parser.all_paras
            if (parser.has_main or not expects_main) and sum(len(p) + 1 for p in paragraphs) > max_chars:
                return paragraphs
    parser.close()
    return parser.result()


class KiwixClient:
    def __init__(self, base_url: str, timeout: float = 5.0, client: httpx.AsyncClient | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = client or httpx.AsyncClient(timeout=timeout, follow_redirects=True)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def catalog(self) -> list[Book]:
        r = await self._client.get(f"{self.base_url}/catalog/v2/entries", params={"count": "-1"})
        if r.status_code != 200:
            raise KiwixError(f"catalog: HTTP {r.status_code}")
        return parse_catalog_xml(r.text)

    async def search(self, books: list[str], q: str, n: int = 8, timeout: float = 2.0) -> list[KiwixHit]:
        params: list[tuple[str, str]] = [("pattern", q)]
        params += [("books.name", b) for b in books]
        params += [("format", "xml"), ("pageLength", str(n))]
        r = await asyncio.wait_for(self._client.get(f"{self.base_url}/search", params=params), timeout)
        if r.status_code != 200:
            raise KiwixError(f"search: HTTP {r.status_code}: {strip_tags(r.text)[:200]}", status=r.status_code)
        _, hits = parse_search_xml(r.text)
        return hits

    async def suggest(self, book: str, term: str) -> list[dict]:
        r = await self._client.get(f"{self.base_url}/suggest", params={"content": book, "term": term})
        if r.status_code != 200:
            return []
        return parse_suggest_json(r.text)

    async def raw_article(self, book: str, path: str) -> str:
        r = await self._client.get(f"{self.base_url}/raw/{book}/content/{path}")
        if r.status_code != 200:
            raise KiwixError(f"raw {book}/{path}: HTTP {r.status_code}")
        return r.text

    async def exists(self, book: str, path: str) -> bool:
        r = await self._client.get(f"{self.base_url}/raw/{book}/content/{path}")
        return r.status_code == 200
