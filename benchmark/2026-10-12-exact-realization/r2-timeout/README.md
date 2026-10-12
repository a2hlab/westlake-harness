# Timeout adapter r2

The frozen adapter imposed a 900-second executor wait. This separate adapter allows 2700 seconds. If the executor wait expires, it returns adapter rc 124 and an `UNKNOWN` receipt: executor exit status, process state, and rollback state are not asserted. Partial stdout/stderr are retained. No retry or rollback is started.

Only `restore.execute` timeout handling changes. `prepare`, `checked_package`, and `guard` retain identical ASTs. The proof, preview, plan, target map, and executor are reused unchanged. The entrypoint imports the frozen parent `realization.py` and this directory's `restore.py`. The old Python files remain unchanged. The separately authorized wrapper change only redirects its explicit `--realization` route to this r2 entry; the legacy fallback is byte-identical. `superseded.json` records this sole supersession of the parent freeze; the parent freeze JSON is not edited. `source-exact.json` and the two unified diffs bind the exact source and derived bytes.

## Outer execution entry

Use the existing proof and prepared preview, a newly independently pinned admission whose `generator_sha256` is `af1ce6fc2f6b43568e8acec9f06cd63c92f48aa10c49c6b3a16c7c39258b2f05`, and a fresh transaction path. Existing independent authorization, boot, holder, package, plan, executor, target, and lock-tool checks still apply. The source admission pinned to the old adapter is refused. After landing the recorded one-line wrapper change, `scripts/lab/demo_restore.sh --realization ...` dispatches to r2. The direct command below also works before that wrapper is landed.

```bash
python3 "$WORKSPACES/westlake-harness/benchmark/2026-10-12-exact-realization/r2-timeout/exact_realization.py" --realization "$PROOF" --prepared "$PREVIEW" --execute --admission "$R2_ADMISSION" --admission-sha256 "$R2_ADMISSION_SHA256" --authorization "$AUTHORIZATION" --authorization-sha256 "$AUTHORIZATION_SHA256" --lock-tool "$LOCK_TOOL" --lock-tool-sha256 "$LOCK_TOOL_SHA256" --transaction-action apply --out "$NEW_TRANSACTION"
```

On timeout the CLI persists `<NEW_TRANSACTION>.realization-receipt.json` with `status=UNKNOWN`, `executor_rc=null`, `adapter_rc=124`, and returns 124. The existing transaction directory is retained for outer inspection; this receipt does not establish zero writes or successful rollback. 超时后由外环检查既有事务及板上实际状态，不自动复跑，也不宣称 rollback 已完成。

## Targeted validation

`python3 -B test_timeout.py`: 3/3 tests pass. Tests use a fake runner and stub prerequisites only to verify argument/receipt plumbing; they do not simulate a production lock or executor transaction. The admission drift test uses the real guard and real file pins, mocking only prepared-package reconstruction. The CLI `--help` import check also passes. No devices, network, locks, builds, or full regression reruns were used.
