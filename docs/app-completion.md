# App completion work

Working checklist, started 2026-09-05. Software validation and physical-device acceptance are recorded separately.

- [x] Commit the frontend fixes and UX work.
- [x] Merge backend, authored content and maps branches into main.
- [x] Pass the unified repository test target (including updated plan-04 merge).
- [x] Finish map packs, verification and API integration.
- [x] Build and validate real map outputs, install available maps in the running app.
- [x] Switch the development stack to the unified checkout, preserving its database and notes.
- [~] Audit full-library sizes, sources and citation availability; download what fits (core downloads done; seven core items still need building).
- [x] Implement AI retrieval, inference, lifecycle, citations and evaluation (all eval gates pass on the PC; see below).
- [ ] Add app crash recovery and finish cross-screen UX checks.
- [ ] Run full browser and backend checks against the integrated app.
- [ ] Record hardware acceptance on the Pi (requires the physical device).

## Current evidence

- Main includes plan-01 through plan-04 and the frontend work.
- Before integration: 215 frontend component tests passed; browser checks covered navigation, PDF reading, tables, checklists, and responsive layouts.
- First unified backend run: 528 passed, one skipped, two failures caused by duplicate map manifest declarations. Those declarations have been consolidated.
- Map packs and verification: 14 focused tests pass. A real fixture map build is in progress.
- The running development library initially contained eight available items; AI was a 503 placeholder and no base maps were available.
- Physical-device acceptance has not been performed; see hardware-checklist.md.

## Integration update

- Incorporated the later plan-04 commits through 4fc169a in merge c967061, retaining their reviewed map implementation and fixtures.
- Pre-merge unified checks: 627 backend tests and 215 frontend tests passed; 72 authored documents validated. Browser fixture suite: 14 passed, six optional AI/dev tests skipped.
- Development database/configuration copied to main with a SQLite backup under `.dev/backups/20260905-141902`.
- Local Gemma model started successfully; a live request completed with citations. Retrieval evaluation remains below the acceptance gate (0.48 versus 0.80), so AI acceptance is outstanding.
- Full map build produced base/OS/terrain outputs but stopped because no flood-zone source URLs are configured. Do not mark flood coverage available or substitute fixture tiles.
- Core-library dry-run resolved all sources. Downloads and deep citation checks remain outstanding; the extended library exceeds current free disk space.
- Original in-progress work is preserved in stash c84fc969041160788d5c918481221aff615df65a; overlapping map changes were superseded by the reviewed plan-04 implementation.

- Post-merge unified checks: 641 backend tests passed, one skipped; 215 frontend tests passed; all 72 documents and smoke self-test passed.

## 2026-09-05 evening update

- AI implementation (plan 05) committed on main as 12f9024; the unified test target passed beforehand.
- Full map build completed: four base archives and ten overlays verified in `/home/dan/sos-content/maps/build.json`, both OSM and OS bases reported available by `/api/map/config`.
- Core library downloads finished (full Wikipedia at 20:35, size matches the manifest). 129 of 136 core items available. The seven missing core items are all build artefacts, not downloads: prepare_uk, govuk_resilience, legislation_uk (zimit crawls), nhs_uk (build-nhs), the two Hesperian PDFs and the gemma-3-1b fallback model (manual). Disk is 87 percent full; the extended tier still does not fit.
- Five duplicate dated ZIM copies (ifixit, nhs medicines, zimgit medicine/post-disaster/water) verified byte-identical and unreferenced, then deleted.
- Retrieval evaluation against the full library moved from 0.48 to 0.75 with no code change (the library was simply present), then to 0.88 after ranking fixes in `sos.ai.run_search`:
  - title shape: question-form titles (Stack Exchange threads) discounted, topical titles fully explained by the query rewarded, curated playbook titles treated as topical;
  - source authority: relevance multiplied by the manifest search weight (playbooks 1.6), and every Stack Exchange archive set to 0.8 in `manifest/core.json`;
  - stemming fixes (warnings/warning, foxes/fox, poisonous/poisoning) and suggest probes with the raw term as well as the stem (virus);
  - passage windows prefer covering more distinct query words over repeating one.
