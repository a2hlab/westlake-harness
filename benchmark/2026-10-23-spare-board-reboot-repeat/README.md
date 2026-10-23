# T109 — 5cd software reboot repeat, first icon tap: FAIL (white, children exited)

## Reboot and readiness
The lock was held from 22:40:09 to 22:44:52.
- `hdc shell reboot` returned rc 0.
- The board reconnected 21 s later on new boot **ecb84d86**.
- Readiness came at uptime 22.7 s: `boot.completed=true`, plus wlan0 IPv4 and a route.
- Nothing auto-started before the tap.

## The one tap
The icon was on WorkSpace_8 at (736,507), found after a 9-page scan. It was tapped once at 22:41:53.

Every screenshot from t10 to t120 is white.

| Sample | Processes |
|---|---|
| t10 | host imehost 5074 and appspawn-x 5201 |
| t30 | child 7011 |
| t60 | child 9860; 7011 no longer listed |
| t90 | no Toutiao child |
| t120 | no Toutiao child; network OK |

## Guardian record for this boot
Read from `state` and `events.log`:

| Attempt | Child | Bootstrap (uptime) | Exit (uptime) |
|---|---|---|---|
| seq1 | 7011 | 116 | 133 |
| seq2 | 9860 | 152 | 170 |
| seq3 | 12688 | 191 | 209 |

- Each exit led to RECOVERING.
- The retries came from the guardian's own backoff (5 s, then 10 s), not from additional taps.
- After seq3 the state went to **RETRY_LIMIT**.
- Child 12688 fell between two CC samples and was never observed directly.

## Launch logs
The `adapter_child_7011.stderr` and `adapter_child_9860.stderr` files were read: the first 128 KiB of each. Each mtime lies inside the matching child's lifetime window. The contents are kept private; only stat and SHA are published here. They were not analysed, and no cause of the exits is claimed.

## Screenshot count
From `run/facts.txt`: `shots 5/5`.

## Restore
Power was restored and read back as 10000/10000. The board was unlocked. The screen was left white; Home was not pressed. 61b was not touched.

## Outer review

The outer reviewer verified the blank app region and regenerated facts from actual records. Raw receipts are SHA-indexed in `raw-manifest.json` and preserved in its persistent private archive. This failure is retained; previous successful software boots do not establish repeatability.
