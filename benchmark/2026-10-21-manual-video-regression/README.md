# T35 — manual video state on 5cd / 61b (read-only; freeze hypothesis withdrawn)

User first reported that on 5cd and 61b the progress bar moved while the picture stayed on the cover/first frame,
then corrected it: the video appears to play (subtitles change). The whole-frame freeze hypothesis is **withdrawn**;
nothing here is a confirmed bug and it does not show that human playback fails.

Read-only sampling (16:15–16:17): identity/lock/power/focus, three `snapshot_display` frames per board ≥ 2 s apart
(one fixed diagnostic file per board, received to the Mac), process list and WMS. No click, wake, reopen, volume,
network or restore action; 5ea untouched.

| Board | boot | power / focus | frames (×3, byte-identical) | processes |
|---|---|---|---|---|
| 61b | `be4badc3…` | AWAKE; focus 63 → 65 (`imehost0`) between reads | feed list with a video card play button (`61b-1.jpeg`), not a playback page | asx `appspawn-x` 5089; `/system/bin/appspawn-x` 16295 → child 17699 `com.kaajjo.libr…`; no Toutiao process in this sample |
| 5cd | `e562ad3e…` | SLEEP; focus 15 | black (`5cd-1.jpeg`) — not observable | asx `appspawn-x` 5866 → Toutiao child 7754 |

Both boards were not on a video playback page when sampled, so timeline vs. frame is UNKNOWN. Child maps / private
SHA comparison against the last video signoff was not done (stopped on the user's correction). Raw receipts:
`$HOME/.local/share/westlake/manual-video-regression-20261021/`.
