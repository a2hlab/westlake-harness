# New-SHA independent review

`candidate_review.py` reads a candidate directory, chooses the watchdog by the caller's full SHA (never mtime), captures exact source/helper bytes, checks input stability, and uses safety assertions instead of treating reproduction of an old defect as PASS. A previously reviewed SHA exits 3 without creating an output directory or executing it again. Refusal-only implementations fail positive controls. Missing functions, stderr, or a broken fixture report `harness_error`, never safe PASS.

```sh
python3 benchmark/2026-10-21-manual-video-regression/host-reentry-peer/candidate_review.py \
  --candidate ../westlake-harness-video/benchmark/2026-10-21-manual-video-regression/host-reentry-candidate \
  --payload <actual-package>/payload \
  --expect-watchdog-sha <new-full-sha256> \
  --out benchmark/2026-10-21-manual-video-regression/host-reentry-peer/<new-run>
```

Without `--payload`, source-only function review is possible with explicit baseline helpers, but assembly fails. `--baseline-payload` changes that disclosed helper origin. An actual package is never overlaid or changed. `--assembly-only` audits a completed package for an already reviewed source without executing the old functions. Multiple common source candidates require selecting an actual unambiguous payload.

Pin audit: required members; member digest/mode/path and duplicate detection; boot-copy coverage; startup.env -> members and bounded-start/decoder/probe hashes; startup.expected -> startup.env; exact entry watchdog/ownership-helper literals; package MANIFEST and source dependency presence. All source/config are read, never sourced or executed. Static pin consistency is not a device, approval, race-exclusion, or visual signoff.

The first revision used an overly broad helper function extractor (`r4b-3aba9d8e-01`, 16 harness errors). The fixed extractor limits input to the watchdog's actual helper dependencies and excludes single-line function headers from multiline matching. `-02` exposed a too-strict oracle: enumeration rc1 with a partial stdout holder list was incorrectly counted as failure despite callers checking rc. `-03` corrects that oracle and adds malformed-UID and recorded-run-inode counterexamples; 16 safe controls/edges, 2 remaining failures, 0 harness errors. All original receipts remain.

The epoch fixture sets up synthetic self/parent stat, namespace and socket-view data. `rc_epoch_binding`, `rc_wait_exit`, epoch record creation, and comparison remain production functions. Signals/start/file-id/ownership observations are explicitly simulated; `recorded_run_inode_changed` restores real production `parent_owned`, and `malformed_owned_uid` restores real `rc_owned_pids_strict` and uses the real `rb_uid` parser. Complete safety approval still requires manual source review and a full production package.
