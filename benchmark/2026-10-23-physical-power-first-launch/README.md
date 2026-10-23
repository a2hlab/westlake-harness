# Actual power-cycle first-launch acceptance — failed

Stage C executed after the user confirmed power restoration following the requested full off/on cycle. The new boot was `e9d0a715-26cb-4f0c-aceb-078373b90771`. Readiness flags became true; Wi-Fi connected automatically 12 seconds after ordinary unlock. One ordinary UITest desktop-icon click at 14:41:32 produced blank views at 10/30/60/120 seconds. **Cold-power first-launch acceptance failed.** No second click was used to replace this result.

[Stage C original results](C/results.json), [120-second screenshot](C/05-tt-t120-white.jpeg), and [outer verification](C/outer-review.json) preserve the actual outcome. Device time remained in 1970; this is a separate readiness gap, not an established cause. Power settings were restored to 30000/10000 and the lock released at 14:43:54. No runtime fix was deployed.

Actual power restoration was confirmed by the user; precise electrical off/on timestamps and duration were not independently measured. Input was ordinary UI automation, not a witnessed human finger. Historical pending A/B records below remain unchanged.

## Earlier preparation and wait


At stages A/B no physical power-cycle test had occurred. Stage A prepared ordinary desktop UI collection. Stage B held the 61b lock from 14:11:22 to 14:19:51, then released it before the external-wait deadline. All 134 observation samples remained on boot `33f35797`; no actual off/on confirmation was received.

- [Stage A](A/results.json): read-only readiness; the serial typo was corrected before B, and B must restore its fresh new-boot power preimage rather than assume A values.
- [Stage B](B/results.json) and [outer verification](B/outer-review.json): waiting only, zero UI actions, no runtime/configuration changes, no cold-power acceptance.
- [Acceptance contract](../../specs/toutiao-video-playback/t75-physical-power-first-launch.spec.md): after actual on-site power removal/restoration, observe automatic startup and network, then one ordinary desktop-icon tap and actual feed screenshots. No Mac bootstrap or deployment after power-on. Failed first attempts remain failures.

Raw receipts are persistent under `$HOME/.local/share/westlake/physical-power-first-launch-20261023/`; public records contain hashes, not credentials. At that point the next window required the user's physical-action confirmation. This pending result does not replace the earlier same-boot recovery evidence or promote it into cold-power success.
