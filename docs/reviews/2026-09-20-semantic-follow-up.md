# Semantic-search follow-up review — 20 September 2026

Reviewed the five fixes `aea2d15`, `c47b8c6`, `791acf4`, `a403bc1`, and `68f4596`, then completed the outstanding Wikipedia and acceptance checks. Follow-up fixes are committed as `2cdceb8`. All pruning experiments used temporary test directories; the live generations were not rebuilt, pruned or renamed.

## Findings fixed

1. **Generation recognition was not exact.** Python's `$` regex anchor accepts a final newline. A directory named `docs.gen-<32 hex digits>\n` was wrongly treated as a generation and deleted. A failing regression reproduced this; recognition now uses `fullmatch`.
2. **Cleanup could fail after successful publication.** A looping `*.current` symlink raised from `Path.resolve()` outside the cleanup handler. Pruning now logs and returns without deleting anything if current pointers cannot be resolved. A failing regression reproduced the loop case.
3. **Concurrent publication could delete unfinished output.** One publisher could create a generation and pause before making it current; another could classify that directory as old and prune it. Publication and its pruning now hold a shared folder-level advisory lock. A controlled two-publisher test pauses the first before moving its part, verifies the second waits, and confirms both generations survive. This serializes publication, not whole builds: same-collection builds still share staging filenames and must not run concurrently.
4. **Metadata could come from the next generation.** The loaders resolved the vector directory, then `_read_meta` independently resolved `*.current` again. A publication between those reads paired old vectors with new metadata and could reject a valid Wikipedia store on count mismatch. Loaders now pass their resolved directory to the metadata reader, and the fallback accepts only a legacy regular file, not a symlink following a newer current generation. Controlled publication-during-load regressions cover all three loaders.

Additional destructive-path regression: a generation-shaped directory symlink is ignored, and a nested symlink inside a deleted old generation does not delete its external target. Existing tests cover both naming schemes, retention of current/previous generations, other collections and generations borrowed by another collection's current pointer.

## Acceptance and limits

- Full published Wikipedia build verified: 8,425,865 keys, 7,243,109 usable vectors. The build completed on 19 September at 20:47:17 UTC.
- Eight controlled real-data rerank comparisons: 60 scored Wikipedia candidates preserved, no meaning-only Wikipedia rows; two queries changed order. This establishes mechanics, not a broad relevance-quality claim.
- Seven live API searches: 511 rows, 42 meaning rows, no duplicate URLs and no excluded-source meaning rows. The controlled comparison used current checkout code; the existing API process was not restarted.
- Backend 1,545 passed; frontend 664 passed; 10,000 simulation views; 131 documents validated; map-style test and smoke self-test passed. The strengthened final metadata case was rechecked in the 9-test focused run.
- Prior browser failures remain visible: the 19 September review recorded 35 passed, 9 skipped, 17 failed. No fresh broad browser pass is claimed. Pi checks remain pending.
- Existing published directories use the old dot-prefixed naming scheme. Preserve them when copying; newer publications use visible generation names. The 19 September review's statement that older generations are retained is superseded by current-plus-previous retention after these fixes.

The review and acceptance artifacts are ready for the owner's merge decision. No merge, push or deployment was performed.
