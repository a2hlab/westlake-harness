# Root execution: original61b provider, no new executor

Run from main under the existing outer(codex) canonical lock. This card does not call devices. Use actual postinstall capture and original R5 observation, not the preinstall projection.

```sh
cd "$WORKSPACES/westlake-harness"
B=benchmark/2026-10-09-demo-boatattack/v2-20261013
P="$B/integration/final-v2-f28"
OUT="$WORKSPACES/westlake-harness-t4/$B/integration/final61b-execution-20261013/postinstall-composed"
: "${POSTINSTALL_CAPTURE:?actual complete497 capture.json}"
: "${POSTINSTALL_940:?actual postinstall940 PASS json}"
: "${POSTINSTALL_OBSERVATION:?matching .evidence/observation.json}"
python3 "$P/board61b/provider/prepare.py" --capture "$POSTINSTALL_CAPTURE" --out "$OUT"
python3 "$P/selfcheck/bind_request.py" --template "$P/selfcheck/request.61b.pending.json" --plan "$OUT/plan.disabled.json" --base-selfcheck "$POSTINSTALL_940" --base-observation "$POSTINSTALL_OBSERVATION" --out "$OUT/request.json"
python3 "$P/selfcheck/compile_selfcheck.py" --request "$OUT/request.json" --out "$OUT/composed"
```

Give `plan.disabled.json`, `composed/planned_selfcheck.json`, `composed/composition.json` and `composed/seal-candidate.json` to outer independent review immediately. Expected counts11 placements/7 binds/488 RouteB/954 union; actual UID must be20011207 from new sameboot raw BMS receipts, never a supplied override.

Enable under a fresh remaining budget: clone plan.disabled -> plan.enabled changing only execution_enabled to true. Clone provider.json row; prepared pin points to enabled plan. Authorization required keys exactly: approved_by=outer(codex), plan_sha256=enabled plan SHA, serial=61b0657200000000000000000324012c, origin_boot_id=plan boot, boot_id=actual current same boot, expires_epoch=fresh window cutoff, action=apply, holder=complete `board_note.sh held` stdout.strip() (owner PID timestamp). Add independent user_authorization typed pin as provenance. BMS lane uses owner-only; provider holder must use full line.

Deployment shape: `{"schema":"demo-restore-deployment/v1","execution_enabled":true,"providers":[ROW]}`; ROW retains original program/common/executor/targets/serial/action, plus independently pinned authorization and enabled prepared plan. Provider executable from main:

```sh
python3 "$P/board61b/provider/boat_provider.py" \
 --seal "$OUT/composed/seal-candidate.json" \
 --serial 61b0657200000000000000000324012c \
 --deployment "$STAGE/deployment.enabled.json" --out "$STAGE/boat"
```

No extra execute flag: deployment.execution_enabled controls the real writer. Run the same command with deployment.disabled.json before enabling. Require executor_rc0, PLACED_PENDING_AUTHORIZED_SINGLE_BOOT, transaction exact11 placed records and preserved-verified496 before snapshot/policy and the separately authorized one boot. Do not substitute placement for postboot restoration/selfcheck.

Window maximum30min. Start only with a fresh20min execution budget plus10min recovery reserve; expiry uses actual lock-window start, not generator start. The frozen provider has a2700s subprocess ceiling; it does NOT enforce a30min total window. Outer must enforce the earlier board-window deadline and leave recovery time, preserve partial intent/observation if interrupted. Do not put preinstall+long remaining stage+boot in an already nearly expired window.

Rollback uses the same enabled plan and original transaction, action=rollback, actual current boot, fresh auth with original origin boot, complete holder, cleanup_receipt typed pin (actual sameboot Boat UID20011207 family stopped, remaining_processes=[]), exact retained_audit metadata/SHA list. Row additionally has transaction_dir and transaction typed pin to transaction.json. Invoke the same original provider with rollback deployment and new output; no recursive audit deletion, no parent kill. A candidate boot requires approved recovery boot followed by original baseline selfcheck/control, not merely successful source restoration.
