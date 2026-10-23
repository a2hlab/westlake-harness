# T69 — first-launch path comparison (61b, T61B vs T66 vs T68)

Read-only comparison of existing receipts; zero device operations, no REA, no crash investigation.

## What was wrong before
After T68 failed (white page, child exit ~30 s after the desktop tap) the natural next move was another reboot trial with a different network setup. This card checks first whether anything *we control* actually differs between the one fresh-boot success (T61B) and the two fresh-boot failures (T66, T68).

## Evidence (per-field matrix in `results.json`, sources hashed)
| field | T61B (feed) | T66 (white, exit) | T68 (white, exit) |
|---|---|---|---|
| HAP / toutiao cfg | b18978b8 / 7b9f2c0e (pre-reboot read) | same | same |
| SSID at tap | Test_2.4GHz | Test_2.4GHz | Compatibility |
| tap uptime | ~78.6 s | ~76.8 s | ~200.7 s |
| tap -> appspawn-x / -> child | 2.4 s / 18.9 s | 1.9 s / 19.2 s | 1.2 s / 16.3 s |
| guardian | ... UI_UNVERIFIED x10 -> first_feed_observation 166 -> READY 173 | UI_UNVERIFIED 102,108 -> ownership check failed at capture 114 -> process_exit 117 | UI_UNVERIFIED 222,227 -> ownership check failed at capture 234 -> process_exit 237 |
| harness between tap+0.6 s and t30 | idle | idle | idle |
| network in exit window | unknown (no log) | reason=34 drop at 11:46:58.5 (adjacent) | none (blips at 12:14:30 and 12:16:53 only) |
| /proc/net/route at t120 | local subnet only, no default | not connected | local subnet only, no default |
| status-bar `!` icon | present | — | present |

Guardian source: `benchmark/2026-10-21-t34-demo61b-video/reentry-retirement-01/deploy-package-r3-root/payload/watchdog.sh` (sha256 8bf74a08…). `child_identity_during_capture` comes from line 154: it only shows that the guardian's ownership check (`child_owned`) failed at capture time, which can include a read error. It does not by itself prove the child had died, and a single line cannot show that the capture had no influence on the exit; both remain unknown. The on-device copy hash was not read in these runs.

## Result
**No controllable difference found.** T61B and T66 match on the captured comparison fields (same pre-reboot HAP/config hashes, icon, SSID, similar uptime at tap and spawn timing, same idle harness); current-boot artifact equality remains unverified, yet one shows the feed and one exits. In both failures the guardian later records `process_exit first_read_exited` (uptime 117 / 237), ~36–41 s after the tap; the preceding ownership-check failure (114 / 234) is not proof of death. Network events are not consistently coincident with the ownership-check failure / exit window (T66 adjacent, T68 none). The missing default route and the `!` icon are identical in the success sample, so neither discriminates.

No minimal experiment is proposed: another reboot would not discriminate any identified variable.

## Kept counterexample
T68 had a 2 s disconnect inside its 30–90 s window; continuous network stability is not claimed.

## Unknowns / search boundary
T61B supplicant events; post-reboot on-device fingerprints; on-device watchdog hash; native/runtime fingerprints; child exit cause (out of scope). Sources: private raw receipts of T61B/T66/T68 (+T59 boot id only) and the repo r3 guardian payload.

## Rule
Before another device trial, require a per-field success/failure matrix; if the success and a failure match on every controlled field, do not repeat the trial.

Outer review: [outer-review.json](outer-review.json) verifies 22 source hashes and the local guardian source. Matching measured fields is not proof that all runtime artifacts or conditions are identical.
