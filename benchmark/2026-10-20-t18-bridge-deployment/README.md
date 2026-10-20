# T18: one fifth bridge artifact in the original guarded T17 transaction

The T17 routing set did not remove Toutiao's `AudioTrack.native_get_buffer_size_frames` JNI wall. This executor mechanically derives from the exact T17 executor07e8e501 and adds only the actual runtime-root `liboh_adapter_bridge.so` as a fifth physical artifact. It does not claim audio, moving video, a random-exit repair or a seal. No device command or runtime build was run by this author.

The bridge before image is d4fae8e5802f3153a85175243edf665714900381d463ffc5ca1e64d0b308775b; candidate dca530eb4b1b53e5dd0ecc41c36953f7463609c5b70bbdf67a49dc3cae17f9d9. Production receipts are pinned separately in `bridge-candidate.json`. The two full candidate builds, input pins and old baseline relink belong to that production package; this package is the deployment recipe. An empty/null candidate hash, missing production status/reference or reference drift refuses before Board construction. The default remains zero-device preview even with a frozen candidate.

## Exact reused behavior and added checks

`derive.py --repo "$REPO"` rejects a changed donor, preserves Board/deadlines, `pathguard`, `fg`, `swap` and WID normalization, and emits the reviewed executor byte for byte. The existing R9 run/media/player/OpenSL set and unchanged network-provider guards remain. Stage and original-backup names change to T18; no T16/T17 apply-plan or backup is borrowed.

`bridge-target-evidence.json` binds the historical T17 physical path and actual child mapped pathname. This is the app-owned runtime root, **not** `/system/android/lib64`. Fresh preflight checks the current physical bridge hash, explicitly admitted mode/UID/GID/label, and parent-private bridge hash/metadata/dev:inode. `/proc/PID/root` is the intentional namespace link, allowed only under the original same-boot/PID-birth/UID/tracer/executable/mount guards. No arbitrary symlink ancestry is accepted for the physical target or backups.

The original apply-plan is persisted before stage mutation. Four backups (run/media/player/bridge) must all be complete and verified before the first replacement. Bridge is replaced first, followed by the original media/player/compat/run order. A partial failure retains the original plan and every command receipt. Rollback accepts only before/candidate byte states, matching metadata, same executor/candidate/source/holder/window and original apply-plan SHA. A changed target without its valid original backup is refused. Bridge always restores exactd4fa; absent-only compat is removed only when its candidate hash matches. No-parent recovery remains physical only, and neither physical success nor a surviving old child proves the new runtime.

The window remains1800seconds with600seconds reserved for recovery. Apply and rollback both require fresh boot verification afterwards. The outer owns reboot, normal icon/feed, the same518+26 snapshot/supplement, original control/parameter/power restoration and lock closure; the executor does none of those automatically. Runtime JNI registration and disappearance of this exact wall require fresh actual logs. Sound and video remain separate acceptance.

## Outer execution order

1. Land the exact T18 production references into `$REPO`; retain the original raw build and materialized input archive durably. Independently review this executor.
2. Make a fresh, locked5cd read using the existing outer identity collector. Fill a new private `admission.template.json`: exact holder/start/boot, current parent mount, host PID/birth, and actual bridge metadata (`mode:20011300:20011300`) and label. No historical PID, WID, mode or inode is supplied as authorization. The copied unsigned template is intentionally unusable.
3. Prepare `$INPUTS` with the same three R8 binaries and copy the exact production candidate bytes to `$INPUTS/liboh_adapter_bridge.so`. The production archive calls the output `candidate.so`; only this local filename changes. All four file hashes are checked before apply. `run.sh` remains the exact local reference derived by the existing logic.
4. Run the original CLI in this directory, first preview, then explicit approved preflight/apply. Use a new persistent output directory each time. On any failure or recovery deadline, use the original apply/plan.json and a fresh current-boot rollback admission; preserve the original holder/start. `--recovery-no-parent` is rollback-only and never extends the window.

```sh
python3 "$REPO/benchmark/2026-10-20-t18-bridge-deployment/executor.py" preflight
# After the outer has filled and independently signed the current admission:
python3 "$REPO/benchmark/2026-10-20-t18-bridge-deployment/executor.py" preflight \
  --execute --repo "$REPO" --inputs "$INPUTS" --hdc "$HDC" \
  --holder "$EXACT_HOLDER" --start "$WINDOW_START" --boot "$CURRENT_BOOT" \
  --parent "$PARENT" --birth "$PARENT_BIRTH" --admission "$ADMISSION" --out "$NEW_PERSISTENT_OUT"
```

Apply uses the same admitted input set with mode `apply` and a fresh output. Rollback additionally passes `--apply-plan "$APPLY_OUT/plan.json"` and binds its SHA in the rollback admission. The tool does not signal a process, reboot, unlock or decide playback.

## Offline verification

The unchanged eight T17 host tests exercise real shell CAS and negative guards. Four added tests cover candidate/production refusal, donor drift, inherited checks and actual generated transaction partial recovery. The latter executes the production `script=pre` segment with real files, cp/mv/hash operations; interruption after each of the first four renames produces mixed original/candidate state, then the same rollback generation restores the originals and removes compat. The first rename asserts that all four backups already exist. Only host stat/owner/SELinux utility seams are adapted, so host PASS is not board metadata validation. Rust invokes these same suites. Live acceptance stays human pending review.

Strict lifecycle completed with3 passed,0 failed and1 human PendingReview (rc1), as required for the unexecuted live window. Its first isolated-context run lacked the already-existing MAIN project spec; that failure is retained separately. The repeat used an exact read-only copy of the MAIN project contract, excluded from this landing.
