# Embedding and reranker bake-off, 2026-09-21

Question: would a bigger or better embedding model, and/or a cross-encoder reranker over the top candidates, buy enough
accuracy on Operation SOS's meaning search to justify switching from `bge-small-en-v1.5`, given a Raspberry Pi 5 with 8 GB
and no GPU? Baseline being improved: `docs/reviews/2026-09-20-search-baseline.md` (paraphrase hit@5 0.60).

Everything here is reproducible from `tools/eval/search/lab/` (scripts) and `tools/eval/search/lab/results/` (raw JSON).
No production code was touched. Branch `search-models`.

## 1. Bottom line

**Recommendation: switch the meaning-search model to `intfloat/e5-base-v2` (110 M parameters, 768 dimensions, q8_0 GGUF 118 MB),
and do NOT add a reranker.** `thenlper/gte-base` is the fallback (same size, no prefixes, statistically indistinguishable
overall, but weaker on the safety guard).

| | bge-small-en-v1.5 (control) | e5-base-v2 |
|---|--|--|
| paraphrase MRR@10 / hit@1 / hit@5, dense only | 0.514 / 0.402 / 0.663 | 0.627 / 0.500 / 0.826 |
| safety MRR@10 / hit@1 / card in top 3, dense only | 0.682 / 0.559 / 26 of 34 | 0.985 / 0.971 / 34 of 34 |
| same, inside the best simple hybrid | 0.750 / 0.647 / 28 of 34 (RRF) | 0.941 / 0.882 / 34 of 34 (weighted, 0.7 meaning) |
| Pi resident memory of `llama-server --embedding` | 151 MB | 245 MB (limit is `MemoryMax=600M`) |
| query embedding, PC, `-t 4` / `-t 1` | 27.5 / 40.0 ms | 35.0 / 68.5 ms (1.3x / 1.7x) |
| rebuild, docs / Wikipedia (GPU) | 18 s / 2.0 h | 38 s / 4.2 h |
| index on disk, Wikipedia (fp16) | 6.5 GB | 12.9 GB |

Expected gain, stated as ranges rather than a point because the comparison depends on how the keyword side is fused:
dense against dense, paraphrase MRR **+0.11** (95% interval +0.02 to +0.20, 34 wins / 15 losses of 92) and safety MRR
**+0.30** (+0.19 to +0.43, 15 wins / 0 losses of 34). Inside the same hybrid (control's RRF against e5's RRF) the gain
shrinks to paraphrase MRR **+0.06** (+0.00 to +0.11) and safety +0.06 (+0.01 to +0.11); with both at the weighted fusion (0.7 on meaning) it is
paraphrase +0.11 and safety +0.22. So plan on **about +0.05 to +0.10 paraphrase MRR and a real improvement on the
hard safety paraphrases**, not on the +0.11 to +0.30 the dense-only rows show. Half of the dense-only gain is the model
preferring the box's short authored cards (section 8), which the gold rewards and a flat score bonus reproduces on any model.

Reranker verdict: **none of the seven cross-encoders is acceptable.** Used on their own they make things worse (50 to
110 of the 172 queries get a worse rank; up to 20 safety rows leave the top 3). Blended with the pool by RRF they no
longer hurt much, but the best small native one (gte-reranker-modernbert-base) adds only +0.02 to +0.03 MRR (interval
touching zero), and costs 2.0 s per query for 10 candidates on this PC at `-t 4` (11.4 s for 30), 300 MB more memory, and
would be slower still on the Pi. Details in section 5.

## 2. Setup and honest caveats

**Corpus.** Exactly what `sos build-embeddings` embeds for the box's own library: `build()` and `passage_text()` of
`api/sos/embeddings.py`, reproduced from `fts_docs` of the dev database opened read-only (`mode=ro`): 21,368 passages
(120 playbooks, 57 modules, 148 cards, 309 pages, 20,734 document pages), each keyed by its url (all unique). 7,572 are at the 2,584 character cap.
The rows and their order equal the shipped `docs.ids` (checked). Model input is the same `passage_text` for every model,
cut to 512 tokens by the tokenizer.

**Queries.** The gold sets `own-library`, `paraphrase`, `safety`; relevant passages are every corpus row whose url matches an
expected url by `evalrun.url_matches` (an `expected` list is alternatives, a query counts at the best rank of any of its relevant
passages). Rows whose only expected pages are Kiwix-only (Wikipedia, NHS ZIM articles, iFixit) are dropped, since they cannot be
in this corpus:

| set | in gold | kept | dropped |
|---|--:|--:|--:|
| own-library | 63 | **46** (39 answer, 7 health) | 17 |
| paraphrase | 126 | **92** (78 answer, 14 health) | 34 (17 questions, both rewordings each) |
| safety | 34 | **34** (17 plain, 17 hard) | 0 |
| total | 223 | **172** | 51 |

Dropped ids are in `results/corpus_stats.json`. These numbers are therefore **not comparable to the baseline report's**, which
counted Wikipedia and NHS alternatives and mixed keyword sources: the control's paraphrase hit@5 here is 0.663 (dense only), the
baseline's 0.603 (whole pipeline, all 126 rows).

**Things a reader must weigh.**

1. **Small, single-author gold.** 46, 92 and 34 queries, written by one person; the 92 paraphrases are 46 questions
   x 2 wordings, so they are not independent. A difference of a few points is noise. Every headline comparison below carries a paired bootstrap
   95% interval (4,000 resamples over queries) and win / loss counts; `*` marks an interval excluding zero. No correction for multiple
   comparisons: about 20 models and 10 systems were looked at, so the best of them is chosen on the same data it is scored on (winner's curse). The
   interval for a headline comparison is therefore too optimistic for the model picked as best.
2. **The gold rewards authored passages.** Every one of the 172 queries has at least one relevant passage among the box's 634 authored
   passages (cards, modules, pages, playbooks: 3% of the corpus); none is answered only by a converted document page. A model or a
   score prior that prefers short authored passages looks better here than it may be on real use (section 8 measures this).
3. **This is not the production pipeline.** Dense retrieval over the 21k passages, plus a simple fusion with the FTS5 keyword
   ranking; no Kiwix sources, no book/Wikipedia groups, no medical boost, no `SEMANTIC_FLOOR` gates. The keyword side reuses the project's query
   preparation (`query.reduce_query`, `fts_match_expanded` synonyms and phrases, AND with OR fallback) in two variants:
   `bm25` (one bm25 ranking over all corpus passages) and `prod` (the box's `fts_rows` as `search.py` runs it: own passages and document pages fetched
   separately and re-sorted by the share of query ideas each carries; the halves merged by rank).
4. **The control's index is not a clean one.** llama-server refuses a passage over 510 tokens, so the box's `embed_batch` shortens it;
   8,560 of 21,368 passages (40%) are over 510 tokens. For passages at or under 510 tokens the shipped vectors equal the torch fp16 ones (cosine 0.9999); for the
   others the mean cosine is 0.972 (`results/control_vs_shipped_index.json`). Scored against the shipped vectors the control gets
   paraphrase MRR 0.500 against 0.514 for the clean 512-token cut (difference -0.014, interval -0.048 to +0.017): inside the noise, so the torch control is a fair stand-in.
5. **Measurement environment.** fp16 on an RTX 4070 SUPER that other processes share (7 GB in use by others), on a host that was
   also running another agent's `eval-search`, `kiwix-serve` and a CPU `llama-server`, load average 2 to 14. Rates and latencies are
   real but noisy; ratios between models measured close together are the more reliable figure.
6. **Not run, because they need remote code** (`auto_map` in `config.json`, checked by fetching only `config.json`; `results/skipped_remote_code.json`):
   nomic-embed-text-v1/v1.5, gte-base-en-v1.5, gte-large-en-v1.5, jina-embeddings-v2 (base, small), arctic-embed-m-v2.0, arctic-embed-m-long,
   jina-reranker-v1 (tiny, turbo). Not attempted: larger than the 150 M budget (Qwen3-Embedding, EmbeddingGemma, bge-m3).

## 3. Experiment A: dense retrieval only

fp16, GPU, plain transformers, max length 512, each model's own pooling and prefixes, unit vectors, exact cosine. Pooling was
checked against each repo's own sentence-transformers `1_Pooling/config.json` (this caught one error of mine: mxbai-embed-xsmall-v1 is
mean-pooled, not CLS; its first run was discarded); the prefixes are those of the model cards / `config_sentence_transformers.json` prompts. Recorded in
`results/model_cards.json` and `results/embed/*.json`.

