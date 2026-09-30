# Unified state on 5cd: 21 of the 23 signed apps on one board

**Result.** 5cd ran all 66 keys on the state all later work builds on: native package
v3c `668e4f7c`, runtime `liboh_android_runtime.so` 9e14bf20, JAR r17r `dd4f0eae`,
background-launch installer (libbms 6aadb8b4 / libapk_installer 7048c7c5). Unedited facts
total: `TOTAL keys=66 screenshots_captured=126/126 alive_t5=28 alive_t20=27`.

Read from the t20 tiles (`evidence/sheet-5cd-t20.jpeg`, keys in case-insensitive name
order, 11 per row), **21 apps show their own UI at t20**, the most on one board so far
(previous best: 18 on 5ea under r17p):

Aegis (welcome), AntennaPod (home), Thunderbird and K-9 (database upgrade page), Auxio,
Fossify Calendar, Amaze, KeePassDX, Droid-ify, Etar (week view), Fossify File Manager,
FitoTrack, Luanti (loading page), mpv, NetGuard, Fossify Notes, SuperTuxKart, Tasks.org,
Tusky (login), Markor (its own onboarding page, `evidence/markor-5cd-t20.jpeg`), OONI.

Of the 23 signed apps, two are missing here: AppManager (white; on the old installer it
stops at its own "verifying" splash, and its second Activity is white on the new one) and
Noice (dies in `AudioProductStrategy.native_list_audio_product_strategies` before any UI).

## What was wrong before

Each board had been carrying a different mix (JAR r17p/r17q/r17r, runtime 9e14/32df, old or
new installer), so no single run showed what the combined fixes light together. The
per-board counts (15-18) understated the state.

## Rule

`evidence/compare-vs-5cd-r17q-32df.txt` against the previous 5cd sweep reports
`variables: 4` (reboot, JAR, runtime, installer), so no per-app change here is attributed
to one of them; the per-variable evidence is in the installer A/B and r17r runs. Future
full sweeps start from this state and change one variable at a time.

Raw run directory (not committed): `runs/unified-r17r-5cd/`.
