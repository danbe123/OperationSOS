# api/sos/ai.py
"""AI assistant core (spec section 12).

Sections, in file order: constants and dataclasses; query reduction and the search adapter; HTML to
paragraphs and window selection; the health router (Task 3); LlamaClient, prompt and budget (Task 4);
citation hold-back (Task 5); the answer_events orchestrator (Task 7). The llama-server process lifecycle
lives in sos.ai_runtime and HTTP framing in sos.routers.ai.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import sqlite3
from dataclasses import asdict, dataclass, field
from html.parser import HTMLParser
from typing import Any, AsyncIterator, Awaitable, Callable, Iterable, Optional
from urllib.parse import unquote

import httpx

from sos import query as sos_query
from sos import search as sos_search
from sos.ai_terms import is_medical
from sos.config import Settings
from sos.kiwix import KiwixClient, KiwixError

log = logging.getLogger(__name__)

# --- constants (spec section 12) -------------------------------------------
MAX_QUESTION_CHARS = 400
MAX_QUERY_TERMS = 6
RETRY_TERMS = 3
MIN_HITS_BEFORE_RETRY = 3
PASSAGE_COUNT = 3
PASSAGE_TOKENS = 400
SYSTEM_TOKENS = 250
QUESTION_TOKENS = 150
PROMPT_CAP = 2000
MESSAGE_OVERHEAD = 30            # role markers plus the passage and question scaffolding
HISTORY_MAX_MESSAGES = 8         # at most four prior turns are even considered
ANSWER_MAX_TOKENS = 400
TEMPERATURE = 0.2
REFUSAL_TEXT = "The library doesn't cover this."
MEDICAL_DISCLAIMER = ("If someone is seriously ill or injured, call 999. "
                      "This is general information from the library, not a diagnosis.")
NON_PASSAGE_KINDS = {"place", "item"}
READ_URL = re.compile(r"^/read/([^/]+)/(.+)$")


@dataclass
class Passage:
    n: int
    title: str
    url: str
    source: str
    text: str


@dataclass
class Verbatim:
    title: str
    url: str
    paragraphs: list[str]
    as_at: Optional[str]


@dataclass
class Hit:
    title: str
    url: str
    source: str
    kind: str


# --- query reduction and search adapter (flow step 1) ----------------------

def content_terms(question: str) -> list[str]:
    """Adapter over plan 01's tokeniser: lowercase, split on non-alphanumerics, stopwords removed."""
    return sos_query.content_terms(question)


def reduce_query(question: str) -> list[str]:
    """At most six distinct content terms, in question order."""
    terms: list[str] = []
    for term in content_terms(question):
        if term not in terms:
            terms.append(term)
        if len(terms) == MAX_QUERY_TERMS:
            break
    return terms


def longest_terms(terms: list[str], n: int = RETRY_TERMS) -> list[str]:
    """The n longest terms, returned in their original order (ties broken by position)."""
    ranked = sorted(range(len(terms)), key=lambda i: (-len(terms[i]), i))[:n]
    return [terms[i] for i in sorted(ranked)]


def _field(obj: Any, name: str, default: Any = "") -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


