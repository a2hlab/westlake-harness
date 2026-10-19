# Exact Toutiao icon-recovery control placement

The older capture-feed transaction rolled the init slot back to an inert service, rather than restoring the currently installed entry. It also could leave the root filesystem writable after a failed remount. Reusing that transaction unchanged would not meet this task's rollback requirement.

This tool places controls in a **new** `icon-manual-*` root, then changes only the service entry path in `01_westlake_u13_toutiao.cfg`. It preserves the current permissions, SELinux context, startup condition and capability configuration. No APK, native library, JAR, user-data directory, existing stop or old control root is modified. Placement does not start any service; init reads the new entry on a subsequent boot.

## Evidence and limits

- `tests-r2.stderr.txt`: 14 offline tests passed. Four run the actual generated shell transaction against a synthetic filesystem with substituted device metadata/mount commands: success, copy failure, rw-remount failure, and ro-remount failure.
- Input tests reject wrong target/root, source drift, source symlinks, cfg permission changes, missing lock and mismatched/missing rollback receipts.
- `lifecycle.json` records the earlier 11-test run: 3 passed, 1 human review pending. It is not a device deployment receipt.
- An independent outer review found a swallowed precondition failure in the first draft; the current remote shell executes `set -eu` inside a subshell and checks an explicit remote exit marker.
- No device success is claimed by the offline tests. Device transaction and screenshot receipts must be recorded separately.

## Preparing an already reviewed candidate

The candidate generator supplies a complete payload, including its pinned `members.tsv`, `startup.env` and `startup.expected.sha256`. This tool does not authorize or invent a candidate. `BEFORE_CFG` is the original cfg read from the actual board; apply checks its SHA and metadata again before writing.

```sh
python3 benchmark/2026-10-19-toutiao-icon-deploy/prepare.py \
  --payload "$REVIEWED_PAYLOAD" --before "$BEFORE_CFG" \
  --boot "$ACTUAL_BOOT" --out "$NEW_PACKAGE"
python3 benchmark/2026-10-19-toutiao-icon-deploy/deploy.py \
  --plan "$NEW_PACKAGE/plan.json"  # preview; no device calls
```

## Apply and recover

Only the outer controller holding the exact 61b board lock can execute. Every command has a persistent stdout/stderr/rc receipt. The initial transaction record binds the actual input plan SHA, root, original boot and cfg pre/post images before the first device write.

```sh
python3 benchmark/2026-10-19-toutiao-icon-deploy/deploy.py \
  --plan "$NEW_PACKAGE/plan.json" --execute --out "$NEW_APPLY_RUN"
python3 benchmark/2026-10-19-toutiao-icon-deploy/deploy.py \
  --plan "$NEW_PACKAGE/plan.json" --rollback --execute \
  --boot "$CURRENT_BOOT" --apply-receipt "$NEW_APPLY_RUN/transaction.json" \
  --out "$NEW_ROLLBACK_RUN"
```

A partial payload transfer leaves the old cfg untouched and retains the new root as evidence. Rollback accepts only the original or this candidate's cfg bytes, first repairs a leftover rw mount to ro with a separate receipt, then restores the exact original cfg if necessary. It refuses foreign bytes. A cfg restore does not alter an already running guardian; execution/stop and reboot sequencing remain an explicit outer responsibility. Never launch a second guardian alongside the existing one.

Source patterns: `benchmark/2026-10-12-v1-seal-execution/capture-feed-package/executor.py` and `restore-v6-base-placement/apply.sh`; the old scripts are unchanged.
