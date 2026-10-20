# T29 design peer admission

Three bounded design gaps were found and closed before the outer coordinator authorized parallel offline implementation: stderr pipe/SIGPIPE exposure, separate producer ref/unref results, and a reserved coverage-exhaustion notice. This package preserves both reviews; it does not erase the original findings or claim implementation tests or runtime playback passed.

- `snapshot-01/` contains the exact first reviewed design, source pins, two original `agent-spec contract` outputs (both commands returned zero), and the three open findings.
- `snapshot-02/` contains the revised exact design, original independent lint stdout/stderr/rc for both task specs, input hashes, and the final admission. Both `agent-spec lint ... --min-score 0.7` commands returned **0**, with **100%** quality. Advice-level warnings remain in full original stdout. All six input files were unchanged across these commands.
- The accepted sink retains a private regular-file descriptor and refuses pipe/socket sinks; ref/unref have independent called/valid/rc fields; invalid records cannot spend the two reserved limit notices. Exhausted paths check eligibility before formatting, time lookup or writing.
- The 16-identity / 8-transition / 6-phase budget, unchanged object lifetimes, errno/return/ref transparency, exact source/object provenance boundary and separate runtime-provider evidence gate remain required.

The snapshots are historical design evidence, not the current implementation authority. Their `DESIGN_ONLY` status correctly reflects the moment of review; the outer coordinator subsequently authorized the two implementation lanes. Final production still depends on consumer source pins and independent implementation review. No old tests were rerun, no implementation test was claimed, and no HDC or REA call was made during this review.

`index.json` pins every other package file, including both snapshots and the landing list. `snapshot-02/receipt.json` also records the exact argv, original stdout/stderr hashes and reviewed source hashes. Public paths are repository-relative; no private author home path is included. The two successful lint commands were run against the author's live T4 worktree, with before/after source hashes checked; these copied snapshots are evidence of those inputs, not a substituted test run.
