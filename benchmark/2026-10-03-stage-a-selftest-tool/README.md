# stage_a_selftest.py — parameterized stage-A selftest (from U13's build_decision.py)

`scripts/lab/stage_a_selftest.py` keeps every U13 behaviour; the tree and selection are
parameters. It does NOT sign decisions (the outer does); `--reference` is reserved for the
retention-hook half and currently unused.

    python3 scripts/lab/stage_a_selftest.py \
        --root $WORKSPACES/westlake-harness-u7-executor/benchmark/2026-10-03-u14-stage-a-plan \
        --pattern 'window*/u14-A*/*/runner/**/record.json' \
        [--known-answer <sha-prefix>] [--out <dir>]

## U13 known answer — REPRODUCED

    python3 scripts/lab/stage_a_selftest.py \
        --root $WORKSPACES/westlake-harness-u7-executor/benchmark/2026-10-03-u13-stage-a-plan \
        --pattern 'window*/u13-A*/*/runner/**/record.json' --known-answer 0488fa09

- report sha256 prefix **0488fa09** ✅ (matches master selftest-u13-stage-a.json)
- **41 explanations** ✅ (same as master's common shard)
- excluded per class: fixture 2, contact-index symlink 51, evidence copy 223, recovery smoke
  73, executor state 81 — unclassified non-runner records error out (none occurred)
- failure lines by any-pid rescan: 0; PASS 180 / unknown 39 / REJECT 0; processes pid-sorted
  → byte-reproducible report
- unit tests (scripts/lab/tests/test_stage_a_selftest.py): the same assertions + a bad-pattern
  error case — 2/2 OK (skipped on hosts without the U13 tree)

## Behaviour preserved

1. aggregate over exactly the candidate's runner records (Selected shim into ps.report)
2. exclusion classes; unknown non-runner record = error
3. any-pid failure-line rescan
4. pid-sorted processes → stable report SHA
5. unknown (record, pid) auto-classification; unclassifiable = error
6. `--known-answer` prefix gate for the tree being scanned
