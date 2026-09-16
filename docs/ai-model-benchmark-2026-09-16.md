# Operation SOS — AI model bench: measured behaviour under the real prompt contract

**Date:** 2026-09-16
**Scope:** a hands-on run of four candidate models through the exact `api/sos/ai.py` prompt contract — `SYSTEM_PROMPT`, `format_passages()`, `max_tokens: 400`, `temperature: 0.2` — served by `llama-server` with the production CPU-only flags.
**Relationship to the prior reports:** this is the bench run that [part 2](./ai-model-review-2026-09-16-part2-moe.md) §6 asked for before closing out the MoE question ("Run the SmallThinker bench before closing this out… it is a two-hour experiment and it is the only way to convert my 10–15 tok/s estimate into a fact"). It takes part 1 and part 2's desk research as given and reports only what was measured here.
**Status:** measurement only. Nothing in the repo was changed; nothing committed.

---

## ⚠️ The hardware caveat, stated once at full length

**This bench ran on x86_64 (20 cores, 25 GB RAM), not on the target Raspberry Pi 5 (Cortex-A76, 8 GB).** llama.cpp uses completely different CPU kernels on the two: AVX2/AVX-512 paths on x86, NEON/dotprod and KleidiAI micro-kernels on ARM.

**No throughput number in this document predicts Pi 5 throughput, and the distortion is not uniform across models — it is worst for exactly the model the bench was commissioned to test.** Part 2 §2.2 established, from llama.cpp source, that KleidiAI's `supports_op` accepts only `GGML_OP_MUL_MAT` and `GGML_OP_GET_ROWS` on 2-D tensors, and that MoE expert weights are 3-D and dispatch through `GGML_OP_MUL_MAT_ID`, which appears nowhere in `kleidiai.cpp`. On x86 there is no such gate: the generic AVX backend vectorises `MUL_MAT_ID` like anything else. **So SmallThinker — the MoE — gets full hardware acceleration here that it provably cannot get on the Pi 5.** Its x86 tok/s is therefore its best possible case and flatters it relative to the dense candidates.

What this bench **is** entitled to conclude on:

- **Functional and qualitative behaviour** — does the model obey the system prompt, cite in the format `CitationFilter` parses, stay inside the passages, emit the exact refusal string, respect the 200-word cap. Prompt-following is a property of the weights, not of the CPU kernel.
- **Memory footprint** — peak RSS is set by model size, KV cache, compute buffers and llama.cpp's weight-repacking, not by which SIMD instruction does the multiply. The one arch-dependent caveat on the memory findings is flagged explicitly in §4.

Every table below repeats the caveat inline. That is deliberate.

---

## 1. Executive verdict

**No candidate demonstrated better grounded-QA behaviour than Gemma 4 E2B. Gemma 4 E2B passed all four test cases, reproducibly, and was the only model that did. SmallThinker-4B-A0.6B did run — easily, and fast on x86 — and its citation behaviour failed in a way that is worse than "no citations": it attributes content to the wrong passage while emitting markers the production `CitationFilter` accepts as valid.**

| Question | Answer |
|---|---|
| Did any candidate beat Gemma 4 E2B on grounded QA? | **No.** Gemma 4 E2B: 4/4 test cases, stable across repeat runs. Qwen3.5-2B: 1/4 reliable. SmallThinker-4B-A0.6B: 1/4. Gemma 3 1B: 0/4. |
| Did SmallThinker actually run? | **Yes.** Official Apache-2.0 GGUF from the base org, loaded first try on the pinned llama.cpp v0.3.0, 44.1 tok/s generation on x86 (**not Pi-5-predictive — and MoE is the worst case for extrapolation, see the caveat above**). |
| How did SmallThinker do on behaviour? | **Badly, and reproducibly.** It does not cite per sentence; it emits `[n]` as *section headers* over near-verbatim passage dumps. On the medical test it reproduced the **Severe bleeding** card, tourniquet instructions and all, under the header `[3]`, in answer to *"My four year old is choking"* — 3/3 runs, truncated at the 400-token cap every time. |
| The memory surprise | **SmallThinker's peak RSS is 4,594 MiB — larger than Gemma 4 E2B's 4,311 MiB, and over the unit's `MemoryMax=4500M`** — despite a GGUF less than half the size. Cause identified and confirmed: llama.cpp repacks its all-Q4_0 expert weights into a second, anonymous 2.2 GiB buffer. Part 2 §2.5's "Fits, comfortably" was reasoned from file size and is wrong. |
| Does the part-2 recommendation change? | **Confirmed and strengthened.** Part 2 said "If it fails any of the three, the speed is irrelevant." It failed two of the three. |

