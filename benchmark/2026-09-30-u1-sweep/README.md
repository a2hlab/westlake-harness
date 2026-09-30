# U1 two-board sharded sweep: 22 lit at t20, Loop Habit Tracker new (cumulative 26)

**State U1** = native v3c `668e4f7c` upgraded to the N1 package `aa57845c` (runtime `77639b80`,
ANL `f9c9b005`, Flutter/JNA/SoundPool pieces) + JAR J2 `0715c964` (J1-final + synthesized `android`
package) + background-launch installer (FZ-001). Deployed on 5ea and 61b and read back; 5cd was
under the boot image L2 test. 66 keys split 33/33, none missing.

| board | facts TOTAL |
|---|---|
| 5ea | `TOTAL keys=33 screenshots_captured=60/60 alive_t5=14 alive_t20=13` |
| 61b | `TOTAL keys=33 screenshots_captured=66/66 alive_t5=16 alive_t20=16` |

Read from `evidence/sheet-66-t20.jpeg` (case-insensitive key order, 11 per row): **22 apps show
their own UI at t20**: Aegis, Thunderbird, Auxio, BinaryEye, Calendar, Amaze, KeePassDX, Droid-ify,
Etar, File Manager, K-9, Luanti, mpv, NetGuard, Notes, SuperTuxKart, Tasks.org, Tusky,
**Loop Habit Tracker (uhabits, new)**, Markor, NewPipe, OONI.

Loop Habit Tracker shows its own "欢迎" onboarding page (`evidence/uhabits-5ea-t20.jpeg`). It passed
three walls in turn tonight: asset-fd removed `nativeOpenAssetFd` "Implement me" (FZ-003), the N1
graphics part removed the hwui no-surface abort, and under U1 it reaches its own page.

Not lit this run: AntennaPod and FitoTrack (both in the intermittent Skia RenderThread crash
family, root cause under investigation), AppManager (white second Activity). Noice is alive but white;
Shattered Pixel Dungeon shows its own error page.

Raw runs (not committed): `runs/u1-5ea/`, `runs/u1-61b/`.
