# Find: precision, one list, and meaning

**Date:** 2026-09-18. **Status:** built the same day. The owner: "do a critical review of the find search
results, these need to display much more elegantly and be much more precise … think about semantic search
and get it done and built".

## 1. What was wrong

Twelve real queries against the box, before:

- The score was the class weight over the rank within the class (`w / (5 + rank)`), so the first hit of every
  class tied whatever its words: "Side effects of warfarin" beside the Severe bleeding card for *bleeding*;
  "Dental drill" fourth for *power cut* while the Wikipedia article titled exactly "Power cut" was eighth;
  "Common questions about loratadine" (hay fever) for *child fever*; "Guide on firearms licensing" for *broken
  arm*; "Side effects of timolol eye drops" for *boil water*. Nothing about a result's own title or snippet
  reached its score; an exact title only led its own class.
- The same article twice: "Bleeding", "Vaginal bleeding", "Potassium iodide", "Dental drill", each from two
  medical encyclopaedias in the same class.
- One source flooding the page: five NHS medicines' side-effect pages for *bleeding*.
- Snippets of one word ('may', 'hay', 'of', "it's", 'gov/'), from a crawled site's furniture; the screen hid
  them and left a bare title that said nothing.
- The screen grouped by source, a heading each, in a fixed order of sources, so a weak source's best stood
  above a strong source's second, and forty results read as a directory.
- Words only: *how long does tinned food last* found a muffin recipe; nothing knew that tins are cans, that
  a blackout is a power cut, that "keep warm" is about hypothermia.

## 2. Precision (`api/sos/search.py`)

Applied after the class scores and the medical boost, before the sort:

1. **Relevance.** Each article and each of the box's own passages is multiplied by
   `1 + 1.2 × (share of the query's terms in the title) + 0.5 × (share in the snippet)`, terms and words
   matched on a light stem ("bleeding" ~ "bleed", "tins" ~ "tin", a term of four letters or more also as a
   prefix). A title that *is* the query is multiplied by 2.2 again. A hit with the query in neither its
   title nor its snippet, and no `<b>` mark from the engine, is a boilerplate match and is multiplied by
   0.45 — put down, not out. Places (exact by construction) and catalogue books (ranked on title and
   author already) are left alone.
2. **One article per title per source.** The best-scoring of the same normalised title (an NHS " - NHS" tail
   removed) stays; a second encyclopaedia's copy goes. Two sources with the same title are two answers.
3. **Diversity.** A source's fourth result and each after it is multiplied by 0.85 per step past the third,
   so no source fills the first screen.
4. **The household's words.** The keyword query to the box's own library is widened by a small synonym map
   (`query.SYNONYMS`, ~90 entries about emergencies): `("tinned" OR "canned" OR "tins") AND "food"`.
   Not applied to the Kiwix searches, whose parser is not ours.

## 3. Meaning (`api/sos/embeddings.py`)

The plan in the Gutenberg design, section 8, built for the box's own library:

- **Model.** bge-small-en-v1.5, 384 dimensions, q8_0 GGUF (37 MB, manifest item `bge-small-en-v1.5`), served
  by llama-server `--embedding --pooling cls` on port 8091: `install/systemd/sos-embed.service` on the box
  (always on, `MemoryMax=600M`, 25 ms a query), the dev stack when the model is present, and
  `sos build-embeddings` on the PC, which starts one if none is up.
- **Index.** `sos build-embeddings` embeds every `fts_docs` passage that is not a catalogue entry — the guides'
  sections, the quick cards, the modules, the pages, and each page of every converted document, some
  21,000 — as "title. body" cut to 1,400 characters (a batch the server refuses is embedded one passage at a
  time, each shortened until it fits the 512-token window). Written to `core/embeddings/docs.f16.bin`,
  `docs.ids` (the passages' urls, which survive a re-index; rowids do not) and `docs.meta.json`, by way of
  `.part` files (manifest item `embeddings-docs`). Rebuilt after the library changes.
- **Query.** The API loads the index once (33 MB as float32, re-read when the files change), prefixes the
  query with bge's instruction (`Represent this sentence for searching relevant passages: `), embeds it
  with a 0.6 s timeout, and takes the twenty nearest by dot product (all unit vectors). A cosine under 0.5
  is not near enough.
- **Fusion.** A near passage the words found is lifted by `score(w, rank)`; one the words missed is added
  with that as its score, its opening words as its snippet, and `via: "meaning"`. The relevance multiplier
  of section 2 is not applied to a row found by meaning: it has no words to be judged by.
- **Off** whenever the files, the server or the model are absent, or the server is slow: search is the
  keyword search, and nothing on the screen says otherwise.

## 4. The screen (`web/src`)

- Two groups: **From this box**, then **From the library** — everything else in the engine's order, the
  source a muted word before each title. The per-source headings and their fixed order are gone.
- The query's words are marked in each title with a rule beneath them.
- A row found by meaning carries a small italic *related* before its title.
- The source chips count the rows on the screen, the box's own as one chip, the rest in the order the engine
  first ranks them, four on the row and the rest behind More.

## 5. Not done

Semantic search over the Kiwix libraries (Wikipedia's and the NHS's articles are searched by kiwix-serve and
never pass through the box's index); the assistant's grounding still takes BM25 alone. Both are the next
step of the same design.
