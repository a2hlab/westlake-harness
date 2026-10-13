# Independent review of the disabled v2 entry

The initial provider accepted a declared UID without deriving it from its raw BMS receipt. The r2 provider now parses dedicated boot/BMS/boot receipt triplets and checks the live UID before writes. T0 separately reviewed that correction; this outer review independently copied all 53 frozen provider/entry files into a detached worktree at main commit `629d1444ab` and verified every source hash.

The isolated candidate suite passed **9/9** and the entry/preinstallation suite passed **12/12**. The source review covered missing-only installation, preservation of existing native libraries, foreign-placeholder refusal, the original R5 Route B check, the real Boat placement receipt and the explicit stop before reboot/final acceptance. Preview tests prohibit transport. None of these tests touched a device.

`results.json` is **OFFLINE_ACCEPT_NOT_DEVICE_ADMISSION**. The provider and entry landed through the repository tool as `cd3bde6703` and `2d9e6cd57b`. The first entry landing stopped at the branch-point guard. A byte comparison proved that current main's complete v1 wrapper body remained unchanged; only the reviewed v2 dispatch block was added. `branch-point-guard-review.json` and `wrapper-reviewed.diff` record that narrow exception. No existing behavior was dropped.

The code is currently 61b-only. Main-tree execution requests must be regenerated with the pinned compiler after landing: the author's original disabled examples bind the T4 worktree. Complete spare rehearsal, actual postinstallation identity, the full regression and final protected-board authorization remain separate requirements.
