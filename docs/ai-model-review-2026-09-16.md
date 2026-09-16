# Operation SOS — AI model and inference review

**Date:** 2026-09-16
**Scope:** the chat/answer model, llama.cpp build and runtime flags in `docs/superpowers/specs/2026-09-03-operation-sos-design.md` §3/§5/§12, and the phase‑2 embedding model in `docs/superpowers/specs/2026-09-14-gutenberg-library-design.md` §8.
**Status:** review only. Nothing in the repo has been changed.

---

## Executive summary

**Verdict: keep the model, change the quantization, change the KV cache, add speculative decoding, and lower one acceptance number.**

| Area | Verdict |
|---|---|
| **Model — Gemma 4 E2B** | **Keep.** It is real, current, Apache‑2.0, and the right class for this job. The spec's "2.9 GB Q4_K_M" is accurate to the byte. |
| **Quantization — Q4_K_M** | **Change, probably.** Q4_K_M is *not* the format `GGML_CPU_KLEIDIAI` accelerates, and Google ships an official **QAT q4_0** GGUF that should be both faster and more accurate on a Cortex‑A76. Needs one A/B measurement on the box before committing. |
| **KV cache — `-ctk q4_0 -ctv q4_0`** | **Change.** The whole KV cache at `-c 4096` is only ~130 MB at f16 because Gemma 4 E2B is 1‑KV‑head with 28/35 layers on a 512‑token sliding window. Quantizing it saves ~95 MB out of a 4500 MB budget and costs both accuracy and CPU time. Use f16 (or q8_0 if you want the headroom). |
| **Runtime flags** | **Change two.** `--reasoning-budget 0` and `chat_template_kwargs: {"enable_thinking": false}` are now the *deprecated* way to turn thinking off in llama.cpp; the supported lever is `--reasoning off`. Also: consider `--spec-type ngram-mod` (free) and the Gemma 4 MTP drafter (~64 MB). |
| **Performance target** | **Change.** The measured figure for this exact model on a Pi 5 8 GB is **5.97 tok/s generation** — *below* the ≥7 tok/s acceptance bar, on an idle box, before kiwix/kiosk/hotspot contention. Prompt processing, conversely, is measured at ~28–32 tok/s vs the spec's assumed 20, so TTFT is *better* than planned. |
| **Embeddings — bge-small-en-v1.5** | **Reasonable but dated.** `granite-embedding-small-english-r2` is a same‑size, same‑384‑dimension, Apache‑2.0 drop‑in with a 8192‑token window instead of 512 and no query‑prefix requirement. Worth a bake‑off; not worth a rewrite of §8. |

**Single most important finding:** the ≥7 tok/s generation gate in milestone 6 is set *above* the only published measurement of Gemma 4 E2B Q4_K_M on Pi 5 hardware matching this build (Pi 5 8 GB + SSD: **5.97 tok/s**; Pi 5 16 GB: 6.71 tok/s). Either the gate moves to ~5 tok/s, or the build has to buy back throughput — and the cheapest way to buy it back is speculative decoding, which Gemma 4 ships a purpose‑built 64 MB drafter for and which the pinned llama.cpp already supports.

---

## 1. Does "Gemma 4 E2B Q4_K_M" name a real model?

**Yes. The spec is correct, including the file size.**

Google released **Gemma 4 on 2 April 2026** in five sizes: E2B, E4B, 12B, 26B‑A4B (MoE) and 31B dense.

