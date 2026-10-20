# Demo61b video migration — not yet accepted

W03-b also failed visual acceptance: nine candidate frames across 89.891
seconds showed a gray host. The original files were restored in physical and
parent-private views; the final image contains text feed cards with image
placeholders. The window closed at 1,488 seconds. Rollback signing was 18.073
seconds late against the 1,200-second experiment cutoff; the original timing
is preserved. No video candidate was retained.

- [W03-b actual images, facts and independent restoration review](../2026-10-21-t34-w03-peer/README.md)
- [Verified W03 archive: 4,746 payloads, 1,163,052 bytes](archive-03/README.md)
- [Runtime comparison: proven facts and missing evidence](environment-diff-01/README.md)
- [Bounded read-only runtime collection](environment-collect-01/README.md)

The API increment now contains 47 observations and 1,173 exact file references,
preserving all preceding 46 objects and historical 315 semantics. W03-b is a
failed-migration/restoration observation, not a new API freeze.

## Earlier W02 result

W02 deployment succeeded, but the candidate screenshots showed a blank host.
The original runtime was restored and the window closed after 1,672 seconds.
The final homepage reported a network error with no feed cards. Deployment
success and restoration of files do not establish video or healthy-feed acceptance.

- [Actual W02 images, rollback and corrected verdict](window-02-closed/README.md)
- [Verified archive: 3,828 payloads, 20,366,770 bytes](archive-01/README.md)
- [Verified publication to remote master](publication-01/results.json)
- [Candidate source and original build correspondence](source-map/README.md)
- [Existing startup evidence and bounded interpretation](triage-01/README.md)
- [Reviewed UI runner commands](ui-01/COMMANDS.md)
- [API observations and exact references](../2026-10-19-api-progress-update/index.html)
- [Genshin experiment queued after this task](next-task-queue.md)

The W02 report and its initial API review describe their creation-time state.
Those records remain unchanged; their archive-pending note is superseded by
the linked verified archive receipt. The failed observation is now integrated
into the main working tree and published to remote `master`; the linked
publication receipt records the exact remotely verified commit.

The UI successor passed eight independent offline tests and was subsequently
used for W03-b's actual baseline, failed candidate and restored captures.
The baseline capture was interrupted by the outer controller and remains
partial. W02's closed lock and admission must never
be reused. A future run requires fresh board readiness, identity, lock,
admission and the same bounded recovery discipline.

## Original preparation record (preserved)

# T34 narrow 61b migration preparation

The frozen T30 executor cannot be used unchanged on 61b: it embeds 5cd UID, cfg,
guardian root, WID templates and backup names. This package derives a separate
61b executor from exact source `693448c2…`, with an auditable unified diff.
No candidate binary or historical source is changed.

Eleven offline tests passed, exercising 64 known rollback combinations, six cutpoints,
five foreign-byte classes and six local-shell cases. The latter include a real
rename proving an old hard-linked inode is preserved. Host ownership/SELinux output
is mocked for that case; actual device transaction behavior remains untested.
The first test run's fixture failures remain in the raw index.

The five existing candidate files match their manifest SHA and size. Current cc-video
intake reports 61b UID20011206, cfg91e31, run6afd/WID30, b189 HAP and original native
files. These are observed input facts, not a signed new-window admission. Additional
guarded directory/provider/private-view data is pending.

`deployment/prepare_data.py` refuses missing/different fields and creates an unsigned
data package. `COMMANDS.md` supplies the exact existing transaction interface, actor
`inner(cc-video)`, original-plan rollback and no-parent physical recovery. All five
backups and the compat absence marker precede the first write. Directory aliases and
symlinks refuse; runtime replacement is atomic rename, not overwrite.

The cx-seal HDC probe returned process rc0 with `Connect server failed`, empty stdout
and no boot evidence. Git branch creation returned rc128 due sandbox ref access.
Neither is bypassed. cc-video is the only device lane. No lock, device mutation,
deployment result, retain decision, screenshot count or playback result is claimed here.

See `results.json`, `evidence/public/raw-index.json`, `manifest.json` and
`landing-paths.txt`. Only explicitly listed files are a delivery; private raw logs
and old benchmark files are excluded.
