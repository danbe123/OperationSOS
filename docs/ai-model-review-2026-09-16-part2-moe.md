# Operation SOS — AI model review, part 2: the MoE question

**Date:** 2026-09-16
**Scope:** an adversarial re-examination of the chat/answer model choice, prompted by the objection *"I don't think this is the right local model for the job… why not a MoE or other."*
**Relationship to part 1:** this report does **not** re-derive part 1's findings. It takes as given, from [`ai-model-review-2026-09-16.md`](./ai-model-review-2026-09-16.md): the 5.97 tok/s Pi 5 8 GB measurement, the KleidiAI-accelerates-only-Q4_0/Q8_0/F16 finding, the `q4_K_8x4_q8_K` dotprod repack path, the Vectara hallucination numbers, and the Apache-2.0 status of Gemma 4. Where I disagree with part 1 I say so.
**Status:** review only. Nothing in the repo has been changed. Nothing committed.

---

## Executive verdict

**Nothing currently available beats Gemma 4 E2B for this specific job, and the MoE argument — which is sound in theory — fails on this specific hardware and this specific toolchain for three independent reasons. But the objection was not wrong to be raised: the search turned up one genuine challenger and one genuinely better-targeted model, and both deserve a bench run rather than a dismissal.**

| Question | Answer |
|---|---|
| Is the Pi 5 memory-bandwidth-bound during generation? | **Yes, decisively** — measured decode runs at ~4.5% of the board's int8 compute ceiling. But it only reaches ~45% of peak DRAM bandwidth, so kernel quality matters too. This nuance is what kills MoE here. |
| Does the MoE active-parameter argument hold on this hardware? | **Partially in theory, not in practice.** Two independent measurements (Jetson Orin Nano, and a Pi 5 running Gemma 4 26B-A4B) show a 25–35% throughput penalty versus a dense model of the *same active-parameter count*. |
| Is there a MoE that fits the 4.5 GB budget? | **Only one credible one.** Every 7B–8B-total MoE (OLMoE, Granite 4.0-h-tiny, LFM2.5-8B-A1B) is 3.93–4.84 GB at Q4 — at or over the cgroup ceiling before KV cache. The exception is **SmallThinker-4B-A0.6B** at 2.63 GB. |
| The decisive toolchain finding | **KleidiAI does not implement `GGML_OP_MUL_MAT_ID` at all.** Verified in `ggml/src/ggml-cpu/kleidiai/kleidiai.cpp` on master. Every MoE expert weight in llama.cpp is routed through `MUL_MAT_ID`, so the Q4_0 + KleidiAI acceleration part 1 recommends buying is **structurally unavailable to any MoE**. |
| The strongest single argument for the incumbent | **Gemma 4 E2B is already a sparse model.** Its 2.35 B-parameter per-layer-embedding table is read with `ggml_get_rows` — ~8,960 values per token instead of 2.35 B — and `GET_ROWS` *is* in KleidiAI's supported-op list. It gets the exact "more capacity at the same per-token cost" property the objection is asking for, through a mechanism that this toolchain accelerates and MoE routing is not. |
| Recommendation | **Keep Gemma 4 E2B.** Apply part 1's tuning changes. Bench **SmallThinker-4B-A0.6B-Instruct Q4_0** as the one honest challenger — it is the only candidate that could plausibly double throughput inside the budget. Do not migrate on theory. |

**Single most important finding:** the objection's premise — *"a MoE gives you more knowledge at the same generation speed"* — is correct as physics but false as engineering on this box, and the proof is in llama.cpp's own source. KleidiAI's `supports_op` gates on `op->op == GGML_OP_MUL_MAT || op->op == GGML_OP_GET_ROWS` **and** `ggml_n_dims(op->src[0]) == 2`. MoE expert tensors are 3-D and dispatch through `MUL_MAT_ID`. They fail both conditions. So the single biggest performance lever part 1 identified — Google's QAT Q4_0 checkpoint feeding the KleidiAI kernels — is a lever that only a dense (or PLE-sparse) model can pull.

---

## 1. The Pi 5's actual bottleneck

### 1.1 Bandwidth figures

The BCM2712 has a **32-bit LPDDR4X-4267 subsystem**, i.e. a theoretical peak of **17.07 GB/s** (4267 MT/s × 4 bytes). Raspberry Pi's own launch material describes it as the "upgraded 32-bit LPDDR4X SDRAM subsystem running at 4267 MT/s". ([Raspberry Pi benchmarking post](https://www.raspberrypi.com/news/benchmarking-raspberry-pi-5/))

Measured, from Jeff Geerling's `sbc-reviews` tinymembench run on a Pi 5:

| Operation | MB/s | Implied DRAM traffic |
|---|---|---|
| standard `memcpy` | 4,805 | ~9.6 GB/s (read+write) |
| C copy | 4,870 | ~9.7 GB/s |
| NEON copy variants | 4,298–4,832 | ~8.6–9.7 GB/s |
| standard `memset` | 13,677 | 13.7 GB/s (write-only) |
| C fill | 13,672 | 13.7 GB/s |

