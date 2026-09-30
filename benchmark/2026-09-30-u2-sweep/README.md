# U2 three-board sharded sweep: 24 lit at t20, AnkiDroid new (cumulative 27)

**State U2** = native v3c `668e4f7c` upgraded to the N2 package `51a78bde` (runtime `d932f2ba`,
ANL `77649b40`, host `42c35453`, ABI `29212bd4`) + JAR J2 `0715c964` + background-launch installer
(FZ-001). Same on all three boards: every `facts.txt` starts with
`RUNTIME fingerprint=937e2a6d0d88 files=119` and `FROZEN checked=4 violations=0`.
The 66 keys of the U1 sweep were split 22/22/22 (`keys-<board>.txt`); only the native package changed
from U1 (U1 = N1 `aa57845c`, same JAR, same installer).

| board | facts TOTAL |
|---|---|
| 5ea | `TOTAL keys=22 screenshots_captured=40/40 alive_t5=10 alive_t20=9` |
| 61b | `TOTAL keys=22 screenshots_captured=44/44 alive_t5=11 alive_t20=10` |
| 5cd | `TOTAL keys=22 screenshots_captured=42/42 alive_t5=12 alive_t20=12` |

Read from `evidence/sheet-<board>-t20.jpeg` (key order, 6 per row), with the same standard as U1 (an app's
own loading/splash page counts): **24 apps show their own UI at t20**.

- 5ea (7): Aegis, BinaryEye, KeePassDX, FitoTrack, mpv, Tasks.org, OONI.
- 61b (7): **AnkiDroid (new)**, Droid-ify, Luanti, Notes, Tusky, Markor, NewPipe.
- 5cd (10): AntennaPod, Thunderbird, Auxio, Calendar, Amaze, Etar, File Manager, K-9, NetGuard, SuperTuxKart.

Against U1 (22): 21 of U1's 22 are lit again; AntennaPod and FitoTrack (the intermittent Skia
RenderThread family) are lit this time; AnkiDroid is new. AnkiDroid draws its own DeckPicker (menu,
"AnkiDroid" title, add button; `evidence/anki-61b-t20.jpeg`), not the LeakCanary launcher entry
that an earlier sweep drew (DIGEST).

The one U1 app not lit here is Loop Habit Tracker (uhabits, 5ea): alive, window 1200×1920, white at t5
and t20, no fatal in hilog. Two reruns on the same board and state with `--reinstall`
(`runs/u2-5ea-uhabits-r2`, `-r3`): r2 shows its own "欢迎" page at t5 and t20, r3 is white at both
(`evidence/uhabits-5ea-r2-r3.jpeg`). So uhabits is lit 1 of 3 under U2: an intermittent white render,
not a deterministic N2 regression. U2 stays on the boards; no rollback.

Not lit, unchanged from U1: AppManager (launcher), Shattered Pixel Dungeon (own error page, libgdx),
Noice (white on 5ea, launcher on 5cd), Termux (white). fd-seal, subwaysurfers and toutiao have
`app_failed` (no screenshots).

Rule kept from FLAW-008: a white screen on one run of an app that was lit before is not a regression
until a same-state rerun with `--reinstall` fails again.

Raw runs (not committed): `runs/u2-5ea/`, `runs/u2-61b/`, `runs/u2-5cd/`, `runs/u2-5ea-uhabits-r{2,3}/`.