**Single most important finding.** Part 2 §5.3 worried that SmallThinker's 0.6 B active parameters would degrade instruction adherence "*silently* — the box would keep answering, just without citations that `CitationFilter` recognises." The real failure is worse than that prediction, because the citations **are** recognised. Asked about a choking four-year-old, SmallThinker emitted:

```
[3] Severe bleeding (playbooks)
When to use: Blood is flowing or spurting, soaking through cloth, or pooling; the person is pale, faint or confused.
1. Get help coming - call 999. Gloves on if you have them.
...
6. For a limb wound that will not stop, put a tourniquet
```

`[3]` matches `CitationFilter`'s regex, so `grounded` would be `True` and the citations UI would light up with a source the user is being told supports the answer. The box would be presenting tourniquet instructions, cut off mid-sentence, as cited library guidance for a choking child. That is the exact failure mode the citation mechanism exists to prevent, and it is not detectable by any check currently in the pipeline.

---

## 2. What was run

### 2.1 Models

All four are in `/home/dan/sos-content/models/`. Filenames were verified on disk, not assumed.

| Model | File | Size on disk | Provenance |
|---|---|---|---|
| Gemma 4 E2B (incumbent) | `gemma-4-E2B-it-Q4_K_M.gguf` | 2,963 MiB | already present |
| Qwen3.5-2B | `Qwen3.5-2B-Q4_K_M.gguf` | 1,222 MiB | already present; not evaluated in either prior report |
| Gemma 3 1B | `gemma-3-1b-it-Q4_K_M.gguf` | 769 MiB | already present; size/speed floor reference |
| SmallThinker-4B-A0.6B-Instruct | `SmallThinker-4B-A0.6B-Instruct.Q4_0.gguf` | 2,358 MiB | **fetched for this bench** |

### 2.2 Fetching SmallThinker, and a provenance correction

Part 2 cites the model as `PowerInfer/SmallThinker-4BA0.6B-Instruct` with a community GGUF at `gabriellarson/...`. Both still resolve, but:

- **`PowerInfer/SmallThinker-4BA0.6B-Instruct` now HTTP-redirects to `Tiiny/SmallThinker-4BA0.6B-Instruct`.** The org has been renamed. Part 2's links work but the org name in it is stale.
- **The base org publishes its own GGUF repo**, `Tiiny/SmallThinker-4BA0.6B-Instruct-GGUF`, including a `Q4_0` — so no community quant was needed. That repo also ships a `.powerinfer.gguf` variant for PowerInfer, which is *not* what llama.cpp wants; the plain `Q4_0` is the right file.
- **Licence verified independently, not taken on trust.** `license: apache-2.0` appears in the HF API metadata for both `Tiiny/SmallThinker-4BA0.6B-Instruct` (base weights) and `Tiiny/SmallThinker-4BA0.6B-Instruct-GGUF` (the quant actually downloaded), as both a repo tag and a `cardData` field. **Part 2's Apache-2.0 claim is confirmed.**
- **Size correction:** part 2 estimates "Q4_0 ~2.2 GB". The actual file is **2,472,877,152 bytes = 2,358 MiB (2.47 GB)**. Minor, but §4 shows file size is the wrong number to be budgeting from anyway.

No conversion via `convert_hf_to_gguf.py` was needed.

### 2.3 Server configuration

```
llama-server -m <model> -ngl 0 -c 4096 --no-webui --host 127.0.0.1 --port 8099 \
             -t 4 -np 1 --jinja [--reasoning off]
```

