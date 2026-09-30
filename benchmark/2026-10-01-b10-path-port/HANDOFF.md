# Outer landing checklist

## Scope

- Baseline master: `a29ec98102f07c8c6aecaa18937694a70a74c383`.
- Apply the six `ported` rows in `results.json`; delete exactly those six
  memberships from master's current user-path exceptions. Drop the now-empty
  B10 archive-comment entry, retain the four live-pinned script entries.
- `registration_sources.py` is **unchanged** after the compressed-cache audit.
  The initial seven-migration progress message is superseded by six.
- Keep all three frozen copies, all existing selectors, all old matrices and
  the nine approved spec exceptions unchanged. No new exception was requested.
- Copy this audit directory and the two task contracts. Add
  `tools/spec-checks/tests/b10_port_u5.rs` as a new integration-test file; do not
  replace master's `lib.rs`. Merge only the two new README/DIGEST lines.
- The new U5 score also needs six unchanged forecast files, absent from this
  master baseline: use `../2026-09-30-u4-sweep/j6n4-scoring/landing-dependencies.json`
  (fixed source commit and SHA per file). Then copy `J6N4-SCORING.{md,json}` and
  `j6n4-scoring/`. Do not import unrelated branch-only U4 files.
- Do not stage the old untracked spec-check-gate delivery files in this worktree.

## Verification

An isolated archive of the exact master baseline received only this payload
and the six forecast dependencies. With the normal lab Python environment,
`WORKSPACES` explicitly set to the real workspace parent, and
`CARGO_TARGET_AARCH64_APPLE_DARWIN_LINKER=/usr/bin/cc`:

```text
user-paths: 9485 files, 25 exceptions, 0 violation(s)
GATE PASS: cargo_exit=101 passed=64 failed=9 excepted=9 unexpected=0
```

The path inventory is the union of archived Git paths and the staged delivery,
passed explicitly because a `git archive` directory has no Git metadata.
The spec gate exits **0**; Cargo still exits **101** for the same nine approved
failures. This is not a claim that all historical specs pass.

New tests: two path tests and five scoring tests; four new Rust selectors.
Both task lifecycles/explain report **2 pass, 0 fail/skip**. Known-answer suite:
**69 run, 2 skipped, 0 failures**. `rustfmt --check` and `git diff --check` pass.
Full final receipts are under `validation/`.

The first scratch run omitted WORKSPACES (expected relocation prerequisite).
The next surfaced the compressed registration-source cache pin and absent
forecast dependencies. Restore that source, retain its exception, and copy the
already-frozen dependencies: the final gate passes without weakening selectors.

## U5 result

**38 hit / 2 false_positive / 26 unknown**, 40 evaluable; outer UI **24/66**.
Eighteen repair checkpoints are **1 failed promise / 17 unknown** under the
literal frozen evidence requirements. Useful partial progress is not erased,
but missing N2-ready/value/consumer-execution markers cannot become scored hits.
Seven unforecast signature families affect fourteen keys. Full logs were read
offline, records/entry/sidecars/t20 were SHA-checked, and 135 portable source
files were checked against their pinned Git versions. No later repeat replaces
a first attempt; no device commands were run.

## Commit handoff

The local `git add` was refused by the shared worktree metadata `index.lock`
permission boundary (Operation not permitted). No local commit was created and
no push was attempted. All changes remain in the worktree for the outer loop's
review and commit; the branch base is `5a9984c8e`.
