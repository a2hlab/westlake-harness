# N7 one-window verification

N6 loaded an extra ABI library but did not route the Flutter raster thread through it. N7 instead routes its six-package private EGL facade to already resident HWUI/platform owners. Loading a library is not evidence that its functions ran.

Candidate: `westlake-generation-n7-fa9ec3c6`, manifest `a77c7c6cfdc1c0f78a9f32dad2c184dabe049afedc9674774bd578fab1ab67ff`. Source/build/audit: sibling `2026-10-01-n7-native`, commit `ac22a839f`. The outer review authorized 185 exact findings once on 61b, after U6 releases the board. No permanent exceptions are added.

## Procedure and predictions

- Verify all U5 payload paths through the device and appspawn parent views, RUNTIME `73ecf422dba2`, BOOTIMAGE `0876029078e2`, J6 `2488052f`.
- Preserve the original J6 mount receipt; expose r8b only during native deployment/rollback, then restore J6 before any app test.
- HW/ZigZag first, then aegis/catima/ooniprobe/Auxio/Calendar/Markor. Screenshots require review before targets. Catima was already desktop in the preceding same-board U5 baseline; do not silently claim it as a lit protection control.
- Six Flutter apps: expect the direct EGL calls to enter the resident HWUI wrapper; maps alone do not establish the raster call path. Compare singleton inode counts with same-board U5 records collected on 61b in this window before deployment. The earlier 5ea counts are background evidence only, not this board's acceptance baseline. No constructor-once claim is made from maps.
- Firefox/Fennec: check the specific `__gnu_strerror_r` loader failure independently of whether another failure prevents UI.
- McDonald's/Element: check the specific missing `libz.so` failure; N7 copies the original 1904-byte r109c alias without changing any OH system SONAME.
- Determine fatal causes from the terminating event and its exception chain or crashing thread, not from the first warning in hilog.

`supervise.py` runs in the VM and owns deployment, batches, and final rollback. Four minutes before expiry it terminates only its own batch process group. Its `finally` immediately restores U5, verifies full SHA and both fingerprints, revokes the grant, and unlocks. It never signals the device appspawn parent. Failed rollback verification retains the lock and records an error. Local fault-injection tests cover activation failure, failed control batch, baseline rejection, and failed rollback; seven grant tests cover exact binding and negative cases.

`inputs/` contains local symlinks and is not committed. `input-identities.json` and `input-preflight.json` bind the pinned master manifest to the merged APK inputs. They do not constitute a board result.

## Results

**Not accepted: ZigZag control gate failed.** HelloWorld t20 displays its complete own UI; ZigZag t20 displays the OH desktop. Candidate controls captured four screenshots, with one app alive at t20; exact tool output is in `facts-all.txt` and the run directories. The six expanded controls and all ten targets were not run under N7. No Flutter call-path, owner lookup, shim recovery, or Realm success is claimed.

ZigZag PID 16644 / UID 20010459 terminated at 04:44:35: `libtuanjie.so: inflateInit2_: symbol not found` → JNI FatalError → ART abort → SIGABRT. `zigzag-terminal-chain.txt` preserves original hilog line numbers and crashing-thread frames; signal 4 FREEZE noise was excluded. The new root-level libz alias is a namespace-resolution suspect, **not an isolated causal conclusion**: no same-window U5 ZigZag run was taken. Copying a validated alias's bytes did not validate this new loading domain.

The VM supervisor restored U5 and unlocked at **04:47:53**, before the original **05:00:59** cutoff. Full live-path and appspawn-parent-view hashes passed; runtime `73ecf422dba2`, boot image `0876029078e2`, J6 `2488052f`. The one-window grant is revoked. `results.json` identifies the exact final receipt.

### Orchestration errors disclosed

The initial baseline sweep unnecessarily scheduled seven keys; it was shortened to the outer-requested LocalSend plus an already captured Aegis baseline. Only our own VM supervisor/batch/observer processes were stopped; the device appspawn parent was not signalled. The successor kept the original expiry.

The successor then misclassified a complete LocalSend batch returning rc=1 as a transport failure. It verified U5 and unlocked without ever deploying N7. The runner was corrected to distinguish complete records/two captured shots from execution failure; a regression test now covers this outcome. We reacquired the board under the same original cutoff and performed exactly one N7 activation. The premature result and grant revocation are retained separately; neither is hidden or counted as a candidate experiment.

Five supervisor fault-injection tests and seven grant-binding tests pass. The offline N7 lifecycle is recorded separately; its passing ELF/source tests do not establish board acceptance. The earlier offline contract's board-write prohibition was superseded only for this window by outer ACK(90) 04:15 and 04:30; its offline verdicts remain offline.