| model | pooling | query prefix | passage prefix |
|---|---|---|---|
| bge-small/base/large-en-v1.5 | CLS | "Represent this sentence for searching relevant passages: " (the project's `QUERY_PREFIX`) | none |
| snowflake-arctic-embed-s / m / m-v1.5, mxbai-embed-large-v1 | CLS | same instruction | none |
| e5-small-v2, e5-base-v2 | mean | "query: " | "passage: " |
| all-MiniLM-L12-v2, gte-small, gte-base, multi-qa-MiniLM-L6-cos-v1, all-mpnet-base-v2, mxbai-embed-xsmall-v1 | mean | none | none |
| granite-embedding-small-english-r2, granite-embedding-english-r2 (ModernBERT) | CLS | none | none |

Control = `bge-small-en-v1.5` with the instruction prefix and no passage prefix. `all-MiniLM-L12-v2@128` (its trained window),
`bge-small@256` are extra rows showing what a shorter window does.

| model | params | dims | par h@1 | par h@5 | par MRR | safety h@1 | safety h@3 | safety MRR | guard (card in top 3) | own h@5 | own MRR | ALL MRR | GPU docs/s |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| bge-small-en-v1.5 | 33M | 384 | 0.402 | 0.663 | 0.514 | 0.559 | 0.765 | 0.682 | 26/34 | 0.913 | 0.712 | 0.600 | 1200 |
| shipped-index | 33M | 384 | 0.391 | 0.641 | 0.500 | 0.588 | 0.794 | 0.702 | 27/34 | 0.891 | 0.745 | 0.606 | 1200 |
| bge-small-en-v1.5@256 | 33M | 384 | 0.348 | 0.652 | 0.486 | 0.588 | 0.853 | 0.710 | 29/34 | 0.891 | 0.726 | 0.594 | 1957 |
| e5-small-v2 | 33M | 384 | 0.391 | 0.652 | 0.495 | 0.676 | 0.853 | 0.768 | 29/34 | 0.826 | 0.723 | 0.610 | 1168 |
| all-MiniLM-L12-v2 | 33M | 384 | 0.424 | 0.696 | 0.543 | 0.529 | 0.853 | 0.696 | 29/34 | 0.848 | 0.733 | 0.624 | 1166 |
| all-MiniLM-L12-v2@128 | 33M | 384 | 0.402 | 0.663 | 0.520 | 0.647 | 0.824 | 0.748 | 28/34 | 0.848 | 0.717 | 0.618 | 3143 |
| gte-small | 33M | 384 | 0.380 | 0.663 | 0.511 | 0.588 | 0.882 | 0.748 | 30/34 | 0.891 | 0.720 | 0.614 | 1001 |
| arctic-embed-s | 33M | 384 | 0.348 | 0.565 | 0.448 | 0.529 | 0.765 | 0.656 | 26/34 | 0.848 | 0.658 | 0.545 | 1141 |
| multi-qa-MiniLM-L6-cos-v1 | 23M | 384 | 0.272 | 0.576 | 0.382 | 0.471 | 0.765 | 0.623 | 26/34 | 0.891 | 0.732 | 0.523 | 1656 |
| mxbai-embed-xsmall-v1 | 24M | 384 | 0.293 | 0.598 | 0.446 | 0.647 | 0.824 | 0.750 | 28/34 | 0.870 | 0.766 | 0.592 | 1326 |
| granite-embedding-small-english-r2 | 48M | 384 | 0.380 | 0.652 | 0.499 | 0.824 | 0.941 | 0.885 | 32/34 | 0.891 | 0.812 | 0.659 | 627 |
| e5-base-v2 | 110M | 768 | 0.500 | 0.826 | 0.627 | 0.971 | 1.000 | 0.985 | 34/34 | 0.870 | 0.777 | 0.738 | 564 |
| gte-base | 110M | 768 | 0.467 | 0.815 | 0.615 | 0.765 | 0.941 | 0.855 | 32/34 | 0.935 | 0.794 | 0.710 | 564 |
| bge-base-en-v1.5 | 110M | 768 | 0.435 | 0.674 | 0.544 | 0.676 | 0.941 | 0.799 | 32/34 | 0.913 | 0.779 | 0.657 | 585 |
| arctic-embed-m | 110M | 768 | 0.326 | 0.696 | 0.486 | 0.529 | 0.912 | 0.720 | 31/34 | 0.935 | 0.728 | 0.597 | 555 |
| arctic-embed-m-v1.5 | 110M | 768 | 0.380 | 0.750 | 0.538 | 0.500 | 0.912 | 0.696 | 31/34 | 0.935 | 0.760 | 0.629 | 562 |
| all-mpnet-base-v2 | 110M | 768 | 0.348 | 0.717 | 0.502 | 0.559 | 0.794 | 0.686 | 27/34 | 0.783 | 0.688 | 0.588 | 333 |
| granite-embedding-english-r2 | 149M | 768 | 0.543 | 0.750 | 0.625 | 0.853 | 0.941 | 0.892 | 32/34 | 0.870 | 0.805 | 0.726 | 239 |
| bge-large-en-v1.5 | 335M | 1024 | 0.424 | 0.772 | 0.559 | 0.706 | 0.853 | 0.775 | 29/34 | 0.891 | 0.694 | 0.638 | 206 |
| mxbai-embed-large-v1 | 335M | 1024 | 0.413 | 0.739 | 0.548 | 0.647 | 0.853 | 0.747 | 29/34 | 0.848 | 0.702 | 0.628 | 195 |

`guard` = safety rows whose card is in the top 3 (34 rows). Own-library (n=46) is flat across models: hit@5 0.78 to 0.94, no model
clearly better than the control. Safety split (dense only):

| system | safety/plain h@1 | h@3 | safety/hard h@1 | h@3 | h@5 | MRR | paraphrase/answer MRR | paraphrase/health MRR (n=14) |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| bge-small-en-v1.5 dense | 0.765 | 1.000 | 0.353 | 0.529 | 0.647 | 0.481 | 0.479 | 0.710 |
| e5-base-v2 dense | 1.000 | 1.000 | 0.941 | 1.000 | 1.000 | 0.971 | 0.588 | 0.845 |
| gte-base dense | 0.882 | 1.000 | 0.647 | 0.882 | 0.941 | 0.770 | 0.592 | 0.744 |
| granite-embedding-english-r2 dense | 1.000 | 1.000 | 0.706 | 0.882 | 0.882 | 0.784 | 0.571 | 0.929 |
| bge-base-en-v1.5 dense | 0.882 | 1.000 | 0.471 | 0.882 | 0.882 | 0.657 | 0.551 | 0.503 |
| bge-large-en-v1.5 dense | 0.824 | 0.882 | 0.588 | 0.824 | 0.882 | 0.691 | 0.571 | 0.493 |
| mxbai-embed-large-v1 dense | 0.647 | 0.882 | 0.647 | 0.824 | 0.882 | 0.737 | 0.551 | 0.531 |

Paired comparison against the control (B minus A; difference of the mean, [95% interval], `*` = excludes 0, W/L = queries B does better / worse on):

| comparison (B minus A) | paraphrase MRR | safety MRR | ALL MRR | paraphrase hit@1 | safety hit@1 |
|---|--|--|--|--|--|
| dense: e5-base-v2 vs control | +0.113 [+0.021, +0.199]* (34W/15L) | +0.303 [+0.185, +0.434]* (15W/0L) | +0.138 [+0.083, +0.194]* (58W/20L) | +0.098 [-0.011, +0.206] (18W/9L) | +0.412 [+0.265, +0.588]* (14W/0L) |
| dense: gte-base vs control | +0.101 [+0.019, +0.186]* (35W/15L) | +0.173 [+0.046, +0.305]* (13W/3L) | +0.110 [+0.058, +0.165]* (58W/20L) | +0.065 [-0.043, +0.174] (16W/10L) | +0.206 [+0.029, +0.382]* (9W/2L) |
| dense: granite-embedding-english-r2 (149M) vs control | +0.111 [+0.018, +0.205]* (38W/15L) | +0.210 [+0.099, +0.336]* (13W/2L) | +0.126 [+0.068, +0.186]* (61W/23L) | +0.141 [+0.022, +0.261]* (23W/10L) | +0.294 [+0.118, +0.471]* (11W/1L) |
| dense: granite-embedding-small-english-r2 (47M) vs control | -0.015 [-0.110, +0.084] (29W/29L) | +0.203 [+0.069, +0.348]* (12W/2L) | +0.059 [-0.004, +0.121] (53W/36L) | -0.022 [-0.130, +0.098] (15W/17L) | +0.265 [+0.088, +0.471]* (11W/2L) |
| dense: e5-small-v2 vs control | -0.019 [-0.093, +0.056] (26W/20L) | +0.086 [-0.042, +0.223] (11W/6L) | +0.010 [-0.041, +0.060] (44W/36L) | -0.011 [-0.109, +0.087] (10W/11L) | +0.118 [-0.060, +0.324] (8W/4L) |
| dense: bge-base-en-v1.5 vs control | +0.030 [-0.054, +0.114] (31W/16L) | +0.117 [+0.000, +0.237]* (10W/3L) | +0.057 [+0.004, +0.111]* (51W/23L) | +0.033 [-0.065, +0.141] (13W/10L) | +0.118 [-0.059, +0.294] (7W/3L) |
| dense: bge-large-en-v1.5 (upper bound) vs control | +0.045 [-0.044, +0.133] (37W/21L) | +0.093 [-0.047, +0.233] (11W/5L) | +0.037 [-0.019, +0.096] (57W/36L) | +0.022 [-0.087, +0.130] (15W/13L) | +0.147 [-0.029, +0.324] (8W/3L) |
| dense: mxbai-embed-large-v1 (upper bound) vs control | +0.034 [-0.050, +0.118] (35W/19L) | +0.065 [-0.076, +0.211] (11W/7L) | +0.028 [-0.030, +0.089] (56W/37L) | +0.011 [-0.098, +0.120] (14W/13L) | +0.088 [-0.118, +0.294] (8W/5L) |
| dense: e5-base-v2 vs gte-base | +0.012 [-0.058, +0.081] (24W/22L) | +0.130 [+0.042, +0.230]* (8W/1L) | +0.028 [-0.018, +0.075] (35W/29L) | +0.033 [-0.076, +0.141] (14W/11L) | +0.206 [+0.059, +0.353]* (8W/1L) |
| dense: e5-base-v2 vs granite-embedding-english-r2 | +0.002 [-0.087, +0.088] (23W/25L) | +0.093 [+0.029, +0.181]* (5W/0L) | +0.012 [-0.040, +0.065] (32W/30L) | -0.043 [-0.152, +0.065] (12W/16L) | +0.118 [+0.029, +0.235]* (4W/0L) |
| dense: shipped index (production's shortened passages) vs control clean 512-token cut | -0.014 [-0.048, +0.017] (11W/11L) | +0.020 [-0.003, +0.056] (3W/1L) | +0.005 [-0.019, +0.030] (22W/15L) | -0.011 [-0.054, +0.033] (2W/3L) | +0.029 [+0.000, +0.088] (1W/0L) |

Reading it:

- **Bigger is not the lever.** bge-large and mxbai-large (335 M, the upper bounds) beat the control by +0.045 and +0.034 paraphrase
  MRR, neither distinguishable from zero. bge-base (110 M) +0.030. The models that help are the ones trained differently at the same size:
  **e5-base-v2, gte-base and granite-embedding-english-r2 (149 M)**, each about +0.10 to +0.11 paraphrase MRR (interval excludes 0) and
  +0.17 to +0.30 safety MRR.
- **Small models do not help.** e5-small-v2 (+0.010 overall), granite-small (+0.059, interval touches 0; but +0.20 on safety) and
  all-MiniLM-L12-v2 (paraphrase MRR 0.543, no interval computed) are level with the control on paraphrase. arctic-embed-s, multi-qa-MiniLM and mxbai-embed-xsmall are lower (0.45, 0.38, 0.45 against 0.51; no interval computed).
- **e5-base-v2 against gte-base and granite-r2** (the other two leaders): indistinguishable on paraphrase (+0.012, +0.002),
  better on the safety rows (+0.130 and +0.093 MRR, intervals exclude 0; 8 wins / 1 loss and 5 / 0). Its 34 of 34 on the guard
  is the only perfect one.
- Sanity: mean pooling versus CLS and prefixes are as documented; getting them wrong would have shown as a collapse (none did).

## 4. Experiment B: hybrid (keyword + meaning)

Top-100 of each side. **RRF**: k = 60, no tuning. **Weighted**: min-max normalise each side's scores over its top 100, `alpha` x meaning +
(1 - alpha) x keyword, alpha in {0.3, 0.5, 0.7} (0.3 shown in `results/B_hybrid.json`; 0.5 and 0.7 below). The alpha grid is a
sensitivity check, not a tuned choice; picking 0.7 as best on this data is optimistic. Both keyword variants (`bm25`, `prod`) are shown.

| dense model | system | par h@1 | par h@5 | par MRR | safety h@1 | safety h@3 | safety MRR | guard | own MRR | ALL MRR |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| bge-small-en-v1.5 | dense | 0.402 | 0.663 | 0.514 | 0.559 | 0.765 | 0.682 | 26/34 | 0.712 | 0.600 |
| (keyword only, same for all) | kw_bm25 | 0.120 | 0.370 | 0.237 | 0.471 | 0.529 | 0.538 | 18/34 | 0.629 | 0.401 |
| (keyword only, same for all) | kw_prod | 0.337 | 0.533 | 0.414 | 0.618 | 0.735 | 0.676 | 25/34 | 0.870 | 0.588 |
|  | rrf+bm25 | 0.239 | 0.533 | 0.385 | 0.618 | 0.765 | 0.696 | 26/34 | 0.716 | 0.535 |
|  | rrf+prod | 0.359 | 0.761 | 0.528 | 0.647 | 0.824 | 0.750 | 28/34 | 0.852 | 0.658 |
|  | wsum0.5+bm25 | 0.250 | 0.685 | 0.421 | 0.559 | 0.676 | 0.660 | 23/34 | 0.742 | 0.554 |
|  | wsum0.7+bm25 | 0.315 | 0.685 | 0.472 | 0.529 | 0.765 | 0.663 | 26/34 | 0.752 | 0.585 |
|  | wsum0.5+prod | 0.337 | 0.630 | 0.480 | 0.647 | 0.794 | 0.731 | 27/34 | 0.841 | 0.626 |
|  | wsum0.7+prod | 0.359 | 0.707 | 0.512 | 0.618 | 0.824 | 0.724 | 28/34 | 0.863 | 0.648 |
| e5-base-v2 | dense | 0.500 | 0.826 | 0.627 | 0.971 | 1.000 | 0.985 | 34/34 | 0.777 | 0.738 |
|  | rrf+bm25 | 0.337 | 0.576 | 0.456 | 0.647 | 0.794 | 0.732 | 27/34 | 0.751 | 0.589 |
|  | rrf+prod | 0.435 | 0.772 | 0.585 | 0.735 | 0.882 | 0.808 | 30/34 | 0.860 | 0.703 |
|  | wsum0.5+bm25 | 0.370 | 0.728 | 0.525 | 0.676 | 0.882 | 0.788 | 30/34 | 0.794 | 0.649 |
|  | wsum0.7+bm25 | 0.457 | 0.783 | 0.604 | 0.824 | 1.000 | 0.907 | 34/34 | 0.789 | 0.713 |
|  | wsum0.5+prod | 0.370 | 0.739 | 0.529 | 0.765 | 0.912 | 0.849 | 31/34 | 0.869 | 0.683 |
|  | wsum0.7+prod | 0.478 | 0.804 | 0.624 | 0.882 | 1.000 | 0.941 | 34/34 | 0.858 | 0.750 |
| gte-base | dense | 0.467 | 0.815 | 0.615 | 0.765 | 0.941 | 0.855 | 32/34 | 0.794 | 0.710 |
|  | rrf+bm25 | 0.283 | 0.565 | 0.419 | 0.618 | 0.765 | 0.702 | 26/34 | 0.732 | 0.558 |
|  | rrf+prod | 0.370 | 0.739 | 0.539 | 0.647 | 0.853 | 0.763 | 29/34 | 0.858 | 0.669 |
|  | wsum0.5+bm25 | 0.315 | 0.728 | 0.492 | 0.588 | 0.794 | 0.711 | 27/34 | 0.785 | 0.614 |
|  | wsum0.7+bm25 | 0.424 | 0.826 | 0.591 | 0.706 | 0.912 | 0.822 | 31/34 | 0.820 | 0.698 |
|  | wsum0.5+prod | 0.380 | 0.783 | 0.556 | 0.647 | 0.853 | 0.770 | 29/34 | 0.870 | 0.682 |
|  | wsum0.7+prod | 0.424 | 0.837 | 0.603 | 0.824 | 0.941 | 0.889 | 32/34 | 0.882 | 0.734 |
| granite-embedding-english-r2 | dense | 0.543 | 0.750 | 0.625 | 0.853 | 0.941 | 0.892 | 32/34 | 0.805 | 0.726 |
|  | rrf+bm25 | 0.370 | 0.663 | 0.486 | 0.647 | 0.765 | 0.739 | 26/34 | 0.750 | 0.607 |
|  | rrf+prod | 0.457 | 0.815 | 0.612 | 0.765 | 0.853 | 0.819 | 29/34 | 0.861 | 0.720 |
|  | wsum0.5+bm25 | 0.380 | 0.750 | 0.538 | 0.706 | 0.794 | 0.779 | 27/34 | 0.791 | 0.653 |
|  | wsum0.7+bm25 | 0.424 | 0.761 | 0.583 | 0.794 | 0.912 | 0.849 | 31/34 | 0.837 | 0.704 |
|  | wsum0.5+prod | 0.424 | 0.815 | 0.581 | 0.735 | 0.853 | 0.814 | 29/34 | 0.838 | 0.696 |
|  | wsum0.7+prod | 0.457 | 0.804 | 0.605 | 0.794 | 0.941 | 0.862 | 32/34 | 0.829 | 0.716 |
| granite-embedding-small-english-r2 | dense | 0.380 | 0.652 | 0.499 | 0.824 | 0.941 | 0.885 | 32/34 | 0.812 | 0.659 |
|  | rrf+bm25 | 0.283 | 0.609 | 0.414 | 0.559 | 0.765 | 0.671 | 26/34 | 0.741 | 0.552 |
|  | rrf+prod | 0.402 | 0.739 | 0.551 | 0.588 | 0.794 | 0.720 | 27/34 | 0.875 | 0.671 |
|  | wsum0.5+bm25 | 0.304 | 0.663 | 0.460 | 0.676 | 0.765 | 0.757 | 26/34 | 0.793 | 0.608 |
|  | wsum0.7+bm25 | 0.370 | 0.685 | 0.510 | 0.735 | 0.912 | 0.830 | 31/34 | 0.851 | 0.664 |
|  | wsum0.5+prod | 0.380 | 0.707 | 0.526 | 0.735 | 0.824 | 0.805 | 28/34 | 0.885 | 0.677 |
|  | wsum0.7+prod | 0.424 | 0.728 | 0.555 | 0.794 | 0.941 | 0.865 | 32/34 | 0.878 | 0.703 |
| bge-base-en-v1.5 | dense | 0.435 | 0.674 | 0.544 | 0.676 | 0.941 | 0.799 | 32/34 | 0.779 | 0.657 |
|  | rrf+bm25 | 0.283 | 0.511 | 0.396 | 0.618 | 0.735 | 0.697 | 25/34 | 0.705 | 0.538 |
|  | rrf+prod | 0.359 | 0.707 | 0.510 | 0.618 | 0.853 | 0.742 | 29/34 | 0.850 | 0.647 |
|  | wsum0.5+bm25 | 0.304 | 0.641 | 0.447 | 0.618 | 0.735 | 0.710 | 25/34 | 0.755 | 0.581 |
|  | wsum0.7+bm25 | 0.359 | 0.717 | 0.503 | 0.618 | 0.882 | 0.745 | 30/34 | 0.765 | 0.621 |
|  | wsum0.5+prod | 0.348 | 0.696 | 0.489 | 0.618 | 0.882 | 0.735 | 30/34 | 0.839 | 0.631 |
|  | wsum0.7+prod | 0.413 | 0.717 | 0.533 | 0.676 | 0.941 | 0.792 | 32/34 | 0.848 | 0.669 |
| e5-small-v2 | dense | 0.391 | 0.652 | 0.495 | 0.676 | 0.853 | 0.768 | 29/34 | 0.723 | 0.610 |
|  | rrf+bm25 | 0.272 | 0.533 | 0.403 | 0.588 | 0.794 | 0.693 | 27/34 | 0.702 | 0.540 |
|  | rrf+prod | 0.391 | 0.685 | 0.526 | 0.647 | 0.824 | 0.744 | 28/34 | 0.836 | 0.652 |
|  | wsum0.5+bm25 | 0.315 | 0.641 | 0.454 | 0.618 | 0.794 | 0.712 | 27/34 | 0.734 | 0.580 |
|  | wsum0.7+bm25 | 0.359 | 0.674 | 0.494 | 0.676 | 0.824 | 0.758 | 28/34 | 0.776 | 0.622 |
|  | wsum0.5+prod | 0.370 | 0.630 | 0.496 | 0.588 | 0.824 | 0.727 | 28/34 | 0.832 | 0.632 |
|  | wsum0.7+prod | 0.413 | 0.685 | 0.523 | 0.676 | 0.853 | 0.770 | 29/34 | 0.832 | 0.655 |

Paired comparisons (B minus A):

| comparison (B minus A) | paraphrase MRR | safety MRR | ALL MRR | paraphrase hit@1 | safety hit@1 |
|---|--|--|--|--|--|
| control: RRF+keyword(prod) vs control dense | +0.014 [-0.071, +0.095] (37W/25L) | +0.068 [+0.000, +0.145] (7W/2L) | +0.058 [+0.008, +0.109]* (61W/30L) | -0.043 [-0.152, +0.076] (12W/16L) | +0.088 [-0.029, +0.206] (4W/1L) |
| e5-base-v2: RRF+keyword(prod) vs e5-base-v2 dense | -0.042 [-0.130, +0.045] (24W/30L) | -0.178 [-0.284, -0.080]* (0W/9L) | -0.035 [-0.089, +0.018] (36W/41L) | -0.065 [-0.185, +0.054] (13W/19L) | -0.235 [-0.382, -0.118]* (0W/8L) |
| e5-base-v2: wsum0.7+prod vs e5-base-v2 dense | -0.003 [-0.051, +0.049] (18W/20L) | -0.044 [-0.103, +0.000] (0W/3L) | +0.012 [-0.021, +0.044] (30W/24L) | -0.022 [-0.109, +0.065] (7W/9L) | -0.088 [-0.206, +0.000] (0W/3L) |
| hybrid RRF+prod: e5-base-v2 vs control | +0.057 [+0.002, +0.114]* (28W/18L) | +0.058 [+0.011, +0.114]* (6W/1L) | +0.044 [+0.009, +0.079]* (40W/23L) | +0.076 [-0.011, +0.163] (12W/5L) | +0.088 [+0.000, +0.206] (3W/0L) |
| hybrid wsum0.7+prod: e5-base-v2 vs control | +0.112 [+0.032, +0.193]* (36W/15L) | +0.217 [+0.118, +0.329]* (12W/0L) | +0.101 [+0.052, +0.154]* (52W/18L) | +0.120 [+0.011, +0.228]* (19W/8L) | +0.265 [+0.118, +0.412]* (9W/0L) |
| e5-base-v2 dense vs control production-shape hybrid (RRF+prod) | +0.099 [+0.011, +0.187]* (40W/23L) | +0.236 [+0.129, +0.353]* (12W/0L) | +0.079 [+0.022, +0.138]* (56W/35L) | +0.141 [+0.011, +0.272]* (25W/12L) | +0.324 [+0.176, +0.471]* (11W/0L) |
| hybrid RRF+prod: gte-base vs control | +0.011 [-0.034, +0.056] (21W/22L) | +0.013 [-0.049, +0.076] (6W/3L) | +0.010 [-0.021, +0.040] (33W/29L) | +0.011 [-0.065, +0.087] (6W/5L) | +0.000 [-0.118, +0.118] (2W/2L) |
| hybrid RRF+prod: granite-embedding-english-r2 vs control | +0.084 [+0.013, +0.158]* (34W/20L) | +0.069 [-0.017, +0.157] (8W/2L) | +0.061 [+0.018, +0.106]* (49W/26L) | +0.098 [-0.011, +0.206] (18W/9L) | +0.118 [+0.000, +0.265] (5W/1L) |
| hybrid RRF+prod: granite-embedding-small-english-r2 vs control | +0.023 [-0.041, +0.084] (29W/21L) | -0.030 [-0.123, +0.056] (6W/5L) | +0.013 [-0.030, +0.053] (40W/31L) | +0.043 [-0.043, +0.130] (10W/6L) | -0.059 [-0.206, +0.088] (2W/4L) |

Reading it:

- **The keyword side is the weaker half here** (paraphrase MRR 0.24 bm25, 0.41 prod, against 0.51 for the control's meaning), because
  the paraphrases share few words with the pages. The `prod` variant beats plain bm25 by a wide margin (its re-sort by query-idea share is what `search.py` does for a reason).
- **For the control, hybrid helps a little** (RRF+prod against dense: ALL MRR +0.058, interval +0.008 to +0.109; paraphrase +0.014, not distinguishable).
- **For e5-base-v2, fusion does not help and RRF hurts the safety rows** (RRF against its dense: safety MRR -0.178, 0 wins / 9 losses;
  the guard falls from 34 to 30). With weight 0.7 on meaning the hybrid is level with dense (+0.012 ALL MRR, interval -0.021 to +0.044) and the guard stays
  at 34 of 34. Whatever the box does with its own fusion weights (`SEMANTIC_WEIGHT`, the floors and boosts in `search.py`) needs re-tuning for this model; that is work this bake-off did not do.
- **The gap between the models shrinks with the fusion** (dense: +0.138 ALL MRR; RRF: +0.044; weighted 0.7: +0.101), because the keyword side already
  carries the authored-page preference that e5 has natively. Same-fusion RRF is the fair, untuned comparison.

## 5. Experiment C: cross-encoder reranking of the top 30

fp16 GPU, plain `AutoModelForSequenceClassification`, (query, `passage_text`) pairs, max 512 tokens. Two ways to use the scores:
`cross-encoder order` (the 30 sorted purely by the reranker) and `RRF(cross-encoder, pool)` (k = 60, the cross-encoder order fused with the pool's own
order, the conservative deployment). Three pools: the control's RRF+prod hybrid, e5-base-v2 dense, and e5-base-v2 weighted hybrid. Pool recall@30 is
0.965, 0.971, 0.977 respectively (the ceiling of any reranker). `better / worse / same` counts queries by the best rank of their answer (absent = worst);
the last column lists every safety row that was in the top 3 before and is not after. Native models only:
`bge-reranker-base`, `bge-reranker-v2-m3`, `ms-marco-MiniLM-L-6-v2`, `ms-marco-MiniLM-L-12-v2`, `mxbai-rerank-xsmall-v1`, `mxbai-rerank-base-v1`
(DeBERTa-v2), `gte-reranker-modernbert-base` (ModernBERT). Pooling of the rerank scores: raw logit.

### Pool: e5-base-v2 dense (the recommended embedding model)

Pool `e5-base-v2:dense` (recall@30 0.971)

| system | par h@1 | par MRR | safety h@1 | safety h@3 | guard | ALL MRR | queries better / worse / same | safety rows leaving top 3 |
|---|--:|--:|--:|--:|--:|--:|--:|--|
| pool as is | 0.500 | 0.627 | 0.971 | 1.000 | 34/34 | 0.738 | | |
| bge-reranker-base (278M), cross-encoder order | 0.304 | 0.471 | 0.529 | 0.794 | 27/34 | 0.573 | 30 / 70 / 72 | choking-hard, cpr-adult-hard, cpr-child-hard, hypothermia-plain, carbon-monoxide-hard, drowning-hard, heat-stroke-hard |
| bge-reranker-base (278M), RRF(cross-encoder, pool) | 0.457 | 0.606 | 0.882 | 0.971 | 33/34 | 0.717 | 25 / 32 / 115 | carbon-monoxide-hard |
| bge-reranker-v2-m3 (568M), cross-encoder order | 0.380 | 0.543 | 0.676 | 0.912 | 31/34 | 0.635 | 35 / 56 / 81 | severe-bleeding-hard, hypothermia-plain, carbon-monoxide-plain |
| bge-reranker-v2-m3 (568M), RRF(cross-encoder, pool) | 0.500 | 0.641 | 0.912 | 1.000 | 34/34 | 0.743 | 32 / 23 / 117 | none |
| ms-marco-MiniLM-L-6-v2 (23M), cross-encoder order | 0.293 | 0.445 | 0.353 | 0.676 | 23/34 | 0.518 | 30 / 86 / 56 | choking-hard, severe-bleeding-hard, cpr-adult-hard, anaphylaxis-hard, hypothermia-plain, carbon-monoxide-hard, stroke-plain, seizures-hard, heat-stroke-hard, heart-attack-plain, asthma-attack-plain |
| ms-marco-MiniLM-L-6-v2 (23M), RRF(cross-encoder, pool) | 0.370 | 0.548 | 0.794 | 0.882 | 30/34 | 0.670 | 32 / 46 / 94 | severe-bleeding-hard, seizures-hard, heat-stroke-hard, heart-attack-plain |
| ms-marco-MiniLM-L-12-v2 (33M), cross-encoder order | 0.174 | 0.332 | 0.294 | 0.441 | 15/34 | 0.421 | 19 / 101 / 52 | choking-plain, choking-hard, severe-bleeding-plain, severe-bleeding-hard, cpr-adult-plain, cpr-adult-hard, cpr-child-hard, hypothermia-plain, hypothermia-hard, carbon-monoxide-hard, stroke-plain, burns-plain, burns-hard, poisoning-plain, poisoning-hard, drowning-hard, seizures-hard, heat-stroke-hard, electric-shock-hard |
| ms-marco-MiniLM-L-12-v2 (33M), RRF(cross-encoder, pool) | 0.413 | 0.553 | 0.676 | 0.853 | 29/34 | 0.642 | 24 / 51 / 97 | cpr-adult-hard, burns-hard, poisoning-plain, seizures-hard, heat-stroke-hard |
| mxbai-rerank-xsmall-v1 (71M), cross-encoder order | 0.391 | 0.543 | 0.412 | 0.706 | 24/34 | 0.588 | 31 / 72 / 69 | choking-hard, cpr-adult-plain, cpr-adult-hard, cpr-child-hard, anaphylaxis-hard, carbon-monoxide-plain, poisoning-hard, heat-stroke-hard, electric-shock-plain, electric-shock-hard |
| mxbai-rerank-xsmall-v1 (71M), RRF(cross-encoder, pool) | 0.554 | 0.667 | 0.853 | 0.971 | 33/34 | 0.738 | 30 / 27 / 115 | anaphylaxis-hard |
| gte-reranker-modernbert-base (150M), cross-encoder order | 0.402 | 0.564 | 0.676 | 0.853 | 29/34 | 0.671 | 37 / 51 / 84 | cpr-adult-hard, carbon-monoxide-plain, seizures-hard, heat-stroke-hard, electric-shock-hard |
| gte-reranker-modernbert-base (150M), RRF(cross-encoder, pool) | 0.522 | 0.654 | 0.912 | 0.971 | 33/34 | 0.757 | 39 / 19 / 114 | seizures-hard |
| mxbai-rerank-base-v1 (184M), cross-encoder order | 0.413 | 0.572 | 0.647 | 0.765 | 26/34 | 0.653 | 35 / 57 / 80 | choking-hard, severe-bleeding-hard, cpr-adult-plain, cpr-adult-hard, anaphylaxis-hard, hypothermia-hard, seizures-hard, heat-stroke-hard |
| mxbai-rerank-base-v1 (184M), RRF(cross-encoder, pool) | 0.554 | 0.677 | 0.882 | 0.941 | 32/34 | 0.761 | 35 / 25 / 112 | seizures-hard, heat-stroke-hard |

### Pool: the control's hybrid (what the box has today, RRF + keyword)

Pool `bge-small-en-v1.5:rrf+prod` (recall@30 0.965)

| system | par h@1 | par MRR | safety h@1 | safety h@3 | guard | ALL MRR | queries better / worse / same | safety rows leaving top 3 |
|---|--:|--:|--:|--:|--:|--:|--:|--|
| pool as is | 0.359 | 0.528 | 0.647 | 0.824 | 28/34 | 0.658 | | |
| bge-reranker-base (278M), cross-encoder order | 0.261 | 0.433 | 0.441 | 0.735 | 25/34 | 0.539 | 32 / 69 / 71 | choking-hard, hypothermia-plain, carbon-monoxide-hard, drowning-hard |
| bge-reranker-base (278M), RRF(cross-encoder, pool) | 0.359 | 0.522 | 0.588 | 0.794 | 27/34 | 0.649 | 39 / 36 / 97 | carbon-monoxide-hard, drowning-hard |
| bge-reranker-v2-m3 (568M), cross-encoder order | 0.348 | 0.503 | 0.618 | 0.794 | 27/34 | 0.596 | 35 / 55 / 82 | severe-bleeding-hard, hypothermia-plain, carbon-monoxide-plain, carbon-monoxide-hard |
| bge-reranker-v2-m3 (568M), RRF(cross-encoder, pool) | 0.391 | 0.558 | 0.588 | 0.824 | 28/34 | 0.655 | 36 / 35 / 101 | carbon-monoxide-plain, carbon-monoxide-hard |
| ms-marco-MiniLM-L-6-v2 (23M), cross-encoder order | 0.239 | 0.384 | 0.529 | 0.765 | 26/34 | 0.497 | 25 / 87 / 60 | choking-hard, severe-bleeding-hard, anaphylaxis-hard, hypothermia-plain |
| ms-marco-MiniLM-L-6-v2 (23M), RRF(cross-encoder, pool) | 0.326 | 0.472 | 0.647 | 0.824 | 28/34 | 0.628 | 36 / 48 / 88 | severe-bleeding-hard, carbon-monoxide-plain, drowning-hard |
| ms-marco-MiniLM-L-12-v2 (33M), cross-encoder order | 0.163 | 0.272 | 0.265 | 0.412 | 14/34 | 0.376 | 17 / 110 / 45 | choking-plain, choking-hard, severe-bleeding-plain, severe-bleeding-hard, cpr-adult-plain, hypothermia-plain, carbon-monoxide-hard, stroke-plain, poisoning-plain, poisoning-hard, drowning-hard, seizures-plain, heart-attack-plain, electric-shock-plain, electric-shock-hard |
| ms-marco-MiniLM-L-12-v2 (33M), RRF(cross-encoder, pool) | 0.315 | 0.464 | 0.500 | 0.735 | 25/34 | 0.580 | 30 / 55 / 87 | choking-hard, poisoning-plain, drowning-hard |
| mxbai-rerank-xsmall-v1 (71M), cross-encoder order | 0.370 | 0.528 | 0.412 | 0.588 | 20/34 | 0.579 | 42 / 61 / 69 | choking-hard, severe-bleeding-hard, cpr-adult-plain, anaphylaxis-hard, carbon-monoxide-plain, carbon-monoxide-hard, poisoning-hard, heat-stroke-plain, electric-shock-plain, electric-shock-hard |
| mxbai-rerank-xsmall-v1 (71M), RRF(cross-encoder, pool) | 0.424 | 0.598 | 0.559 | 0.765 | 26/34 | 0.660 | 45 / 36 / 91 | cpr-adult-plain, anaphylaxis-hard, carbon-monoxide-hard |
| gte-reranker-modernbert-base (150M), cross-encoder order | 0.326 | 0.495 | 0.559 | 0.706 | 24/34 | 0.607 | 39 / 53 / 80 | severe-bleeding-hard, anaphylaxis-hard, hypothermia-plain, carbon-monoxide-plain, carbon-monoxide-hard, electric-shock-hard |
| gte-reranker-modernbert-base (150M), RRF(cross-encoder, pool) | 0.359 | 0.557 | 0.588 | 0.824 | 28/34 | 0.670 | 44 / 28 / 100 | severe-bleeding-hard |
| mxbai-rerank-base-v1 (184M), cross-encoder order | 0.380 | 0.549 | 0.618 | 0.706 | 24/34 | 0.631 | 45 / 57 / 70 | choking-hard, severe-bleeding-hard, cpr-adult-plain, anaphylaxis-hard, poisoning-hard |
| mxbai-rerank-base-v1 (184M), RRF(cross-encoder, pool) | 0.457 | 0.628 | 0.676 | 0.824 | 28/34 | 0.720 | 46 / 19 / 107 | stroke-plain |

### Pool: e5-base-v2 weighted hybrid

Pool `e5-base-v2:wsum0.7+prod` (recall@30 0.977)

| system | par h@1 | par MRR | safety h@1 | safety h@3 | guard | ALL MRR | queries better / worse / same | safety rows leaving top 3 |
|---|--:|--:|--:|--:|--:|--:|--:|--|
| pool as is | 0.478 | 0.624 | 0.882 | 1.000 | 34/34 | 0.750 | | |
| bge-reranker-base (278M), cross-encoder order | 0.293 | 0.457 | 0.500 | 0.765 | 26/34 | 0.564 | 24 / 78 / 70 | choking-hard, cpr-adult-hard, hypothermia-plain, hypothermia-hard, carbon-monoxide-hard, drowning-hard, heat-stroke-hard, low-blood-sugar-plain |
| bge-reranker-base (278M), RRF(cross-encoder, pool) | 0.402 | 0.574 | 0.794 | 1.000 | 34/34 | 0.701 | 23 / 43 / 106 | none |
| bge-reranker-v2-m3 (568M), cross-encoder order | 0.337 | 0.515 | 0.618 | 0.853 | 29/34 | 0.610 | 29 / 61 / 82 | severe-bleeding-hard, hypothermia-plain, carbon-monoxide-plain, carbon-monoxide-hard, heat-stroke-hard |
| bge-reranker-v2-m3 (568M), RRF(cross-encoder, pool) | 0.446 | 0.608 | 0.853 | 1.000 | 34/34 | 0.732 | 25 / 25 / 122 | none |
| ms-marco-MiniLM-L-6-v2 (23M), cross-encoder order | 0.293 | 0.444 | 0.382 | 0.735 | 25/34 | 0.520 | 27 / 88 / 57 | choking-hard, severe-bleeding-hard, anaphylaxis-hard, hypothermia-plain, stroke-plain, seizures-hard, heat-stroke-hard, heart-attack-plain, asthma-attack-plain |
| ms-marco-MiniLM-L-6-v2 (23M), RRF(cross-encoder, pool) | 0.391 | 0.555 | 0.824 | 0.941 | 32/34 | 0.707 | 32 / 42 / 98 | heat-stroke-hard, heart-attack-plain |
| ms-marco-MiniLM-L-12-v2 (33M), cross-encoder order | 0.174 | 0.313 | 0.294 | 0.412 | 14/34 | 0.412 | 15 / 110 / 47 | choking-plain, choking-hard, severe-bleeding-plain, severe-bleeding-hard, cpr-adult-plain, cpr-adult-hard, hypothermia-plain, hypothermia-hard, carbon-monoxide-hard, stroke-plain, burns-plain, burns-hard, poisoning-plain, poisoning-hard, drowning-hard, seizures-plain, seizures-hard, heat-stroke-hard, electric-shock-plain, electric-shock-hard |
| ms-marco-MiniLM-L-12-v2 (33M), RRF(cross-encoder, pool) | 0.402 | 0.539 | 0.618 | 0.853 | 29/34 | 0.644 | 21 / 57 / 94 | choking-hard, cpr-adult-hard, burns-hard, seizures-hard, heat-stroke-hard |
| mxbai-rerank-xsmall-v1 (71M), cross-encoder order | 0.380 | 0.536 | 0.382 | 0.676 | 23/34 | 0.585 | 26 / 70 / 76 | choking-hard, cpr-adult-plain, cpr-adult-hard, anaphylaxis-hard, hypothermia-hard, carbon-monoxide-plain, burns-hard, poisoning-hard, heat-stroke-hard, electric-shock-plain, electric-shock-hard |
| mxbai-rerank-xsmall-v1 (71M), RRF(cross-encoder, pool) | 0.435 | 0.608 | 0.794 | 0.941 | 32/34 | 0.719 | 25 / 32 / 115 | cpr-child-hard, anaphylaxis-hard |
| gte-reranker-modernbert-base (150M), cross-encoder order | 0.359 | 0.537 | 0.647 | 0.824 | 28/34 | 0.649 | 30 / 56 / 86 | cpr-adult-hard, hypothermia-plain, carbon-monoxide-plain, seizures-hard, heat-stroke-hard, electric-shock-hard |
| gte-reranker-modernbert-base (150M), RRF(cross-encoder, pool) | 0.457 | 0.614 | 0.882 | 0.971 | 33/34 | 0.742 | 29 / 24 / 119 | seizures-hard |
| mxbai-rerank-base-v1 (184M), cross-encoder order | 0.402 | 0.565 | 0.647 | 0.735 | 25/34 | 0.645 | 30 / 58 / 84 | choking-hard, severe-bleeding-hard, cpr-adult-plain, cpr-adult-hard, anaphylaxis-hard, hypothermia-hard, poisoning-hard, seizures-hard, heat-stroke-hard |
| mxbai-rerank-base-v1 (184M), RRF(cross-encoder, pool) | 0.522 | 0.657 | 0.765 | 0.941 | 32/34 | 0.756 | 32 / 26 / 114 | seizures-hard, heat-stroke-hard |

Paired comparisons for the serious candidates (B minus A, A = the pool without a reranker unless the row says otherwise):

| comparison (B minus A) | paraphrase MRR | safety MRR | ALL MRR | paraphrase hit@1 | safety hit@1 |
|---|--|--|--|--|--|
| rerank blend: gte-reranker-modernbert-base on pool bge-small-en-v1.5:rrf+prod | +0.029 [-0.019, +0.078] (31W/18L) | -0.029 [-0.105, +0.036] (5W/4L) | +0.012 [-0.022, +0.044] (43W/26L) | +0.000 [-0.076, +0.076] (7W/7L) | -0.059 [-0.176, +0.059] (1W/3L) |
| rerank blend: mxbai-rerank-base-v1 on pool bge-small-en-v1.5:rrf+prod | +0.100 [+0.041, +0.161]* (34W/12L) | +0.014 [-0.051, +0.072] (3W/1L) | +0.061 [+0.022, +0.102]* (44W/18L) | +0.098 [+0.011, +0.185]* (14W/5L) | +0.029 [-0.059, +0.147] (2W/1L) |
| rerank ce: gte-reranker-modernbert-base on pool e5-base-v2:dense | -0.063 [-0.151, +0.025] (26W/32L) | -0.196 [-0.302, -0.102]* (0W/11L) | -0.067 [-0.123, -0.008]* (35W/49L) | -0.098 [-0.228, +0.033] (13W/22L) | -0.294 [-0.441, -0.147]* (0W/10L) |
| rerank blend: gte-reranker-modernbert-base on pool e5-base-v2:dense | +0.028 [-0.028, +0.086] (25W/12L) | -0.037 [-0.088, +0.000] (0W/3L) | +0.019 [-0.016, +0.052] (33W/17L) | +0.022 [-0.065, +0.109] (9W/7L) | -0.059 [-0.147, +0.000] (0W/2L) |
| rerank ce: bge-reranker-v2-m3 on pool e5-base-v2:dense | -0.084 [-0.168, +0.002] (22W/31L) | -0.190 [-0.304, -0.085]* (1W/11L) | -0.103 [-0.160, -0.049]* (31W/54L) | -0.120 [-0.239, +0.000] (11W/22L) | -0.294 [-0.471, -0.118]* (1W/11L) |
| rerank blend: bge-reranker-v2-m3 on pool e5-base-v2:dense | +0.014 [-0.043, +0.074] (23W/15L) | -0.034 [-0.088, +0.000] (0W/2L) | +0.005 [-0.028, +0.037] (29W/19L) | +0.000 [-0.087, +0.087] (8W/8L) | -0.059 [-0.147, +0.000] (0W/2L) |
| rerank blend: mxbai-rerank-base-v1 on pool e5-base-v2:dense | +0.051 [-0.010, +0.117] (21W/16L) | -0.068 [-0.136, -0.009]* (0W/4L) | +0.024 [-0.016, +0.061] (30W/23L) | +0.054 [-0.043, +0.152] (14W/9L) | -0.088 [-0.176, +0.000] (0W/3L) |
| control pool (RRF+prod) + gte-reranker-modernbert blend vs e5-base-v2 dense | -0.070 [-0.155, +0.016] (28W/33L) | -0.265 [-0.382, -0.158]* (0W/14L) | -0.068 [-0.125, -0.011]* (40W/50L) | -0.141 [-0.272, -0.011]* (12W/25L) | -0.382 [-0.559, -0.235]* (0W/13L) |
| e5-base-v2 dense + gte-reranker-modernbert blend vs control production-shape hybrid | +0.126 [+0.048, +0.207]* (39W/18L) | +0.199 [+0.085, +0.320]* (11W/1L) | +0.098 [+0.040, +0.155]* (55W/30L) | +0.163 [+0.043, +0.283]* (25W/10L) | +0.265 [+0.088, +0.441]* (10W/1L) |

Reading it:

- **Reranking alone is harmful.** On the e5 pool the pure cross-encoder order makes 51 to 101 of 172 queries worse and 19 to 37 better, and safety hit@1 falls from
  0.971 to between 0.29 and 0.68; the guard falls from 34 to as few as 15. Safety rows that leave the top 3 include the plain wordings
  ("hypothermia", "carbon monoxide poisoning", "choking"): the cross-encoders rank a long textbook page about the topic above the box's short card
  (`results/C_diag_bge-reranker-v2-m3.json`: for "hypothermia" the cross-encoder puts an Army first-aid manual page first and the card sixth). An emergency
  reranker that demotes the card is unacceptable, so the cross-encoder order is rejected outright.
- **Blended by RRF they cost less but earn little.** The best blend on the e5 pool (gte-reranker-modernbert: ALL MRR +0.019, [-0.016, +0.052], 33 wins / 17 losses; mxbai-rerank-base
  +0.024, [-0.016, +0.061]; bge-reranker-v2-m3 +0.005) is inside the noise, and most blends put a safety row out of the top 3 (on the e5-dense pool: gte-reranker-modernbert `seizures-hard`; mxbai-rerank-base `seizures-hard` and `heat-stroke-hard`; bge-reranker-v2-m3 none there, but 2 rows on the control's pool).
- **A reranker helps the control's hybrid more than it helps e5** (mxbai-rerank-base blend on the control pool: ALL MRR +0.061, [+0.022, +0.102]), but the control
  with a reranker still trails e5-base-v2 on its own (control pool + gte-reranker blend against e5 dense: ALL MRR -0.068, [-0.125, -0.011]; safety hit@1 0 wins / 13 losses). Swapping the embedding
  model is the better spend than adding a cross-encoder to the current one.
- ms-marco MiniLM cross-encoders (trained on web search, short passages) are the worst: the 12-layer one drops the guard to 14 of 34 on its own.

**Cheapest sensible variant** (top 10 only, passage cut to 256 tokens including the query, RRF blend), in case latency is what mattered:

Pool `e5-base-v2:dense` (recall@10 0.901)

| system | par h@1 | par MRR | safety h@1 | safety h@3 | guard | ALL MRR | queries better / worse / same | safety rows leaving top 3 |
|---|--:|--:|--:|--:|--:|--:|--:|--|
| pool as is | 0.500 | 0.627 | 0.971 | 1.000 | 34/34 | 0.738 | | |
| gte-reranker-modernbert-base (150M), cross-encoder order | 0.511 | 0.644 | 0.676 | 0.971 | 33/34 | 0.712 | 26 / 32 / 114 | seizures-hard |
| gte-reranker-modernbert-base (150M), RRF(cross-encoder, pool) | 0.554 | 0.667 | 0.971 | 1.000 | 34/34 | 0.772 | 26 / 11 / 135 | none |
| mxbai-rerank-base-v1 (184M), cross-encoder order | 0.511 | 0.640 | 0.588 | 0.853 | 29/34 | 0.683 | 26 / 42 / 104 | severe-bleeding-hard, anaphylaxis-hard, poisoning-hard, seizures-hard, heat-stroke-hard |
| mxbai-rerank-base-v1 (184M), RRF(cross-encoder, pool) | 0.576 | 0.689 | 0.912 | 0.971 | 33/34 | 0.770 | 25 / 12 / 135 | seizures-hard |
| bge-reranker-v2-m3 (568M), cross-encoder order | 0.467 | 0.612 | 0.765 | 0.971 | 33/34 | 0.690 | 24 / 41 / 107 | carbon-monoxide-plain |
| bge-reranker-v2-m3 (568M), RRF(cross-encoder, pool) | 0.522 | 0.646 | 0.971 | 1.000 | 34/34 | 0.753 | 19 / 10 / 143 | none |

It is the best a reranker does here: gte-reranker-modernbert blend on the e5-dense pool: paraphrase MRR +0.040 ([-0.002, +0.085], 20 wins / 9 losses), ALL MRR
+0.034 ([+0.007, +0.061], 26 / 11), no safety row leaves the top 3. It still needs 2.0 s (`-t 4`) or 6.1 s (`-t 1`) per query for 10 candidates on this PC
(`results/rerank_cheap_latency.json`), 296 MB resident, and the gain is small and n = 172. Not worth it.

## 6. Experiment D: Pi feasibility

### D1. Can llama.cpp serve it, and from what GGUF

The installed `llama-server` (0.3.0-dev, build 1, commit c1d0e7a) and `~/llama.cpp/convert_hf_to_gguf.py` at the same commit support BERT, XLM-RoBERTa and ModernBERT
(and their `...ForSequenceClassification` heads, for `--reranking`). They do not support MPNet (all-mpnet-base-v2) or DeBERTa-v2 (both mxbai-rerank models): no converter is registered
for them, so the two best-scoring blended rerankers cannot be served on the Pi at all in this build.

Existing q8_0 GGUFs from established converters exist for every leading model (ChristianAzinn `e5-base-v2.Q8_0.gguf` 118 MB and `gte-base.Q8_0.gguf` 118 MB,
CompendiumLabs `bge-base-en-v1.5-q8_0.gguf` 118 MB, mradermacher `granite-embedding-english-r2.Q8_0.gguf` 160 MB, gpustack `bge-reranker-v2-m3-Q8_0.gguf` 636 MB,
keisuke-miyako `gte-reranker-modernbert-base-Q8_0.gguf` 161 MB, cstr `bge-reranker-base-q8_0.gguf` 303 MB). **None was downloaded**: every model was instead converted locally
from the official weights with the box's own converter (`lab/convert.py`, `--outtype q8_0`), which gave files of the same size and removes a third party from the loop.
Conversion is therefore possible for all the leaders; it takes seconds. The Pi needs only the GGUF, not the converter.

### D2 to D3. Fidelity, latency, memory (embedding models)

Server as in `sos-embed.service`: `--embedding --pooling <cls|mean> -c 512 -ub 512 -b 512 -t N --no-webui`, CPU only, ports 8110 to 8151. Fidelity: 200 random passages of at most
480 tokens (the window llama-server accepts) and all 172 queries, GGUF-served vector against the torch fp16 vector of experiment A. Latency: one query at a time over HTTP, 5 warm-ups then 60
gold queries, median. Memory: resident set of the server after the workload. The whole search has a median of 1.3 s in the baseline, so a few tens of ms
is not the constraint.

| model | q8_0 GGUF | RSS -t4 (MB) | fidelity: passage cos / query cos (n=200 / 172) | query ms -t4 (PC) | query ms -t1 (PC) | x control (-t4 / -t1) | Pi 5 estimate -t1 (3-4x PC) | ALL MRR (dense) | paraphrase MRR | safety MRR |
|---|--:|--:|--|--:|--:|--:|--:|--:|--:|--:|
| bge-small-en-v1.5 | 37 MB | 151 | 0.99986 / 0.99983 | 27.5 | 40.0 | 1.00 / 1.00 | 120-160 ms | 0.600 | 0.514 | 0.682 |
| e5-small-v2 | 37 MB | 148 | 0.99986 / 0.99986 | 27.8 | 35.9 | 1.01 / 0.90 | 108-144 ms | 0.610 | 0.495 | 0.768 |
| granite-embedding-small-english-r2 | 52 MB | 221 | 0.99993 / 0.99991 | 28.1 | 37.3 | 1.02 / 0.93 | 112-149 ms | 0.659 | 0.499 | 0.885 |
| e5-base-v2 | 118 MB | 245 | 0.99984 / 0.99990 | 35.0 | 68.5 | 1.27 / 1.71 | 206-274 ms | 0.738 | 0.627 | 0.985 |
| gte-base | 118 MB | 238 | 0.99991 / 0.99989 | 38.9 | 57.0 | 1.41 / 1.43 | 171-228 ms | 0.710 | 0.615 | 0.855 |
| bge-base-en-v1.5 | 118 MB | 252 | 0.99982 / 0.99979 | 44.1 | 81.7 | 1.60 / 2.04 | 245-327 ms | 0.657 | 0.544 | 0.799 |
| granite-embedding-english-r2 | 160 MB | 333 | 0.99984 / 0.99981 | 40.5 | 79.0 | 1.47 / 1.98 | 237-316 ms | 0.726 | 0.625 | 0.892 |

- **Fidelity: every candidate is above the 0.99 bar by a wide margin** (0.9998 to 0.9999); the top-10 overlap of GGUF-query against torch-query rankings is 0.97 to 0.99 (q8_0 noise), no accuracy claim depends on it. Note the
  fidelity holds for passages the window accepts; long ones are shortened by the box's build (caveat 4), for whichever model.
- **Latency.** On this (busy) PC `-t 1` costs 40 ms for the control, 68.5 ms for e5-base-v2 (1.7x), 57 ms for gte-base (1.4x). Estimating the Pi 5 is uncertain: the brief's rule
  (a Pi core is 3 to 4 times slower) applied to the PC's `-t 1` figure gives 120 to 160 ms for the control, but the docs record about 25 ms measured on the Pi for the control at `-t 2`, five times faster than
  that rule predicts (this PC was loaded and HTTP overhead is included). Anchoring on the real Pi number and scaling by the measured ratios is the better estimate: **e5-base-v2 about 1.3x to 1.7x the control, i.e. roughly 35 to 45 ms per query on the Pi
  at `-t 2`**, uncertainty at least +-50% (a 768-wide matmul may scale differently on ARM NEON). Even the pessimistic rule (170 to 270 ms) is small next to the 1.3 s search.
- **Memory.** 245 MB resident for e5-base-v2 (151 MB for the control) against `MemoryMax=600M`: fits with room; granite-embedding-english-r2 needs 333 MB. On the box, the query-time
  cosine over the docs matrix grows from 21,368 x 384 to 21,368 x 768 (66 MB as float32 instead of 33 MB in the application; scan 0.5 ms to 1.4 ms measured on this PC, the docs say about 5 ms on the Pi). The household hnswlib index is 118 MB at 384 dimensions and roughly double at 768 (an estimate, not measured).

### D4. Rerankers on CPU (30 pairs at `-t 4`, passage cut to 1,200 characters so a pair fits the 512 window)

| reranker | q8_0 GGUF | llama.cpp | fidelity vs torch fp32 (Pearson of scores / top-1 agreement) | 30 pairs -t4 (median) | 30 pairs -t1 (median) | RSS (MB) |
|---|--:|--|--|--:|--:|--:|
| ms-marco-MiniLM-L-6-v2 | 25 MB | serves | 0.0325 (min -0.5370) / 1/12 (n=12) | 1.5 s | 4.0 s | 120 |
| gte-reranker-modernbert-base | 161 MB | serves | 0.9986 (min 0.9972) / 10/12 (n=12) | 11.4 s | 31.0 s | 303 |
| bge-reranker-base | 304 MB | serves | 0.9995 (min 0.9990) / 4/4 (n=4) | 9.4 s | 26.0 s | 925 |
| bge-reranker-v2-m3 | 636 MB | serves | 0.9995 (min 0.9992) / 3/4 (n=4) | 29.9 s | 85.5 s | 1245 |

- The cross-encoders that give the least harm are also the ones the Pi cannot afford: **9 to 11 seconds per query for 30 pairs at `-t 4` on this PC** for the 278 M and 150 M ones (bge-reranker-base 9.4 s, gte-reranker-modernbert 11.4 s) and 30 s for bge-reranker-v2-m3, which also take 0.9 to 1.2 GB resident (bge-reranker-base, bge-reranker-v2-m3) or 0.3 GB (gte-reranker-modernbert).
  The Pi would be slower than the PC, by anything from about the same (the control's Pi figure suggests the PC was not much faster) to 4x. Even the 10-candidate, 256-token variant is 2.0 s (PC `-t 4`) to 6.1 s (`-t 1`).
- Fidelity of the served rerankers is fine for the ModernBERT and XLM-R ones (Pearson of scores 0.9986 to 0.9995; top-1 agreement 10/12, 4/4, 3/4 because ties among near-equal
  logits). **The ms-marco MiniLM GGUF is wrong** (Pearson 0.03, top-1 agrees 1 in 12): its weights include a pooler layer (`bert.pooler.*`, confirmed) that the converter deliberately
  drops for BERT (`conversion/bert.py`, "we are only using BERT for embeddings"), so the served model applies the classifier to the raw CLS state. The `ms-marco-MiniLM-L-12-v2` (same architecture) would be
  wrong in the same way (not served). That does not change the verdict: they are also the worst rerankers by accuracy.

## 7. Experiment E: rebuild cost

Rates from experiment A on this PC (torch fp16, mean passage 400 tokens, docs corpus), applied to each collection; the last real bge-small builds are the reference
(`/home/dan/sos-content/embeddings/*.meta.json`, read only): household 70,558 books in 11,876 s (5.9 per second, bounded by ZIM reading and PDF text extraction, not the GPU) and Wikipedia
8,425,865 article leads in 14,134 s (3.93 h, 596 per second, half the GPU rate for this model). "GPU" is the model's own cost; "wall" is the larger of it and the last build's observed pipeline rate, so a model that is not
slower than that pipeline costs no more wall time. Assumptions: leads and books have the docs corpus's mean length (worst case, every text at 512 tokens: 1.3x the GPU figures); the hypothetical 150k
small-library collection is embedded like Wikipedia's pipeline (no observed rate). Production embeds through `llama-server-cuda` on the q8_0 GGUF, not torch; that rate was not measured.

| model | dims | docs (21k) | household (70.6k) | small library (150k) | Wikipedia (8.43M) | Wikipedia index fp16 |
|---|--:|--:|--:|--:|--:|--:|
| bge-small-en-v1.5 | 384 | 18 s | 1.0 min GPU / 3.3 h wall | 2.1 min GPU / 4 min wall | 2.0 h GPU / 3.9 h wall | 6.5 GB |
| e5-small-v2 | 384 | 18 s | 1.0 min GPU / 3.3 h wall | 2.1 min GPU / 4 min wall | 2.0 h GPU / 3.9 h wall | 6.5 GB |
| granite-embedding-small-english-r2 | 384 | 34 s | 1.9 min GPU / 3.3 h wall | 4.0 min GPU / 4 min wall | 3.7 h GPU / 3.9 h wall | 6.5 GB |
| e5-base-v2 | 768 | 38 s | 2.1 min GPU / 3.3 h wall | 4.4 min GPU / 4 min wall | 4.2 h GPU / 4.2 h wall | 12.9 GB |
| gte-base | 768 | 38 s | 2.1 min GPU / 3.3 h wall | 4.4 min GPU / 4 min wall | 4.1 h GPU / 4.1 h wall | 12.9 GB |
| bge-base-en-v1.5 | 768 | 36 s | 2.0 min GPU / 3.3 h wall | 4.3 min GPU / 4 min wall | 4.0 h GPU / 4.0 h wall | 12.9 GB |
| granite-embedding-english-r2 | 768 | 89 s | 4.9 min GPU / 3.3 h wall | 10.5 min GPU / 10 min wall | 9.8 h GPU / 9.8 h wall | 12.9 GB |
| bge-large-en-v1.5 | 1024 | 104 s | 5.7 min GPU / 3.3 h wall | 12.2 min GPU / 12 min wall | 11.4 h GPU / 11.4 h wall | 17.3 GB |
| mxbai-embed-large-v1 | 1024 | 109 s | 6.0 min GPU / 3.3 h wall | 12.8 min GPU / 13 min wall | 12.0 h GPU / 12.0 h wall | 17.3 GB |

Index size on disk at fp16 is N x dims x 2 bytes: 384 dims 6.5 GB for Wikipedia, 768 dims 12.9 GB, 1024 dims 17.3 GB; docs 16 / 33 / 44 MB; household 54 / 108 / 145 MB (raw, before the hnsw graph).
The Wikipedia file is read only for the keyword hits' rerank, but the box's storage has to hold it: switching to 768 dimensions **doubles a 6.5 GB file**.
Everything must be rebuilt together, because the query vector has to come from the same model as the index (the box refuses an index whose meta names another model).

## 8. Accuracy against Pi cost

| candidate | params | q8_0 | Pi RSS | query cost vs control | Wikipedia rebuild (GPU) | Wikipedia index | dense paraphrase MRR | dense safety MRR | guard | verdict |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--|
| bge-small-en-v1.5 (control) | 33 M | 37 MB | 151 MB | 1.0x | 2.0 h | 6.5 GB | 0.514 | 0.682 | 26/34 | baseline |
| e5-small-v2 | 33 M | 37 MB | 148 MB | 1.0x | 2.0 h | 6.5 GB | 0.495 | 0.768 | 29/34 | no gain on paraphrase |
| granite-embedding-small-english-r2 | 48 M | 52 MB | 221 MB | 0.9 to 1.0x | 3.7 h | 6.5 GB | 0.499 | 0.885 | 32/34 | safety only, paraphrase flat |
| **e5-base-v2** | 110 M | 118 MB | 245 MB | 1.3 to 1.7x | 4.2 h | 12.9 GB | **0.627** | **0.985** | **34/34** | **recommended** |
| gte-base | 110 M | 118 MB | 238 MB | 1.4x | 4.2 h | 12.9 GB | 0.615 | 0.855 | 32/34 | fallback (no prefixes) |
| granite-embedding-english-r2 | 149 M | 160 MB | 333 MB | 1.5 to 2.0x | 9.8 h | 12.9 GB | 0.625 | 0.892 | 32/34 | equal accuracy, 2.3x the rebuild, slowest |
| bge-base-en-v1.5 | 110 M | 118 MB | 252 MB | 1.6 to 2.0x | 4.0 h | 12.9 GB | 0.544 | 0.799 | 32/34 | little gain |
| bge-large / mxbai-large (upper bounds) | 335 M | (not built) | n/a | n/a | 11 to 12 h | 17.3 GB | 0.559 / 0.548 | 0.775 / 0.747 | 29/34 | not Pi-feasible, and not better |

**The gold favours authored passages; how much of e5's advantage is that?** e5-base-v2's top-1 is a card, module, page or playbook for 77% of queries (control 59%; gte-base 68%),
with a median top-1 of 755 characters (control 1,490). All relevant passages are among the 634 authored ones (median 1,066 characters against 2,093 for document pages), so a model that likes short
authored passages wins this gold. `results/prior.json` adds a flat bonus for authored passages (in units of each model's own cosine standard deviation) to every model:
the **control's ALL MRR rises from 0.600 to 0.775 with a 1-sd bonus** (paraphrase 0.514 to 0.702, guard 26 to 31 of 34), more than any model swap. The box already boosts authored kinds
in `search.py`, and the bonus is a diagnostic that also hurts any question answered by a document page, which this gold cannot see: it is not an accuracy estimate for the box. What it shows: (i) the gold
cannot separate "understands the question better" from "prefers cards", and (ii) **the gap between the models survives the same bonus**:
e5-base-v2 against the control, both with the bonus: ALL MRR +0.071 ([+0.030, +0.113], 39 wins / 12 losses), paraphrase +0.068 ([+0.003, +0.133]), safety +0.149 ([+0.068, +0.243], 9 / 0);
gte-base +0.080 ([+0.038, +0.124]); granite-r2 +0.043 ([-0.002, +0.090]). So roughly half of the dense-only advantage is a real, model-quality one.

**Score scales differ, and the box gates on cosine.** `search.py` keeps a meaning hit only above `SEMANTIC_FLOOR` (0.60, 0.66, 0.66, 0.74 by case) and saturates at `SEMANTIC_CEIL` 0.82, all calibrated on bge-small. Under e5-base-v2 the median cosine of a
random passage is 0.72, of the best relevant one 0.845, and 100% of every query's top 20 are above 0.74 (bge-small: 12.8%; `results/score_scale.json`). gte-base and granite are the same. Ported unchanged, the floors would
pass everything and the ceiling would flatten the ranking: **the thresholds must be recalibrated (likely rescaled by (cos - random) / (1 - random)) before switching**, and the rerank scale `WIKIPEDIA_RERANK_*` likewise.

## 9. Recommendation

**Switch the embedding model to `intfloat/e5-base-v2`; no reranker; do the work in this order.**

Expected gain (this gold, n = 172, single author): paraphrase MRR +0.05 to +0.11 and hit@5 +0.10 to +0.16 (dense: 0.663 to 0.826), the hard safety paraphrases from 9 of 17 to 17 of 17 cards in the top 3 under dense
retrieval and 34 of 34 guard under the 0.7-weighted hybrid (control's best hybrid: 28 of 34). Own-library (n = 46) does not improve (hit@5 0.913 to 0.870, not significant either way; MRR 0.71 to 0.78).
Cost: +94 MB resident (245 MB of a 600 MB limit), about 1.3x to 1.7x the query embedding time (roughly 35 to 45 ms on the Pi, uncertainty +-50%), about +1 ms for the cosine scan (measured on this PC: 0.5 ms at 384 dimensions, 1.4 ms at 768 for 21,368 passages, float32 matrix), index 2x
(docs 33 MB, Wikipedia 12.9 GB instead of 6.5 GB), one rebuild of everything: docs 0.6 minutes, household about the 3.3 h the PDF and ZIM extraction already took,
Wikipedia about 4.2 h of GPU (was 3.9 h of wall clock).

Risks and what to do about them:

1. **Winner's curse and gold bias** (sections 2 and 8). The gain is real but smaller than the dense-only table shows. Before committing to the 4-hour Wikipedia rebuild, run the full `sos eval-search` with the new model on
   the **docs collection only** (its rebuild is seconds) and on a fresh set of queries written after this bake-off, ideally by someone else, and include queries whose answer is a document page.
2. **Gates must be recalibrated** (section 8), and the fusion weights re-tuned: with e5 the best simple fusion was 0.7 weight on meaning; RRF hurt the safety rows.
3. **Code touches** (not done here): the query and passage prefixes ("query: ", "passage: ": `embeddings.py` has a query prefix only), `--pooling mean` instead of `cls` in `embeddings.py`, `sos-embed.service`, `dev/run-dev.sh`;
   `DIMS = 384` is hard-coded (`_vectors_from`, `Index.load`, `ApproxIndex.build`); the 512-token window now includes the 3-token passage prefix. If prefixes are the risk, `gte-base` needs none (mean pooling and 768 dims only),
   with -0.130 safety MRR against e5 (interval +0.04 to +0.23; its guard is 32 of 34), and equal paraphrase accuracy.
4. **Storage** on the Pi: the Wikipedia vectors double to 12.9 GB. If that does not fit, keep bge-small for the Wikipedia rerank only (two servers: 151 MB + 245 MB, within budget by memory, but two models to keep in step and the
   wikipedia rerank is where meaning search already hurt in the baseline), or leave the Wikipedia rebuild for last.
5. **Pi timing was not measured on a Pi.** The 25 ms control figure in the docs is the only Pi anchor; re-measure e5-base-v2 on the box before committing.

**Do not** pay for bge-large or mxbai-large (not feasible on the Pi, +0.03 to +0.05 MRR, inside the noise), for any small model, or for a reranker. If a reranker is revisited later, the only candidate that
served correctly, hurt least and could run on llama.cpp is gte-reranker-modernbert-base, top 10 only, RRF-blended; its measured benefit here is +0.03 MRR for 2 s or more per query.

## 10. Reproduce

All under `tools/eval/search/lab/`, run with `/home/dan/.local/share/sos-embed-venv/bin/python` (added `sentencepiece` only):
`prep.py` (corpus, gold, counts), `cards.py` (model cards, remote-code check), `embed.py` / `run_embed_all.sh` (A), `dense.py` (A tables), `keyword.py` (B keyword side), `hybrid.py` (B), `rerank.py` (C),
`compare.py` (paired bootstrap), `convert.py`, `serve_bench.py`, `rerank_cheap_latency.py` (D), `rebuild.py` (E), `control_check.py`, `shipped_tag.py`, `bias.py`, `prior.py`, `prior_compare.py`, `score_scale.py`,
`remote_code_check.py`, `make_tables.py` (this report's tables from the JSON). Raw results in `results/` (largest file 530 KB). The corpus/vector caches are in a scratch directory and are not committed.
