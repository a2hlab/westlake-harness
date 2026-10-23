# T112 — 5cd same-boot icon tap after T109 exits: FAIL (no new child, RETRY_LIMIT unchanged)

## Pre-check (22:48:15)
- Same boot as T109: ecb84d86.
- No Toutiao child. Host 5074 and appspawn-x 5201 were still alive.
- Guardian state `RETRY_LIMIT`; last event 209, seq3, `attempts_exhausted_no_cleanup`.
- Network OK. Power SLEEP 10000/10000.

## Actions under the lock
The lock was held from 22:48:29 to 22:51:15.
1. After waking and unlocking, the screen was already white: the host window.
2. After Home the launcher was already on WorkSpace_8, where a fresh layout found the exact target at (736,507).
3. **One tap** at 22:48:54.

## Result
Screenshots at t5, t10, t20, t40, t60 and t90 were all white. Throughout:
- no Toutiao child appeared;
- the focus stayed on host window 29;
- the guardian state stayed `RETRY_LIMIT`, with no new event after the tap;
- the network was OK.

## Screenshot count
From `run/facts.txt`: `shots 6/6`.

## Restore
Power was restored and read back as 10000/10000. The board was unlocked.

## Scope
This card is separate from T109's first-launch failure. There was no reboot, no config change and no exit analysis. 61b was not touched.

## Outer review

The outer reviewer verified the blank app region and regenerated facts from actual records. Raw receipts are SHA-indexed in `raw-manifest.json` and preserved in its persistent private archive. This failure is retained; previous successful software boots do not establish repeatability.
