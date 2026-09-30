# r16 full-66 sweep (2026-09-30, 5cd + 61b)

**Result: 2 new apps lit (FitoTrack, mpv); cumulative outer-signed lit = 10.**
Screenshots are the ground truth; every tile below was read by the outer loop at t5 and t10.

| | shard A (5cd) | shard B (61b) |
|---|---|---|
| keys | 33 | 33 (subwaysurfers refused: input SHA mismatch) |
| run_facts totals | `screenshots_captured=66/66 alive_t5=8` | `screenshots_captured=64/64 alive_t5=8` |
| on screen (own UI) | aegis, fd-AppManager, **fd-fitness** | **fd-mpv**, fd-noice, noice, fd-notes, fd-stk, ooniprobe |

Setup on both boards: v3a generation `74d1d6d4` + r16 runtime JAR `6a5d7fca` (bind-mount overlay) + the
network trio (appspawn-x `d977bd15` adding gid 3003, installer libbms `6f94d4f4` / libapk_installer
`eb6824b4` keeping `ohos.permission.INTERNET`). Command: `bms_batch.py --reinstall --hilog 20 --shots 5,10
--focus-check`, key lists in `shardA.txt` / `shardB.txt`. Facts are verbatim in `evidence/facts-*.txt`.

Evidence: `evidence/fd-fitness-5cd-t10.jpeg` (FitoTrack "锻炼" with the units dialog and empty-state hint),
`evidence/fd-mpv-61b-t5.jpeg` (mpv main menu), contact sheets `evidence/sheet-{A-5cd,B-61b}-t10.jpeg`.

## What was wrong before

Two previously signed apps were not on screen, and neither is an r16 JAR regression:

1. **fd-auxio on 5cd** dies at `VelocityTracker.nativeInitialize` (no JNI implementation), exactly as in r15c on
   5cd. It lit on 61b on 09-29 only because #87 single-file-swapped runtime `c835a93e` (registers
   VelocityTracker) and liblog `8c81a937` there. A native fix swapped onto one board is not a fix for the
   campaign until it is in the unified generation (v3c).
2. **fd-droidify on 5cd** now reaches its `SyncService` because r15's in-process `bindService` bridge works;
   the service then calls `Service.startForeground` → `IActivityManager.setServiceForeground` on a null
   `mActivityManager`. Fixing one wall exposed the next one.

## Rules adopted

- Same key, different result on two boards → diff the boards' runtime libraries before suspecting the JAR.
- Every per-board native swap goes into the v3c consolidation list (VelocityTracker runtime + liblog added).
- When a bridge makes a real app component run (services, receivers), give it non-null stub system handles
  (`IActivityManager` no-op proxy in `Service.attach`) per the empty-stub rule — r17, cc-t3.

Open walls from this sweep (white/black with process alive): fd-binaryeye, fd-filemanager, fd-gallery,
fd-tusky, fd-mobile; anki opens its LeakCanary launcher. Wall ranking by blocked-app count: oc-t4 auto_triage;
prediction backtest against `predictions.csv` `bb721a18`: cx-bms.