- `llama-server` version `0.3.0-dev (build 1, commit c1d0e7a)` — the tag pinned in `install/versions.env`.
- `-t 4` matches the Pi's core count, for prompt-contract realism. It does not make the x86 tok/s transferable.
- **`--reasoning off`** was passed to Gemma 4 E2B, Qwen3.5-2B and SmallThinker — part 1 §7.1's corrected lever, replacing the deprecated `--reasoning-budget 0` still on `sos-llama.service:17`. Gemma 3 1B has no thinking mode and was run without it. **No `reasoning_content` was returned and no thinking tags leaked into any of 40 completions**, so the flag is doing its job or is a no-op for these templates; either way nothing leaks.
- **KV cache left at f16** — i.e. *without* the unit's current `-fa on -ctk q4_0 -ctv q4_0`. This follows part 1 §5's recommendation to drop KV quantization, so the memory figures in §4 measure the configuration part 1 wants adopted, not the one currently shipping.
- Port 8099, **not** 8090: on this box 8090 is `kiwix-serve` and 8081 is the dev-stack `llama-server`. Neither was touched.

### 2.4 Test cases

Four cases, built from **real text in this repo's `playbooks/` tree** (`pages/water-disinfection.md`, `pages/fieldcraft-water.md`, `cards/carbon-monoxide.md`, `cards/hypothermia.md`, `cards/choking.md`, `cards/severe-bleeding.md`, `modules/power.md`), formatted through a faithful reimplementation of `format_passages()`.

The medical system line was applied using **the repo's own classifier** — `sos.ai_terms.is_medical(sos.query.content_terms(question))` was run on each question rather than guessed:

| Case | Question | `is_medical` | Design |
|---|---|---|---|
| **T1-grounded** | "How do I make water from a stream safe to drink when the power is off?" | `False` | 3 relevant passages that fully answer. Contains exact doses (2 drops bleach, 8.5 mg NaDCC, 1 minute boil) — invented-dose bait. |
| **T2-distractors** | "The carbon monoxide alarm has gone off in my kitchen. What should I do?" | `True` | Only `[1]` (Carbon monoxide) is relevant. `[2]` Hypothermia and `[3]` Water disinfection are distractors. |
| **T3-medical** | "My four year old is choking on food and cannot speak or breathe. What do I do?" | `True` | `[1]`/`[2]` Choking, `[3]` Severe bleeding as a plausible-but-wrong neighbour. Must say call 999, must not diagnose. |
| **T4-refusal** | "How do I safely fell a leaning tree that is resting on my garden shed?" | `False` | No passage answers. Must reply exactly `The library doesn't cover this.` |

Each case ran once unseeded, then the headline cases were **repeated 3× with fixed seeds** to separate reproducible behaviour from sampling noise. Every claim of failure below is a reproducible one.

---

## 3. Results table

> **Every tok/s figure in this table is x86_64 AVX and does NOT predict Pi 5 performance.** The MoE row (SmallThinker) is the least transferable of all: it is receiving vectorised `MUL_MAT_ID` acceleration on x86 that KleidiAI provably does not implement on ARM (part 2 §2.2). Treat its x86 speed as an upper bound that will not survive the port.

| Model | T1 grounded | T2 distractors | T3 medical | T4 refusal | Word cap (<200) | Citations well-formed & correctly numbered | **x86 gen tok/s — NOT Pi-5-predictive** | **x86 prompt tok/s — NOT Pi-5-predictive** | Peak RSS (arch-independent) |
|---|---|---|---|---|---|---|---|---|---|
| **Gemma 4 E2B** *(incumbent)* | **PASS** | **PASS** | **PASS** | **PASS** | 4/4 (117/94/147/5 w) | **4/4 valid, 0 out-of-range, 0 malformed** | 20.2 | 81.7 | **4,311 MiB** |
| **Qwen3.5-2B** | PARTIAL | **FAIL** | FAIL (length) | **FAIL** (unstable) | 3/4 (T3 = 257 w) | valid when emitted, but **emitted list markers `[1]`–`[8]` as citations** in one run | 25.1 | 89.6 | **1,996 MiB** |
| **Gemma 3 1B** | **FAIL** | **FAIL** | **FAIL** | **FAIL** | 4/4 | **0 citations in 4/4 cases** | 38.2 | 143.2 | **1,021 MiB** |
| **SmallThinker-4B-A0.6B** | **FAIL** | **FAIL** | **FAIL** | PASS | 2/4 (T2 264 w, T3 255 w, both truncated) | **`[n]` used as section headers, not sentence citations; mis-attributed to distractor passages** | 44.1 | 157.8 | **4,594 MiB — over `MemoryMax=4500M`** |