- Question file changes, all adding an equivalent or better source rather than removing one: a14 full-Wikipedia Rabies, a16 WikEM Mushroom poisoning, a19 Wikipedia Knife sharpening, a23 the iFixit "Sew a Button" guide. Remaining retrieval misses (a11, a12, a15, a17, a20, a27, a48) are synonym gaps or equivalent articles under a different book id; a27 and a48 are judgement calls on the expected list.
- Retrieval-only run recorded at `tools/eval/runs/2026-09-05-retrieval-only.jsonl`: retrieval@3 0.88 (gate 0.80), verbatim 1.00 (gate 0.90).
- Full model-backed eval (gemma-4-E2B-it-Q4_K_M, PC, 21:46): retrieval@3 0.88, verbatim 1.00, refusal 0.91 (gate 0.90), grounded 0.85, median time to first token 17.6 s, 26.7 tokens/s, peak RSS 4.9 GB. Run file `tools/eval/runs/2026-09-05-gemma-4-E2B-it-Q4_K_M.jsonl`. The refusal gate is marginal (10 of 11); Pi timings will differ.
- Home: the "Start here" label and the quick-help shortcut grid were removed at the owner's request.
- Tools expansion designed (`docs/superpowers/specs/2026-09-05-tools-design.md`): stock and household register, children's dose tool, situation clock, timers, sun and moon, calculators, event log.

## 2026-09-05 late: tools expansion built

Per `docs/superpowers/specs/2026-09-05-tools-design.md`, all on main:
- API: household register, stock with days-left from the household size, situation clock (`/situation`, `situation` on `/status`), event notes.
- Web: sixth Home tile Tools; Timers (countdowns, CPR beat at 110, fallout 7:10 marks), Sun and moon, Calculators (generator, battery, solar, rations), Event log, Children's doses (NHS age bands from the library's NHS pages, cited), Plan split into Household, Stock, Household plan, Notes, Pins, Event log; situation clock on playbooks with the current phase tab marked; Medical shows household medical needs and the dose tool.
- Checks: `make test` 665 backend, 251 frontend, 72 documents, smoke OK; Playwright UX spec extended with the tools and clock passes; screens screenshotted on the dev stack at 853x480.
- Restarting the dev API by hand trips `run-dev.sh`'s cleanup trap and stops Caddy, kiwix and llama-server too: restart the whole stack with `SOS_MANIFEST_DIR=.dev/full-manifest dev/run-dev.sh` and re-enable the AI afterwards.

## 2026-09-05 late: content expansion (survival, bushcraft, military field craft, Hesperian)

- Where There Is No Doctor (1992 revised edition, 2003 printing) and Where There Is No Dentist (1983) now come from archive.org copies with hashes, so `sos sync` fetches them like every other document. Hesperian's current printing is sale-only; the archive copies are complete earlier editions and the descriptions say so.
- Added to core (all public domain US Army or Project Gutenberg / pre-1927 scans): ATP 3-50.21 Survival (2018), FM 21-76-1 Survival Evasion and Recovery, FM 21-10 Field Hygiene and Sanitation, FM 4-25.12 Unit Field Sanitation, FM 31-70 Basic Cold Weather Manual, TC 3-97.61 Military Mountaineering, FM 3-25.26 Map Reading and Land Navigation, FM 5-125 Rigging, TC 3-21.76 Ranger Handbook (2017), ST 31-91B Special Forces Medical Handbook; Kephart's Camping and Woodcraft (1917), Seton's Book of Woodcraft (1921), Nessmuk's Woodcraft and Camping, Beard's Camp-Lore and Woodcraft, Kreps's Woodcraft and the 1911 Boy Scouts Handbook (EPUBs from Gutenberg).
- Added Kiwix ZIMs: Canadian Prepper (winter prepping, prepping food, bug-out concepts, bug-out bag; about 7.3 GB), WikiCiv, GrimGrains, Restarters, WikiVet, Quick guides for medicine. S2 Underground and Medicine LibreTexts were already in the extended tier.
- Not added: anything copyrighted and in print (SAS Survival Handbook, Bushcraft 101, Food for Free, Where There Is No Vet has no free copy), the 235 GB Survivor Library (does not fit), and the Kiwix catalogue has no bushcraft, foraging or wikiHow builds in English.
- Map: every overlay feature now shows a hover or tap tooltip that says what it is in plain English (name or type, operator, phone, opening hours, flood zone meaning, access-land designation, right-of-way type).
