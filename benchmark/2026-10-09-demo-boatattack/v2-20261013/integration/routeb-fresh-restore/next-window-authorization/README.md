# Next-window authorization: every required key

This additive page documents the unchanged Boat installer50336582 and provider641a82ee. Templates deliberately contain approved_by:null, expires_epoch:0 and invalid placeholders; they cannot pass admission. The cleanup shape is NOT a receipt. No device command was run. This is separate from the current487 authorization/admission pair: **Boat has one pinned authorization; it does not read the487 `signed_by`, `admitted`, `actions`, `target_sha256`, or `lock_tool` fields.** Its lock-tool pin is already inside the prepared plan.

| Required authorization key | Type and exact source |
|---|---|
| approved_by | string, authorized outer fills literal `outer(codex)` |
| plan_sha256 | 64 lowercase hex; SHA of the **final enabled Boat plan**, not its disabled parent, recipe, seal or487 plan |
| serial | exact `5cd1e3dd00000000000000000923012c` |
| origin_boot_id | original Boat plan.boot_id, `362f2212-1a42-4c1a-8487-0dddb091c74b`; stays unchanged through rollback |
| boot_id | apply: identical to origin; rollback: independent current board boot, possibly different |
| expires_epoch | JSON number, Unix epoch seconds, strictly future at every device call; outer keeps its existing window and rollback reserve |
| action | exact `apply` or `rollback`, matching provider.action / installer --action |
| holder | nonempty **full** current board_note held stdout.strip(), including owner PID timestamp; BMS lane separately uses only its owner token |
| cleanup_receipt | **rollback only**, exactly `{path,sha256}`, pinning the real same-current-boot cleanup JSON |
| retained_audit | **rollback only**, list of every permitted retained file, each with `target,exists,sha256,mode,uid,gid,label`; list is required even if empty, and empty is valid only if enumeration proves no retained files |

The existing authorization has no required `schema`, `execution_enabled`, UID, executor pin or explicit reboot flag. Do not invent such fields as a substitute for the checks above. Reboot authority belongs to outer's separate window authorization; installer/provider do not reboot. The reviewed JSON schema describes these keys only and is not a replacement gate.

Rollback cleanup JSON has ALL six required keys: `serial`, `boot_id` (authorization current boot), `package`=`com.Unity3d.BoatAttackDay`, `uid`=20011301 (same actual plan/live BMS identity), `remaining_processes`=[] and `success`=true. Root generates it only after the existing BMS cold_stop/UID+PPID check and fresh process enumeration. Retain the actual raw process records; never fill success from this template.

Every retained-audit row has ALL seven keys: `target` (actual path), `exists`:true, `sha256` (actual full hash), `mode`:`644`, `uid`:0, `gid`:0, `label`:`u:object_r:data_file:s0`. Allowed paths are candidate/stock CFG `cfg-stage-<sha>` and `boat-<origin/current boot>.log/.receipt/.intents` under the exact Boat ROOT. Do not guess entries or normalize differing metadata. Unknown entries or differing metadata reject. Full enumeration plus directory journal inode checks remain in original rollback.

## Fill and bind in this order

1. Actual487 completes: pin its original new recipe and `transaction/recipe-receipt.json`. Successor prepare verifies487 placed records/backups and29 directory records. These pins go into successor.route_b, **not** Boat authorization.
2. New window held: copy the current disabled Boat plan, change only execution_enabled to true; compute its final SHA. Fill apply authorization using this hash/current holder/expiry; independently SHA the finalized authorization bytes.
3. Copy original deployment; keep `schema=demo-restore-deployment/v1`, `serial`, provider `layer,serial,targets,program,common,executor` intact. Set deployment.execution_enabled=true, provider.action=apply, provider.prepared={enabled plan path,SHA}, provider.authorization={final authorization path,SHA}. All `{path,sha256}` objects contain exactly those two keys. No cyclic hash: plan → authorization → deployment → successor.
4. Run the frozen `prepare_stage.py` with actual487 recipe/receipt, **this new deployment** and the unchanged full954 seal-candidate pins. Copy its disabled successor, change only execution_enabled=true, compute SHA; call the direct new restore_entry.py --v2-recipe/--recipe-sha256/--out/--execute. Do not use old demo_restore.sh routing.
5. Rollback: retain the SAME enabled plan SHA and original transaction. Fill NEW rollback authorization with current boot/holder/expiry, cleanup pin and actual audit rows. Copy deployment; set provider.action=rollback, provider.authorization=new pin, provider.transaction_dir=original `$RUN/staged/boat/transaction`, provider.transaction={that directory's transaction.json path,actual SHA}. Keep provider.prepared unchanged and use the same candidate seal. New provider output must be fresh.

Exact dispatch commands (root-selected NEXT/RUN/CORE/PROV/PKG as in the previous command card):

```sh
sha() { shasum -a 256 "$1" | cut -d ' ' -f1; }
python3 "$CORE/restore_entry.py" --v2-recipe "$NEXT/recipe.enabled.json" \
  --recipe-sha256 "$(sha "$NEXT/recipe.enabled.json")" --out "$RUN/staged" --execute
python3 "$PROV/boat_provider.py" --seal "$PKG/composed/seal-candidate.json" \
  --serial 5cd1e3dd00000000000000000923012c \
  --deployment "$NEXT/deployment.rollback.json" --out "$RUN/rollback-provider"
```

The second command is the failure/recovery branch, not an instruction to immediately undo a successful candidate. All actual execution stays with root. Neither template authorizes61b or a boot.