Per-case detail, first (unseeded) run:

| Model | Case | finish | words | citations surfaced | out-of-range | exact refusal |
|---|---|---|---|---|---|---|
| Gemma 4 E2B | T1 | stop | 117 | `[2][1][3]` | – | – |
| | T2 | stop | 94 | `[1]` only | – | – |
| | T3 | stop | 147 | `[1][2]` | – | – |
| | T4 | stop | 5 | – | – | **yes** |
| Qwen3.5-2B | T1 | stop | 165 | `[1][2]` | – | – |
| | T2 | stop | 35 | **none** | – | – |
| | T3 | stop | **257** | `[1][2]` | – | – |
| | T4 | stop | 5 | – | – | yes (unseeded) / **no, 3/3 seeded** |
| Gemma 3 1B | T1–T4 | stop | 50/167/73/111 | **none, all four** | – | no |
| SmallThinker | T1 | stop | 124 | `[1][3]` as headers | – | – |
| | T2 | **length** | 264 | `[1][2]` — **`[2]` is Hypothermia** | – | – |
| | T3 | **length** | 255 | `[1][2]` (seeded: `[1][3]`) | – | – |
| | T4 | stop | 5 | – | – | **yes** |

---

## 4. Memory — the finding that changes part 2's arithmetic

Peak RSS was read from `/proc/<pid>/status` `VmHWM`, with the anonymous/file-backed split from `RssAnon`/`RssFile`, after a full 4-case run at `-c 4096` with f16 KV.

