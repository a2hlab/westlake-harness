# Route-B Toutiao overlay on spare board 5cd (cc-t3 #91) — on-board run, honest outcome

Spare board `5cd1e3dd…`, LOCK 21:02:27 → UNLOCK 21:07:36 (~5 min, < 30). Goal: the four steps from the outer dispatch —
static overlay manifest → overlay + 3× toutiao_accept → 10 lit keys don't regress → rollback tested. **Screenshots are
ground truth; numbers below are from `facts.txt`, not the plan.**

## What was wrong before I touched the board (read-only prep caught a landmine)
`provision_toutiao.sh:40` and `toutiao_accept.sh` both run **`kill -9 $(pidof … appspawn-x)`** in their clean step.
RUNBOOK #12 (hard rule): *no lane may `kill -9` the appspawn-x main process* — OH init's `CheckOndemandService`
NULL-derefs (SEGV@0x34) and the **whole board goes down**. Running the stock scripts as-is would risk bricking 5cd.
That kill is also unnecessary for Route B: its Toutiao child is parented by `source_app_namespace`, not the host
appspawn-x. **Fix shipped + used here**: `provision_toutiao.SAFE.sh` / `rollback_toutiao.sh` clean only B's own
`com.ss.android.article.news / source_app_namespace / host_spawn` and never touch appspawn-x.

## Outcome per step
| step | result | evidence |
|---|---|---|
| 1 static overlay manifest | **done** | `overlay-manifest.md` (every path/process/bind-mount B writes; all under 1 HAP + `/data/local/tmp`, 0 `/system`, 0 frozen) |
| 2 overlay + 3× accept | **overlay applied; on-screen NOT verified** | provision steps 1-7 (host `bm install`, `tt-rt.tar` extract, stage, watchdog, start) ran with no FAIL; but the board **rebooted during the on-screen wait** → **0** feed-on-screen cold starts confirmed |
| 3 10 lit keys no-regress | **not attempted** | board rebooted; 5cd was idle (no live unified 10-key state to protect) |
| 4 rollback tested | **OK** | `rollback_toutiao.sh` → `uninstall bundle successfully`, B dirs removed, `imehost_bundles_remaining=0`, `imehost0_windows=0`; board left at 199 bundles, reachable |

## The reboot — cause, and what it was NOT
Immediately after provision steps 1-7, the on-screen wait loop returned `E001005 Device not found` for 150 s; the board
came back on its own with **`/proc/uptime` = 96.68 s** and the window-owner pid changed `31687 → 2014`. **5cd rebooted
mid-provision.** This is the documented **hub hazard** (RUNBOOK line 11: hub-connected boards drop/reboot during
provision/remount; prefer direct-connect for reboot-class ops). It was **NOT** a `kill -9 appspawn-x` board-down — the SAFE
scripts never touch appspawn-x, and after the reboot the board was healthy and reachable. The 755 MB `tt-rt.tar` push +
extract is exactly the heavy provision step the RUNBOOK warns stresses a hub link.

## What this run proved / did not prove
- **Proved**: (a) the RUNBOOK #12 `kill -9 appspawn-x` landmine is real in the stock scripts, and the SAFE patch avoids it
  (the board-down this run was a hub reboot, not appspawn-x); (b) the Route-B overlay **mechanically applies** (host
  install + RT extract + stage + watchdog all succeeded); (c) the **rollback is clean and reversible** (imehost + B dirs
  fully removed, board stable).
- **Did NOT prove** (honest): **Toutiao feed on screen** (0 confirmed cold starts — the reboot interrupted the ZOrder/
  snapshot verification), and **10-key coexistence**. These are the acceptance-critical items and remain **unverified**.

## Next step (needs a direct-connected board)
Re-run `provision_toutiao.SAFE.sh <serial>` on a **USB-direct** spare board (or ask the user to move 5cd off the hub),
then 3 cold starts with `snapshot_display` ZOrder verification, then relaunch 10 lit keys, then `rollback_toutiao.sh`.
The hub link is unreliable for the 755 MB provision; a direct board removes the reboot variable. No frozen item, no
`/system` write, fully reversible — the static decision stands; only the on-screen proof is pending a stable link.

## Files
- `overlay-manifest.md` — step-1 static overlay manifest.
- `provision_toutiao.SAFE.sh` — RUNBOOK #12-safe provisioner (no appspawn-x kill).
- `rollback_toutiao.sh` — RUNBOOK #12-safe rollback (verified OK on 5cd).
- `facts.txt` — per-step numbers from the run.
- `before.log` / `provision-run.log` / `rollback-run.log` — raw run logs.
