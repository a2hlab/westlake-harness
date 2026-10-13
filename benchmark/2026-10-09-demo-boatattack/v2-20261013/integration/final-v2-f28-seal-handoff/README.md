# V2 f28 final seal wiring — disabled offline handoff

The existing `demo_seal_61b --mode v2` is not the current f28 deployment path. Its fixed workflow writes DISABLED, performs a bare reboot, invokes the old installer, then reboots again. The current t5 contract calls for all layers together and one final reboot. Repointing one runtime path cannot fix that mismatch. No orchestration, provider, validator, frozen package, or device was changed for this handoff.

`source-pins.json` identifies the signed V1 seal/signoff, original real R5 checks, seven locally SHA-verified artifacts, actual 5ea GAME_PASS/fresh337 provenance and the current tools. `objects.disabled.json` declares the seven bind objects and four controls. `assembly.disabled.json` leaves all execution/signature fields disabled/pending. `demo-seal.plan.disabled.json` retains the original orchestration schema for inspection and is rejected by its actual validator as disabled. **It must not be enabled: changing false to true does not implement the missing wiring.**

The current 5ea game/fresh337 boot is `b7116cfc-14c0-43cb-b46b-c233ce5f13a6`. The historical 61b baseline capture is boot `9f5af7c8-d359-4c25-99c6-63206b50cf0a`, Boat unregistered, UID null, APK and signal placeholder absent, two stock private libraries present. This is not a fresh deployment capture. Do not borrow 5ea UID20011062, its RouteB absence, boot, source inodes or authorization for61b.

## Concrete minimum gaps

| Existing location | Exact gap | Smallest reuse |
|---|---|---|
| `scripts/lab/demo_seal_61b.py:354–403` | Always disables/reboots/reinstalls before final reboot; no incremental Boat provider phase | New explicit reviewed incremental dispatch around the existing staged entry, snapshot, policy, acceptance and seal compiler. Preserve default historical workflow; never call its current execute branch on signed61b. |
| `final-v2-candidate-r2/candidate_contract.py:94–101,130–146` and `prepare.py` | Exact r4 seven-bind SHA, worker and artifact equality still lock runtime947 | New sibling derived from this provider: replace only runtime source/after SHA947→f28, table SHA and worker verify-bound runtime SHA. Preserve stock187 apply guard, ns/no_parent, all transaction/preimage/partial/rollback checks and RouteB488. Rebuild complete11-member/7-bind plan from actual61b postinstall metadata. |
| `final-v2-entry/restore_entry.py` | Exact provider/executor pins and local r2 executor path | Narrow successor pin/path update; retain RouteB verify-existing → Boat placement and STOP on any failure. Missing-only APK/empty placeholder preinstall is a separate existing phase, followed by mandatory new BMS UID capture. |
| `final-v2-selfcheck/compile_selfcheck.py:10,47` | Provider freeze allowlist and validated program pins admit947 frozen packages only | New narrowly pinned compiler version accepting the reviewed f28 provider; preserve original R5/raw/parameter validators. Existing union/observer composition remains the mechanism. |
| t0 `final-v2-identity-61b/candidate_identity.py:28` | Compiler SHA fixed to prior union producer; package is present in t0, not current main | Land reviewed board-specific successor with exact new compiler/program pins; keep full954, actual RouteB presence, BMS UID, metadata, original319 and original128 driver. Existing5ea fresh337 is source evidence only. |
| `demo_seal_61b.py:437–443` | Preparation argv lacks candidate-proof arguments required by the candidate driver; its regression admission is separately pinned | Narrow explicit candidate argv/pins, or invoke the existing61b candidate prepare entry then original eight-window executor. Do not substitute a path while retaining incompatible argv. |
| Snapshot/seal pipeline | V1 `step-2-r5.py` source allowlist and `step-3.py` explicitly assume Boat absent | Derive full group/source map and explicit admitted Boat overlay. Use original capture/build_seal, independent WMS observation, realization compiler and R5 collector. Do not relabel V1 SHA differences as UID/WID changes. |

The old orchestrator also requires literal `approved_by=outer(claude)` for its authorization/guard/regression admission. A root `outer(codex)` receipt is not automatically compatible with this legacy entry. Record the interface gap; do not fabricate a signer or silently relax validation. User unseal permission is a separate requirement from either outer literal.

## Exact object accounting

Keeping the current independent Boat root gives **954 unique targets = original940 +13 files +1 APK**: seven new immutable sources, three new controls, three private bind targets, plus Boat APK. Five existing files change: adapter, JAR, runtime, libandroid, and U13 recovery cfg. Original319 remains315 unchanged +4 explicit shared replacements. Original811 file objects become824; original129 packages become130. `union-targets.disabled.json` mechanically computes these sets from actual V1 R5 checks and the original11/7 plan. It is a path union, not a full compiled SHA proof: table/worker depend on the final capture and remain unresolved.

