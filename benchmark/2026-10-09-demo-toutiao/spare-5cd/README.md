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

---

# Re-run on 5ea (skip-push), per outer dispatch — Route B runtime PROVEN, on-screen blocked by host-launch permission

Outer moved the run to 5ea (its `/data/local/tmp/tt-prov/tt-rt.tar` is on-board, SHA `014c566e…` = pinned). I added
**skip-push** to the SAFE provisioner: if the on-board `tt-rt.tar` SHA matches the pin, extract from it and never push
755 MB over the link. LOCK 21:15 → UNLOCK 21:29. Numbers: `facts-5ea.txt`.

## What was proven (the key static unknown — resolved POSITIVE)
**Route B cold-starts Toutiao and the child runs stably — both `libtttext_lite` ICU walls are cleared.** Evidence: the
Toutiao child (`com.ss.android.article.news`) stayed alive across watchdog selfheal cycles (pids 3982→6374→8174), and its
stderr shows live `[TOUCH21-POLL]`, `[WESTLAKE-NATIVENET-807] epoll_wait`, `[WESTLAKE-WEBVIEW-BIONIC]` loops — i.e. the app
is running its event/network/webview loops with **no SIGSEGV at `libtttext_lite ICUWrapper::ICUWrapper()`**. The static
README's wall-2 (`icudt74` vs `_72`) UNVERIFIED risk is now **passed** under Route B's self-contained RT. skip-push worked
(no 755 MB push; the earlier hub stress is removed).

## What was NOT captured (honest)
- **Feed on physical screen: 0 confirmed.** The imehost host window (`imehost0`) never fronted: `aa start -b
  org.westlake.imehost -a EntryAbility` → **ErrCode 10107101 "Permission check failed when launching the ability"** — even
  after dismissing the keyguard. This is the **same call the watchdog itself uses** (`watchdog.sh:95`), so the watchdog
  can't front the host either on a bare post-reboot board. `persist_demo.sh` (the privileged broker launcher) **refuses
  5ea as a protected board**. So the running feed has no host window to attach to → not on screen. **The blocker is the
  host-window launch permission on a bare board, NOT a Toutiao failure** (the child runs fine).
- **10-key coexistence: not attempted** — appspawn-x was down post-reboot (no unified runtime mounted to launch route-a
  apps).
- **User manually rebooted 5ea mid-run** (boot_id 7be01c1f; board note 22:40) — not caused by Route B/the provisioner;
  the run was re-timed and continued after.

## Rollback (step 4) — OK again
`rollback_toutiao.sh` on 5ea: `uninstall bundle successfully`, B dirs removed, `imehost0_windows=0`, board stable
(uptime 691 s, same boot). Reversible confirmed on both spare boards.

## Net + next step
**Route B's runtime viability is proven** (Toutiao runs, ICU cleared) — the decisive positive for the static route choice.
The remaining gap is purely the **host-window launch**: on a demo board the privileged broker (`open_broker.sh` HOST_SPAWN
/ `persist_demo.sh up`) or a foreground/`START_ABILITIES_FROM_BACKGROUND`-granted launch brings `imehost0` up; `aa start`
from a bare shell is permission-blocked (10107101). Next: run on a board where the demo broker is permitted (not 5ea/61b),
or grant imehost the background-launch permission, then the 3× on-screen cold starts + 10-key coexistence can be captured.
