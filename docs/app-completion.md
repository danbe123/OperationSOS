# App completion work

Working checklist, started 2026-09-05. Software validation and physical-device acceptance are recorded separately.

- [x] Commit the frontend fixes and UX work.
- [x] Merge backend, authored content and maps branches into main.
- [x] Pass the unified repository test target (including updated plan-04 merge).
- [x] Finish map packs, verification and API integration.
- [ ] Build and validate real map outputs, install available maps in the running app.
- [x] Switch the development stack to the unified checkout, preserving its database and notes.
- [ ] Audit full-library sizes, sources and citation availability; download what fits.
- [ ] Implement AI retrieval, inference, lifecycle, citations and evaluation.
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
