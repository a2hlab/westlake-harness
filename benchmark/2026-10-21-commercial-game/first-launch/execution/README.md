# COMMERCIAL-G06 execution on 5ea — actual first blocker: installer ZIP reader rejects the official APK

Lane cc-video (sole device lane). Board 5ea only; 61b/5cd untouched. Plans/hook by Codex (see `../COMMANDS.md`).

## window-outer-01 (15:53:50–15:56:22) — read-only failure before install

`after_lock` hook refused: `G06_REFUSE_KEEP_LOCK: malformed ps row` (kernel threads with spaces in their names);
104 read-only commands, restore 0 commands, smoke/shards not reached; post-check identical; outer-authorized unlock.

## window-outer-02 (lock 15:58:02, unlock 15:59:16; board_run pid 72413)

Main `69d0b2e1e1`, `board_run.py` 6440897e, hook 6c6d7bd0. `after_lock` 0 → smoke PASS (fresh RUNTIME
`fd464714645b`, BOOTIMAGE `ee927db88a67`, zigzag control alive t5/t20; `evidence/smoke-zigzag-t5.jpeg`) → Genshin
shard (wait 60, shots 5/20/60) → `before_unlock` 0 (`RESTORED_NO_INSTALL`, 74.45 s, 11 package dirs ABSENT).

facts (verbatim, `evidence/genshin-facts.txt`):

```
genshin              shots 0/0  alive t5=? last=?  child_hilog=0  app_failed
TOTAL keys=1 screenshots_captured=0/0 alive_t5=0 alive_last=0 alive_unknown=1
```

`bm install` → `error: failed to install bundle. code:9568260 error: install internal error.` No launch, no child,
no screenshot. First fatal (install hilog, `evidence/install-hilog-bms-excerpt.txt`), process `installs` pid 13171:

```
10-21 15:59:05.058 E C01120/BMS: [zip_file.cpp(CheckEndDir:71)]endDir.numDisk != 0
10-21 15:59:05.058 E C01120/BMS: [base_extractor.cpp(Init:43)]open zip file failed, errno:22
10-21 15:59:05.058 E C01122/BMSInstalld: installd_operator.cpp:ExtractApkNativeFiles:3212 APK extractor init failed
10-21 15:59:05.058 E C01121/BMSInstaller: base_bundle_installer.cpp:ProcessBundleInstall:1715 ExtractFiles(APK_NATIVE_SO) failed abi=arm64-v8a ec=8519936
```

Before that, manifest parse (com.miHoYo.Yuanshen vc1241), copy to the `+new` dir and BuildApkResourcesHap all
succeeded. Not a runtime crash. `+new`/stream_install cleanup is known from logs only, not by a device read.

## Deployment binding of the ZIP extractor (read-only, same boot)

`installs` = pid 13171, PPID 1, UID 3060, exe `/system/bin/sa_main`, starttime 19258583 (unchanged across the
clamp). Its maps include `libinstalls.z.so` (inode 5576, `51e1b525…`), `libapk_installer.so` (`7048c7c5…`),
`platformsdk/libappexecfwk_common.z.so` (`c39eba26…`), `platformsdk/libappexecfwk_base.z.so` (`85c84aff…`),
`chipset-sdk/libextractortool.z.so` (`13e03d9c…`). Local same-SHA copies of `libinstalls.z.so` contain every log
literal (`CheckEndDir`@157650, `open zip file failed`@273164, `APK extractor init failed`@289136,
`endDir.numDisk`@301080), the deployed `libappexecfwk_common.z.so` none → **zip_file.cpp/base_extractor.cpp are
linked into `libinstalls.z.so` 51e1b525**. On-board toybox `grep -c` returned 0 for every DSO and is not evidence.

Next: Codex checks `CheckEndDir` against the APK's EOCD bytes. No reinstall or APK edit until a fix is pinned.
Check: `python3 check_execution.py`. Not wired into `commercial_game_first_launch.rs`: that file is SHA-pinned by Codex `../manifest.json`; wiring needs a manifest update by outer/Codex.
