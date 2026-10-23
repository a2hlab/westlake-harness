# Cold-power demonstration readiness — 2026-10-23

The previous handoff accepted one same-boot icon recovery, approximately 63 seconds after the click. That evidence does **not** satisfy the user's subsequently explicit requirement: remove and restore power, then use the first ordinary desktop-icon tap without computer bootstrap.

## Current result

T74 stopped at a safety-classifier refusal; its cause is unknown and no candidate was produced or deployed. See [original inner record](inner/results.json) and [outer disposition](outer-review.json). The inner proposal to continue the refused source review is not authorized. No root cause or fix is claimed for the click-to-spawn delay.

The independent [power audit](peer-power-audit.json) checked 12 SHA-bound sources. It found no mapped power actuator within the stated repository search scope. Actual supply topology remains unknown; this is not a claim that no such hardware exists anywhere. Physical off/on must be performed and confirmed on site with currently documented capabilities.

Independent ordinary-UI acceptance is scoped by [T75](../../specs/toutiao-video-playback/t75-physical-power-first-launch.spec.md). Software reboot, USB disconnection, and a changed boot ID alone are not physical-power evidence. The first failed launch remains a failure; later retries cannot replace it. Source analysis is not resumed through this observation.

No cold-power acceptance is signed here. The 5–10 second target is an optimization goal, not measured capability. [T74 estimate](../../specs/toutiao-video-playback/t74-estimate.md) covers bounded readiness analysis; its conditional downstream 30–60 minute repair allowance is no longer reliable after the stop.
