# Explicit v2 staging, with a fresh-capture barrier

The old wrapper could neither dispatch Boat nor distinguish placement from completed recovery. This delta adds only the explicit `--v2-recipe` route; deleting that inserted block reproduces the original wrapper bytes. Default, `--realization` and `--directory-recipe` paths remain unchanged. No legacy bare-reboot/reinstall seal flow is invoked.

**Scope: 61b only, disabled requests, zero device operations in this delivery. No complete v2 spare restoration rehearsal has occurred.** 5ea currently proves Boat without RouteB. 5cd has the prior v1 r5/487 + empty-directory closure and is a suitable next combined-state rehearsal target, but the current entry/provider rejects it. The small follow-up must derive actual5cd APK/UID/private targets/cfg/root metadata, retain complete RouteB20011300 and independently observed WID, make a separately reviewed serial-aware Boat provider and identity proof, then compose existing r2 restore + r4b directory completion + Boat + one authorized boot + r5 full v2 selfcheck. Nothing here claims that follow-up passed.

## Two explicit phases

1. `phase=preinstall`: `prepare_boat.py` uses the original SHA-pinned BMS Board and byte-identical missing-only `install_one`. It protects/backups the two existing stock libraries before installing original APK8dc, then verifies their exact bytes/metadata after installation. BMS unknown/transport failure is never absence; registered drift is never reinstalled. It creates only a missing zero-byte signal-box target with 644/0/0/data_app_el1_file metadata, fail-if-exists and exact readback. The policy comes from historical `boat-attack-apk-lightup.sh:470` and t3 worker:44–46, not from APK contents. No bundle directory is deleted, no parent is killed, no app is launched. The result is `PREINSTALL_COMPLETE_PENDING_FRESH_CAPTURE`; execution stops there. Original install records, stock backups and placeholder intent/readback are retained. A failed installation is not automatically uninstalled, because the pre-existing nonempty private directory must be preserved; failure remains stopped with evidence for outer recovery.
2. Root obtains a new same-boot BMS UID/private-file/cfg/RouteB/319 capture and compiles/reviews a new disabled r2 Boat plan. `phase=placement` runs the pinned r5 live verification of existing RouteB, or r2 restoration followed by r3 admission of all487 original receipts, then invokes the actual Boat provider with standard argv. Any rc failure or incomplete receipt stops before the next stage. Child budgets/lock/admission rules remain; the parent adds no competing transaction timeout. Success is pending the separately authorized single boot and complete new-identity selfcheck, never restored or signed.

Both phases use the same explicit entry:

```sh
bash scripts/lab/demo_restore.sh --v2-recipe "$RECIPE" --recipe-sha256 "$SHA256" --out "$FRESH_OUT"
# Only root's later authorized execution adds --execute with enabled, independently pinned inputs.
```

`preinstall-61b-disabled/` was actually assembled from root's same-boot9f5 preinstall capture and the local original143881767-byte APK; no UID or new private preimage was fabricated. `prepare_boat.py` real CLI preview and the wrapper's real v2 preview both returned rc0 with zero device calls. The request intentionally has `execution_enabled=false` and `PENDING_REAL_LOCK_HOLDER`. Rebuild/repin transport holder and execution state under root authorization; no placeholder holder is a production lock. APK bytes remain external, referenced by exact SHA and a relative `app-input.json` source path.

```sh
python3 prepare_request.py --capture "$PREINSTALL_CAPTURE" --apk "$ORIGINAL_8DC_APK" --out "$NEW_DISABLED_REQUEST"
python3 prepare_boat.py --request "$NEW_DISABLED_REQUEST/request.disabled.json" --request-sha256 "$REQUEST_SHA" --out "$FRESH_OUT"
```

`placement.request.example.json` lists the precise next-phase input shape; it is intentionally incomplete and cannot execute before postinstall capture/admission. `SYNC-T0.md` and `identity-interface.json` identify the external full128 adaptation owned by T0. The old 5ea identity-r4 absence proof must not be reused on61b. Original full128 membership, all three identity hook points, collect/comparison and special slots stay intact.

## Object accounting and tests

`count_union.py` mechanically keeps all v1 file/package entries, adds Boat18 targets and its original APK, and reports the complete union. The current r4-shape proposal yields 824 unique files (811+13, with5 old-file replacements), 130 packages (129+Boat) and954 unique expected objects. All three private targets are included. `expected-union.json` is an expected inventory, not a sealed object or actual readback.

Six entry tests cover unchanged-v1 bytes, six argv dispatches, bash syntax, RouteB-before-Boat, failure STOP, full487 history admission dispatch and the preinstall barrier. Six preinstall known-answer tests execute the original install_one on a recording Board: positive registration/placeholder, unknown transport, stock drift before and after installation, existing APK drift and foreign placeholder. No production lock or live device is simulated as evidence. Provider UID guards have their separate nine-test suite.

## Next spare input, not current coverage

Root has collected `outer/5cd-v2-readonly-preinstall/{capture.json,summary.json}` at boot8d0f7543: original319 equal; Boat BMS/APK/signal missing, two stock libraries present; the three RouteB directories have actual UID20011300. This first capture reused the61b target list: only474 targets overlap the original5cd R5 inventory and match. It is not a complete5cd RouteB capture. Root is collecting the original5cd940 objects separately. This delivery remains61b-only; an independent next version must bind those real5cd sources and postinstall UID/private receipts before the combined recovery rehearsal. No61b capture, historical940 count or5ea absence is substituted for that evidence.