async def run_search(q: str, conn: sqlite3.Connection, kiwix: KiwixClient, settings: Settings,
                     fts_mode: str = "or") -> list[Hit]:
    """Adapter over sos.search.search: FTS5 OR mode, cache bypassed, plain Hit objects."""
    resp = await sos_search.search(conn, settings, kiwix, q, limit=40, fts_mode=fts_mode, use_cache=False)
    rows = list(_field(resp, "results", []))
    terms = content_terms(q)
    authored = conn.execute(
        "SELECT title, body, url, kind FROM fts_docs WHERE fts_docs MATCH ? "
        "AND kind IN ('playbook', 'module', 'card', 'page') ORDER BY bm25(fts_docs, 5.0, 1.0) LIMIT 80",
        (sos_query.fts_match(terms, fts_mode),),
    ).fetchall()
    authored = sorted(authored, key=lambda r: term_hits(r["title"] + " " + r["body"], terms), reverse=True)
    guidance = []
    guide_urls = set()
    for r in authored:
        base = r["url"].split("#", 1)[0]
        if base in guide_urls:
            continue
        guide_urls.add(base)
        guidance.append({"title": r["title"], "url": r["url"], "kind": r["kind"], "source": "playbooks",
                         "score": sos_search.score(sos_search.PLAYBOOK_WEIGHT, len(guidance) + 1)})
        if len(guidance) == 12:
            break
    fulltext_rows = [*guidance, *rows]
    rows.extend(guidance)
    # Some useful ZIMs have only a title index. Query it rather than silently excluding them.
    if kiwix is not None:
        books = conn.execute("SELECT id, category, tier FROM library_items WHERE kind='zim' AND available=1").fetchall()
        semaphore = asyncio.Semaphore(4)

        async def titles(book, term):
            async with semaphore:
                try:
                    entries = await asyncio.wait_for(kiwix.suggest(book["id"], term), 3)
                except (KiwixError, httpx.HTTPError, TimeoutError):
                    return []
            return [{"title": e.get("value", ""), "url": f"/read/{book['id']}/{e['path']}",
                     "source": sos_search.classify(book), "kind": "article", "score": 0.1}
                    for e in entries if e.get("path")]

        stems = dict.fromkeys(t[:-2] if t.endswith("xes") else t[:-1] if len(t) > 3 and t.endswith("s") else t
                              for t in terms)
        tasks = [asyncio.create_task(titles(book, term)) for book in books for term in stems]
        batches = []
        try:
            if tasks:
                done, _ = await asyncio.wait(tasks, timeout=12)
                batches = [task.result() for task in tasks if task in done]
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
        rows.extend(row for batch in batches for row in batch)

    def matches(term, text):
        words = sos_query.tokenise(text)
        return any(word == term or (len(term) > 3 and word.startswith(term.rstrip("s"))) for word in words)

    def relevance(row):
        title = str(_field(row, "title"))
        snippet = str(_field(row, "snippet"))
        coverage = sum(matches(term, title) for term in terms)
        body_coverage = sum(matches(term, snippet) for term in terms)
        return (coverage * 2 + body_coverage, float(_field(row, "score", 0)))

    rows.sort(key=relevance, reverse=True)
    # Judge title-only hits using article text too; a product name alone is weak evidence.
    if kiwix is not None:
        # Preserve full-text matches before filling the remaining budget with title suggestions.
        # Large libraries can otherwise supply forty incidental title matches and displace guidance.
        candidates = []
        candidate_urls = set()
        for row in [*fulltext_rows[:20], *rows]:
            url = str(_field(row, "url"))
            if url in candidate_urls or _field(row, "kind") in NON_PASSAGE_KINDS:
                continue
            candidate_urls.add(url)
            candidates.append(row)
            if len(candidates) == 40:
                break
        async def preview(row):
            hit = Hit(title=str(_field(row, "title")), url=str(_field(row, "url")),
                      source=str(_field(row, "source")), kind=str(_field(row, "kind")))
            async with semaphore:
                try:
                    body = await asyncio.wait_for(passage_text(hit, terms, conn, kiwix), 3)
                except (KiwixError, httpx.HTTPError, TimeoutError):
                    body = ""
            title = hit.title
            covered = sum(matches(t, body) or matches(t, title) for t in terms)
            title_covered = sum(matches(t, title) for t in terms)
            quality = covered * 2 + title_covered * 0.5 + float(_field(row, "score", 0))
            if hit.source == "playbooks" and covered >= max(1, len(terms) / 2):
                quality += 2
            return quality, row
        ranked = await asyncio.gather(*(preview(row) for row in candidates))
        rows = [row for _, row in sorted(ranked, key=lambda pair: pair[0], reverse=True)]
    seen = set()
    hits = []
    for row in rows:
        url = str(_field(row, "url"))
        identity = url.split("#", 1)[0] if _field(row, "source") == "playbooks" else url
        if identity in seen:
            continue
        seen.add(identity)
        hits.append(Hit(title=str(_field(row, "title")), url=url,
                        source=str(_field(row, "source")), kind=str(_field(row, "kind"))))
    return hits[:12]


