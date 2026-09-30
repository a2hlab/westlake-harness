# U5 repeated zero-variable probes on 5ea

The signed U5 sweep cannot establish a success rate from one screenshot.
Outer ACK(90) at 01:39:26 requested three consecutive clean-install trials each
for `fd-uhabits`, `antennapod`, and `fd-noice`. No native/JAR/installer/boot-image
change was made. Every trial uses the master batch, single key, `--reinstall`,
`--hilog 20 --shots 5,20 --focus-check`, preserving every result.

The lock window ran from 01:40:17 to approximately 01:54 (within 20 minutes).
All nine trial fingerprints are RUNTIME `73ecf422dba2` and BOOTIMAGE
`0876029078e2`, boot ID unchanged. End verification checked both shell and
appspawn-root SHA views; the board was unlocked retaining U5.

`facts-all.txt` contains verbatim master facts plus each t20 path.
`probe-index.json` indexes all nine original records and portable screenshots
under `evidence/<run>/<serial>/<key>/`. Compressed process tables are lossless.
The raw run directories remain local. No repeated sample was discarded.

Visual rates await outer reading; process survival does not assign a lit count.
The authorized Habit stability threshold is at least 2/3 own-UI t20 images.
No native causality follows from this repeatability check. No flaky registry
entry is changed by this lane before outer review.

## Outer verdict

ACK(90) at 02:01:31 read all nine images: Habit white/white/welcome = 1/3;
AntennaPod home/home/desktop = 2/3; fd-noice welcome/welcome/white = 2/3.
The outer reviewer registered all three as intermittent. U5 remains the signed
unified baseline. Completed-trial counts are never visual-success counts.