- **E2B is a real, released variant** and uses the same "effective parameters" naming as Gemma 3n: **2.3B effective out of 5.1B total**, via **Per‑Layer Embeddings (PLE)** — each decoder layer gets its own small embedding table, looked up per token rather than matmul'd, so the effective count is far below the stored count. ([model card](https://huggingface.co/google/gemma-4-E4B), [architecture write‑up](https://ritvik19.medium.com/papers-explained-gemma-4-ba2108a444a9), [tech report](https://arxiv.org/html/2607.02770v1))
- **License: Apache 2.0** — confirmed in the HF model‑card front matter for `google/gemma-4-E2B-it` (`license: apache-2.0`) and in Google's launch blog. This is a real change from Gemma 3's custom Gemma Terms of Use and is materially good news for a product that is distributed or sold. ([launch blog](https://blog.google/innovation-and-ai/technology/developers-tools/gemma-4/))
- **Context window 128K** on the small models; decoder‑only with interleaved sliding‑window and global attention; text + image + **audio** natively on E2B/E4B (a 150M vision encoder ships separately as `mmproj`).
- **"2.9 GB Q4_K_M" checks out exactly.** `unsloth/gemma-4-E2B-it-Q4_K_M.gguf` is **2.89 GiB**. Google's own docs state E2B needs "11.4 GB" at BF16 and "2.9 GB" at 4‑bit. ([Gemma 4 overview](https://ai.google.dev/gemma/docs/core))

Architecture facts pulled from `google/gemma-4-E2B-it/config.json`, because several of them drive the rest of this review:

```
num_hidden_layers        35      (28 sliding_attention + 7 full_attention)
sliding_window           512
num_attention_heads      8
num_key_value_heads      1       <- single KV head
head_dim                 256     (global_head_dim 512 on the full-attention layers)
num_kv_shared_layers     20
hidden_size              1536
vocab_size               262144
hidden_size_per_layer_input 256  (the PLE tables)
```

**Nothing in the spec needs correcting here.** The name, generation, variant and file size are all right.

---

## 2. Is Gemma 4 E2B a sound choice for this job?

**Yes on suitability, borderline on speed.**

### 2.1 Suitability

For terse, citation‑constrained, offline RAG on a 3–4 GB budget this is close to the ideal pick:

- **Apache 2.0.** No use‑policy audit, no redistribution clause, no MAU threshold. Llama 3.2 (Llama Community License) and anything under a bespoke licence would need legal review before shipping a box to a customer; Gemma 4 does not.
- **Grounded‑answering quality looks good in‑family.** Vectara's HHEM leaderboard (snapshot 11 May 2026) — which measures exactly the failure mode that matters here, *claims in a summary not supported by the source document* — puts the Gemma 4 family at the top of the open pack: `gemma-4-26b-a4b-it` **5.2%** hallucination / 94.8% factual consistency, `gemma-4-31b-it` 7.4% / 92.6%. Gemma 3's 4B scored 6.4% / 93.6%. ([leaderboard](https://github.com/vectara/hallucination-leaderboard))
  **Caveat, stated plainly: E2B itself is not on that leaderboard.** The family trend is suggestive, not proof. Your own `sos eval` refusal‑rate gate is the real measurement.
- **The 128K context is irrelevant here and that's fine** — running it at `-c 4096` is normal and costs nothing.
- **Thinking is off by default in Gemma 4**, which is what this design wants. Vectara's own note that "reasoning models consistently perform worse on grounded summarization" supports the spec's decision to keep thinking disabled. (But see §7.1 — the *mechanism* for disabling it in the spec is stale.)

### 2.2 Speed — the problem

The best available measurement is a published llama.cpp benchmark of **this exact model and quant** on Pi 5 hardware (potato‑os/core, 4 April 2026, llama.cpp `a1cfb64`, `gemma-4-E2B-it-Q4_K_M.gguf`, 2.88 GiB):

| Board | pp512 (prompt) | tg128 (generation) |
|---|---|---|
| Pi 5 **16 GB** / SD | 28.02 tok/s | **6.71 tok/s** |
| Pi 5 **8 GB** / NVMe SSD + zram | 31.86 tok/s | **5.97 tok/s** |
| Pi 4 8 GB / SD | 4.06 tok/s | 1.68 tok/s |

([benchmark](https://github.com/potato-os/core/blob/main/docs/benchmarks/gemma4-pi-benchmark-2026-04-04.md))

Two consequences:

- **Prompt processing is better than the spec assumes.** Spec says ~20 tok/s; measured ~28–32. A 1500‑token prompt is therefore **≈47–54 s to first token**, not 75 s, comfortably inside the 90 s median gate. The spec's TTFT estimate is pessimistic, which is the safe direction to be wrong in.
- **Generation is worse than the spec's floor.** The 8 GB/SSD row — the configuration closest to the SOS box — is **5.97 tok/s**, and the acceptance gate in milestone 6 is **≥7 tok/s**. That row was a bare benchmark, not a box also running kiwix‑serve, a Chromium kiosk, Caddy, dnsmasq and a hotspot, with `Nice=10` and `CPUWeight=30` deliberately de‑prioritising llama‑server.

This is corroborated by a first‑principles check. Generation on a Pi 5 is memory‑bandwidth bound (LPDDR4X, and neither llama.cpp nor Ollama can use VideoCore VII for matmul). TinyLlama‑1.1B at Q4_0 (~0.64 GB of weights) measures 14.4 tok/s generation and 108 tok/s prefill on a Pi 5; scaling by per‑token weight traffic to Gemma 4 E2B's ~2.3B *effective* parameters at 4 bits (~1.3–1.4 GB touched per token) predicts ~6.6 tok/s. That independently lands on the measured number, so the measurement is not a fluke of one person's build. ([TinyWeights Pi 5 benchmarks](https://tinyweights.dev/posts/run-llms-raspberry-pi-5/), [Pi 5 GPU status](https://everylocalai.com/hardware/raspberry-pi-5))

Secondary sources give wider ranges (3–8 tok/s from MindStudio, "8–12 tok/s" from an aetos.ai post that also states a "~1.5 GB download" for a model that is 2.9 GB, so I would not weight it). **Sources conflict at the optimistic end; nothing credible reproduces the spec's 7–12 tok/s band on an idle Pi 5, and the one careful benchmark sits below it.**

### 2.3 What to do about it

Three options, in order of preference:

1. **Buy the throughput back with speculative decoding** (§7.2). Gemma 4 ships a co‑trained MTP drafter; the GGUF is **64 MB**. Reported GGUF speedups are 1.4×–2.2× — but every published measurement is on a GPU, so treat 1.3–1.6× as the honest CPU expectation and *measure it*. If it lands, 5.97 → ~8 tok/s and the existing gate passes unchanged.
2. **Relax the gate to ≥5 tok/s.** In UX terms this is almost nothing: a 200‑token answer takes 33 s instead of 29 s, against a TTFT of ~50 s that dominates the wait anyway. A gate that the hardware cannot meet on an idle box is a gate that will be quietly waived under pressure, which is worse than a gate set honestly.
3. **Drop to a smaller model.** `Qwen3.5-2B` (Apache 2.0, dense ~2B, ~1.3 GB at Q4) would roughly double generation speed. But Qwen3.5's larger siblings score notably *worse* on Vectara's grounded‑summarization test than Gemma 4's (qwen3.5‑27b 12.1% hallucination vs gemma‑4‑31b 7.4%), which is the wrong trade for a device whose whole safety story is "answers only from the retrieved passage." **I would not make this swap on current evidence.**

The spec's existing risk note ("drop to the 1B model if needed") is the right instinct, but options 1 and 2 should both be exhausted first.

---

## 3. Strongest current alternatives in the same class

Verified as of today, with licence noted because this is a distributed product:

| Model | Size | Licence | Notes for this job |
|---|---|---|---|
| **Gemma 4 E2B** (current) | 2.3B eff / 5.1B total, 2.89 GiB Q4_K_M | **Apache 2.0** | Best licence + best in‑family grounding evidence. Slowest of this list on Pi 5. |
| **Qwen3.5‑2B** | dense 2B, ~1.3 GB Q4 | **Apache 2.0** | Released 2 Mar 2026; 0.8B/2B/4B/9B sizes, 262K context, ships an MTP head. Roughly 2× the generation speed. Family scores *worse* on grounded summarization. ([review](https://www.toolworthy.ai/tool/qwen-3-5-small-series)) |
| **Qwen3‑4B** | 4B | Apache 2.0 | **5.7% hallucination / 94.3% factual consistency** on Vectara — the best small‑model score on that board. But 4B dense at Q4 ≈ 2.4 GB of per‑token traffic → *slower* than Gemma 4 E2B on this box. Good quality, wrong hardware. |
| **Phi‑4‑mini‑instruct** | 3.8B | MIT | **Rule it out.** 23.5% hallucination / 76.5% factual consistency on Vectara — by far the worst small model measured, and hallucination under provided context is precisely the failure this product cannot tolerate. |
| **Llama 3.2 1B / 3B** | 1B/3B | Llama Community License | Still a solid instruction‑follower, but the licence carries a use policy, redistribution and naming obligations. For a box you sell, that is a real (if surmountable) cost that Apache‑2.0 alternatives simply don't have. Also now two generations old. |
| **Granite 4 / granite‑3.3** | 2B–8B | Apache 2.0 | IBM tunes explicitly for enterprise RAG; `granite-3.3-8b` scores 10.6% on Vectara — worse than Gemma, and 8B is far too big for this box. The small Granite *embedding* models are more interesting than the generative ones here (§6). |
| **SmolLM / LFM2.5‑1.2B** | 0.3–1.2B | Apache 2.0 / LFM licence | LFM2.5‑1.2B is credited with 10–20 tok/s at ~0.9 GB on Pi 5. Worth keeping as the named fallback in the spec's risk section instead of "the 1B model", but instruction‑following and citation discipline at ~1B is where grounded RAG starts to break. |

**Conclusion: no alternative beats Gemma 4 E2B on the combination of licence, grounding behaviour and memory fit.** The only genuine competitor on *speed* is Qwen3.5‑2B, and it trades away the thing this product most needs. Keep the model.

---

## 4. Is Q4_K_M still the right quantization?

**Probably not. This is the change I'd make first, and it is cheap to test.**

### 4.1 KleidiAI does not accelerate Q4_K_M

The spec builds with `-DGGML_CPU_KLEIDIAI=ON`. **KleidiAI's llama.cpp micro‑kernels cover only `Q4_0`, `Q8_0` and `F16` weights.** Everything else — the whole K‑quant and IQ family, Q4_K_M included — declines the KleidiAI buffer type. ([Arm learning path](https://learn.arm.com/learning-paths/mobile-graphics-and-gaming/performance_llama_cpp_sme2/kleidiai_integration/))

So today that build flag buys the SOS box nothing at all. It is not *harmful* — I checked `ggml/src/ggml-cpu/ggml-cpu.cpp`, KleidiAI's buffer type is registered ahead of the generic repack buffer type, and tensors it declines fall through cleanly to repack — but it is decoration unless the model is Q4_0 or Q8_0.

### 4.2 Q4_K_M is *not* unaccelerated, though — the common advice is out of date

I checked `ggml/src/ggml-cpu/repack.cpp` on master directly rather than trusting blog posts. Current llama.cpp has a **dotprod‑only repack path for Q4_K**:

```cpp
} else if (cur->type == GGML_TYPE_Q4_K) {
    if (ggml_cpu_has_neon() && ggml_cpu_has_matmul_int8()) { ... return &q4_K_8x8_q8_K; }
    if (ggml_cpu_has_neon() && ggml_cpu_has_dotprod())     { ... return &q4_K_8x4_q8_K; }   // <- Cortex-A76 lands here
```

`q4_K_8x4_q8_K` requires only NEON + dotprod, not i8mm. The Cortex‑A76 gets it. I confirmed this path exists in **both** the pinned `v0.3.0` and the current `v0.4.1`. So the widely repeated claim "K‑quants fall back to generic scalar kernels on ARM" is stale — it was true in 2024, it is not true now.

That means the gap between Q4_K_M and Q4_0 on this board is *narrower* than the KleidiAI marketing numbers (5.03× decode, measured with SME2/i8mm on phone silicon the Pi 5 does not have) would suggest.

### 4.3 The actual case for changing: Google ships a QAT q4_0 checkpoint

Normally Q4_0 is a quality downgrade from Q4_K_M — cruder blocks, one scale per 32 weights. **Quantization‑Aware Training removes that penalty**, and Google publishes one for exactly this model:

- **`google/gemma-4-E2B-it-qat-q4_0-gguf`** — `gemma-4-E2B_q4_0-it.gguf`, **3.119 GiB**, Apache 2.0, ~548k downloads.
- Community QAT repack: `unsloth/gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf` at **2.44 GiB** (QAT weights, K‑quant layout — quality of QAT without the Q4_0 kernel benefit).

Reported behaviour of QAT vs plain Q4 on Gemma 4: on the 26B MoE, QAT "matched Q4_K_M's speed while improving the GPQA score." One write‑up also warns that naively re‑quantizing the QAT checkpoint to Q4_0 *outside* Google's pipeline can misalign with the trained lattice and lose accuracy — which is an argument for taking **Google's own published q4_0 GGUF** rather than rolling your own. ([Google QAT post](https://blog.google/innovation-and-ai/technology/developers-tools/quantization-aware-training-gemma-4/), [QAT vs non‑QAT](https://3h4x.github.io/tech/2026/06/08/gemma4-qat-vs-non-qat))

**The prize:** a Q4_0 model is the *one* format that gets both the KleidiAI dotprod kernels and the `q4_0_4x4_q8_0` repack path, i.e. the best‑optimised route through llama.cpp on an A76, while QAT keeps quality at roughly BF16 level.

**The cost:** Google's QAT GGUF is **3.119 GiB vs 2.89 GiB** — about 230 MB more resident, presumably because the embedding/PLE tensors are kept at higher precision. Against `MemoryMax=4500M` and an expected ~3.5 GB RSS that is affordable but not free; it wants re‑measuring, not assuming.

### 4.4 Other formats considered

- **IQ4_XS (2.78 GiB):** smaller, but IQ‑quants have **no ARM repack path at all** (only `IQ4_NL` does, at 4x4 dotprod). On a CPU‑bound box, IQ4_XS is the wrong direction — smaller file, slower inference. Rule out.
- **IQ4_NL (2.83 GiB):** has a dotprod repack path, but no QAT checkpoint and no clear quality edge over Q4_K_M. No reason to prefer it.
- **Q4_K_S / UD‑Q4_K_XL:** marginal size changes, same kernel path as Q4_K_M. Not worth a change on their own.
- **Q5_K_M (3.13 GiB) or higher:** more weight traffic per token, directly slower on a bandwidth‑bound board. Wrong direction given §2.2.

### 4.5 Recommendation

Run `llama-bench` on the box over three candidates and pick on measured tok/s, not theory:

```
gemma-4-E2B-it-Q4_K_M.gguf                (current, 2.89 GiB)
gemma-4-E2B_q4_0-it.gguf   (Google QAT,   3.12 GiB)
gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf        (2.44 GiB)
```

My expectation is that the Google QAT q4_0 wins on tok/s and ties or wins on `sos eval` quality; if the 230 MB pushes RSS uncomfortably close to `MemoryMax`, the 2.44 GiB QAT K‑quant is the fallback. **Do not change this without the measurement** — it is a 20‑minute experiment and the theory here has enough moving parts that I would not trust it unverified.

---

## 5. Is `-ctk q4_0 -ctv q4_0` still advisable?

**No. Change it to f16 (or q8_0). This is the clearest and lowest‑risk improvement in the review.**

The reasoning is arithmetic, not taste. Gemma 4 E2B is unusually cheap on KV cache:

- **1 KV head** (`num_key_value_heads: 1`), `head_dim` 256.
- **28 of 35 layers are sliding‑window with a 512‑token window** — llama.cpp does not allocate full‑context KV for those unless you pass `--swa-full`, which the spec correctly does not.
- Only **7 layers are full‑attention**, at `global_head_dim` 512.

At `-c 4096`, f16:

| | tokens cached | per‑token per‑layer (K+V) | layers | f16 size |
|---|---|---|---|---|
| sliding layers | ~512 + batch | 2 × 1 × 256 | 28 | ~73 MB |
| full layers | 4096 | 2 × 1 × 512 | 7 | ~59 MB |
| **total** | | | | **~130 MB** |

(`num_kv_shared_layers: 20` may reduce this further depending on how much of Gemma 4's KV sharing llama.cpp implements; 130 MB is the conservative upper figure. `-np 1` means no multiplication by slots.)

So `-ctk q4_0 -ctv q4_0` saves roughly **95 MB out of a 4500 MB cgroup limit** — about 2%. In exchange:

- **Accuracy:** current guidance is that q8_0 KV is "essentially free quality‑wise" while **q4_0 KV is the risky one**, with degraded long‑context behaviour especially on structured output. This build's output *is* structured — it must emit `[1]`/`[2]`/`[3]` citation markers that the streaming hold‑back logic parses and drops if they don't map to an emitted passage. Degrading exactly the token class the safety mechanism keys on is a bad trade for 95 MB.
- **Speed:** quantized KV costs per‑token dequantization work on every attention step. On a board that is already 1 tok/s short of its own acceptance gate, spending CPU to save 2% of RAM is backwards.

([quantization guidance](https://runlocalmodel.com/choosing-quantization-2026.html), [llama.cpp KV discussion](https://github.com/ggml-org/llama.cpp/discussions/20969))

**Recommendation:** drop `-ctk q4_0 -ctv q4_0` entirely (f16 default). If a later measurement shows RSS pressure, `-ctk q8_0 -ctv q8_0` is the compromise — never q4_0 at this context size. Keep `-fa on`: flash attention is a straight win and is required if you ever *do* quantize V.

---

## 6. Sanity‑check on `bge-small-en-v1.5` for phase 2

**Still defensible, but it is a September 2023 model and there is a same‑size, same‑dimension, better‑licensed successor worth an afternoon's comparison.**

| | bge-small-en-v1.5 | granite-embedding-small-english-r2 | EmbeddingGemma-300m |
|---|---|---|---|
| Params | 33.4M | 47M | 308M |
| Dimensions | 384 | **384** | 768 (Matryoshka → 512/256/128) |
| Max sequence | **512** | **8192** | 2048 |
| Licence | MIT | Apache 2.0 | Gemma terms |
| Score | MTEB 62.17 (v1, 56 tasks) | MTEB‑v2 61.1 / BEIR 50.9 | **MTEB eng v2 69.67** |
| Query prefix needed | **Yes** — `"Represent this sentence for searching relevant passages:"` | No | Task prompts |

Sources: [bge-small-en-v1.5](https://huggingface.co/BAAI/bge-small-en-v1.5), [granite-embedding-small-english-r2](https://huggingface.co/ibm-granite/granite-embedding-small-english-r2), [EmbeddingGemma](https://ai.google.dev/gemma/docs/embeddinggemma).

Three observations:

1. **The 512‑token window on bge-small is a real constraint** for a library build. Gutenberg book vectors (title + author + subjects + blurb) fit easily; document‑corpus passages at 400 tokens fit; but it leaves no room to grow. Granite R2's 8192 window is a genuine capability difference at the same 384 dimensions, so §8's storage maths (`70,000 × 384` f16, ~20 ms brute‑force numpy cosine) is **unchanged** by the swap. That makes it a cheap experiment.
2. **The query‑prefix requirement is an easy thing to ship broken.** bge-small-en-v1.5 was trained with an asymmetric instruction on the *query* side only. If `sos build-embeddings` indexes passages without the prefix (correct) and the box embeds queries without it too (incorrect), retrieval quality degrades silently — no error, just worse results. **If bge-small is kept, §8 should state the prefix explicitly** and the four‑row fixture test in `api/tests/test_embeddings.py` should assert it.
3. **EmbeddingGemma is the quality leader but a poor fit here.** 308M params, ~300 MB at Q8 — an order of magnitude past the "30–100 MB" budget in the brief — and 768 dimensions doubles the vector store unless truncated. Its MRL truncation to 256d would keep storage sane, but you would be adding a second Gemma model, a second warm‑up cost and a second set of task‑prompt conventions to a box that is already tight on RAM. **Not worth it for "books about X" search.** Also note llama.cpp has had at least one Gemma‑embedding accuracy report traced to a pooling‑type mismatch (`model default pooling_type is [1], but [2] was specified`, issue #19040, closed) — a class of bug bge‑small does not expose you to.

**Sources conflict on the bge‑vs‑granite margin** and I will not pretend otherwise: one comparison puts bge-small ahead on BEIR (51.7 vs 50.9), while IBM's own model card claims a much larger win (55.6 vs 45.22 average). Benchmark suites and versions differ. The honest position is "comparable, granite slightly ahead on newer suites, and clearly ahead on sequence length and prefix ergonomics."

**Recommendation:** keep `bge-small-en-v1.5` as the spec'd default so phase 2 is not blocked, but add `granite-embedding-small-english-r2` as the A/B candidate and decide on your own retrieval@3 numbers over the real corpus. Both are 384‑d, so the decision is reversible without touching the vector format. Verify GGUF availability for whichever wins before committing — bge-small's GGUF ecosystem is mature; Granite R2's is less so.

---

## 7. Other material risks and misses

### 7.1 The thinking‑disable flags are the deprecated ones — **fix this**

The spec uses `--reasoning-budget 0` plus a per‑request `chat_template_kwargs: {"enable_thinking": false}`. Reading `common/arg.cpp` on the pinned tag:

```cpp
if (item.key() == "enable_thinking") {
    LOG_WRN("Setting 'enable_thinking' via --chat-template-kwargs is deprecated. "
            "Use --reasoning on / --reasoning off instead.\n");
}
...
{"--reasoning-budget"}, "N",
"token budget for thinking: -1 for unrestricted, 0 for immediate end, N>0 for token budget (default: -1)"
```

`--reasoning-budget 0` is a *sampler‑level forced termination* of thinking, not a template‑level suppression, and `enable_thinking` is explicitly deprecated. The supported switch is **`-rea` / `--reasoning on|off|auto`**. A llama.cpp discussion on Gemma 4 reports that neither `--reasoning-budget 0` nor `enable_thinking:false` reliably suppressed thinking on the 26B, and that **`--reasoning off` was the working answer**. ([discussion #21338](https://github.com/ggml-org/llama.cpp/discussions/21338))

Mitigating context: **Gemma 4's thinking mode is off by default** — you must pass `enable_thinking=True` to turn it on — so the current setup is unlikely to be actively leaking `<|think|>` blocks into answers. But the spec is relying on two deprecated levers to enforce something important, and if thinking ever *does* engage, a 4000‑token chain of thought against a 400‑token `max_tokens` on a 6 tok/s box is a user‑visible failure.

**Action:** add `--reasoning off` to `sos-llama.service`; drop `--reasoning-budget 0` and the `chat_template_kwargs` from the request body. Add an assertion to the fake‑llama‑server test suite that no reasoning content reaches the SSE `token` stream.

### 7.2 Speculative decoding is available, free, and unexploited — **the biggest upside**

The pinned `v0.3.0` already supports it; I verified the type names in `common/speculative.cpp`:

```
{"draft-mtp",  COMMON_SPECULATIVE_TYPE_DRAFT_MTP},
{"ngram-mod",  COMMON_SPECULATIVE_TYPE_NGRAM_MOD},
```

Two options, both applicable:

- **`--spec-type ngram-mod`** — n‑gram / lookup decoding, **no draft model, no extra RAM**. It drafts tokens by finding repeats of the current suffix in the existing context. This workload is close to a best case for it: the model is instructed to answer *only* from three retrieved passages sitting in its own context, so generated text overlaps the prompt heavily. Free to try, nothing to download.
- **`--spec-type draft-mtp -md <assistant>`** — Gemma 4's co‑trained Multi‑Token Prediction head. `ggml-org/gemma-4-E2B-it-GGUF` publishes `mtp-gemma-4-E2B-it-Q4_0.gguf` at **0.06 GiB**; Google publishes the weights as `google/gemma-4-E2B-it-assistant` (Apache 2.0, 147 MB safetensors). Unlike generic draft models it shares activations with the target, so the drafting cost is near‑trivial. Recommended `--spec-draft-n-max 4` (sometimes 3 on Q4). ([Google MTP docs](https://ai.google.dev/gemma/docs/mtp/overview), [llama.cpp how‑to](https://dev.to/everylocalai/how-to-get-2x-speed-on-gemma-4-with-multi-token-prediction-in-llamacpp-1b8e))

**Honest caveat:** every published MTP speedup (1.4×–2.5×) is measured on a GPU. On a 4‑core CPU, verifying 4 drafted tokens in one batched pass amortizes the weight read — which is the bound here — but pushes toward being compute‑bound, so the realistic gain is smaller. **I would not put a number in the spec until `sos eval` measures it on the box.** But if it delivers even 1.3×, 5.97 → 7.8 tok/s and the milestone‑6 gate passes as written, for 64 MB of RAM.

### 7.3 A scary‑looking llama.cpp issue that I believe is wrong

`ggml-org/llama.cpp` issue **#22243** (opened 22 April 2026, still open, label `bug-unconfirmed`, no maintainer response) claims Gemma 4 E2B/E4B **Per‑Layer Embeddings are never injected into the decoder layers**, making the models "unreliable for production use via llama.cpp" with "subtly degraded output quality." If true that would invalidate the whole model choice.

**I checked the source rather than taking the issue at face value, and it does not hold up.** `src/models/gemma4.cpp` on master implements the full PLE pipeline:

```cpp
inp_per_layer = build_inp_per_layer();                     // get_per_layer_inputs() equivalent
inp_per_layer = project_per_layer_inputs(inpL, inp_per_layer);
...
cur = build_lora_mm(model.layers[il].per_layer_inp_gate, cur);
ggml_tensor * inp_this_layer = gemma4_view_2d_slice(ctx0, inp_per_layer, il);
cur = build_lora_mm(model.layers[il].per_layer_proj, cur);
cur = build_norm(cur, model.layers[il].per_layer_post_norm, ...);
cb(cur, "per_layer_embd_out", il);
```

The per‑layer signal is gated, sliced per layer, projected and normed into each decoder layer. The issue was either filed against an older build or is simply mistaken. **No action needed — but don't be alarmed if someone finds that issue, and don't pin llama.cpp backwards.**

### 7.4 llama.cpp version pin

`install/versions.env` pins `LLAMA_CPP_TAG=v0.3.0` (commit `c1d0e7a`, 25 Aug 2026). llama.cpp moved from `b####` build tags to semver; current release is **v0.4.1** (14 Sep 2026).

I verified that v0.3.0 already contains everything this review depends on: `q4_K_8x4_q8_K` dotprod repack, `--reasoning on|off`, `--spec-type draft-mtp` and `ngram-mod`. **The pin is fine and does not need moving for any recommendation here.** Worth a routine bump to v0.4.1 at some point, but nothing forces it.

One note: the comment in `versions.env` describing the tag is sourced from a build log outside the repo (`/home/dan/sos-content/llama-build.log`). That's a fragile provenance chain for a pinned dependency — consider recording the tag's own date and a checksum of the built binary instead.

### 7.5 Is there a better inference engine for an ARM SBC?

**No. llama.cpp is clearly correct here**, and I found direct evidence rather than assuming it:

- **ExecuTorch** (PyTorch's edge runtime, with Google's own Gemma 4 deployment example): measured **0.72–0.87 tok/s decode** for Gemma 4 E2B INT4 on a Pi 5 8 GB — roughly **7.7× slower** than llama.cpp on the same class of board, with a 5.14 GB artifact. The author explicitly notes the decode rate does not improve with alternative partitioner configs. ([repo](https://github.com/bamb00boy/Gemma4_executorch_deployment))
- **ik_llama.cpp** (the CPU‑focused fork sometimes recommended for quantization kernels): the potato‑os benchmark reports **E2B and E4B crash on ik_llama**; only the 26B MoE loaded. Not an option.
- **Ollama:** a wrapper over the same llama.cpp engine, and measurably slower in SBC comparisons (llamafile showed 3–4× higher throughput than Ollama on SBCs in an arXiv evaluation of 25 models across Pi 4 / Pi 5 / Orange Pi 5 Pro). Adding it would cost performance and a daemon.
- **GPU offload is genuinely unavailable.** The Pi 5's VideoCore VII has no production Vulkan or OpenCL path in llama.cpp for LLM matmul. **`-ngl 0` is correct, not a compromise.**

([arXiv SBC evaluation](https://arxiv.org/html/2511.07425v1))

### 7.6 Thermal headroom is tighter than the spec's gate implies

The spec's acceptance criterion is "CPU stays under 80°C" and there's a thermal watchdog at 80°C. **80°C is precisely where Raspberry Pi firmware begins soft‑throttling the ARM cores**, with hard throttling at 85°C. So the gate is set at the exact temperature where performance starts degrading — meaning any run that approaches it is also a run where the tok/s measurement becomes unreliable.

With active cooling, a Pi 5 under full load typically sits in the 60s, so this should be fine in the open. **In a sealed printed case it is the open question the spec already flags.** Suggestion: have `sos eval` record `vcgencmd get_throttled` alongside the temperature, so a throttled run is *detected* rather than silently producing a low tok/s number that gets blamed on the model. ([Raspberry Pi thermals](https://www.raspberrypi.com/news/heating-and-cooling-raspberry-pi-5/))

### 7.7 Smaller flag observations

- **`-t 4`** uses all four cores. With `Nice=10`/`CPUWeight=30` the scheduler will de‑prioritise llama‑server, which is the intent — but the combined‑load test in the hardware checklist should confirm that search p95 stays under 3 s during generation. `-t 3` is the obvious lever if it doesn't.
- **`cache_prompt: true`** only ever hits on the ~250‑token system prefix, since the three retrieved passages differ per question. That's fine, but don't expect it to help TTFT materially. `--ctx-checkpoints` interacts with SWA models; not worth tuning at `-c 4096`.
- **Don't load `mmproj`.** Gemma 4 E2B is multimodal (image + audio) and the vision projector is a separate 0.92 GiB file. The spec correctly says "no image input"; just make sure nothing downloads or loads `mmproj-*.gguf` — that's a GB of RAM for a feature the product doesn't have.
- **`--no-webui`, `-np 1`, localhost bind, never proxied** — all correct and well judged.

---

## 8. Concrete recommendation

**Keep Gemma 4 E2B.** It is real, current, Apache‑2.0, correctly sized, and the best‑evidenced family for grounded answering in this class.

Changes, in priority order:

1. **KV cache — do this now, no measurement needed.**
   Remove `-ctk q4_0 -ctv q4_0`. Keep `-fa on`. Saves nothing worth having (~95 MB of 4500 MB), costs accuracy on exactly the citation tokens the hold‑back logic depends on, and costs CPU time the box doesn't have.

2. **Thinking control — do this now.**
   Replace `--reasoning-budget 0` with **`--reasoning off`** on the unit, and drop `chat_template_kwargs: {"enable_thinking": false}` from the request body. Both current mechanisms are deprecated in llama.cpp and at least one report says they don't reliably work on Gemma 4.

3. **Quantization — measure, then switch.**
   `llama-bench` on the box across `Q4_K_M` (current) vs **`google/gemma-4-E2B-it-qat-q4_0-gguf`** (3.12 GiB) vs `unsloth/gemma-4-E2B-it-qat-UD-Q4_K_XL` (2.44 GiB). Expect the QAT q4_0 to win: Q4_0 is the only format that gets *both* the KleidiAI kernels the build already enables *and* the `q4_0_4x4` repack path, and QAT removes Q4_0's usual quality penalty. Confirm RSS stays inside `MemoryMax=4500M` before adopting — it is ~230 MB larger than the current file.

4. **Speculative decoding — measure, likely adopt.**
   Try `--spec-type ngram-mod` first (free, no download, well‑suited to answer‑from‑context). Then the MTP drafter: `--spec-type draft-mtp -md mtp-gemma-4-E2B-it-Q4_0.gguf --spec-draft-n-max 4` (64 MB). Published gains are GPU‑only, so treat this as an experiment, not a promise — but a 1.3× gain resolves the throughput gap entirely.

5. **Acceptance criteria — correct two numbers.**
   - Generation gate: **≥7 tok/s is not supported by the evidence** (5.97 measured on Pi 5 8 GB/SSD, idle). Either move it to ≥5 tok/s, or keep 7 and make it conditional on (3) and (4) landing. Do not leave a gate the hardware fails on an idle bench.
   - TTFT: the underlying assumption (~20 tok/s prompt processing) is too pessimistic; measured is 28–32 tok/s, so ~50 s for a 1500‑token prompt. The 90 s median gate is safe and can stay.
   - Add `vcgencmd get_throttled` to the `sos eval` run record so throttled runs are visibly invalid rather than silently slow.

6. **Phase‑2 embeddings — keep, with a caveat and a candidate.**
   Keep `bge-small-en-v1.5` as the default so phase 2 isn't blocked. **Document the mandatory query prefix** (`"Represent this sentence for searching relevant passages: "`) in §8 and assert it in `test_embeddings.py` — silent retrieval degradation is the failure mode here. Bake off against **`granite-embedding-small-english-r2`** (47M, same 384 dimensions, Apache 2.0, 8192‑token window, no prefix) on real retrieval@3; the vector format is identical either way so the decision is reversible. Skip EmbeddingGemma — better scores, wrong size and dimensionality for this box.

**Not recommended:** switching to Qwen3.5‑2B, Llama 3.2, or Phi‑4‑mini. Faster in one case, cheaper in none, and all three trade away either grounding quality (Phi‑4‑mini's 23.5% hallucination rate is disqualifying for this product) or licence simplicity.

---

## Sources

- [Gemma 4 launch blog](https://blog.google/innovation-and-ai/technology/developers-tools/gemma-4/) · [Gemma 4 model overview](https://ai.google.dev/gemma/docs/core) · [Gemma 4 tech report](https://arxiv.org/html/2607.02770v1) · [google/gemma-4-E2B-it](https://huggingface.co/google/gemma-4-E2B-it) · [google/gemma-4-E4B card](https://huggingface.co/google/gemma-4-E4B) · [architecture explainer](https://ritvik19.medium.com/papers-explained-gemma-4-ba2108a444a9)
- [Gemma 4 QAT announcement](https://blog.google/innovation-and-ai/technology/developers-tools/quantization-aware-training-gemma-4/) · [QAT vs non-QAT](https://3h4x.github.io/tech/2026/06/08/gemma4-qat-vs-non-qat) · [google/gemma-4-E2B-it-qat-q4_0-gguf](https://huggingface.co/google/gemma-4-E2B-it-qat-q4_0-gguf) · [unsloth GGUF repo](https://huggingface.co/unsloth/gemma-4-E2B-it-GGUF) · [ggml-org GGUF repo](https://huggingface.co/ggml-org/gemma-4-E2B-it-GGUF)
- [Pi 5 Gemma 4 benchmark (potato-os/core, 2026-04-04)](https://github.com/potato-os/core/blob/main/docs/benchmarks/gemma4-pi-benchmark-2026-04-04.md) · [TinyWeights Pi 5 benchmarks](https://tinyweights.dev/posts/run-llms-raspberry-pi-5/) · [arXiv: LLM inference on SBCs](https://arxiv.org/html/2511.07425v1) · [Gemma 4 ExecuTorch on Pi 5](https://github.com/bamb00boy/Gemma4_executorch_deployment) · [Pi 5 GPU status](https://everylocalai.com/hardware/raspberry-pi-5)
- [Arm: KleidiAI in llama.cpp](https://learn.arm.com/learning-paths/mobile-graphics-and-gaming/performance_llama_cpp_sme2/kleidiai_integration/) · llama.cpp source read directly: `ggml/src/ggml-cpu/repack.cpp`, `ggml/src/ggml-cpu/ggml-cpu.cpp`, `src/models/gemma4.cpp`, `common/arg.cpp`, `common/speculative.cpp` (tags v0.3.0 and v0.4.1)
- [llama.cpp #22243 (PLE claim — appears incorrect)](https://github.com/ggml-org/llama.cpp/issues/22243) · [llama.cpp #21338 (Gemma 4 thinking)](https://github.com/ggml-org/llama.cpp/discussions/21338) · [llama.cpp #19040 (gemma embedding pooling)](https://github.com/ggml-org/llama.cpp/issues/19040)
- [Gemma 4 MTP overview](https://ai.google.dev/gemma/docs/mtp/overview) · [MTP in llama.cpp how-to](https://dev.to/everylocalai/how-to-get-2x-speed-on-gemma-4-with-multi-token-prediction-in-llamacpp-1b8e) · [Gemma thinking docs](https://ai.google.dev/gemma/docs/capabilities/thinking)
- [Vectara hallucination leaderboard](https://github.com/vectara/hallucination-leaderboard) · [KV cache quantization guidance](https://runlocalmodel.com/choosing-quantization-2026.html) · [llama.cpp KV cache discussion](https://github.com/ggml-org/llama.cpp/discussions/20969)
- [BAAI/bge-small-en-v1.5](https://huggingface.co/BAAI/bge-small-en-v1.5) · [ibm-granite/granite-embedding-small-english-r2](https://huggingface.co/ibm-granite/granite-embedding-small-english-r2) · [EmbeddingGemma](https://ai.google.dev/gemma/docs/embeddinggemma) · [Granite Embedding R2 paper](https://arxiv.org/pdf/2508.21085)
- [Qwen3.5 small series](https://www.toolworthy.ai/tool/qwen-3-5-small-series) · [Raspberry Pi thermals](https://www.raspberrypi.com/news/heating-and-cooling-raspberry-pi-5/)