([geerlingguy/sbc-reviews #21](https://github.com/geerlingguy/sbc-reviews/issues/21))

So the board's realistic single-direction streaming bandwidth is somewhere in the **8–14 GB/s** band, against a 17.07 GB/s paper figure. Random-read latency at 64 MB buffers is 118.7 ns — relevant below.

### 1.2 Is generation bandwidth-bound? Yes, by a factor of ~20

First-principles check on the **compute** side, which part 1 did not do:

- Cortex-A76 has two 128-bit NEON pipes; `SDOT` performs 16 int8 MACs per 128-bit vector. That is 32 MACs/cycle/core ≈ **64 int8 ops/cycle/core**.
- 4 cores × 2.4 GHz × 64 = **~614 GOPS** peak int8.
- Gemma 4 E2B generation costs 2.3 B effective params × 2 ops = **4.6 GOP/token**.
- Compute ceiling: **614 / 4.6 ≈ 133 tok/s**.
- Measured: **5.97 tok/s** — i.e. **4.5% of the compute ceiling**.

On the **bandwidth** side: 5.97 tok/s × ~1.29 GB streamed per token (part 1's figure, calibrated against the TinyLlama scaling check) = **~7.7 GB/s**, which is **~45% of the 17.07 GB/s paper peak** and roughly 55–90% of the measured streaming band.

**Conclusion: autoregressive generation on this board is memory-bandwidth-dominated, unambiguously.** Twenty-fold headroom on compute, and decode already sitting at nearly half of theoretical DRAM bandwidth.

### 1.3 The nuance that matters — it is not *purely* bandwidth-bound

This is where I part company with the simple version of the story, and it is the hinge of the whole MoE argument.

A llama.cpp maintainer-triaged issue on the Arm CPU backend reports precisely this: *"Arm CPU backend: quantized decode is compute-bound at ~55–60% of memory bandwidth (Neoverse-N2, SVE2+i8mm)"* ([llama.cpp #25976](https://github.com/ggml-org/llama.cpp/issues/25976), closed), alongside a sibling report that Arm prefill GEMM is flat at ~18 t/s pp512 regardless of thread count ([#25977](https://github.com/ggml-org/llama.cpp/issues/25977)).

The practical reading: on Arm, llama.cpp decode extracts roughly half to two-thirds of available bandwidth, with the rest lost to dequantization and kernel inefficiency. That leaves **no spare margin to absorb additional per-token overhead**. A MoE's expert dispatch-and-gather is exactly such an overhead, and it lands on a path that is already leaving 40–45% of the bandwidth on the table. It is not free.

**Sources:** [Raspberry Pi 5 benchmarking](https://www.raspberrypi.com/news/benchmarking-raspberry-pi-5/) · [tinymembench on Pi 5](https://github.com/geerlingguy/sbc-reviews/issues/21) · [llama.cpp #25976](https://github.com/ggml-org/llama.cpp/issues/25976) · [Arm CPU kernel paper](https://arxiv.org/pdf/2501.00032) (autoregressive decode is GEMV, "the entire set of model weights must be transferred from DRAM to CPU registers")

---

## 2. The MoE argument, evaluated honestly

### 2.1 The theory, stated fairly

The objection is architecturally correct. In a MoE, each token routes to *k* of *N* experts. Per-token FLOPs and per-token weight traffic track the **active** parameter count. Total capacity — the knowledge stored across all experts — tracks the **total** count. On a bandwidth-bound device, per-token cost is weight traffic, so in the ideal limit a 7B-A1B MoE should generate at the speed of a 1B dense model with the quality of something meaningfully larger.

If that held on this box, it would be the right answer. It does not hold, for four reasons, in descending order of how decisive they are.

### 2.2 Reason 1 (decisive): KleidiAI does not implement `MUL_MAT_ID`

I read the source rather than reasoning from documentation. From `ggml/src/ggml-cpu/kleidiai/kleidiai.cpp` on master:

```cpp
bool supports_op(ggml_backend_dev_t, const struct ggml_tensor * op) override {
    ...
    const bool src0_is_kleidiai =
        op->src[0]->buffer &&
        (ggml_n_dims(op->src[0]) == 2) &&        // <- 2-D only
        op->src[0]->buffer->buft->context == this &&
        slot_total > 0;

    if ((op->op == GGML_OP_MUL_MAT || op->op == GGML_OP_GET_ROWS) &&   // <- no MUL_MAT_ID
        (op->src[0]->type == GGML_TYPE_Q4_0 || op->src[0]->type == GGML_TYPE_Q8_0 || op->src[0]->type == GGML_TYPE_F32) &&
        src0_is_kleidiai) {
```

and, in the tensor-traits work-size path:

```cpp
bool work_size(int, const struct ggml_tensor * op, size_t & size) override {
    if (op->op != GGML_OP_MUL_MAT) {
        return false;
    }
```

`GGML_OP_MUL_MAT_ID` does not appear anywhere in the file. MoE expert weights are stored as 3-D tensors and dispatched via `MUL_MAT_ID`, so they fail the op check *and* the `n_dims == 2` check. **KleidiAI accelerates zero percent of an MoE's expert FFN weights**, which on a 7B-A1B model is the large majority of the parameters.

For contrast, the *generic* repack path **does** handle MoE. From `ggml/src/ggml-cpu/repack.cpp`:

```cpp
} else if (op->op == GGML_OP_MUL_MAT_ID
        && op->src[0]->buffer
        && (ggml_n_dims(op->src[0]) == 3)
        && op->src[0]->buffer->buft == ggml_backend_cpu_repack_buffer_type()
        && ggml_repack_get_optimal_repack_type(op->src[0])
        ) {
```

So an MoE on a Cortex-A76 still gets `q4_0_4x4_q8_0` / `q4_K_8x4_q8_K` repacked NEON+dotprod kernels — it is not falling back to scalar. But it gets **only** that. It cannot take the upgrade path part 1 recommends as the single cheapest performance win on this box (Google's QAT Q4_0 checkpoint → KleidiAI micro-kernels), because that path is gated on `MUL_MAT_ID` never being involved.

That is a structural, source-verified disadvantage that applies to *every* MoE candidate below, regardless of its parameter counts.

### 2.3 Reason 2 (measured): the active-parameter advantage erodes on edge ARM

The best available evidence is a July 2026 empirical study built for exactly this question: **["Does Mixture-of-Experts Actually Help Inference on Consumer and Edge Hardware? An Empirical Study"](https://arxiv.org/abs/2606.21428)** (arXiv:2606.21428v3, 9 July 2026). It benchmarks **OLMoE-1B-7B-0924-Instruct** (1.3 B active / 6.9 B total) against dense baselines, all at Q4_K_M under llama.cpp:

| Device | OLMoE (1.3 B active) | Llama-3.2-1B (1.0 B) | Gap |
|---|---|---|---|
| MacBook Pro M2 Pro 16 GB | 114.5 tok/s | 127.4 tok/s | MoE ~10% slower |
| Jetson Orin Nano 8 GB @ 15 W | **22.9 tok/s** | **33.4 tok/s** | **MoE ~31% slower** |

Peak memory: OLMoE **8.0 GiB on the Jetson — at the physical ceiling**, surviving only via zram swap, against 0.98–2.09 GiB for the dense baselines. Energy: **0.96 J/token vs 0.45 J/token**, ~2.1× worse.

The authors patched llama.cpp to split routing time from FFN time and found routing arithmetic itself is cheap (8.9% of MoE-block compute). Their stated conclusion is blunt: *"on bandwidth-bound hardware, inference cost tracks total parameters, not active ones"*, because *"the per-token bandwidth requirement is a function of the total expert weight that must be paged through the compute units, not just the active parameter count"*, plus a *"dispatch-and-gather pattern… structural to MoE inference and absent from dense models."*

**Where I qualify that paper, explicitly:** its strong claim ("cost tracks total parameters") is stated more absolutely than its own data supports — a 1.3 B-active model running only 31% slower than a 1.0 B dense model on the Jetson is *not* the behaviour of a model paying 6.9 B of traffic per token; that would be ~6× slower. What the data actually shows is a **25–35% erosion of the active-parameter advantage**, not its elimination. And the authors themselves note **no Raspberry Pi or ARM SBC was tested**, and that findings should not be extrapolated to other silicon without measurement. I am treating it as strong directional evidence, not proof.

### 2.4 Reason 3 (measured, on a Pi 5): the one same-family comparison available

The potato-os Pi 5 benchmark referenced in part 1 happens to contain a near-controlled MoE-vs-dense comparison within the Gemma 4 family:

| Board | Model | Active params | Quant | Size | Runtime | pp512 | **tg128** |
|---|---|---|---|---|---|---|---|
| Pi 5 16 GB | Gemma 4 **E4B** (PLE-dense) | 4.5 B eff | Q4_0 | 4.49 GiB | llama.cpp | 18.46 | **3.48** |
| Pi 5 16 GB | Gemma 4 **26B-A4B** (MoE) | 4.0 B active | IQ4_NL | 12.48 GiB | ik_llama | 6.38 | **2.54** |
| Pi 5 8 GB | Gemma 4 26B-A4B (MoE) | — | IQ4_NL | 12.48 GiB | ik_llama | **OOM** | **OOM** |
| Pi 5 8 GB | Gemma 4 **E2B** | 2.3 B eff | Q4_K_M | 2.88 GiB | llama.cpp | 31.86 | **5.97** |

([potato-os/core benchmark, 2026-04-04](https://github.com/potato-os/core/blob/main/docs/benchmarks/gemma4-pi-benchmark-2026-04-04.md))

At **essentially equal active-parameter counts (4.5 B effective vs 4.0 B active), the MoE is 27% slower on a Pi 5** — 2.54 vs 3.48 tok/s. And it OOMs outright on the 8 GB board.

**Caveats, stated plainly:** different quantization (IQ4_NL vs Q4_0 — and part 1 already established IQ-quants have a weaker ARM repack story), different runtime (ik_llama vs llama.cpp), and a 12.48 GiB file on a 16 GB board means significant page-cache pressure. This is not a clean experiment. But it points the same direction as the Jetson data, from a completely independent source, on the exact board in question, and the magnitude agrees (27% vs 31%).

### 2.5 Reason 4 (arithmetic): residency is the binding constraint

This is the one that actually eliminates most candidates before any of the above matters.

A MoE must hold **all** experts resident. There is no "only load the active ones" on llama.cpp CPU — expert selection changes every token, and paging from an SD card or SSD at 118 ns random-read latency would be catastrophic. So the constraint is: **total quantized file must fit inside `MemoryMax=4500M`, minus KV cache, minus compute buffers, minus llama-server overhead.** Call the realistic weight ceiling ~3.6 GB.

| Model | Total / active | Best Q4 size | Fits ≤3.6 GB? |
|---|---|---|---|
| OLMoE-1B-7B-0125-Instruct | 6.9 B / 1.3 B | Q4_0 **3.93 GB**, Q4_K_M 4.21 GB | **No** |
| Granite 4.0-h-tiny | 7 B / 1 B | Q4_K_M **4.23 GB** | **No** |
| LFM2.5-8B-A1B | 8.3 B / 1.5 B | Q4_0 **4.84 GB** | **No** |
| Phi-mini-MoE-instruct | 7.6 B / 2.4 B | Q4_0 **4.36 GB** | **No** |
| Gemma 4 26B-A4B | 26 B / 4 B | IQ4_NL 12.48 GB | **No** (measured OOM) |
| Qwen3.5-35B-A3B / Qwen3.6-35B-A3B | 35 B / 3 B | ~10 GB at 1-bit | **No** |
| **SmallThinker-4B-A0.6B-Instruct** | **4 B / 0.6 B** | **Q4_0 ~2.2 GB, Q4_K_M 2.63 GB** | **Yes** |

The pattern is not an accident. **A MoE's value proposition requires total ≫ active, and "total" is exactly what a 4.5 GB cgroup budgets.** The only way to build a MoE that fits is to make total small — at which point you have given back most of the capacity advantage that motivated the MoE in the first place. That is the central tension, and it is why the search space here is essentially one model wide.

### 2.6 Status of every candidate named in the brief

**OLMoE-1B-7B (Ai2).** Real, GGUF published by Ai2 themselves, Apache 2.0. The successor is `OLMoE-1B-7B-0125-Instruct` (Dolmino mid-training + Tülu 3 post-training, "35% better on average" than the 0924 release) — **but that is January 2025, and there is no 2026 successor.** Q4_0 is 3.93 GB / Q4_K_M 4.21 GB. It is the model the arXiv study measured at 31% slower than Llama-3.2-1B on a Jetson while sitting at the memory ceiling. **Out on size, age, and measured throughput.** ([allenai/OLMoE-1B-7B-0125-Instruct-GGUF](https://huggingface.co/allenai/OLMoE-1B-7B-0125-Instruct-GGUF), [Ai2 OLMoE repo](https://github.com/allenai/OLMoE))

**Qwen small MoE lineage.** Qwen1.5-MoE-A2.7B is 14.3 B total — never viable, and now three generations stale. The current lineup (Qwen3.5, Apache 2.0, 2 Mar 2026) is **0.8 B / 2 B / 4 B / 9 B / 27 B dense**, with MoE starting at **35B-A3B**. Qwen3.6-35B-A3B (April 2026) and Qwen3.8 (August 2026) continue that pattern; Qwen3.8's only new MoE is 2.4T-A95B under a bespoke Max licence. **Qwen has no small MoE and shows no sign of building one — they solve the small end with dense models.** ([Qwen 3.5–3.8 guide](https://codersera.com/blog/qwen-3-5-complete-guide-2026/), [Qwen3.6-35B-A3B](https://qwen.ai/blog?id=qwen3.6-35b-a3b))

**IBM Granite MoE.** Granite 4.0-h-tiny (7B-A1B, hybrid Mamba-2 + MoE, Apache 2.0) is the best-designed candidate on paper — IBM tunes explicitly for RAG and long-context summarization. **Q4_K_M is 4.23 GB: over budget.** More importantly, **Granite 4.1 (28 Apr 2026) and Granite 4.2 (25 Aug 2026) dropped the small MoE entirely** — both are dense 3 B / 8 B / 30 B. IBM has walked away from the 7B-A1B point. ([Granite 4.0 announcement](https://www.ibm.com/new/announcements/ibm-granite-4-0-hyper-efficient-high-performance-hybrid-models), [granite-4.0-h-tiny GGUF](https://huggingface.co/bartowski/ibm-granite_granite-4.0-h-tiny-GGUF), [Granite 4.2](https://explainx.ai/blog/ibm-granite-4-2-open-reasoning-models-august-2026))

**Llama-family small MoE.** None exists. Meta has shipped no small MoE; Llama 4's MoEs start at 109B-A17B. Llama 3.2 1B/3B remain dense and are now three generations old, under the Llama Community License with its use policy and naming obligations — a licence cost Apache-2.0 alternatives simply don't carry.

**Mistral-family small MoE.** Mixtral 8x7B (46.7B) and 8x22B are the only Mistral MoEs; both are an order of magnitude too large, and 8x7B is a 2023 model.

**DeepSeek.** The smallest DeepSeek MoE work (DeepSeek-V2-Lite, 16B-A2.4B) is ~9 GB at Q4 and pre-dates the current generation by a wide margin. Nothing in the V3/R1 line is remotely close to this size class.

**Liquid AI LFM2.5-8B-A1B.** The most interesting *architecture* found: hybrid convolution+attention MoE, 8.3 B total / 1.5 B active, explicitly designed for on-device, with Liquid's own claim that it is *"faster than models with a similar number of active parameters, like Qwen3-1.7B"* on a Snapdragon. **Two hard blockers.** (1) **Q4_0 is 4.84 GB** — comfortably over the cgroup ceiling; no smaller quant is published. (2) The **LFM Open License v1.0** is Apache-2.0-derived but caps free commercial use at **under $10 M annual revenue**; above that you must separately license from Liquid AI. For a hardware product that is a real, if distant, landmine, and it is exactly the class of restriction the brief asked me to flag. ([LFM2-8B-A1B blog](https://www.liquid.ai/blog/lfm2-8b-a1b-an-efficient-on-device-mixture-of-experts), [LFM2.5-8B-A1B-GGUF](https://huggingface.co/LiquidAI/LFM2.5-8B-A1B-GGUF), [LFM licence](https://www.liquid.ai/lfm-license))

**Microsoft Phi-mini-MoE-instruct.** 7.6 B total / 2.4 B active, MIT, distilled from Phi-3.5-MoE via SlimMoE. **Q4_0 is 4.36 GB / Q4_K_M 4.99 GB — over budget**, and its active-parameter count is *higher* than Gemma 4 E2B's effective count, so it would also be slower. Combined with part 1's finding that phi-4-mini scores 23.5% hallucination on Vectara — the worst small model measured — this is a clear no. ([Phi-mini-MoE-instruct-GGUF](https://huggingface.co/gabriellarson/Phi-mini-MoE-instruct-GGUF))

**Anything else September 2026?** I searched specifically for new sub-5B-total MoE releases in August–September 2026 and found none. The newest small-ish MoE release is K2-Horizon-MoVA-36B-A4B (MBZUAI, 3 Sep 2026, Apache 2.0) — 36 B total, an order of magnitude too large. **The sub-4 GB MoE niche is essentially unoccupied, and the labs that could occupy it (Qwen, IBM) have moved away from it.**

### 2.7 The one MoE that actually fits: SmallThinker-4B-A0.6B-Instruct

| | |
|---|---|
| Architecture | Fine-grained MoE, 32 experts, top-4, **4 B total / 0.6 B active**, 32 layers, 32K context |
| Extra sparsity | ReGLU sparse FFN — additional *activation* sparsity on top of expert routing |
| GGUF | Q4_0 ~2.2 GB, **Q4_K_M 2.63 GB**, IQ2_XXS 1.24 GB |
| Licence | **Apache 2.0** |
| llama.cpp | Supported — [PR #14898](https://github.com/ggml-org/llama.cpp/pull/14898) merged 28 Jul 2025, plus [PR #16782](https://github.com/ggml-org/llama.cpp/pull/16782) (embedding-output fix) Oct 2025 |
| Origin / date | IPADS + School of AI, SJTU; [arXiv:2507.20984](https://arxiv.org/abs/2507.20984), 28 July 2025 |

Benchmarks from the model card, all in **non-thinking mode** (it is not a reasoning model despite the name):

| Model | MMLU | GSM8K | HumanEval | Average |
|---|---|---|---|---|
| **SmallThinker-4B-A0.6B** | **66.11** | 80.02 | **82.32** | **61.75** |
| Qwen3-1.7B | 64.19 | 81.88 | 61.59 | 57.73 |
| Gemma-3n-E2B-it | 63.04 | 82.34 | 64.63 | 55.70 |
| Qwen3-0.6B | 43.31 | 62.85 | 31.71 | 41.67 |

And the throughput table from the paper (Table 5, Q4_0, model fully in RAM):

| Device | tok/s |
|---|---|
| i9-14900K | 108.17 |
| OnePlus 13 | 78.99 |
| RK3588 | 39.76 |
| **Raspberry Pi 5** | **28.77** |
| RK3576 | 15.10 |

**28.77 tok/s on a Raspberry Pi 5 — 4.8× the incumbent's 5.97.** If that number transferred, the throughput problem in part 1 would evaporate and the acceptance gate would pass with room to spare.

**It will not transfer in full, and the paper says so implicitly:** *"the document reports results only from their PowerInfer framework"* — no llama.cpp numbers are given. PowerInfer exploits (a) the ReGLU activation sparsity, which llama.cpp does not implement, and (b) a pre-attention router that prefetches expert weights while attention computes. Neither exists in llama.cpp.

**My honest llama.cpp estimate, labelled as an estimate:** per-token weight traffic ≈ 0.6 B active × ~0.56 B/param (Q4_0 with scales) ≈ 0.34 GB, plus attention/router/norms, call it **0.4–0.5 GB/token** against Gemma 4 E2B's ~1.29 GB. At the same measured 7.7 GB/s effective read rate that is **~15–19 tok/s**, minus the 25–35% MoE dispatch erosion the Jetson and Pi 5 data both show, minus the absence of any KleidiAI path (§2.2). **Landing estimate: 10–15 tok/s, i.e. 1.7×–2.5× the incumbent.** I would not bet money on the top of that range, but the bottom of it is still a real win.

**Why I am not recommending it anyway — see §5.3.**

---

## 3. Non-MoE alternatives, against this task shape

The task is: 250-token system prompt with six hard constraints (exact refusal string, `[n]` markers after each sentence that uses a passage, British English with 999/111/105, never invent doses or phone numbers, under 200 words, no diagnosis), three ≤400-token passages, ≤150-token question, ≤400-token answer at temperature 0.2. **The binding capability is instruction adherence under a constrained format, not knowledge.** The corpus supplies the knowledge; `ai.py` never lets the model answer from parametric memory.

That reframing matters, because it changes which benchmark is the right proxy. MMLU measures the capability this product deliberately does not use.

### 3.1 The best available proxy metric, and what it says

**Gemma 4 E2B scores 90.4% on IFEval** (Gemma 4 Technical Report, Table 5), against 94.6% for E4B and 98.9% for the 31 B. IFEval measures verifiable instruction-following — exactly "did it obey the format constraints". The report also confirms E2B is **2.3 B effective of 5 B total** via per-layer embeddings, under **Apache 2.0**. ([Gemma 4 Technical Report](https://arxiv.org/html/2607.02770v1))

I could not find an IFEval figure for SmallThinker, OLMoE, or any small MoE. **That is itself a finding: the small-MoE literature reports MMLU/GSM8K/HumanEval and not instruction-following or faithfulness.**

### 3.2 Vectara HHEM — confirming what is *not* on it

I re-pulled the Vectara leaderboard (last updated 11 May 2026). Within the ≤5 B band it lists `google/gemma-3-4b-it` at 6.4% hallucination and `qwen/qwen3-4b` at 5.7%. **It lists no Gemma 4 E2B, no OLMoE, no SmallThinker, no LFM, no small Granite, and no MoE under 26 B.** ([vectara/hallucination-leaderboard](https://github.com/vectara/hallucination-leaderboard))

So part 1's family-trend argument for Gemma 4 stands, and so does its caveat — but it is worth saying plainly that **every MoE candidate in this report has *zero* published grounded-QA or faithfulness evidence.** Swapping to one would be swapping a model with suggestive family evidence and a strong IFEval score for a model with none of either.

### 3.3 Dense candidates, verified current as of today

| Model | Status | Size @ Q4 | Licence | Verdict for this job |
|---|---|---|---|---|
| **Qwen3.5-2B** | Current (2 Mar 2026), Apache 2.0, dense, 256K ctx | ~1.3 GB | Apache 2.0 | Real candidate. But part 1's objection stands: the family scores worse on grounded summarization (qwen3.5-27b 12.1% vs gemma-4-31b 7.4%). **I also disagree with part 1's "roughly 2× the generation speed":** subtracting the `get_rows` embedding table, per-token traffic is ~0.95 GB vs Gemma's ~1.29 GB, so ~1.3×, not 2×. Smaller win than advertised, same quality cost. |
| **Qwen3.5-4B** | Current, dense, multimodal | ~2.5 GB | Apache 2.0 | 4 B fully-active dense → ~2.5 GB/token traffic → *slower* than the incumbent. Wrong direction. |
| **Granite 4.1-3B / 4.2-3B** | Current (Apr / Aug 2026), **dense** 3.4 B, 128K ctx | Q4_K_M **2.1 GB**, ~3.3 GB total RSS | Apache 2.0 | The most RAG-intentional vendor in the list — natively trained for RAG, tool use and JSON. But 3.4 B fully active ≈ 2.1 GB/token → **~3.7 tok/s estimated, worse than the incumbent**. Smaller on disk, slower per token: the PLE trick is why. ([Granite 4.1 3B sizes](https://localmodel.run/model/granite-4.1-3b)) |
| **Llama 3.2 1B / 3B** | Stale (three generations old) | 0.8 / 2.0 GB | Llama Community Licence | Use policy, redistribution and naming obligations on a box you sell. Not worth it when Apache-2.0 options exist. |
| **SmolLM3-3B** | **No SmolLM4 exists** as of today; SmolLM3 is 8 July 2025 | ~1.9 GB | Apache 2.0 | Fully-open and well documented, but a year stale and dense-3B-slow. No advantage over Granite 4.1-3B. ([SmolLM3-3B](https://huggingface.co/HuggingFaceTB/SmolLM3-3B)) |
| **Phi (current gen)** | Phi-4 family; Phi-4-reasoning-vision-15B (Mar 2026) is the newest release; **Phi-5 is unreleased** and the "specs" circulating are pre-release speculation | — | MIT | Part 1 already ruled this family out on 23.5% Vectara hallucination for phi-4-mini. Nothing has changed. ([Phi guide 2026](https://singularitymoments.com/microsoft-phi/)) |
| **LFM2.5-1.2B-Instruct** | Current, dense hybrid | ~0.9 GB | LFM Open License ($10 M cap) | Genuinely fast on Pi 5 — a sibling, LFM2.5-230M, is reported at 42 tok/s Q4_K_M. But 1.2 B is where citation discipline starts to break, and the licence carries the revenue cap. Keep as the named fallback in the spec's risk section. ([Pi 5 LFM2.5 post](https://runaihome.com/blog/raspberry-pi-5-local-ai-lfm25-2026/)) |

### 3.4 Models explicitly built for grounded, cited answering — the real find

The brief asked me to look for models targeted at RAG/citation behaviour rather than chat quality. There are two, and they are worth naming.

**IBM Granite RAG intrinsics.** IBM ships LoRA adapters for *exactly* this job: `granite-rag-3.0-8b-lora` generates output as a JSON object containing **output sentences, hallucination detections and citations**; there are separate `citation-generation`, `hallucination-detection` and `uncertainty-quantification` intrinsics. This is the most directly task-shaped open-weights work in existence. **It is 8 B only.** There is no 2 B or 3 B version, and 8 B at Q4 is ~4.9 GB — over budget and roughly 4× too slow on this board. ([Granite 3.3 RAG LoRAs](https://www.ibm.com/new/announcements/ibm-granite-3-3-speech-recognition-refined-reasoning-rag-loras), [LLM Intrinsics for RAG](https://arxiv.org/pdf/2504.11704))

**OCC-RAG-1.7B — the single most task-aligned model I found.** ([arXiv:2606.00683](https://arxiv.org/html/2606.00683v1), 30 May 2026; [occ-ai/OCC-RAG-1.7B](https://huggingface.co/occ-ai/OCC-RAG-1.7B); [official GGUFs](https://huggingface.co/occ-ai/OCC-RAG-1.7B-GGUF))

- Mid-trained from Qwen3-1.7B-Base on 3.25 M synthetic multi-context QA examples with citation-anchored reasoning traces.
- Purpose-built to **(a) answer only from supplied sources, (b) cite them, (c) decide ANSWERABLE/UNANSWERABLE and abstain.** That is `ai.py`'s three core behaviours, as a training objective.
- **ConFiQA faithfulness 81.4** vs Qwen3-1.7B's 64.8 — a 17-point gain over its own base model on the exact axis this product cares about. **MuSiQue-Un refusal accuracy 87.2.**
- Authors publish GGUFs: **Q4_K_M 1.11 GB**, Q4_0 1.05 GB, Q8_0 1.83 GB. ~29K downloads last month.

**Why it is nonetheless not a drop-in, and I think not the right pick today:**

1. **Output format is structurally incompatible.** It always emits five sections — `<|query_analysis_start|>`, source analysis, `<|reasoning_start|>`, ANSWERABLE/UNANSWERABLE status, then `<|answer_start|>…<|answer_end|>`. `answer_events()` streams deltas straight to the browser; the user would watch a reasoning trace scroll past before any answer appeared. With `ANSWER_MAX_TOKENS = 400`, the trace could plausibly consume the whole budget and truncate the answer.
2. **The latency maths is the killer.** At ~7 tok/s (1.11 GB/token traffic), 250 tokens of trace before the first answer token is **~35 s added on top of the existing ~50 s TTFT**. On a kiosk that people walk up to in an emergency, that is worse than the incumbent, not better — even though the model itself is faster per token.
3. **`CitationFilter` would emit zero citations.** It parses `[n]`; OCC-RAG cites as `<|source_id|>N` inside the source-analysis block. `grounded` would be permanently `False` and the citations UI would go dark.
4. **The system prompt would be out-of-distribution.** It is mid-trained on a fixed schema; the SOS system prompt (exact refusal string, British English, 999/111/105, medical disclaimer) is nothing like its training format and would likely be ignored.
5. **Licence is ambiguous.** The paper says CC BY 4.0; the model cards say MIT. Both are redistributable, but that needs resolving before shipping.

**Verdict on OCC-RAG: the most interesting model in this report, and the one I would revisit first if the answer pipeline is ever rebuilt.** Adopting it is not a model swap — it is a rewrite of `build_messages()`, `CitationFilter`, the SSE contract and the refusal path, in exchange for a model whose reasoning trace makes the box feel slower. Wrong trade today. Worth writing into the spec as a named future option.

---

## 4. State-space and hybrid architectures

**Real answer, not a hedge: mature enough to load, not mature enough to bet a product on, and architecturally wrong for this specific task even if it were.**

### 4.1 llama.cpp maturity — better than expected, still moving

Support is genuinely there. Mamba-2 and hybrids (Granite 4.0-h, Falcon-H1, Nemotron-H) load and run; RWKV-7 has been supported since [PR #12412](https://github.com/ggml-org/llama.cpp/pull/12412) (March 2025) with GGUFs across the size range.

But the commit log says the implementation is still being fixed, *this quarter*:

| Date | Item |
|---|---|
| 2026-08-26 | [#27775](https://github.com/ggml-org/llama.cpp/pull/27775) opencl: perf optimization for mamba2 `ssm_scan` (**open**) |
| 2026-08-21 | [#27513](https://github.com/ggml-org/llama.cpp/pull/27513) mamba2: flatten in/out projections to dispatch GEMM instead of GEMV |
| 2026-08-20 | [#27464](https://github.com/ggml-org/llama.cpp/issues/27464) Perf: CUDA Mamba2 batched decode dispatches GEMV instead of GEMM |
| 2026-05-15 | [#23082](https://github.com/ggml-org/llama.cpp/pull/23082) mamba2: remove hardcoded 2× expansion factor |
| 2026-03-10 / 03-09 | [#20335](https://github.com/ggml-org/llama.cpp/pull/20335), [#20270](https://github.com/ggml-org/llama.cpp/pull/20270) fix assert in mamba2 graph |
| 2026-01-06 | [#18631](https://github.com/ggml-org/llama.cpp/issues/18631) long-context GPU utilization spikes on Mamba2 hybrids (Granite 4-h Small, Nemotron 30B) |

A subsystem still receiving graph-assert fixes in March and dispatch-strategy rewrites in August is not where a kiosk that must boot unattended should be. Community assessment is consistent: Mamba-2 is *"fully functional in llama.cpp on CPU, although it's not using the faster quadratic prompt processing made possible by the state space duality"* ([llama.cpp discussion #9196](https://github.com/ggml-org/llama.cpp/discussions/9196)).

That last clause matters specifically here. **This workload is prefill-heavy** — a ~1500-token prompt against a 400-token answer. An SSM path that does not use the fast SSD prefill route is being penalised exactly where SOS spends most of its wall-clock time.

### 4.2 The architectural objection, which is the stronger one

Even with perfect kernels, a constant-state recurrent model is the wrong shape for this task.

`ai.py` hands the model three verbatim passages and demands answers drawn from them, with per-sentence attribution back to the specific passage. That is **in-context copying and retrieval**. Transformers can attend to the exact token; an SSM must have compressed those 1200 tokens into a fixed-size state before generation begins.

This is not speculation — it is a proved separation. [*"Repeat After Me: Transformers are Better than State Space Models at Copying"*](https://arxiv.org/abs/2402.01032) (Jelassi et al.) shows theoretically that a two-layer transformer can copy strings of exponential length while generalised state-space models are *"fundamentally limited by their fixed-size latent state"*, and shows empirically that pretrained transformers *"dramatically outperform state space models at copying and retrieving information from context."*

For a general chat assistant this is a minor cost. For a product whose entire safety story is *"it only says what the retrieved passage says, and it tells you which one"*, it is the wrong failure mode to buy.

### 4.3 Specific candidates

- **RWKV-7 "G1" 2.9B** — genuinely competitive (matches Qwen2.5-3B on English averages, 71.5 vs 71.4, on 3× fewer tokens), llama.cpp+GGUF ready, zero KV cache. But the G1 line *"incorporated deep thinking abilities"* — a reasoning model, which part 1 already established (via Vectara) performs *worse* on grounded summarization. Plus §4.2. ([rwkv7-1.5B-g1-GGUF](https://huggingface.co/Mungert/rwkv7-1.5B-g1-GGUF), [RWKV llama.cpp wiki](https://wiki.rwkv.com/inference/llamacpp.html))
- **Granite 4.0-h-tiny** — the hybrid + MoE combination is the most thoughtfully designed candidate in this report, and IBM targets RAG explicitly. Killed on size (4.23 GB at Q4_K_M) before anything else, and IBM discontinued it in 4.1/4.2.
- **Falcon-H1 / Jamba / Nemotron-H** — all either far above the size budget or carrying the same immaturity plus §4.2.

**Verdict: no. Revisit in twelve months if the Mamba-2 CPU path stabilises *and* someone ships a hybrid under 3.5 GB with published faithfulness numbers.** Right now that is zero models.

---

## 5. Comparative verdict

### 5.1 The table

Throughput figures are marked **M** (measured on Pi-5-class ARM under llama.cpp), **M\*** (measured but under a different runtime or board), or **E** (my estimate from per-token weight traffic at the 7.7 GB/s effective rate established in §1.2, discounted for MoE overhead where applicable). Estimates are soft — treat ±30%.

| Model | Arch | Total | Active/effective | Recommended quant & size | Licence | Pi 5 tok/s | Fits 4.5 GB? | Grounded-QA suitability |
|---|---|---|---|---|---|---|---|---|
| **Gemma 4 E2B** *(incumbent)* | Dense + per-layer embeddings (sparse gather) | 5.1 B | 2.3 B eff | QAT **Q4_0 3.12 GiB** (or Q4_K_M 2.89 GiB) | **Apache 2.0** | **5.97 M** | Yes, ~3.5 GB RSS | **Best evidenced.** IFEval 90.4. Family tops Vectara's open pack. Thinking off by default. Only format that gets KleidiAI + repack. MTP drafter available. |
| **SmallThinker-4B-A0.6B-Instruct** | **MoE** 32 experts top-4 + ReGLU sparse FFN | 4 B | **0.6 B** | **Q4_0 ~2.2 GB** | **Apache 2.0** | 28.77 **M\*** (PowerInfer) → **10–15 E** (llama.cpp) | **Yes, comfortably** | **Unknown — no faithfulness, IFEval or citation data exists.** Strong MMLU/HumanEval, which is the wrong proxy. 0.6 B active is a thin budget for a 250-token constrained system prompt. No KleidiAI path (§2.2). July 2025. |
| **OCC-RAG-1.7B** | Dense (Qwen3-1.7B-Base, RAG mid-trained) | 1.7 B | 1.7 B | **Q4_K_M 1.11 GB** | MIT (card) / CC BY 4.0 (paper) — **resolve** | ~7 **E** per token, but **net worse** end-to-end | Yes, easily | **Best-targeted by a mile** — ConFiQA 81.4 (vs 64.8 base), refusal 87.2. But always emits a 5-section reasoning trace in a bespoke token schema; breaks `CitationFilter`, the SSE contract and the latency budget. |
| **OLMoE-1B-7B-0125-Instruct** | MoE 64 experts top-8 | 6.9 B | 1.3 B | Q4_0 **3.93 GB** | Apache 2.0 | 22.9 on Jetson vs 33.4 for Llama-3.2-1B **M\*** → **~5–7 E** on Pi 5 | **No** — 3.93 GB + KV + overhead breaches `MemoryMax` | No faithfulness data. Jan 2025, no successor. The model the arXiv study used to show MoE erosion. |
| **Granite 4.1-3B** | Dense | 3.4 B | 3.4 B | Q4_K_M **2.1 GB** (~3.3 GB RSS) | Apache 2.0 | **~3.7 E** | Yes | Vendor is the most RAG-intentional in the list, and the real RAG intrinsics are Granite — but only at 8 B. At 3 B it is simply slower than the incumbent for no measured grounding gain. |
| **Granite 4.0-h-tiny** | **Hybrid Mamba-2 + MoE** | 7 B | 1 B | Q4_K_M **4.23 GB** | Apache 2.0 | — | **No** | Best-designed on paper; over budget, discontinued in 4.1/4.2, and §4.2 applies. |
| **LFM2.5-8B-A1B** | Hybrid conv+attn **MoE** | 8.3 B | 1.5 B | Q4_0 **4.84 GB** | **LFM Open License — $10 M revenue cap** | — | **No** | Over budget and licence-encumbered. Otherwise the most interesting on-device MoE shipping. |
| **Qwen3.5-2B** | Dense | 2 B | 2 B | ~1.3 GB | Apache 2.0 | **~8 E** (not 2×, see §3.3) | Yes | Family scores worse on grounded summarization. Smaller speed win than part 1 assumed. |

### 5.2 Reading the table

Three clean groups:

- **Over budget:** OLMoE, Granite 4.0-h-tiny, LFM2.5-8B-A1B, Phi-mini-MoE, Gemma 4 26B-A4B. Every one of them is a MoE, and they are over budget *because* they are MoEs — total-≫-active is the point of the architecture and total is what the cgroup counts.
- **Fits but slower or no better:** Granite 4.1-3B, Qwen3.5-4B, SmolLM3, Llama 3.2. Dense models with fully-active parameter counts at or above 2.3 B pay more bandwidth per token than the incumbent does.
- **Fits and genuinely interesting:** SmallThinker-4B-A0.6B (speed) and OCC-RAG-1.7B (task fit). Exactly two models, and neither is a straightforward win.

### 5.3 Why I am not recommending SmallThinker, despite the speed case

I came close. It fits, it is Apache 2.0, it is supported in llama.cpp, and 10–15 tok/s would resolve the throughput gate outright. Against that:

1. **Zero grounded-QA evidence.** Not weak evidence — *none*. No IFEval, no faithfulness benchmark, no Vectara entry, no citation evaluation. Its own card reports MMLU, GSM8K and HumanEval: general knowledge and code generation, the two capabilities this product deliberately does not use. Meanwhile Gemma 4 E2B has a published IFEval of 90.4 and a family that tops Vectara's open pack.
2. **0.6 B active parameters is very little to follow six simultaneous constraints.** The system prompt demands an exact refusal string, `[n]` placement per sentence, British English with three specific phone numbers, a prohibition on inventing doses, a word limit, and a conditional medical clause. Instruction adherence is the first thing to degrade as active capacity falls, and it degrades *silently* — the box would keep answering, just without citations that `CitationFilter` recognises.
3. **The headline number is from a different inference engine.** 28.77 tok/s is PowerInfer exploiting ReGLU activation sparsity and pre-attention expert prefetch — neither implemented in llama.cpp. The honest llama.cpp figure is unmeasured.
4. **It forfeits every optimisation part 1 identified.** No KleidiAI path for its experts (§2.2, source-verified). No QAT checkpoint. No MTP drafter. `ngram-mod` speculative decoding would still work, so that one survives.
5. **It is 14 months old** — roughly two generations, in a field where Gemma 4 landed in April 2026.
6. **Thin llama.cpp support.** Two commits total, one of them a bug fix for a broken output tensor ([#16782](https://github.com/ggml-org/llama.cpp/pull/16782)). An arch with that little traffic is an arch where the next regression may go unnoticed for months.

That is a lot of unquantified risk to take on for a speed problem that part 1 already offers two cheaper fixes for: `--spec-type ngram-mod` (free, and this workload — answer strictly from three passages sitting in context — is close to its best case) and honestly re-setting the gate to ≥5 tok/s.

### 5.4 The strongest argument for the incumbent, stated properly

**Gemma 4 E2B is not a naive dense pick. It is already a sparse model, and its sparsity mechanism is better suited to this hardware than MoE routing is.**

I verified the mechanism in llama.cpp's own source (`src/models/gemma3n.cpp`, the architecture Gemma 4's E-variants inherit):

```cpp
per_layer_tok_embd = create_tensor(tn(LLM_TENSOR_PER_LAYER_TOKEN_EMBD, "weight"),
                                   {n_embd_altup * n_layer, n_vocab}, 0);
...
inp_per_layer = ggml_get_rows(ctx0, model.per_layer_tok_embd, inp->tokens);
```

That tensor is 256 × 35 × 262,144 ≈ **2.35 billion parameters — roughly 46% of the model** — and it is read with `ggml_get_rows`: **8,960 values per token**, not 2.35 B. That is why 5.1 B stored behaves like 2.3 B streamed.

This is precisely the property the objection wants from an MoE: *more total capacity at the per-token cost of a smaller model.* Gemma 4 E2B already has it. And it gets it through a mechanism that is strictly better on this stack than expert routing:

| | MoE expert routing | Gemma 4 PLE gather |
|---|---|---|
| ggml op | `GGML_OP_MUL_MAT_ID` (3-D) | `GGML_OP_GET_ROWS` |
| KleidiAI accelerated? | **No** — absent from `kleidiai.cpp` entirely | **Yes** — explicitly in `supports_op` |
| Generic ARM repack? | Yes | n/a (gather, not matmul) |
| Memory access pattern | Scattered across *k* of *N* expert blocks, re-selected every token | One contiguous row per token |
| Measured penalty on edge ARM | 25–35% (§2.3, §2.4) | None observed |
| Requires all capacity resident? | Yes | Yes — but the capacity is embeddings, which are cheap per byte |

The pick was not flippant. Whether or not it was arrived at deliberately, **it landed on the one architecture in this size class that delivers the MoE benefit through the one sparsity primitive that llama.cpp's ARM path actually accelerates.**

---

## 6. Final recommendation

**Keep Gemma 4 E2B. Migration is not warranted. Apply part 1's tuning changes instead.**

**Model:** `google/gemma-4-E2B-it`
**Quantization:** Google's QAT **`gemma-4-E2B_q4_0-it.gguf`** (3.12 GiB) if it fits RSS, else current Q4_K_M (2.89 GiB) — per part 1 §4.5, decided by measurement, not theory. The KleidiAI finding in §2.2 *strengthens* part 1's case for Q4_0 here: `MUL_MAT` on 2-D dense tensors is the only shape KleidiAI accepts, and Gemma 4 E2B is entirely that shape.

**Why not to migrate, in one line each:**

- **MoE, in general** — the architecture's benefit is gated on total ≫ active, and "total" is exactly what a 4,500 MB cgroup budgets; every sub-4 GB MoE is therefore a small MoE, which gives back the capacity advantage that motivated it.
- **MoE, on this toolchain** — KleidiAI implements no `MUL_MAT_ID` path, so no MoE can use the single biggest ARM optimisation available on this box (source-verified, §2.2).
- **MoE, on this hardware** — measured 25–35% erosion of the active-parameter advantage on edge ARM, from two independent sources, one of them on a Pi 5 (§2.3, §2.4).
- **OLMoE / Granite-h-tiny / LFM2.5-8B-A1B / Phi-mini-MoE** — 3.93 / 4.23 / 4.84 / 4.36 GB at Q4. Over budget before the KV cache exists.
- **SSM and hybrids** — llama.cpp's Mamba-2 CPU path was still taking dispatch-strategy rewrites three weeks ago, and transformers are provably better at the in-context copying this product is built on (§4).
- **Dense alternatives** — Qwen3.5 trades grounding quality for a ~1.3× speed gain (not part 1's 2×); Granite 4.1-3B and Qwen3.5-4B are *slower* per token than the incumbent; Phi is disqualified on hallucination; Llama 3.2 carries licence friction and is three generations stale.
- **OCC-RAG-1.7B** — the best-targeted model found, and I would revisit it first, but adopting it means rewriting the prompt builder, the citation filter and the SSE contract to gain a model whose mandatory reasoning trace adds ~35 s before the first answer token.

**Two things I would actually do, in priority order:**

1. **Run the SmallThinker bench before closing this out.** It is a two-hour experiment and it is the only way to convert my 10–15 tok/s estimate into a fact:
   ```
   llama-bench -m SmallThinker-4B-A0.6B-Instruct-Q4_0.gguf -p 512 -n 128 -t 4 -ngl 0
   llama-bench -m gemma-4-E2B_q4_0-it.gguf                 -p 512 -n 128 -t 4 -ngl 0
   ```
   Then — and this is the part that decides it — run `sos eval` against both with the **real** system prompt and check three things the benchmarks cannot: does it emit `[1]`/`[2]`/`[3]` where `CitationFilter` expects them; does it return the exact string `The library doesn't cover this.` on zero-relevance queries; does it hold British English and the 999/111/105 conventions. **If SmallThinker clears 12 tok/s *and* matches Gemma on all three, revisit this recommendation. If it fails any of the three, the speed is irrelevant.**

2. **Record OCC-RAG-1.7B in the spec's risk/futures section**, with the specific blocker written down (output schema and streaming contract, not capability), so that if `ai.py` is ever restructured the option is not rediscovered from scratch.

**Not recommended, explicitly:** migrating to any MoE, any SSM/hybrid, Qwen3.5, Granite, Llama 3.2, Phi, or OCC-RAG on current evidence.

---

## 7. Where the evidence is thin — stated plainly

I would rather flag these than have them found later.

1. **No published llama.cpp throughput exists for SmallThinker-4B-A0.6B on any device.** The 28.77 tok/s Pi 5 figure is PowerInfer with two optimisations llama.cpp lacks. My 10–15 tok/s is arithmetic, not measurement.
2. **No MoE in this size class has *any* published grounded-QA, faithfulness, citation or refusal evaluation.** Not weak evidence — absent. Every quality comparison in §5.1 involving a MoE is therefore an inference from general benchmarks, which the brief correctly identifies as a weak proxy.
3. **Gemma 4 E2B is itself not on Vectara**, as part 1 already conceded. Its IFEval 90.4 is the strongest direct evidence in this report for the incumbent, and IFEval is a proxy for format-following, not for faithfulness.
4. **The arXiv MoE study tested no Raspberry Pi and no ARM SBC** — Apple M2 Pro and Jetson Orin Nano only. Its authors say so. I have treated it as directional.
5. **The Pi 5 Gemma 26B-A4B-vs-E4B comparison in §2.4 is not controlled** — different quant (IQ4_NL vs Q4_0), different runtime (ik_llama vs llama.cpp), and severe page-cache pressure at 12.48 GiB on a 16 GB board. It agrees with the Jetson data in direction and magnitude, which is why I weight it, but it is not a clean experiment.
6. **OCC-RAG's licence is contradictory** — CC BY 4.0 in the paper, MIT on both model cards. Resolve before any use.
7. **My per-token traffic estimates assume the embedding tables are `get_rows`-gathered and not streamed.** I verified this for Gemma (source, §5.4). For Qwen3.5-2B and Granite 4.1-3B I assumed it by analogy. That is the main source of error in the E-marked throughput column.
8. **This environment's llama.cpp version numbering (v0.3.0 / v0.4.1) and Gemma 4's April 2026 release both post-date my training data.** The source excerpts in §2.2 and §5.4 are read from `ggml-org/llama.cpp` master as of today and are reliable; version-pin claims are inherited from part 1 and were not independently re-verified here.

---

## Sources

**Hardware and bandwidth**
[Raspberry Pi 5 benchmarking (official)](https://www.raspberrypi.com/news/benchmarking-raspberry-pi-5/) · [tinymembench on Pi 5 — geerlingguy/sbc-reviews #21](https://github.com/geerlingguy/sbc-reviews/issues/21) · [Highly Optimized Kernels for LLM Inference on Arm CPUs (arXiv:2501.00032)](https://arxiv.org/pdf/2501.00032) · [llama.cpp #25976 — Arm decode at 55–60% of bandwidth](https://github.com/ggml-org/llama.cpp/issues/25976) · [llama.cpp #25977 — Arm prefill GEMM flat](https://github.com/ggml-org/llama.cpp/issues/25977)

**MoE on edge hardware**
[Does MoE Actually Help Inference on Consumer and Edge Hardware? (arXiv:2606.21428v3, 9 Jul 2026)](https://arxiv.org/abs/2606.21428) · [potato-os/core Pi 5 Gemma 4 benchmark (2026-04-04)](https://github.com/potato-os/core/blob/main/docs/benchmarks/gemma4-pi-benchmark-2026-04-04.md)

**llama.cpp source, read directly on master (2026-09-16)**
`ggml/src/ggml-cpu/kleidiai/kleidiai.cpp` (`supports_op`, `work_size` — no `MUL_MAT_ID`) · `ggml/src/ggml-cpu/repack.cpp` (`MUL_MAT_ID` 3-D path, `ggml_repack_get_optimal_repack_type`) · `src/models/gemma3n.cpp` (`per_layer_tok_embd`, `ggml_get_rows`) · [PR #14898 SmallThinker support](https://github.com/ggml-org/llama.cpp/pull/14898) · [PR #16782 SmallThinker embedding fix](https://github.com/ggml-org/llama.cpp/pull/16782) · [PR #27513 mamba2 GEMM dispatch](https://github.com/ggml-org/llama.cpp/pull/27513) · [#27464](https://github.com/ggml-org/llama.cpp/issues/27464) · [#18631 Mamba2 hybrid long-context](https://github.com/ggml-org/llama.cpp/issues/18631) · [PR #12412 RWKV-7](https://github.com/ggml-org/llama.cpp/pull/12412) · [Discussion #9196 Mamba2 in llama.cpp](https://github.com/ggml-org/llama.cpp/discussions/9196)

**MoE candidates**
[allenai/OLMoE-1B-7B-0125-Instruct-GGUF](https://huggingface.co/allenai/OLMoE-1B-7B-0125-Instruct-GGUF) · [Ai2 OLMoE](https://github.com/allenai/OLMoE) · [SmallThinker paper (arXiv:2507.20984)](https://arxiv.org/html/2507.20984v1) · [PowerInfer/SmallThinker-4BA0.6B-Instruct](https://huggingface.co/PowerInfer/SmallThinker-4BA0.6B-Instruct) · [SmallThinker GGUF](https://huggingface.co/gabriellarson/SmallThinker-4BA0.6B-Instruct-GGUF) · [LFM2-8B-A1B blog](https://www.liquid.ai/blog/lfm2-8b-a1b-an-efficient-on-device-mixture-of-experts) · [LFM2.5-8B-A1B-GGUF](https://huggingface.co/LiquidAI/LFM2.5-8B-A1B-GGUF) · [LFM licence](https://www.liquid.ai/lfm-license) · [Phi-mini-MoE-instruct-GGUF](https://huggingface.co/gabriellarson/Phi-mini-MoE-instruct-GGUF) · [Granite 4.0 announcement](https://www.ibm.com/new/announcements/ibm-granite-4-0-hyper-efficient-high-performance-hybrid-models) · [granite-4.0-h-tiny GGUF](https://huggingface.co/bartowski/ibm-granite_granite-4.0-h-tiny-GGUF) · [Qwen3.6-35B-A3B](https://qwen.ai/blog?id=qwen3.6-35b-a3b) · [Qwen 3.5–3.8 lineup guide](https://codersera.com/blog/qwen-3-5-complete-guide-2026/)

**Dense and RAG-specific candidates**
[Gemma 4 Technical Report (arXiv:2607.02770)](https://arxiv.org/html/2607.02770v1) · [OCC-RAG paper (arXiv:2606.00683)](https://arxiv.org/html/2606.00683v1) · [occ-ai/OCC-RAG-1.7B](https://huggingface.co/occ-ai/OCC-RAG-1.7B) · [occ-ai/OCC-RAG-1.7B-GGUF](https://huggingface.co/occ-ai/OCC-RAG-1.7B-GGUF) · [Granite 3.3 RAG LoRAs](https://www.ibm.com/new/announcements/ibm-granite-3-3-speech-recognition-refined-reasoning-rag-loras) · [A Library of LLM Intrinsics for RAG (arXiv:2504.11704)](https://arxiv.org/pdf/2504.11704) · [Granite 4.1 3B sizes](https://localmodel.run/model/granite-4.1-3b) · [Granite 4.2](https://explainx.ai/blog/ibm-granite-4-2-open-reasoning-models-august-2026) · [HuggingFaceTB/SmolLM3-3B](https://huggingface.co/HuggingFaceTB/SmolLM3-3B) · [Phi family status 2026](https://singularitymoments.com/microsoft-phi/) · [LFM2.5 on Pi 5](https://runaihome.com/blog/raspberry-pi-5-local-ai-lfm25-2026/)

**Evaluation and architecture theory**
[Vectara hallucination leaderboard (updated 2026-05-11)](https://github.com/vectara/hallucination-leaderboard) · [Repeat After Me: Transformers are Better than State Space Models at Copying (arXiv:2402.01032)](https://arxiv.org/abs/2402.01032) · [FACTS Grounding leaderboard (arXiv:2501.03200)](https://arxiv.org/abs/2501.03200) · [rwkv7-1.5B-g1-GGUF](https://huggingface.co/Mungert/rwkv7-1.5B-g1-GGUF) · [RWKV llama.cpp wiki](https://wiki.rwkv.com/inference/llamacpp.html)
