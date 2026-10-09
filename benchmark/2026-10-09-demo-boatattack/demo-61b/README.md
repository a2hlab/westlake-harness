# BoatAttack on the 61b demo board

The spare-board route2d driver cannot be used unchanged: it uninstalls every regression app and removes their data. This window retains the 128 already-installed demo apps, uses the master board runner through the existing launch-only demo adapter, and rolls back only the five journalled overlay mounts plus the newly installed BoatAttack package on failure.

## Frozen inputs and source

`inputs.json` pins the original APK and all five approved members. Recipe and touch commands come from `westlake-harness-wiki/benchmark/2026-10-09-demo-boatattack/spare-5cd/run_boat_route2d.sh`, with the acceptance evidence in `RESULT-route2d.md`. C8 adapter replaces 84695d62 with 8ab85446; C9-only non-BCP JAR replaces bbc3f530 with 6333bcab; three private natives are 1bea0fae/f6b806b5/7a931c79. No APK modification, provider rebuild, foundation restart, or other-board write.

## Window and rollback

`plan.json` invokes `demo_board_run.py --detach`, using canonical master board_run and bms_batch. The 30-minute window has a 20-minute new-test cutoff. `window_hook.py apply` validates the original 319 identities, full shared-base SHAs, parent11752 and boot131b8ff9, installs only BoatAttack, uses the accepted B1 sandbox recipe, and adds five binds. It captures 1920×1200 racing plus five approved touches, reads the same BMS-UID child PID after each touch, and waits for explicit screenshot review. Activation smoke checks the new runtime fingerprint3cac428ba219, original boot fingerprintee927db88a67, child-view hashes, and existing U13 library-copy bounds.

Ten `selected-signoff.json` keys have outer t3 verdict=lit, including LibreSudoku and2048. They are launched without reinstall/uninstall, with real t5/t20 captures. Retention requires all ten records, smoke PASS, explicit screenshot review, and final 322-path equality (319 baseline paths with two substitutions plus three private additions). Counts come only from run_facts.

`rollback.sh` requires the cx-t0 lock. It cold-stops only the installed Boat UID, unwinds only exact journalled top mounts with matching source-root and effective SHA, deletes only its guarded empty signal-box placeholder, uninstalls only the newly installed Boat package, verifies original319/runtime/boot/parent/bootID, and runs original U13 restoration smoke. Foreign mounts, SHA drift, or failed restoration retain the lock. Staging/evidence are preserved.

## Seal integration

The approved configuration contains five members, whereas the old seal slot described four. `t5/build_seal.py` now requires exactly one adapter at `/system/android/lib64/liboh_adapter_bridge.so`, one JAR and three private members. No generic extra member is accepted. A negative fixture rejects a missing or mis-targeted adapter. The independent Toutiao slot is preserved. After the user mandated rollback, the BoatAttack slot is marked `absent`, with the exact five-member tested configuration retained separately; it is not falsely marked active.

## Verification

Seven final transaction known answers passed on Mac and a2hlab (including the restored-group HDC PATH regression), including input drift refusal and `/data` mount-root handling. Sixteen seal tests passed. Pre-lock readonly receipt:319 diff{}, runtime452447a4a0ba, bootee927db88a67. On-board facts, screenshots and retained/rollback receipt are collected under `window1/`; screenshots remain the UI ground truth. Final readout is pending until the window completes.

## Final result and correction

All six Boat screenshots are1920×1200. Same child PID28544 was checked after every touch. The actual racing viewpoints/minimap changed and accel2 displaysKPH001. Ten regression t20 captures show their own interfaces in the contact sheet; final external screenshot signoff remains pending, with no self-reported lit aggregate. `evidence/facts.txt` is verbatim run_facts over an index linking the ten real records. An initial invocation against the parent runner directory found0records; that wrong-directory diagnostic is preserved under `window1/facts-wrong-parent-diagnostic.txt` and is not used for counts.

Outer ACK(91)06:00 superseded retention: all five binds were removed and the newly installed APK uninstalled. Final319diff{}, runtime452447a4a0ba, bootee927db88a67, parent11752 and boot131b8ff9 are unchanged. Boat BMS entry and owned mounts are absent. Initial restoration smoke failed because activation_smoke forwards its explicit HDC option only to the child probe, while its group bms_batch still resolves `hdc` from PATH. The lock remained held; a task-local VM PATH wrapper fixed this tool error. The exact original restoration spec then passed and HW/ZZ t20 images showed their interfaces. Final read-only identity passed before manual UNLOCK, at about19minutes. No OrbStack restart or other-board operation occurred.

Legacy agent-spec lifecycle returnedrc1:all four scenarios skipped because the two BoatAttack Rust selectors match zero tests in the current repository. This is reported rather than substituting the direct unit results for contract completion. The original contract's nine-generation table/static and desktop-launch historical work is outside this transfer window; Boat launch in this window uses the same explicit aa start as validated route2d. No claim of desktop-launch verification is made.
