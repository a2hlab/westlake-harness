# Successor entry for the completed current487 transaction

This is a separate release from freeze-core.json. It does not change executor3f176393 or prepare38176fcc. The frozen f28 Boat provider, original R5 binary collector and signed V1 proof stay unchanged. The new entry accepts only full current-prestate restoration or its completed history; it does not offer verify-existing as a substitute for recovery.

The current operational sequence is two independent authorized windows:

1. Run only the487 core, no Boat and no reboot. Require all487 placed receipts, transaction/backups and29 exact directory records. Release its lock.
2. Admit that completed history offline, acquire a new window, run original R5 live, place the11 Boat members through the original7-bind provider, then outer's existing snapshot/policy/single-boot/live954 path. Do not reuse the first window's expiry or authorization.

## Prepare the disabled successor on main

Use the completed core transaction, not the historical43bc receipt. All references below must be actual main files. `$HDCPATH` is the already approved native HDC executable, read and pinned locally here; preparation never runs it.

```sh
CORE=benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/routeb-fresh-restore
PKG=benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/final-v2-f28-main
RESTORE=benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/routeb-fresh-restore-main
NEXT=benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/routeb-fresh-boat-stage
sha() { shasum -a 256 "$1" | cut -d ' ' -f1; }
python3 "$CORE/prepare_stage.py" \
  --directory-recipe "$RESTORE/recipe.json" --directory-recipe-sha256 "$(sha "$RESTORE/recipe.json")" \
  --completed-receipt "$RESTORE/transaction/recipe-receipt.json" \
  --completed-receipt-sha256 "$(sha "$RESTORE/transaction/recipe-receipt.json")" \
  --deployment "$PKG/deployment.disabled.json" --deployment-sha256 "$(sha "$PKG/deployment.disabled.json")" \
  --seal "$PKG/composed/seal-candidate.json" --seal-sha256 "$(sha "$PKG/composed/seal-candidate.json")" \
  --hdc "$HDCPATH" --hdc-sha256 "$(sha "$HDCPATH")" --out "$NEXT"
python3 "$CORE/restore_entry.py" --v2-recipe "$NEXT/recipe.disabled.json" \
  --recipe-sha256 "$(sha "$NEXT/recipe.disabled.json")" --out "$NEXT/preview-output"
```

The default entry only prints argv, creates no execution output and calls no device. It validates the completed487 history, including original realization and activation binding, even during preview. If the487 receipt does not yet exist, omitting the paired completed-receipt arguments produces a full-chain disabled preview using the NEW core recipe. This is not permission to combine both windows into45 minutes.

`prepare_stage.py` always emits disabled/unsigned output. For the second window, root must use the existing Boat authorizer to create an independently pinned enabled plan/deployment and its current authorization; generate a fresh successor from that deployment, then create a separately reviewed copy with only the recipe execution_enabled flag true. Pin that exact copy in the new window. Invoke the same restore_entry command with `--execute`. The original provider checks its own/common/executor pins, authorization, fresh UID, current boot and all488 RouteB protections. The successor never grants these permissions.

Successor order in resume mode is exactly `route-b-selfcheck`, then `boat-placement`. A nonzero child or incomplete receipt stops before the next step. Full-chain mode inserts `route-b-complete` first and requires its487 receipt before live R5. There is no parent timeout to interrupt a legitimate child transaction. A completed staged receipt remains `PLACED_PENDING_AUTHORIZED_SINGLE_BOOT_AND_FINAL_SELFCHECK`; it does not claim restoration/UI acceptance or a seal.

## Existing single-boot and postboot chain

Use the already reviewed snapshot at `outer/r5-preflight/candidate-snapshot.r4.json` (62 targets; all7 actual bind targets included). Do not add the owned source/control directory members to snapshot plan_targets. Outer owns snapshot/policy, one authorized coldboot, READY and BOUND7 checks, foreground recovery where required, UI review and eventual unlock/rollback.

Use the frozen main f28 checker directly with the actual NEW boot:

```sh
CHECK=benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/final-v2-f28/selfcheck
python3 "$CHECK/selfcheck_entry.py" \
  --composition "$PKG/composed/composition.json" \
  --composition-sha256 "$(sha "$PKG/composed/composition.json")" \
  --serial 5cd1e3dd00000000000000000923012c --boot-id "$NEWBOOT" \
  --hdc "$HDCPATH" --out "$POSTBOOT/selfcheck.json"
```

`$POSTBOOT` must already exist and output must be fresh. This existing checker obtains independent host/WMS evidence and derives running_files with complete SHA checks. After actual954 PASS, copy the existing composition request to a NEW file; add `current_boot` equal to NEWBOOT and `running_parameter_evidence` as `{path,sha256}` of the actual generated `parameter-observation.json`. Re-run the unchanged `compile_selfcheck.py --request NEW_REQUEST --out NEW_COMPOSITION`. Never guess WID or edit the preboot composition/old seal. A new composition is still candidate/not_sealed. UI and full128/signoff remain separate real-evidence gates.

Failure before Boat does not authorize Boat. Failure during Boat retains its exact transaction for original provider rollback. After any boot, use the independently approved existing rollback procedure and current-boot authority; the core487 action intentionally refuses a different boot. Do not interpret source rollback or old940 equality as postboot954 acceptance.
