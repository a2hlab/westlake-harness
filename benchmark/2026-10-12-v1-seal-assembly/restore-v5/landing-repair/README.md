# Supplemental v5 landing closure repair

The original 23-file v5 landing was incomplete for its test entry point: the
frozen test directly opened omitted control payloads and every runtime member.
Its previous 8/8 result depended on the producer's unlanded package. The old freeze
`756c57e899ff89855f12bc174fdcd35c1e10fdd01ffb5d11b01501e193087ed8` is preserved
byte-for-byte; this independent supplement corrects delivery and reproduction.

The explicit source inventory has 48 files: original 23 v5 files, all 19 small v5
control payloads, five v4 test dependencies and one pinned v3 stage metadata JSON.
The v4 dependencies are provider, binding, plan, watchdog and launch. No v4 runtime
is needed. JPEG and screen-gate-feed are intentional small binary inclusions;
the outer landing must include ignored files explicitly, not rely on git add's
usual ignore behavior. `landing-paths.txt` is the complete replacement handoff list
including original v5 files and this supplement, not just the incremental files.

Run from the receiving repository root after landing that complete list:

```sh
python3 benchmark/2026-10-12-v1-seal-assembly/restore-v5/landing-repair/replay_clean_landing.py \
  --workspaces "$WORKSPACES" \
  --out /private/tmp/restore-v5-clean-landing-review
```

Set WORKSPACES to the existing workspace collection. The output directory must not
exist. The original direct `python3 test_restore_v5.py` entry assumes a hydrated
package; use the command above for a sparse landed checkout. It copies only the
48 inventory files into an empty temporary tree, then uses the frozen compiler
and binding to rebuild from their independently pinned local inputs/CAS. It checks
that the rebuilt manifest is exactly the original
`0c5da8dadaec9e6fc4969d06f884b6204ce5601297f18f76b25fc0407f0d8ab5`, verifies all
486 manifest files, hydrates only omitted runtime files in that temporary tree,
and runs the unchanged eight-test suite there. It never overwrites a frozen file
or the receiving checkout's package. Runtime/CAS data stays out of Git.

The compiler has one legacy t4-specific metadata reference used by three stage
rows. Only in this local reproducer, its resolver maps that exact reference to
the landed v3 JSON, independently checked at SHA
`00551807bb579ccfa28aa369480a22d610063492c7425aebb11578beb6173b0e`.
Neither the frozen binding nor provider is changed. All other required sources
remain explicit local dependencies under the main tree, t0 frozen checkpoints,
and westlake-inputs/CAS; no downloads or remote calls occur. Missing or changed
pinned input causes failure rather than an invented replacement.

After copying the allowed inventory, the Python audit hook rejects access to the
private t4 checkout. The only allowed child processes are the frozen test's two
reviewed bash snippets (helper diagnostic and isolated success branch). This is
an application-level check, not an OS sandbox. It does not simulate a production
lock or execute a complete worker, provider invocation, transaction or board call.

The recorded clean replay is in `evidence/`: compile rc0, exact manifest reproduced,
8/8 tests, zero errors/failures, no attempted private-checkout reads. This is the
limited v5 delta suite, not a new transaction matrix. All deployment flags remain
disabled; no seal or execution authority is created.
