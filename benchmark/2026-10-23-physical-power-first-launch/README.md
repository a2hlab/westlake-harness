# Actual power-cycle first-launch acceptance — pending

No physical power-cycle test has occurred in this record. Stage A prepared ordinary desktop UI collection. Stage B held the 61b lock from 14:11:22 to 14:19:51, then released it before the external-wait deadline. All 134 observation samples remained on boot `33f35797`; no actual off/on confirmation was received.

- [Stage A](A/results.json): read-only readiness; the serial typo was corrected before B, and B must restore its fresh new-boot power preimage rather than assume A values.
- [Stage B](B/results.json) and [outer verification](B/outer-review.json): waiting only, zero UI actions, no runtime/configuration changes, no cold-power acceptance.
- [Acceptance contract](../../specs/toutiao-video-playback/t75-physical-power-first-launch.spec.md): after actual on-site power removal/restoration, observe automatic startup and network, then one ordinary desktop-icon tap and actual feed screenshots. No Mac bootstrap or deployment after power-on. Failed first attempts remain failures.

Raw receipts are persistent under `$HOME/.local/share/westlake/physical-power-first-launch-20261023/`; public records contain hashes, not credentials. The next window requires the user's physical-action confirmation. This pending result does not replace the earlier same-boot recovery evidence or promote it into cold-power success.