# --- HTML to paragraphs (flow step 3) --------------------------------------

SKIP_TAGS = {"nav", "header", "footer", "aside", "script", "style", "noscript", "svg", "form", "button",
             "title", "head"}
SKIP_CLASSES = {"nhsuk-header", "nhsuk-footer", "nhsuk-skip-link"}
BLOCK_TAGS = {"p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "dd", "dt", "td", "th", "blockquote", "pre",
              "figcaption", "summary"}


class _Extractor(HTMLParser):
    """Collects text blocks from <main> or #maincontent (else <body>), skipping page chrome."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._body: list[str] = []
        self._main: list[str] = []
        self._in_main = 0
        self._skip = 0
        self._stack: list[tuple[str, bool, bool]] = []
        self._buf: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        a = dict(attrs)
        classes = set((a.get("class") or "").split())
        is_skip = tag in SKIP_TAGS or a.get("role") == "navigation" or bool(classes & SKIP_CLASSES)
        is_main = tag == "main" or a.get("id") == "maincontent"
        if tag in BLOCK_TAGS and not self._skip:
            self._flush()
        self._stack.append((tag, is_main, is_skip))
        if is_skip:
            self._skip += 1
        if is_main:
            self._in_main += 1
        if tag == "br" and not self._skip:
            self._buf.append(" ")

    def handle_endtag(self, tag: str) -> None:
        while self._stack:
            t, is_main, is_skip = self._stack.pop()
            if t in BLOCK_TAGS and not self._skip:
                self._flush()
            if is_skip:
                self._skip -= 1
            if is_main:
                self._in_main -= 1
            if t == tag:
                break

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self._buf.append(data)

    def _flush(self) -> None:
        text = re.sub(r"\s+", " ", "".join(self._buf)).strip()
        self._buf = []
        if len(text) >= 2:
            (self._main if self._in_main else self._body).append(text)

    def result(self) -> list[str]:
        self._flush()
        return self._main if self._main else self._body


def article_paragraphs(html: str) -> list[str]:
    """Text blocks of an article: <main>/#maincontent if present else <body>, chrome removed."""
    parser = _Extractor()
    parser.feed(html)
    parser.close()
    return parser.result()


# --- window selection -------------------------------------------------------

def estimate_tokens(text: str) -> int:
    """Words × 1.3 (+1): the approximation used before /tokenize is consulted."""
    return int(len(text.split()) * 1.3) + 1


def term_hits(text: str, terms: Iterable[str]) -> int:
    low = text.lower()
    return sum(1 for t in terms if re.search(r"\b" + re.escape(t.lower()), low))


