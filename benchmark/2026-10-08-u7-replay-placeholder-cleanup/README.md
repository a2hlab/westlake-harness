# Post-reboot replay removes only declared empty additions

Evidence first: the original 61b U14 transaction declared `/system/android/lib64/libicu74compat.so` in `plan.additions[0]`, with operation 30 marked `absent=true`. After a new boot, the approved original executor replayed all baseline layers and verified the signed 124-path runtime fingerprint `452447a4a0ba`. The broader smoke capture still saw the candidate's empty placeholder, producing a 125-path fingerprint `204ab50509d1`. Original recovery evidence is in `benchmark/2026-10-08-61b-newboot-recovery/`; outer explicitly identified this transaction-owned placeholder on 2026-10-08 at 21:55:26.

## Change and safety boundary

`scripts/lab/u7_executor.py::replay_baseline` now cleans only `previous['plan']['additions']`, after replaying baseline mounts and before starting the parent. Each target requires the same boot, stopped parent/children, and no exact mount-point entry. It reuses `DeviceIO.remove_placeholder`: absent is harmless; a present file must have SHA256 EMPTY or deletion is rejected. Each cleanup phase is journaled. The full baseline SHA check now also verifies every declared addition is absent.

Mounted or nonempty additions are rejected. The existing exception path records `recovery_required`, keeps the parent stopped and leaves the lock for inspection. Unrelated paths are never passed to removal. No frozen artifact, original signed fingerprint, smoke criterion, boot-ownership assertion, native policy or startup configuration was changed. The production master tool was left unchanged throughout the live recovery; the implementation here is an offline handoff.

## Verification

Both Mac and a2hlab VM ran `benchmark/2026-10-01-u7-executor/test_executor.py`: **30 tests, OK, rc=0**. Five new cases cover empty-placeholder cleanup before parent start, an already absent addition, nonempty refusal, mounted refusal, and an undeclared file never being removed. Existing replay/transaction/rollback/provenance tests remain green. `N2 refused` and non-rollout-ready messages in the logs are expected negative-test output.

Logs: [Mac](tests-mac.log), [VM](tests-vm.log). These are offline fake-device tests, not new board validation. The actual one-path cleanup and unchanged smoke/final recovery are separately recorded in the recovery report.

Landing replaces the executor and its existing test module, and adds this report. Outer should land it only after 61b recovery is complete and the lock released, preserving the pinned tool bytes during the live window.

## Explicit four-case handoff (window7)

The focused `BaselineReplayPlaceholderTests -v` run passed all five cases on both Mac and VM. `regression-matrix.json` maps each of the four requested conditions to its exact test and source line. The success test asserts removal **before** parent start; refusal tests assert no start and unchanged contents; the undeclared test asserts the removal helper is never called. See [focused Mac output](focused-tests-mac.log) and [focused VM output](focused-tests-vm.log). These tests already accompany the implementation; this handoff makes their independent results explicit.
