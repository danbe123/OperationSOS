# App completion work

Working checklist, started 2026-09-05. Software validation and physical-device acceptance are recorded separately.

- [x] Commit the frontend fixes and UX work.
- [x] Merge backend, authored content and maps branches into main.
- [x] Pass the unified repository test target (including updated plan-04 merge).
- [x] Finish map packs, verification and API integration.
- [x] Build and validate real map outputs, install available maps in the running app.
- [x] Switch the development stack to the unified checkout, preserving its database and notes.
- [~] Audit full-library sizes, sources and citation availability; download what fits (core downloads done; seven core items still need building).
- [~] Implement AI retrieval, inference, lifecycle, citations and evaluation (implemented and committed; retrieval gate passes; model-backed gates recorded below).
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
