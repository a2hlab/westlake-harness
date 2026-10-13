# Next 5cd window: exact CLI card (static review only)

**No command below was executed.** Core3f176/38176 and entry4b5c99 remain unchanged. Source hashes are in source-pins.json. Current captured origin is `362f2212-1a42-4c1a-8487-0dddb091c74b`, Boat UID20011301, host UID20011300. A new boot/holder/expiry must come from outer's actual window; never substitute the origin boot for a postboot observation.

Common local variables, from main:

```sh
BASE=benchmark/2026-10-09-demo-boatattack/v2-20261013
CORE="$BASE/integration/routeb-fresh-restore"
PROV="$BASE/integration/final-v2-f28/board5cd/provider"
PKG="$BASE/outer/final-v2-f28-main"
SERIAL=5cd1e3dd00000000000000000923012c
sha() { shasum -a 256 "$1" | cut -d ' ' -f1; }
# NEXT and RUN: new outer-selected directories; HDCPATH: approved native HDC.
```

**1. Next-window authorization and placement.** First require actual current487 `recipe-receipt.json` complete/rc0/487 and release that window. Use ENTRY.md's real prepare_stage CLI with `--completed-receipt` to compile the successor; no487 rerun. Outer creates a new enabled Boat plan by changing only `execution_enabled`, pins it in the new deployment, and signs the following apply authorization: `approved_by=outer(codex)`, `plan_sha256=SHA(enabled plan)`, `serial`, `origin_boot_id=362f…`, `boot_id=362f…`, `action=apply`, `expires_epoch`, `holder=complete held stdout.strip()`. Deployment provider.authorization is its independent `{path,sha256}`. Deployment and successor execution_enabled must also be true; sign neither candidate seal nor recipe. Keep the same candidate seal file and all18 declared targets. New window reserves rollback time separately; the installer only checks expiry, not a600-second reserve.

```sh
python3 "$CORE/restore_entry.py" --v2-recipe "$NEXT/recipe.enabled.json" \
  --recipe-sha256 "$(sha "$NEXT/recipe.enabled.json")" --out "$RUN/staged" --execute
```

This runs original live R5 then the standard Boat provider. Require actual11 placed receipts and protected488 proof. **Do not use `demo_restore.sh --v2-5cd-recipe`: main still routes the old rehearsal entry.** Direct successor CLI is the current working route. Root's board_run must have explicit after_lock/before_unlock argv, `execution_enabled:true`, real HW/ZZ smoke, and no app shards for this restore-only window; a nonzero before_unlock retains the existing lock.

**2. Original provider rollback, including a failed candidate boot.** Keep the SAME enabled plan and `$RUN/staged/boat/transaction`; do not rewrite its origin to NEWBOOT. Before rollback, outer's existing callback uses pinned BMS `Board.ready → cold_stop(Boat package,20011301) → fresh UID/PPID process table`; system parent is never killed. BMS lane is owner token only; installer holder is the full held line. Bind the actual cleanup JSON (`serial,boot_id,package,uid,remaining_processes:[],success:true`) and every retained audit file's actual SHA/mode/uid/gid/label. `cold_stop` is an existing Python API, **not** a CLI flag.

Fresh rollback authorization: same fields as apply, but `action=rollback`, `boot_id=actual current boot`, original origin_boot_id preserved, plus `cleanup_receipt:{path,sha256}` and exact `retained_audit:[...]`. Allowed audit names are cfg-stage hashes and boat-ORIGIN/CURRENTBOOT `.log/.receipt/.intents`, metadata644:0:0:data_file; unknown entries reject. Copy the deployment, set provider.action=rollback, authorization=new pin, transaction_dir=original transaction path, transaction={path:original transaction.json,sha256:actual}; retain prepared/program/common/executor/targets unchanged.

```sh
python3 "$PROV/boat_provider.py" --seal "$PKG/composed/seal-candidate.json" \
  --serial "$SERIAL" --deployment "$NEXT/deployment.rollback.json" \
  --out "$RUN/rollback-provider"
# Equivalent underlying CLI (choose one, never run both):
# python3 "$PROV/installer.py" --plan "$NEXT/plan.enabled.json" --action rollback \
#   --execute --authorization "$NEXT/rollback-authorization.json" \
#   --authorization-sha256 "$(sha "$NEXT/rollback-authorization.json")" \
#   --out "$RUN/staged/boat/transaction"
```

The original installer verifies all backups before unmount, accepts base or exact candidate per bind (including worker partial-bind failure), restores in reverse order and verifies319/488 protections. Provider rc0 requires `RESTORED_RETAINED_AUDIT_VERIFIED`; its receipt explicitly does **not** claim the live parent reloaded restored libraries. Early apply failure before both directory-created journals is not covered by successful audit_verify: inspect the actual journals/intent and retain the lock rather than inventing completion.

**3. Single candidate boot and failure exit.** After placement, run existing snapshot/policy, then outer's separately authorized ONE candidate boot. The current 62-target plan already includes all7 real bind targets; add no source-directory targets.

```sh
python3 scripts/lab/board_state_snapshot.py "$SERIAL" --hdc "$HDCPATH" \
  --plan "$BASE/outer/r5-preflight/candidate-snapshot.r4.json" --out "$RUN/preboot-snapshot"
python3 scripts/lab/sepolicy_gate.py --evidence "$RUN/preboot-policy.json"
# Outer alone executes/records its authorized boot; this review supplies no HDC invocation.
CHECK="$BASE/integration/final-v2-f28/selfcheck"
python3 "$CHECK/selfcheck_entry.py" --composition "$PKG/composed/composition.json" \
  --composition-sha256 "$(sha "$PKG/composed/composition.json")" \
  --serial "$SERIAL" --boot-id "$NEWBOOT" --hdc "$HDCPATH" --out "$RUN/selfcheck954.json"
```

Require snapshot complete/stable/errors[], policy failures[], lowercase READY56 actualboot, BOUND7 actualboot, then actual954/nonfile PASS and separate screenshots. On partial worker/READY/954 failure while reachable: execute step2 under the current held lock, take baseline-return snapshot/policy, then the separately authorized recovery boot (distinct from candidate boot). Restore actual imehost desktop foreground using the existing BMS desktop_launch sequence, then:

```sh
BIND=benchmark/2026-10-12-v1-seal-execution/seal-final-20261013/activation-binding.5cd.json
python3 benchmark/2026-10-12-toutiao-recovery-review/r5-binary-collector/selfcheck_entry.py \
  --checker activation --activation-binding "$BIND" --binding-sha256 "$(sha "$BIND")" \
  --serial "$SERIAL" --boot-id "$RETURNBOOT" --hdc "$HDCPATH" --out "$RUN/restored-r5.json"
python3 scripts/lab/activation_smoke.py --spec "$HWZZ_SPEC" --serial "$SERIAL" \
  --lane "$OWNER" --hdc "$HDCPATH" --lock-cmd "bash scripts/lab/board_note.sh" --out "$RUN/restored-hwzz"
```

Require actual940/nonfile PASS and HW/ZZ images before successful cleanup/unlock. No transaction AND no intents/created-directory evidence needs foreground/R5 verification, no automatic recovery boot. If detached, retain evidence/lock and stop; no verified rollback or blind repeated boot claim. **Do not run old window_hooks.r4.py verbatim (BOUND6/old installer/stock187 inputs) or old recover_foreground.py verbatim (fixed8d0f/output).** Reuse their reviewed callback sequence with new pins, BOUND7 and actual boot/output. WID is independent live evidence, never guessed; no61b operation or new framework.
