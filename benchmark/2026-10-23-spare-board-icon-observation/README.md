# T103 — 5cd ordinary icon observation: stopped, Toutiao icon not on the desktop

**No tap was made and no baseline was obtained.**

## Pre-check (20:14:37)
| Item | Observed |
|---|---|
| Holder | none (`held` rc=1) |
| Boot | 62db0627 |
| Toutiao child | none |
| imehost host process | none (only the guardian entry `sh` process, pid 4041) |
| Power | SLEEP, timeouts 10000/10000 |
| WiFi | connected |

## What happened under the lock
The lock was held from 20:14:49 to 20:16:19.
1. Woke the screen and unlocked it. The lock screen had no credential nodes.
2. Pressed Home and checked desktop pages WorkSpace_0, 1 and 2. None of them has `AppIconCommonView_org.westlake.imehost.EntryAbility`.
3. Stopped. The package is installed (`bm dump -a` lists `org.westlake.imehost`), but the target icon is unknown, so I did not search further pages and did not tap.

## Restore
- Pressed Home.
- Power `-r` / `-o 10000`, read back as 10000/10000, matching the pre-check.
- No temp files from this task remain on the device.
- Unlocked; `held` rc=1 afterwards.
- 61b was not touched.

## Screenshot count
The count comes from `run/facts.txt` (the `scripts/lab/run_facts.py` output) and is 0: the run stopped before the screenshot step.

## Outer review

Facts regenerated from the submitted record and matched verbatim. Raw receipts are SHA-indexed in `raw-manifest.json` and retained in its persistent private archive. No white-screen repair or cold-power acceptance. Power timeout restoration does not imply restoration of the original sleep state.
