# Board inventory of the three U2 boards: the reference a clean board is diffed against

**Why.** The lab boards reached the unified state U2 in layers over several days (PR03 BMS restore, B79/B89
installers, FZ-001, generations v3c → N2, JAR overlay). The runtime fingerprint covers 119 files; nothing
recorded the rest of what those layers left on `/system`. A clean board brought up elsewhere could therefore
look "done" and still miss a file. These inventories are the ground truth for that comparison.

**What.** `scripts/lab/board_inventory.sh <serial> <dir>` (read-only) on 5ea / 61b / 5cd at U2, 2026-09-30 15:0x:
props (device IDs stripped), every `/system` file with size+mtime and sha256 (4848–4849 files), all of
`/system/android` (239 files), `/data/local/tmp` layout and its jar/so/hap/apk hashes, mountinfo (the JAR
overlay), `bm dump -a`, SELinux mode, appspawn-x, hilog buffers.

**Findings.**
- `/system/android` is identical on all three boards (239/239).
- `/system` differs only in experiment leftovers: 61b carries a different `libinstalls.z.so` (both copies; the
  5ea/5cd one is the PR03 payload's, which `bringup_clean_board.py diff` names as its source) and
  `wl_toutiao.cfg.disabled`; 5cd still has `/system/etc/init/wl_toutiao.cfg` (Toutiao autostart experiment).
  Neither is part of U2.
- Factory `/system` mtimes are mixed (3501 of 4848 files are newer than `ohos.para`), so drift is found by
  hash, not by timestamp.
- The installer swap tool in the FZ-001 package refuses any starting pair but the B89 baseline and hard-codes
  one serial and the old Mac's paths; a clean board cannot use it as is → `scripts/lab/swap_installer.py`
  (same transaction, `--serial` from `knowledge/boards.json`, `--accept-baseline`).

**Rule.** A board is at U2 when `bringup_clean_board.py diff <serial>` reports 0 missing / 0 different
against this reference (board-specific leftovers excepted) and `bms_batch` facts start with
`RUNTIME fingerprint=937e2a6d0d88`. The bring-up order is `bringup_clean_board.py plan`.