def trim_around_first_term(text: str, terms: list[str], max_words: int) -> str:
    """Keep max_words words starting a third of the way before the first query-term occurrence."""
    words = text.split()
    if len(words) <= max_words:
        return text
    idx = 0
    for i, w in enumerate(words):
        wl = w.lower()
        if any(wl.startswith(t.lower()) for t in terms):
            idx = i
            break
    start = max(0, idx - max_words // 3)
    return " ".join(words[start:start + max_words])


def best_window(blocks: list[str], terms: list[str], max_tokens: int = PASSAGE_TOKENS) -> str:
    """The run of consecutive blocks within max_tokens that contains the most query terms; ties go earlier."""
    blocks = [b for b in blocks if b.strip()]
    if not blocks:
        return ""
    costs = [estimate_tokens(b) for b in blocks]
    scores = [term_hits(b, terms) for b in blocks]
    best_text, best_score = "", -1.0
    for start in range(len(blocks)):
        used, chosen, score = 0, [], 0.0
        for j in range(start, len(blocks)):
            if used + costs[j] > max_tokens:
                if not chosen:               # a single oversized block: trim it around the first term
                    chosen.append(trim_around_first_term(blocks[j], terms, int(max_tokens / 1.3)))
                    score += scores[j]
                break
            chosen.append(blocks[j])
            used += costs[j]
            score += scores[j]
        score -= start * 0.001
        if score > best_score:
            best_score, best_text = score, "\n".join(chosen)
    return best_text


# --- retrieval (flow steps 1 and 3) ----------------------------------------

async def passage_text(hit: Hit, terms: list[str], conn: sqlite3.Connection, kiwix: KiwixClient) -> str:
    """The best 400-token window of one hit: ZIM articles via /kiwix/raw, everything else from fts_docs."""
    if hit.kind == "article":
        m = READ_URL.match(hit.url)
        if not m:
            return ""
        html = await kiwix.raw_article(m.group(1), unquote(m.group(2)))
        return best_window(article_paragraphs(html), terms, PASSAGE_TOKENS)
    row = conn.execute("SELECT body FROM fts_docs WHERE url = ? ORDER BY rowid LIMIT 1", (hit.url,)).fetchone()
    if row is None:
        return ""
    body = row["body"] or ""
    if hit.kind == "doc":                # a PDF page: the body trimmed around the first query term
        return trim_around_first_term(body, terms, int(PASSAGE_TOKENS / 1.3))
    base = hit.url.split("#", 1)[0]
    sections = conn.execute(
        "SELECT body FROM fts_docs WHERE url = ? OR substr(url, 1, length(?) + 1) = ? || '#' ORDER BY rowid",
        (base, base, base),
    ).fetchall()
    blocks = [r["body"] for r in sections if r["body"]]
    return best_window(blocks, terms, PASSAGE_TOKENS)


async def retrieve(query_tokens: list[str], conn: sqlite3.Connection, kiwix: KiwixClient,
                   settings: Settings) -> list[Passage]:
    """OR-mode search over the reduced query, retry with the three longest terms when fewer than three
    non-place hits come back, then the top three fetchable non-place hits as numbered passages."""
    terms = list(query_tokens)
    if not terms:
        return []
    hits = await run_search(" ".join(terms), conn, kiwix, settings)
    usable = [h for h in hits if h.kind not in NON_PASSAGE_KINDS]
    if len(usable) < MIN_HITS_BEFORE_RETRY and len(terms) > RETRY_TERMS:
        terms = longest_terms(terms)
        hits = await run_search(" ".join(terms), conn, kiwix, settings)
        usable = [h for h in hits if h.kind not in NON_PASSAGE_KINDS]
    passages: list[Passage] = []
    seen: set[str] = set()
    for hit in usable:
        if len(passages) == PASSAGE_COUNT:
            break
        if hit.url in seen:
            continue
        seen.add(hit.url)
        try:
            text = await passage_text(hit, terms, conn, kiwix)
        except (KiwixError, httpx.HTTPError) as exc:
            log.warning("ai: passage fetch failed for %s: %s", hit.url, exc)
            continue
        if not text.strip():
            continue
        passages.append(Passage(n=len(passages) + 1, title=hit.title, url=hit.url, source=hit.source, text=text))
    return passages


async def prefer_health_source(passages: list[Passage], verbatim: Optional[Verbatim], terms: list[str],
                               conn: sqlite3.Connection, kiwix: KiwixClient) -> list[Passage]:
    """Keep the matched NHS page or quick card among the sources used to answer a medical question.

    Fetch the passage normally; the separate verbatim UI excerpt is never used as prompt text.
    """
    if verbatim is None or any(p.url.split('#', 1)[0] == verbatim.url.split('#', 1)[0] for p in passages):
        return passages
    article = verbatim.url.startswith('/read/')
    source = 'nhs' if article else 'playbooks'
    hit = Hit(verbatim.title, verbatim.url, source, 'article' if article else 'card')
    try:
        text = await passage_text(hit, terms, conn, kiwix)
    except (KiwixError, httpx.HTTPError):
        return passages
    if not text.strip():
        return passages
    selected = [Passage(1, hit.title, hit.url, source, text), *passages][:PASSAGE_COUNT]
    return [Passage(n, p.title, p.url, p.source, p.text) for n, p in enumerate(selected, 1)]

# --- health router (flow step 2) -------------------------------------------

HEALTH_BOOK_SQL = ("SELECT id, COALESCE(resolved_as_at, as_at) AS as_at FROM library_items "
                   "WHERE kind = 'zim' AND available = 1 AND (id = 'nhs_uk' OR id LIKE 'nhs%') "
                   "ORDER BY CASE WHEN id = 'nhs_uk' THEN 0 ELSE 1 END, id")
CARD_TITLES_SQL = "SELECT DISTINCT title, url FROM fts_docs WHERE kind = 'card'"
MIN_VARIANT_LEN = 4        # single tokens shorter than this only match as part of the whole query
SUGGEST_STEM_LEN = 5       # "parac" finds paracetamol pages even when the question misspells it
MAX_SUGGEST_TERMS = 4
MIN_PARAGRAPH_CHARS = 40


@dataclass
class TitleMatch:
    kind: str                       # "card" or "nhs"
    title: str
    url: str
    book: Optional[str]
    path: Optional[str]
    as_at: Optional[str]


def edit_distance(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def title_key(title: str) -> str:
    """Lowercase title without the ' - NHS' suffix, the ': subtitle' and punctuation."""
    t = title.lower().strip()
    if t.endswith(" - nhs"):
        t = t[:-6]
    t = t.split(":", 1)[0]
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def clean_title(title: str) -> str:
    return re.sub(r"\s+-\s+NHS\s*$", "", title).strip()


def match_rank(q: str, key: str) -> Optional[int]:
    """0 for an exact title match, 1 for a word-boundary prefix within the allowed edit distance, else None.

    Allowed distance: 2 for queries of six or more characters, 1 for four or five, 0 below that."""
    if not q or not key:
        return None
    if q == key:
        return 0
    allowed = 2 if len(q) >= 6 else 1 if len(q) >= 4 else 0
    words = key.split()
    for k in range(1, len(words) + 1):
        prefix = " ".join(words[:k])
        if len(prefix) > len(q) + allowed:
            break
        if abs(len(prefix) - len(q)) <= allowed and edit_distance(q, prefix) <= allowed:
            return 1
    return None


def query_variants(tokens: list[str]) -> list[str]:
    """The whole reduced query, then adjacent bigrams, then single tokens of at least four characters."""
    variants = [" ".join(tokens)]
    if len(tokens) >= 2:
        variants += [f"{a} {b}" for a, b in zip(tokens, tokens[1:])]
        variants += [t for t in tokens if len(t) >= MIN_VARIANT_LEN]
    out: list[str] = []
    for v in variants:
        if v and v not in out:
            out.append(v)
    return out


def suggest_terms(tokens: list[str]) -> list[str]:
    """Terms sent to /kiwix/suggest: the whole query plus five-letter stems of the longer tokens."""
    terms = [" ".join(tokens)]
    for t in tokens:
        stem = t[:SUGGEST_STEM_LEN]
        if len(t) >= SUGGEST_STEM_LEN and stem not in terms:
            terms.append(stem)
    return terms[:MAX_SUGGEST_TERMS]


async def health_candidates(tokens: list[str], conn: sqlite3.Connection, kiwix: KiwixClient) -> list[TitleMatch]:
    """Quick-card titles from fts_docs plus suggest titles from every available NHS ZIM."""
    cands = [TitleMatch("card", r["title"], r["url"], None, None, None) for r in conn.execute(CARD_TITLES_SQL)]
    seen = {c.url for c in cands}
    for book in conn.execute(HEALTH_BOOK_SQL).fetchall():
        for term in suggest_terms(tokens):
            try:
                entries = await kiwix.suggest(book["id"], term)
            except (KiwixError, httpx.HTTPError) as exc:
                log.warning("ai: suggest failed for %s %r: %s", book["id"], term, exc)
                continue
            for e in entries:
                if not e.get("path"):
                    continue
                url = f"/read/{book['id']}/{e['path']}"
                if url in seen:
                    continue
                seen.add(url)
                cands.append(TitleMatch("nhs", e.get("value", ""), url, book["id"], e["path"], book["as_at"]))
    return cands


def card_paragraphs(conn: sqlite3.Connection, url: str) -> list[str]:
    rows = conn.execute("SELECT body FROM fts_docs WHERE kind = 'card' AND url = ? ORDER BY rowid", (url,)).fetchall()
    text = "\n\n".join((r["body"] or "") for r in rows)
    parts = [p.strip() for p in re.split(r"\n\s*\n|\n", text) if len(p.strip()) >= 20]
    return parts[:2]


async def verbatim_block(query: str, conn: sqlite3.Connection, kiwix: KiwixClient) -> Optional[Verbatim]:
    """Exact or near-prefix match of the reduced query against quick-card and NHS titles → first two paragraphs.

    Preference order: exact over prefix, card over NHS page, longer matching variant, shorter title, shorter URL."""
    tokens = query.split()
    if not tokens:
        return None
    cands = await health_candidates(tokens, conn, kiwix)
    best: Optional[tuple[tuple, TitleMatch]] = None
    for variant in query_variants(tokens):
        for c in cands:
            key = title_key(c.title)
            rank = match_rank(variant, key)
            if rank is None:
                continue
            score = (rank, 0 if c.kind == "card" else 1, -len(variant), len(key), len(c.url))
            if best is None or score < best[0]:
                best = (score, c)
    if best is None:
        return None
    match = best[1]
    if match.kind == "card":
        paragraphs = card_paragraphs(conn, match.url)
    else:
        html = await kiwix.raw_article(match.book or "", match.path or "")
        head = clean_title(match.title).split(":")[0].strip().lower()
        paragraphs = [b for b in article_paragraphs(html)
                      if len(b) >= MIN_PARAGRAPH_CHARS and not b.lower().startswith(head)][:2]
    if not paragraphs:
        return None
    return Verbatim(title=clean_title(match.title), url=match.url, paragraphs=paragraphs, as_at=match.as_at)

# --- llama-server client ----------------------------------------------------

class LlamaError(Exception):
    """llama-server unreachable, not ready, or returned an error chunk."""


class LlamaClient:
    """Async client for llama-server: /health, /props, /tokenize and the streaming chat endpoint."""

    def __init__(self, base_url: str, client: Optional[httpx.AsyncClient] = None) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(connect=10.0, read=200.0, write=30.0, pool=10.0))

    async def aclose(self) -> None:
        await self._client.aclose()

    async def health(self) -> bool:
        try:
            r = await self._client.get(f"{self.base_url}/health", timeout=5.0)
            return r.status_code == 200
        except httpx.HTTPError:
            return False

    async def model_name(self) -> Optional[str]:
        """Basename of /props model_path without .gguf, e.g. 'gemma-4-E2B-it-Q4_K_M'."""
        try:
            r = await self._client.get(f"{self.base_url}/props", timeout=5.0)
            if r.status_code != 200:
                return None
            data = r.json()
            path = data.get("model_path") or data.get("model_alias") or ""
        except (httpx.HTTPError, ValueError):
            return None
        name = path.rsplit("/", 1)[-1]
        return (name[:-5] if name.endswith(".gguf") else name) or None

    async def tokenize(self, text: str) -> int:
        """Token count from POST /tokenize; falls back to four characters per token."""
        try:
            r = await self._client.post(f"{self.base_url}/tokenize", json={"content": text}, timeout=10.0)
            if r.status_code == 200:
                return len(r.json()["tokens"])
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            pass
        return max(1, len(text) // 4)

    async def stream_chat(self, messages: list[dict], max_tokens: int = ANSWER_MAX_TOKENS,
                          temperature: float = TEMPERATURE) -> AsyncIterator[str]:
        """Yield text deltas from POST /v1/chat/completions (OpenAI-style SSE, ends with 'data: [DONE]')."""
        body = {"messages": messages, "stream": True, "max_tokens": max_tokens, "temperature": temperature,
                "cache_prompt": True, "chat_template_kwargs": {"enable_thinking": False}}
        try:
            async with self._client.stream("POST", f"{self.base_url}/v1/chat/completions", json=body) as r:
                if r.status_code != 200:
                    raise LlamaError(f"llama-server returned {r.status_code}")
                async for line in r.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if payload == "[DONE]":
                        return
                    obj = json.loads(payload)
                    if "error" in obj:
                        err = obj["error"]
                        raise LlamaError(str(err.get("message", err)) if isinstance(err, dict) else str(err))
                    choices = obj.get("choices") or []
                    if not choices:
                        continue
                    text = (choices[0].get("delta") or {}).get("content")
                    if text:
                        yield text
        except httpx.HTTPError as exc:
            raise LlamaError(f"llama-server unreachable: {exc}") from exc


# --- prompt and token budget (spec 12, flow step 5 and the budget table) ----

SYSTEM_PROMPT = (
    "You are the Operation SOS library assistant, working offline in the UK. "
    "You cannot make calls, send messages, place orders, access private records or retrieve live data. "
    "If asked to do these things, reply exactly: The library doesn't cover this. "
    "Answer only from the numbered passages in the user's message. After each sentence that uses a passage, "
    "cite it as [1], [2] or [3]. "
    "If the passages do not answer the question, reply exactly: The library doesn't cover this. "
    "Use British English and UK terms: 999 for an emergency, 111 for urgent medical advice, 105 for a power cut, "
    "paracetamol not acetaminophen. "
    "Never invent doses, laws, phone numbers, dates or place names; if the passages give none, say the library "
    "page must be checked. "
    "Keep the answer under 200 words, as short paragraphs or numbered steps."
)
MEDICAL_SYSTEM_LINE = " The question is medical: say when to call 999 and do not give a diagnosis."

TokenCounter = Callable[[str], Awaitable[int]]


@dataclass
class Budget:
    system: int = 0
    passages: list[int] = field(default_factory=list)
    question: int = 0
    history: int = 0
    dropped_history: int = 0

    @property
    def total(self) -> int:
        return self.system + sum(self.passages) + self.question + self.history + MESSAGE_OVERHEAD


async def trim_to_tokens(text: str, limit: int, counter: TokenCounter) -> tuple[str, int]:
    """Cut whole words proportionally until the counter says the text fits; characters as a last resort."""
    count = await counter(text)
    for _ in range(3):
        if count <= limit:
            return text, count
        words = text.split()
        keep = max(1, int(len(words) * limit / count) - 1)
        text = " ".join(words[:keep])
        count = await counter(text)
    if count > limit:
        text = text[: limit * 3]
        count = await counter(text)
    return text, count


def format_passages(passages: list[Passage]) -> str:
    lines = ["Passages from the library:"]
    for p in passages:
        lines.append(f"[{p.n}] {p.title} ({p.source})\n{p.text}")
    return "\n\n".join(lines)


async def build_messages(question: str, passages: list[Passage], history: list[dict], llama: LlamaClient,
                         medical: bool = False) -> tuple[list[dict], Budget]:
    """System ≤ 250, passages 3 × 400, question ≤ 150, history newest-first while it fits under the 2,000 cap."""
    counter = llama.tokenize
    budget = Budget()
    system, budget.system = await trim_to_tokens(
        SYSTEM_PROMPT + (MEDICAL_SYSTEM_LINE if medical else ""), SYSTEM_TOKENS, counter)
    trimmed: list[Passage] = []
    for p in passages[:PASSAGE_COUNT]:
        text, n = await trim_to_tokens(p.text, PASSAGE_TOKENS, counter)
        trimmed.append(Passage(p.n, p.title, p.url, p.source, text))
        budget.passages.append(n)
    question, budget.question = await trim_to_tokens(question.strip(), QUESTION_TOKENS, counter)
    remaining = PROMPT_CAP - budget.total
    recent = [m for m in history
              if m.get("role") in ("user", "assistant") and (m.get("content") or "").strip()][-HISTORY_MAX_MESSAGES:]
    kept: list[dict] = []
    for m in reversed(recent):                   # newest first; stop at the first turn that does not fit
        n = await counter(m["content"])
        if n > remaining:
            break
        kept.append({"role": m["role"], "content": m["content"]})
        remaining -= n
        budget.history += n
    kept.reverse()
    budget.dropped_history = len(history) - len(kept)
    user = f"{format_passages(trimmed)}\n\nQuestion: {question}"
    return [{"role": "system", "content": system}, *kept, {"role": "user", "content": user}], budget

# --- citation hold-back (flow step 6) --------------------------------------

CITATION_HOLD_CHARS = 6      # hold back from "[" until "]" or this many characters


class CitationFilter:
    """Streams text while holding back bracketed citations until they close, dropping unknown [n]."""

    def __init__(self, valid: Iterable[int]) -> None:
        self.valid = set(valid)
        self.citations: list[int] = []
        self._buf = ""

    def feed(self, text: str) -> str:
        out: list[str] = []
        for ch in text:
            if self._buf:
                self._buf += ch
                if ch == "]":
                    out.append(self._resolve())
                elif len(self._buf) >= CITATION_HOLD_CHARS:
                    out.append(self._release())
            elif ch == "[":
                self._buf = "["
            else:
                out.append(ch)
        return "".join(out)

    def flush(self) -> str:
        return self._release()

    def _release(self) -> str:
        held, self._buf = self._buf, ""
        return held

    def _resolve(self) -> str:
        held, self._buf = self._buf, ""
        m = re.fullmatch(r"\[\s*(\d+(?:\s*,\s*\d+)*)\s*\]", held)
        if not m:
            return held
        out: list[str] = []
        for num in re.findall(r"\d+", m.group(1)):
            n = int(num)
            if n in self.valid:
                out.append(f"[{n}]")
                if n not in self.citations:
                    self.citations.append(n)
        return "".join(out)

# --- the answer pipeline (flow steps 1 to 7) --------------------------------

async def answer_events(question: str, history: list[dict], conn: sqlite3.Connection, kiwix: KiwixClient,
                        llama: LlamaClient, settings: Settings) -> AsyncIterator[tuple[str, dict]]:
    """Yield (event, data) pairs: optional verbatim, retrieving, token*, done. Exceptions propagate."""
    tokens = reduce_query(question)
    query = " ".join(tokens)
    medical = is_medical(tokens)
    verbatim: Optional[Verbatim] = None
    if tokens:
        try:
            verbatim = await verbatim_block(query, conn, kiwix)
        except (KiwixError, httpx.HTTPError, sqlite3.Error) as exc:
            log.warning("ai: health router failed: %s", exc)
    if verbatim is not None:
        yield "verbatim", asdict(verbatim)
    passages = await retrieve(tokens, conn, kiwix, settings) if tokens else []
    passages = await prefer_health_source(passages, verbatim, tokens, conn, kiwix)
    yield "retrieving", {"query": query, "passages": [asdict(p) for p in passages]}
    if not passages:
        yield "done", {"answer": REFUSAL_TEXT, "grounded": False, "citations": []}
        return
    messages, budget = await build_messages(question, passages, history, llama, medical=medical)
    log.info("ai: prompt %d tokens (system %d, passages %s, question %d, history %d, dropped %d)",
             budget.total, budget.system, budget.passages, budget.question, budget.history, budget.dropped_history)
    filt = CitationFilter(p.n for p in passages)
    parts: list[str] = []
    async for delta in llama.stream_chat(messages, max_tokens=ANSWER_MAX_TOKENS, temperature=TEMPERATURE):
        text = filt.feed(delta)
        if text:
            parts.append(text)
            yield "token", {"text": text}
    tail = filt.flush()
    if tail:
        parts.append(tail)
        yield "token", {"text": tail}
    answer = "".join(parts).strip()
    if medical or verbatim is not None:
        extra = ("\n\n" if answer else "") + MEDICAL_DISCLAIMER
        answer += extra
        yield "token", {"text": extra}
    by_n = {p.n: p for p in passages}
    citations = [{"n": n, "title": by_n[n].title, "url": by_n[n].url, "source": by_n[n].source}
                 for n in filt.citations]
    yield "done", {"answer": answer, "grounded": bool(citations), "citations": citations}