Boat sources are8ab adapter,633 JAR,7a93 signal-box,1bea unity,f6b8 il2cpp,f28 runtime andadc libandroid. ADC belongs at libandroid9cc's original target; it must not overwrite runtime187. ADC remains historical exact-reuse/49-byte replay provenance with original source-build closure incomplete; no new provenance claim is made. The actual deployed f28 source, build log and archive receipt are pinned.

## Required sequence and pending evidence

1. Finish the current5ea ten-control/full128 run under its current authorization. Require eight original window receipts, all128 exact records/APK pins/screenshots, full membership/boot/identity bookends, original comparison and outer visual review. `round-complete.json` itself says UI pending; it is not acceptance. Preserve the final original947 recovery result/lock disposition. No results from the rejected947 full128 may replace this f28 round.
2. **Only the user can approve unsealing61b.** Until that explicit approval, zero61b operations. Existing approval for parameter derivation and a5ea batch does not authorize61b changes. Keep that authorization null in this draft.
3. After approval and root window: fresh original61b R5/319/RouteB/CFG evidence; existing missing-only fixed8dc APK registration and controlled empty signal target creation, preserving both stock libraries; then fresh sameboot BMS UID/version/APK and complete497/319 metadata capture. Never mark the historical incomplete capture complete.
4. Offline compile the new f28 provider plan and a single full planned union; all11 placement objects, seven targets, Boat APK, RouteB487+HAP, directories and original inventory are bound. Postinstall boot/UID/cfg/raw pins are actual inputs, not constants. Obtain outer placement authorization only after this plan is concrete.
5. Stage all layers without rewriting RouteB data. Snapshot only original allowed mount/label targets plus true binds/system cfg; source/control SHA+metadata are checked by the installer, not smuggled into unsupported snapshot domains. Run original sepolicy proof. Only then the one authorized final boot. New boot is unknown until observed.
6. Read independent sameboot host/WMS evidence. Derive only permitted WL_PARENT_ID/UID/GID/serial/control-root changes through the original exact realization mechanism. Keep whole-file SHA; never exempt run.sh. New f28 behavior is a declared V2 overlay, not parameter-only realization of V1.
7. Real full V2 R5/nonfile check, Boat UI/LAP/steering, RouteB live UI and applicable full128 acceptance remain required.5ea's RouteB-ABSENT337 proof cannot replace a61b RouteB-present proof. Preserve V1 Plan2 scope history without inventing a new61b128 PASS or silently borrowing that exception for V2.
8. Rehearse the complete f28 Boat+RouteB restoration on a spare via existing exact restore/staged provider/R5 mechanism. Existing5ea Boat-only and old5cd947/187 windows do not prove this. After actual full capture, build a separate V2 seal/candidate, compile exact realization and append independent signoff. Never overwrite the signed V1 seal, appendices or raw evidence.

## Existing local CLI seams (inputs still pending)

These show the existing interfaces to be reused by the narrowly updated siblings. They are not executable deployment instructions, and no device command is provided here.

```sh
# Missing-only request compilation after a fresh authorized capture; local only.
python3 "$V2_ENTRY/prepare_request.py" --capture "$PREINSTALL_CAPTURE" --apk "$ORIGINAL_8DC_APK" --out "$NEW_PREINSTALL_OUT"
# New f28 provider sibling, once implemented/reviewed; actual postinstall capture required.
python3 "$F28_PROVIDER/prepare.py" --capture "$POSTINSTALL_CAPTURE" --out "$BOAT_DISABLED"
python3 "$F28_SELFCHECK/bind_request.py" --template "$REQUEST_61B_TEMPLATE" --plan "$BOAT_DISABLED/plan.disabled.json" --out "$BOUND_REQUEST"
python3 "$F28_SELFCHECK/compile_selfcheck.py" --request "$BOUND_REQUEST" --out "$COMPOSITION"
python3 "$F28_IDENTITY/compile_candidate.py" --request "$IDENTITY_REQUEST" --out "$IDENTITY_OUT"
python3 "$F28_IDENTITY/run_candidate_post_reboot.py" --out "$ROUND_OUT" --boot-before "$ACTUAL_ORIGIN_BOOT" --serial 61b0657200000000000000000324012c --candidate-proof "$IDENTITY_OUT/candidate-proof.json" --candidate-proof-sha256 "$PROOF_SHA" --smoke "$IDENTITY_OUT/smoke.json"
# After actual final snapshot/complete inventories/admitted overlays, offline seal compilation.
python3 "$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-baseline/t5/build_seal.py" --snapshot "$ACTUAL_SNAPSHOT" --overlays "$ADMITTED_OVERLAYS" --manifest "$MANIFEST128" --out "$NEW_V2_SEAL"
python3 "$WORKSPACES/westlake-harness/benchmark/2026-10-12-exact-realization/realization.py" compile --request "$V2_EXACT_REQUEST" --out "$NEW_REALIZATION"
```

No new executor or framework is introduced. This handoff is data, source pins and precise missing seams. `verification.json` records seven artifact SHA checks, mechanical954 membership and an actual disabled rejection by the existing orchestrator validator. No board/VM/SSH command, signing, installation or live test occurred.
