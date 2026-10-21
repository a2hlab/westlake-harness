# Exact guardian-only deployment successor

The donor assumed the sealed r1 cfg and accepted only the first lock token. This successor keeps its cfg CAS, fresh-root staging, metadata checks, remount recovery and transaction-bound rollback, but binds the current r2 entry and a complete `inner(cc-video) PID ISO` holder/start. It does not deploy video runtime files or start a guardian directly.

`prepare.py` validates all16 boot-copy members, literal entry watchdog/owner pins, decoder/probe pins, shell source dependencies and the members → startup → expected hash chain. The actual reviewed r3 private payload was packaged offline:20 payload files; generated after.cfg is byte-identical to the CC proposal, SHA `7b9f2c0e6431a486f3138f8fca04e3c5aea2c21f4f8acb6f83e815735d998e4b`. Before.cfg is `91e31b959995772d305d5b034c9a5ebdbf3f8371495e3964185ada928db4ee2e`. This was a preview using a historical intake boot, not live admission.

Every target transport command first records and verifies the exact holder and current boot. Budget derives from the bound original start and then uses a monotonic clock: apply1200s, rollback1800s. Each subprocess records actual argv, binary stdout/stderr and rc; timeout preserves partial bytes and records124. A unique remote `ICON_REMOTE_RC=0` is required independently of HDC exit status. Scripts over32KiB refuse; unknown writes never retry automatically. Runtime UI/reboot/restore verification and lock release remain the explicit operation card, not hidden executor actions.

The same signed session, plan and source pins are required for rollback; only `--boot` changes after reboot. The original apply `transaction.json` must match exactly. Restore accepts only actual before/after cfg hashes, restores this transaction's before bytes and keeps the new root for evidence. Physical cfg restoration does not prove a running guardian was replaced: normal reboot and actual identity/control-chain verification are still required.

## CLI

All output directories must be new. The existing `admission.pending.json` is NOT executable. The outer supplies a reviewed session with `approved_by`, `serial`, exact `holder`, holder-bound numeric `start`, `plan_sha256`, and `source_pins` (`deploy.py`, `prepare.py`, `board_note.sh` actual hashes). Unfilled or drifting values refuse. Merely generating armed candidate content is not device admission.

```sh
python3 "$TOOLS/prepare.py" --payload "$R3_PAYLOAD" --before "$ACTUAL_BEFORE_CFG" --boot "$BEFORE_BOOT" --out "$PACKAGE"
python3 "$TOOLS/deploy.py" --plan "$PACKAGE/plan.json"
python3 "$TOOLS/deploy.py" --plan "$PACKAGE/plan.json" --execute --session "$SIGNED_SESSION" --repo "$MAIN" --hdc "$HDC" --out "$APPLY_OUT"
python3 "$TOOLS/deploy.py" --plan "$PACKAGE/plan.json" --rollback --boot "$CURRENT_BOOT" --apply-receipt "$APPLY_OUT/transaction.json" --execute --session "$SIGNED_SESSION" --repo "$MAIN" --hdc "$HDC" --out "$ROLLBACK_OUT"
```

## Offline evidence

22 tests passed, including real generated transaction-shell apply, rollback, cp failure, rw failure and ro failure with only device metadata/mount seams. The Rust `demo61b_guardian_deployment` trampoline actually ran those22 tests and passed. Transport tests preserve non-UTF8 timeout output and refuse holder drift, exhausted budget, missing/duplicate/failing remote markers. Binary fixture contents are explicitly synthetic and never executed; no device commands were issued.

An initial author run lacked the ignored r2 binary inputs; the test fixture was corrected to use explicit non-executed bytes. Another sparse-tree peer found eager evaluation of the fallback repository path; the test now honors `T34_MAIN` first. Failed receipts are retained. Public source pins and the private raw index distinguish these runs. No device success, guardian retention or video pass is claimed.
