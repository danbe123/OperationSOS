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
   `1 + 1.2 × (share of the query's ideas in the title) + 0.5 × (share in the snippet)`, words matched on
   a light stem ("bleeding" ~ "bleed", "tins" ~ "tin", a term of four letters or more also as a prefix), a
   synonym of a term worth half of it ("fridge" for "freezer"), two words that are one idea taken as one
   ("power cut" is a phrase, not electricity and a wound: `query.PHRASES`). For the box's own passages
   the share carried by the whole passage stands in for the engine's fourteen-word snippet. A title that
   *is* the query is multiplied by 2.2 again. A hit with the query in neither its title nor its snippet,
   and no `<b>` mark from the engine, is a boilerplate match and is multiplied by 0.45 — put down, not
   out. Places (exact by construction) and catalogue books (ranked on title and author already) are left
   alone.
   The keyword index is asked twice, for the box's own passages (up to 150 rows: the library is 750
   passages, and "water" AND ("stops" OR "off" OR "fails") matches 173 of them, the Water module's
   sections at bm25's 47th, 92nd and 96th) and for the converted documents' pages (30 rows), each set
   ranked on its own. Within a set the rows rank by the share of the query's ideas the passage carries
   plus the share its title carries — the page that is *about* the query above one that mentions it —
   and bm25 decides among equals; bm25 alone put a short passage repeating one word above the long one
   that answered. When the AND of a query's ideas finds fewer than five rows, the OR is asked too, its
   rows after the AND's ("generator indoors": the Mains electricity page says "never indoors" two
   sentences from "generator"). A page's "Go deeper" links and a card's "Source" list are worth half, so
   a page found there is represented by the section that says something. The household's words for a
   failure ("the water stops", "the heating's gone") are in the synonym map as "off", "fails", "failure".
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
  time, each shortened until it fits the 512-token window). The section heading a passage opens with
  ("What to do", "Key facts": the anchor's words) is left out, since every module and card shares it and
  "what to do if the water stops" was finding every "What to do"; the "Go deeper" and "Source" link lists
  are not embedded at all. Written to `core/embeddings/docs.f16.bin`,
  `docs.ids` (the passages' urls, which survive a re-index; rowids do not) and `docs.meta.json`, by way of
  `.part` files (manifest item `embeddings-docs`). Rebuilt after the library changes.
- **Query.** The API loads the index once (33 MB as float32, re-read when the files change), prefixes the
  query with bge's instruction (`Represent this sentence for searching relevant passages: `), embeds it
  with a 0.6 s timeout, and takes the twenty nearest by dot product (all unit vectors).
- **How near is near.** bge-small's cosines run close together: on this library a passage that answers
  sits at 0.68 to 0.82, the nearest stranger at 0.62 to 0.72 (a building regulation for "generator
  indoors" at 0.71; the box's own "Mains electricity" answers at 0.68). So the floor depends on what the
  cosine is evidence for (`search.SEMANTIC_FLOOR`): a lift to a row the words found takes 0.60 (0.66 for a
  converted document's page); a row the words missed takes 0.66, and 0.74 for a document's page, whose
  21,000 neighbours are dense with strangers. Above its floor a hit is worth
  `0.5 × source weight × (cosine − 0.60) / (0.82 − 0.60)`, capped at the ceiling — worth its distance, not
  its rank in the list.
- **Fusion.** A near passage the words found is lifted by that; one the words missed is added with it as
  its score, its opening words (heading stripped) as its snippet, and `via: "meaning"`. The relevance
  multiplier of section 2 is not applied to a row found by meaning: it has no words to be judged by.
- **The cache.** `Semantic.generation` counts each load of the index; a search seeing a new generation
  drops the persistent `search_cache` first, so an index rebuilt under a running API does not serve the
  old answers until they expire.
- **Off** whenever the files, the server or the model are absent, or the server is slow: search is the
  keyword search, and nothing on the screen says otherwise.

### 3.1. Semantic expansion accepted on the PC, 20 September 2026

The full passage window is now `PASSAGE_CHARS=2584`, with reactive shortening for text that still exceeds the 512-token context; 21,368 document passages are published. The household collection uses an approximate index over 70,558 books (60,093 Gutenberg, 10,465 Survivor Library), not the document matrix. It adds or boosts books by meaning; the response uses `source: books`, and meaning-only additions carry `via: meaning`.

Wikipedia is a separate memory-mapped lookup, never an approximate nearest-neighbour search. Its completed build contains 8,425,865 keys: 7,243,109 usable vectors and 1,182,756 zero-vector entries for insufficient text. The vector file is 6,471,064,320 bytes. Measured full-build duration was 14,133.67 seconds, 596.16 candidate rows/s (3 h 55 m 34 s), superseding the need to estimate remaining build time. Household took 11,876.10 seconds, 5.94 embedded books/s. These are PC build measurements.

Only Wikipedia rows already found by Kiwix keywords are rescored, by `0.7 + 0.6 × max(0, cosine)`. Eight real queries preserved all 60 candidate rows through that step; two changed order. Cross-source title deduplication happens afterwards and can change which source supplies a final result. Seven live API queries also confirmed household meaning results and no meaning badges on 73 keyword hits from 17 excluded archives. Exclusions are `wiktionary_en_all_nopic`, `wikipedia_cy_all_maxi`, and all manifest IDs ending in `*.stackexchange.com_en_all`.

Publications keep the current and previous generation, serialize publication/pruning, ignore directory symlinks, and skip pruning if current pointers cannot be resolved. Loaders read vectors and metadata from the same resolved generation. Old flat metadata and dot-prefixed generations remain supported. Same-collection builds must not overlap because their staging filenames are shared. Query embeddings are reused across collections; failed queries are cached briefly. `Semantic.generation` changes only when loaded state changes, not on repeated failed loads.

See `docs/app-completion.md` for full acceptance results and `docs/reviews/2026-09-20-semantic-acceptance.json` for measured rows. Pi memory, latency and physical-device acceptance remain outstanding.

## 4. The screen (`web/src`)

- Two groups: **From this box**, then **From the library** — everything else in the engine's order, the
  source a muted word before each title. The per-source headings and their fixed order are gone.
- The query's words are marked in each title with a rule beneath them.
- A row found by meaning carries a small italic *related* before its title.
- One of the box's own passages says which section of its page it is, after the title in the source's tone
  ("Water · What to do"), and its snippet no longer opens with that heading.
- The source chips count the rows on the screen, the box's own as one chip, the rest in the order the engine
  first ranks them, four on the row and the rest behind More.

## 5. The battery, after

Fourteen queries against the box on the PC (the NHS ZIM absent). Top result, then what follows:
*bleeding* → Severe bleeding card, Ship Captain's Medical Guide, Pregnancy emergencies and Shock cards;
*cpr* → the two CPR cards; *power cut* → Solar panels in a power cut, Power module, Mains electricity,
"Power cut", "Power cuts - Prepare"; *how long does tinned food last* → Food module, famine playbook, Food
storage (related); *child fever* → Fever in a child card, Where There Is No Doctor; *broken arm* → Broken
bones card; *iodine tablets dose* → the NRPB stable iodine paper, Radiation module; *boil water* → Water
disinfection; *generator indoors* → Carbon monoxide card, Mains electricity (related); *snake bite* →
FM 4-25.11 First Aid, Where There Is No Doctor; *keep warm no heating* → Shelter and staying warm,
Shelter and heat, Hypothermia; *radio channels* → PMR446 channels, Getting help without phones; *what to
do if the water stops* → Water module ("when the mains fails, use in this order…"), Heatwave, drought and
water failure; *is it safe to eat food from the freezer after a power cut* → Food module ("in a power
cut, keep fridge and freezer doors shut"), National grid collapse ("eat the fridge first, then the
freezer"), Power. Each answers in 1.2 to 1.7 s, the Kiwix full-text searches the whole of it. The muffin recipe, the dental drill, loratadine, firearms licensing and Approved Document L are
gone.

## 6. Not done

Semantic retrieval over NHS and other article libraries remains unimplemented. Wikipedia now reranks
its existing keyword candidates as described in section 3.1, and household books have their own semantic
index. The assistant's grounding still takes BM25 alone. Physical Pi acceptance is also outstanding.
