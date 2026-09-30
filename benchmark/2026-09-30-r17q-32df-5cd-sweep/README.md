# r17q + graphics 32df full sweep on 5cd: 17 lit, no new app; the white screens are the installer

**Result.** 5cd ran all 66 keys on native package v3c `668e4f7c` with runtime
`liboh_android_runtime.so` 32dfac83 (graphics session sync + BLAST methods), JAR r17q
`94424d60`, old installer. Unedited facts total:
`TOTAL keys=66 screenshots_captured=126/126 alive_t5=28 alive_t20=26`.

Read from the t20 tiles (`evidence/sheet-5cd-t20.jpeg`, keys in case-insensitive name
order, 11 per row), 17 apps show their own UI: Aegis, AntennaPod, AppManager (verifying
splash), Auxio, Fossify Calendar, Amaze, KeePassDX, Droid-ify, Etar, FitoTrack, Luanti
(loading page), mpv, NetGuard, Fossify Notes, SuperTuxKart, Tasks.org, OONI. All were
already signed; the cumulative count stays at 23.

## What was wrong before

32df was built to fix the "BLAST white screen" family (K-9, Tusky, AppManager). On 5cd
those apps are still white, and so are Thunderbird, Fossify File Manager, Gallery and
BinaryEye: the same set that is white on 61b with the old installer. In cx-t0's 61b
installer A/B (commit 82fc1c00 in westlake-harness-bms-deploy), Thunderbird, K-9, Tusky
and File Manager turned into their own pages when only the installer (plus a forced
reboot) changed, and the same trace went from a WMS background denial to
`canStartAbilityFromBackground:1`. For these four the white screen is the blocked
background launch of the second Activity, not the BLAST sync path.

## Rule

`evidence/compare-vs-61b-r17p.txt` is the `compare_runs.py` output against the 61b r17p
sweep: 3 variables (board, JAR, runtime). No per-app difference in this sweep is
attributed to 32df alone. On 5ea, 32df's only unique gain was Wikipedia's onboarding page
at t5, and it broke AntennaPod, so 5ea was rolled back to runtime 9e14bf20.

Raw run directory (not committed): `runs/r17q-32df-all-5cd/`.
