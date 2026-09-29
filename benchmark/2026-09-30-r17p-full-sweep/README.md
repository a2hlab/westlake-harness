# r17p full sweep on 5ea and 61b: 22 apps lit, installer is the only board difference

**Result.** Runtime JAR r17p (`a0ed5c4f`, WindowSessionProxy wraps IWindow and drops
non-first `resized`) over native package v3c (`668e4f7c`), all 66 keys, both boards.
Three apps show their own UI for the first time: **AntennaPod** (home page, 5ea),
**Amaze File Manager** (file list, both boards) and **Tusky** (login page, 5ea).
Cumulative signed-lit count goes from 19 to **22**.

Unedited `facts.txt` totals:

| board | facts TOTAL line |
|---|---|
| 5ea | `TOTAL keys=66 screenshots_captured=126/126 alive_t5=25 alive_t20=24` |
| 61b | `TOTAL keys=66 screenshots_captured=126/126 alive_t5=26 alive_t20=24` |

Lit is decided from the t20 screenshot (the last one), not from `alive` and not from t5
(FLAW-007). Visual verdicts, read tile by tile from `evidence/sheet-*-t20.jpeg`:

| app | 5ea t20 | 61b t20 |
|---|---|---|
| AntennaPod (new) | home page, 5 bottom tabs | no live child (desktop) |
| Amaze (new) | file list + FAB | file list + FAB |
| Tusky (new) | login page | white |
| Thunderbird / K-9 | own "updating database" page | white |
| Fossify File Manager | own list | white |
| AppManager | white | own "verifying" splash |
| FitoTrack | no live child (desktop) | own settings dialog |
| Aegis, Auxio, Calendar, KeePassDX, Droid-ify, mpv, NetGuard, Notes, STK, Tasks.org, OONI, Luanti (loading page) | lit | lit |
| Etar | desktop | desktop |
| NewPipe | t5 only | t5 only |
| Wikipedia | no live child (desktop) | t5 only |

Etar needs r17q's PowerExemptionManager stub, which r17p does not contain, so its
desktop here is expected and is not counted as a regression. NewPipe and Wikipedia
reach a first frame and are gone by t20; they are recorded as "first frame not stable".
The first frames are real app UI: NewPipe shows its red "直播" tab bar on both boards, and
Wikipedia on 61b shows its main feed (header, 社群/推荐给你 tabs, five-item bottom bar,
loading spinner) rather than the onboarding page seen on 5ea earlier.

## What was wrong before

The first reading of the two boards' differences was going to be "the JAR behaves
nondeterministically across boards". The runtime fingerprint (added to `bms_batch.py`
after FLAW-004) says otherwise: of 117 fingerprinted files, **115 are byte-identical**
and only the installer pair differs
(`evidence/runtime-fingerprint-5ea-vs-61b.diff`):

- 5ea: background-launch installer, libbms `6aadb8b4`, libapk_installer `7048c7c5`
- 61b: older installer, libbms `6f94d4f4`, libapk_installer `eb6824b4`

## Rule

Compare the runtime fingerprints before attributing a cross-board difference to the
JAR or to nondeterminism. Here the hypothesis is that the apps lit only on 5ea
(Thunderbird, K-9, Tusky, AntennaPod, Fossify File Manager) depend on the
START_ABILITIES_FROM_BACKGROUND grant; the reverse cases (AppManager, FitoTrack) are
not explained by it. Discriminating experiment: install the background-launch
installer on 61b and rerun these seven keys with the same JAR. Until that runs, this
is a hypothesis, not a cause.

## Files

- `evidence/facts-5ea.txt`, `evidence/facts-61b.txt`: unedited batch facts
- `evidence/runtime-fingerprint-*.txt` and the diff
- `evidence/sheet-5ea-t20.jpeg`, `evidence/sheet-61b-t20.jpeg`: all 66 t20 tiles,
  keys in case-insensitive name order, 11 per row
- `evidence/{antennapod,amaze,tusky}-*-t20.jpeg`: the three new-lit screenshots
- Raw run directories (not committed): `benchmark/2026-09-30-r17p-5ea-sweep/runs/`,
  `benchmark/2026-09-30-r17p-61b-sweep/runs/`