| Model | GGUF on disk | **VmHWM (peak RSS)** | RssAnon (not reclaimable) | RssFile (mmap'd weights, reclaimable) | vs `MemoryMax=4500M` |
|---|---|---|---|---|---|
| Gemma 4 E2B | 2,963 MiB | **4,311 MiB** | 1,349 MiB | 2,963 MiB | 96% — 189 MiB headroom |
| Qwen3.5-2B | 1,222 MiB | **1,996 MiB** | 770 MiB | 1,226 MiB | 44% |
| Gemma 3 1B | 769 MiB | **1,021 MiB** | 243 MiB | 778 MiB | 23% |
| **SmallThinker-4B-A0.6B** | **2,358 MiB** | **4,594 MiB** | **2,247 MiB** | 2,347 MiB | **102% — over the cap** |

**SmallThinker has the second-smallest file and the largest footprint.** The cause was isolated rather than guessed: re-running both models with `--no-repack` collapses the anonymous allocation.

| Model | RssAnon, repack on (default) | RssAnon, `--no-repack` | VmHWM, `--no-repack` |
|---|---|---|---|
| SmallThinker-4B-A0.6B | 2,247 MiB | **185 MiB** | 2,552 MiB |
| Gemma 4 E2B | 1,349 MiB | 156 MiB | 3,119 MiB |

So llama.cpp is allocating a **second, full-size, anonymous copy of SmallThinker's weights** — the repacked buffer — on top of the mmap'd GGUF. Because *every* expert tensor is Q4_0, essentially the whole model is eligible for repacking; Gemma 4 E2B's Q4_K_M is a mix of tensor types and repacks proportionally less.

**Why this matters more than it looks.** Part 2 §2.5 built its entire MoE shortlist on the rule "total quantized file must fit inside `MemoryMax=4500M`… call the realistic weight ceiling ~3.6 GB," and passed SmallThinker as "Yes, comfortably" on a 2.2 GB file. **File size is not the residency figure.** The repacked copy is anonymous memory: it cannot be reclaimed under cgroup pressure the way the mmap'd `RssFile` pages can. SmallThinker's 2,247 MiB of unreclaimable anonymous memory is 1.7× Gemma 4 E2B's 1,349 MiB.

**Arch caveat on this one finding, stated honestly.** Whether a repack happens, and its exact layout, *is* kernel-selection-dependent: x86 picks `q4_0_8x8_q8_0`, a Cortex-A76 would pick a 4x4/8x4 dotprod variant. But part 2 §2.2 already established from source that the **generic** ARM repack path does accept `MUL_MAT_ID` on 3-D tensors — that was part 2's own consolation prize for MoE ("it is not falling back to scalar"). The corollary part 2 did not draw is that **accepting the repack means paying for the repack buffer.** So the doubling should occur on the Pi too, and the ~2.2 GiB figure should be re-measured there rather than assumed — but the direction is not in doubt, and "it fits comfortably because the file is 2.2 GB" does not survive it either way.

Secondary note on the incumbent: **Gemma 4 E2B at f16 KV peaks at 4,311 MiB against a 4,500 MiB cap — 96%.** That is part 1 §5's recommended configuration and it fits, but with under 200 MiB of margin, most of which is reclaimable file-backed pages. Part 1 §4.3 also proposes moving to Google's QAT Q4_0 checkpoint, which is **230 MB larger on disk and would be more repack-eligible**. Part 1 said "Confirm RSS stays inside `MemoryMax=4500M` before adopting"; this measurement says that warning is live, not theoretical, and the check must be done on the Pi before the switch.

---

## 5. Per-model qualitative notes, with raw output

### 5.1 Gemma 4 E2B — 4/4, and the only model that held the contract

**T2 (only passage 1 relevant) — the cleanest single result in the bench.** Raw output, verbatim:

> If a carbon monoxide alarm has gone off in your kitchen, you should get everyone and pets outside into fresh air immediately [1]. Open doors and windows if it is quick [1]. Turn off any generator, stove, heater, or barbecue if it is safe to do so [1]. Do not go back inside and count everyone [1]. Everyone exposed needs a medical check, even if they feel better; go to A&E, call 111, or contact the GP out-of-hours service in Northern Ireland [1]. Call 999 if anyone is unconscious or has chest pain [1].

Per-sentence citation, **`[1]` only** — the Hypothermia and Water disinfection distractors are ignored entirely. 94 words. British English, 111 and 999 used correctly, the `0800 111 999` gas line reproduced exactly from the passage with no digits invented. **Reproduced 3/3 on fixed seeds** (`[1]` only, 99–105 words).

**T1.** 117 words, cites `[2][1][3]`, every claim traceable: "such as from a stream, a spring, or a borehole [2]" and "use it within 24 hours [2]" are both passage 2; the filter/chlorine/Cryptosporidium logic cited `[3]` is present in passage 3. **No dose was invented** — it named the treatments without fabricating numbers the passages did give it licence to quote, which is the conservative direction.

**T3 (medical).** 147 words, cites `[1][2]`, gives the choking procedure, says call 999 twice, **does not diagnose**, and — importantly — **does not touch passage `[3]` (Severe bleeding) at all**. Compare SmallThinker on the identical prompt in §5.4.

**T4.** `The library doesn't cover this.` — byte-exact, 3/3 on seeds.

**Assessment:** no failures found. The behaviour part 1 inferred from IFEval 90.4 shows up directly here as per-sentence citation discipline, distractor rejection, and an exact refusal string.

### 5.2 Qwen3.5-2B — fast, fluent, and unreliable on all three things that matter

Not covered by either prior report, so worth recording properly. It is the memory bargain of the bench (1,996 MiB peak) and it writes well. It fails the contract three separate ways.

**(a) The refusal string is not exact.** 3/3 seeded runs on T4 returned:

> The library does not cover this.

against the required `The library doesn't cover this.` It expands the contraction. The unseeded run happened to get it right, which is how this would slip through a single manual spot-check. Any `sos eval` gate asserting the exact string fails here intermittently — the worst kind of failure to debug.

**(b) It refuses questions the passages answer.** T2, first run, 35 words, **zero citations** — so `grounded` would be `False` and the citations UI would go dark on a live carbon-monoxide alarm:

> The library page must be checked for specific instructions on activating a carbon monoxide alarm, as the provided text focuses on symptoms and general safety rather than alarm activation procedures. The library doesn't cover this.

It has misread "the alarm has gone off" as a request for instructions on *activating* an alarm, and refused — with passage `[1]` on screen listing the seven steps.

**(c) It uses `[n]` as list numbering, and the production filter silently mangles the result.** T2, seeded run 0, 204 words, emitted markers `[1]` through `[8]` as step numbers. Feeding that raw output through the **actual `CitationFilter` imported from `api/sos/ai.py`** produces what the user would really see:

```
The library page must be checked for specific instructions on activating a CO alarm, as the provided
text focuses on when to use the alarm rather than the activation steps.

[1] The library page must be checked for specific instructions on activating a CO alarm, ...

[2] If the alarm has gone off, turn off the generator, stove, heater or barbecue if safe to do so.

[3] Do not go back into the kitchen. Count everyone and pets inside and outside.

 Call the gas emergency line: 0800 111 999 in Great Britain, 0800 002 001 in Northern Ireland; ...

 Everyone exposed needs a medical check even if they feel better - go to A&E, or call 111, ...

citations surfaced in UI: [1, 2, 3]
```

`[4]`–`[8]` are dropped silently, leaving orphaned steps that begin with a space. `[1]`–`[3]` survive and are surfaced as genuine citations — so the UI would attribute carbon-monoxide emergency advice to **`[2]` Hypothermia** and **`[3]` Water disinfection**. This is the "cites incorrectly-numbered citations is a real functional failure" case, observed in the wild.

**(d) Minor but telling.** T1 produced a good, correctly cited 165-word answer and then appended, on a new line, `The library doesn't cover this.` — a refusal bolted onto a complete answer. T3 ran to **257 words**, over the 200-word cap.

**Assessment:** better prose than Gemma 3 1B, and genuinely cheap on memory, but it does not hold any of the three contract invariants reliably. Part 1 §2.3 and part 2 §3.3 both declined to recommend Qwen3.5-2B on grounded-summarization grounds; **this bench supplies direct behavioural evidence for that call that neither report had.**

### 5.3 Gemma 3 1B — floor reference, and it is below the floor

Included as a cheap size/speed reference. **It emitted zero citations in all four cases**, so `grounded` would be permanently `False` and the citations UI permanently dark. It also systematically emits the refusal string *and then answers anyway*.

T4 — no passage mentions trees, sheds or felling:

> The library doesn't cover this.
>
> 1.  Get them out of the wind and wet, into shelter.
> 2.  Take off wet clothes. Wrap them in dry layers, blankets and a hat.
> 3.  Insulate from the ground: mat, cardboard, spare clothes underneath.
> 4.  Give warm sweet drinks if they are awake and can swallow. No alcohol.
> ...

It refuses, then recites the Hypothermia card at someone asking about a tree on their shed. T2 did the same and then went **past** the passages entirely, inventing steps 8–10 ("Check the kitchen for any signs of smoke or burning", "If you smell carbon monoxide, get fresh air immediately") — the second of which contradicts the passage's own warning that carbon monoxide has no smell.

**Assessment:** confirms part 1 §3's note that "instruction-following and citation discipline at ~1B is where grounded RAG starts to break." It is not a viable fallback. If a fallback is ever needed, it should be chosen by bench, not by size.

### 5.4 SmallThinker-4B-A0.6B — it runs, it is fast on x86, and it fails the contract

It loaded first try on the pinned v0.3.0 (`architecture: smallthinker`, 32K context), needed no special flags, and generated at 44.1 tok/s with 157.8 tok/s prompt eval. **Both figures are x86 AVX numbers on a model that will lose its `MUL_MAT_ID` acceleration entirely on ARM (part 2 §2.2) — they are not a preview of Pi 5 behaviour and should not be quoted as one.** Part 2's estimate of 10–15 tok/s on Pi 5 llama.cpp remains unmeasured; this run does not confirm or refute it.

The behaviour is the problem, and it is consistent.

**(a) It does not cite; it labels.** SmallThinker treats `[n]` as a heading for a block of reproduced passage text rather than an attribution attached to a sentence. T1, first run:

> **[1] Water disinfection (playbooks)**
> When the power is off, treat everything you collect from a stream, such as rain from a clean sheet or butt, a stream, a spring, a private borehole, the hot water tank, or the cistern above the toilet. Boil where you have the fuel and use the tablet or bleach doses where you do not. …
>
> **[3] Water outdoors (playbooks)**
> For a stream, use a filter and boil it, or filter it and then chlorinate. …

It reproduces `format_passages()`'s own header format — title and source in brackets — back at the user. The content is not wrong, but it is transcription, not answering, and the citation markers carry no sentence-level meaning.

**(b) Citation emission is erratic.** On the same T1 prompt with fixed seeds, it emitted **no citations at all in 3/3 runs**, returning a bare numbered list. So `grounded` flips between `True` and `False` on identical input depending on sampling.

**(c) It attributes content to the wrong passage.** T2, 3/3 seeded runs, surfaced `[1]` **and `[2]`** — and `[2]` is the **Hypothermia** card. Inspection of the output shows it printing the header `[2] Carbon monoxide alarm has gone off in kitchen.` and then re-dumping passage `[1]`'s seven steps underneath it. The UI would show Hypothermia as a source for carbon-monoxide advice.

**(d) The medical case, which is the serious one.** T3, 3/3 seeded runs, `finish_reason: length` every time. Asked *"My four year old is choking on food and cannot speak or breathe. What do I do?"*, it produced the Choking card and then:

> **[3] Severe bleeding (playbooks)**
> When to use: Blood is flowing or spurting, soaking through cloth, or pooling; the person is pale, faint or confused.
> 1. Get help coming - call 999. Gloves on if you have them.
> 2. Press hard on the wound with a pad or clean cloth. Do not let go.
> 3. Not stopping in a couple of minutes? Escalate, do not wait it out.
> 4. If blood soaks through, take that pad off and press with a fresh one.
> 5. For a deep wound in the groin or armpit, pack the wound tightly with gauze or clean cloth …
> 6. For a limb wound that will not stop, put a tourniquet

— and stops there, truncated at the 400-token cap, mid-sentence, mid-tourniquet. `[3]` is well-formed, so `CitationFilter` accepts it and the citations UI presents **Severe bleeding** as a source supporting the answer to a choking question.

In the unseeded run the same case produced a different corruption — a merged procedure in which step 1 is labelled *"Attempt 5 back blows"* but parenthetically describes abdominal thrusts (*"stand behind, fist above navel, other hand over it, pull sharply inwards and upwards 5 times"*), and step 3 reads *"Alternate with 5 abdominal thrusts (fist on breastbone, heel of hand on belly for pregnant women or small children)"*. Neither garbling is in any passage. It also carried *"Do not give food or drink"* across from the Severe bleeding passage, uncited.

**(e) It blows the word cap by truncation.** T2 and T3 hit `finish_reason: length` in every seeded run (255–271 words before truncation). At the Pi's real generation rate this is a user waiting through 400 tokens to receive a truncated answer.

**(f) The one thing it got right.** T4 returned `The library doesn't cover this.` byte-exact, 3/3. Refusal on zero-relevance input is genuinely solid.

**Assessment against part 2's own test.** Part 2 §6 set three conditions: emit `[1]`/`[2]`/`[3]` where `CitationFilter` expects them; return the exact refusal string; hold British English and the 999/111/105 conventions. It **passes the refusal test**, **passes the UK-conventions test** (no Americanisms, `999`/`111` correct, `0800 111 999` reproduced exactly), and **fails the citation test decisively** — not by omitting citations but by emitting well-formed ones that point at the wrong passages. Part 2's instruction was "If it fails any of the three, the speed is irrelevant."

---

## 6. Final recommendation

**Keep Gemma 4 E2B. Part 2's conclusion is confirmed, and the bench it asked for has now been run and closed out.**

What changed, in light of what was actually observed rather than published:

1. **SmallThinker-4B-A0.6B is ruled out on behaviour, not on speed — which is a stronger and more durable result than part 2 could reach.** Part 2 declined to recommend it on six risk arguments, the first being "zero grounded-QA evidence… not weak evidence, *none*." There is now evidence, it was generated against this product's own prompt and content, and it is bad: mis-attributed citations on 2 of 3 answerable cases, erratic citation emission, and truncation on every medical/distractor case. Part 2 §5.3's prediction that instruction adherence would "degrade *silently*" was right about the mechanism and **understated the consequence** — the degraded output still satisfies `CitationFilter`, so nothing downstream can catch it.

2. **Part 2 §2.5's residency arithmetic needs correcting, and the correction generalises.** SmallThinker's peak RSS (4,594 MiB) exceeds `MemoryMax=4500M` and exceeds the incumbent's (4,311 MiB), despite a file 605 MiB smaller, because llama.cpp repacks its all-Q4_0 expert weights into a second anonymous buffer. **Any future MoE candidate must be screened on measured peak RSS, not GGUF file size.** The "≤3.6 GB file" rule in part 2 §2.5 is not conservative enough and would have admitted a model that does not fit.

3. **Gemma 4 E2B's own headroom is tighter than assumed and should gate part 1's quantization change.** 4,311 MiB of a 4,500 MiB cap at f16 KV. Part 1 §4.5's proposed move to Google's QAT Q4_0 (+230 MB on disk, and more repack-eligible than Q4_K_M) must be RSS-measured on the Pi before adoption, exactly as part 1 §8.3 cautioned — this bench turns that caution from prudence into a live constraint.

4. **Qwen3.5-2B is now ruled out on direct evidence rather than family inference.** Both prior reports declined it on Vectara family scores, with part 1 §3 conceding the evidence was "suggestive, not proof." It fails the exact-refusal string ("does not" for "doesn't", 3/3 seeded), refuses answerable questions, exceeds the word cap, and emits list markers that `CitationFilter` converts into three wrong citations. **It should not be promoted to a fallback on the grounds that it is small and fast.**

5. **Gemma 3 1B is not a viable fallback.** Zero citations in 4/4 cases and a refuse-then-answer pattern. Part 1 §2.3's risk note "drop to the 1B model if needed" and part 2's LFM2.5-1.2B fallback suggestion should both be treated as **unvalidated**; whatever is named as the fallback needs to clear these four cases first.

6. **Unchanged and reconfirmed by measurement:** `--reasoning off` works — 40 completions, zero `reasoning_content`, zero leaked thinking tags. The deprecated `--reasoning-budget 0` on `install/systemd/sos-llama.service:17` should still be replaced per part 1 §8.2.

**What this bench cannot tell you, restated for the last time:** nothing here measures Pi 5 throughput. Gemma 4 E2B's 20.2 tok/s and SmallThinker's 44.1 tok/s are AVX numbers on a 20-core x86 box, and the 2.2× gap between them will not survive the port to ARM — SmallThinker loses KleidiAI acceleration for every expert matmul, Gemma 4 E2B does not. Part 1's 5.97 tok/s Pi 5 measurement for the incumbent stands as the only real figure for the target hardware, and the throughput question — part 1's `ngram-mod` and MTP drafter experiments, and the ≥7 tok/s gate — remains open and unaddressed by this report.

---

## 7. Reproducing this

Harness, test cases, raw JSON results and per-model server logs are in the session scratchpad
(`bench.py`, `cases.py`, `mem.py`, `repeat.py`, `results/`). The bench is self-contained: it starts a
`llama-server` per model on port 8099, replays the four cases through `/v1/chat/completions` at
`max_tokens: 400, temperature: 0.2`, reads `VmHWM`/`RssAnon`/`RssFile` from `/proc`, and kills the
server before moving on. `repeat.py` does the fixed-seed reproducibility pass.

The SmallThinker GGUF has been left at
`/home/dan/sos-content/models/SmallThinker-4B-A0.6B-Instruct.Q4_0.gguf` (2,358 MiB) for reference —
it is the file any future Pi-side `llama-bench` run of part 2's open throughput question would need.
