# First-board snapshot feedback correction

## Evidence first

The original seccomp index missed `/system/etc/sandbox/appdata-sandbox.json`:
its label was `data_local_tmp` on the pre-fix 61b and `system_etc_file` on 5cd,
while both files had SHA `49a278fa47c28ef58ef056864278195d8ac8cdac5a362d737c0c71d7ec0a3f6a`.
The supplied original text captures also report **23** data-local-tmp libraries
in 61b's `/system/lib64` and **0** on 5cd. The selected regression replay has
those 23 library paths plus the sandbox JSON: **24 versus 0 observed paths**.

`evidence/61b-5cd-selected-fields.json` pins all three original text captures
by SHA and cites line numbers. It is a selected-field regression replay,
**not a full original snapshot**. Healthy library labels are replay values
derived from the zero-bad-label count, not fabricated per-file raw rows.
The parameter error text is retained as an error, not normalized into unset.

Importantly, the later `/private/tmp/claude-501/bss/{61b,5cd}/snapshot.json`
captures are already **post-label-fix**: both JSON labels are `system_etc_file`
and both bad-label counts are 0. Replaying those actual SHA-verified captures
must not invent the earlier 24-path difference. The compact offline replay
receipt binds their original hashes and records that distinction; full raw
board parameter/process data are not copied into this public delivery.

## Three corrections

1. The CLI deliberately keeps one capture per `--out`, with no silent overwrite
   or API-breaking automatic nesting. The parent README gives a serial/time/PID
   directory pattern. Known answers prove two boards can use sibling outputs
   and that reuse refuses without changing prior bytes.
2. Sandbox JSON labels, all `const.cust.*` parameters and scoped `/system`
   data-label counts are indexed as `causal_proof=false` hints. The capture also
   reads discovered sandbox JSON labels without requiring a deployment plan.
   Counts include paths and the captured-path total; partial collection cannot
   masquerade as a whole-tree census or a proven seccomp cause.
3. `collection_complete` measures mandatory read and boot integrity;
   `coverage.deployment_targets_complete` measures plan coverage. Missing plan
   gives `PARTIAL_COVERAGE` with a warning; failed reads give `INCOMPLETE_READS`.
   `complete` stays false without the plan, and CLI exit 1 remains conservative.
   The diff can compare integrity-checked observed fields while naming its
   partial scope. The exact legacy missing-plan warning is recognized; other
   failures and tampered raw evidence are still incomparable.

The minimal reboot simulator's full `complete` gate is unchanged. This patch
does not authorize a reboot or change security policy, labels, deployment,
autostart, or any board. All new capture calls use mock transport; replaying
existing local evidence invokes no HDC, VM or SSH.

## Verification and landing

Run `python3 scripts/lab/test_board_state.py -v`, the Rust `board_state_readonly`
selector, and `agent-spec lifecycle specs/board-state-tools/t2-first-board-fix.spec.md
--code tools/spec-checks --format json`. Raw fresh outputs and precise exits
are in `evidence/` and `results.json`. The prior 10-test receipt is retained;
the corrected suite has **16 tests**. `landing-paths.txt` is limited to this
correction, not other pending worktree deliverables. Git metadata is read-only;
the outer lane must land it. No private raw board directory is removed or copied.
