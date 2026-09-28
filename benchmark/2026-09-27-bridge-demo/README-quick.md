# Quick-switch bridge demo (`demo_quick.sh`) — 61b06572 — 2026-09-27/28

A ~1-minute, camera-friendly version of the bridge demo: instead of staging each app live (`demo_bridge_apps.sh`,
~1 min/app), it **pre-launches all apps once** and then flips between them by killing the top one, so each
switch is ~1-2 s. It ends on the **Toutiao feed with zero wait** (Toutiao is pre-warmed at the bottom of the
stack). Only 61b06572; 5cd1e3dd / 5ea34a45 hard-refused.

## Subcommands
```
demo_quick.sh 61b06572 prep            # off-camera, untimed: warm Toutiao at bottom + pre-launch 13 apps
demo_quick.sh 61b06572 go [HOLD=4.5]   # on-camera: flip through the apps, end on Toutiao (instant)
demo_quick.sh 61b06572 restore         # after filming: relaunch Toutiao watchdog+keeper (standalone)
demo_quick.sh 61b06572 open <app-key>  # ad-hoc: bring one app onto the screen
```
`go` env: `RENDER_WAIT=13` (first-frame wait after a fresh relaunch), `REWARM_LAST=N` (force-relaunch the
last N go-apps fresh — see the surface-loss note). `APPS="..."` overrides the list.

## Approach A (concurrent pre-launch + kill-top reveal) — the crux
Verified empirically: two source apps run concurrently, each in its own `source_app_namespace`; both bridge
sub-windows composite into the host surface; **the last-launched is on top, and killing it reveals the one
below in ~1-2 s** (the lower app stays alive and rendered). So:
- **prep** cold-starts Toutiao via the watchdog, waits for the feed, then stops the watchdog (its
  `watchdog.sh` line 164: *"stop prevents relaunch … live app intentionally remains"* — so Toutiao stays
  alive at the **bottom**). Then it pre-launches the 13 apps in **reverse** go-order, so go-app #1 is on top
  and Toutiao is underneath everything.
- **go** shows the top app, HOLDs, kills it → the next reveals. After the 13th app is killed the pre-warmed
  Toutiao is revealed **instantly (0 s)**. Then the watchdog+keeper are restored for self-heal (one-time
  maintenance cold-restart), leaving 61b on Toutiao.

Memory: 13 apps + Toutiao ≈ 4 GB peak; board has 7.5 GB (MemAvailable stayed ~3.4 GB) — comfortable.

## Known limitation found in testing — deep-buried apps lose their surface
With A, the **last-shown apps are the first-launched** (LIFO), so they sit occluded the longest (~8 min for a
13-app stack whose prep takes ~6.5 min). OH reclaims the surface of a long-occluded window: the process stays
alive but, when revealed, it shows the app *below* it instead of its own UI. In the first full test the two
deepest apps failed this way (droidify showed noice; burgerking showed Toutiao); the 11 shallower apps rendered
their real UI cleanly. Fixes:
- `go` now waits `RENDER_WAIT` after any fresh relaunch (a relaunched app needs ~13 s to first-frame; the first
  test snapshotted after 1 s and caught the app below).
- `REWARM_LAST=N` force-relaunches the deepest N go-apps fresh (they're the at-risk ones), trading ~30 s/app for
  a guaranteed real frame. Use `REWARM_LAST=2` (or more) for a clean film; leave 0 for the fastest go.
- The `host_z>=0 && child-alive` check can't tell a surface-reclaimed app from a live one — **the screenshots
  are the ground truth**, always eyeball `quick-screens/`.

## Apps (go order; termux removed — its bootstrap-error dialog is not demo-worthy)
wikipedia · ooniprobe · fd-com-kunzisoft-keepass-libre · fd-com-amaze-filemanager · fd-auxio · antennapod ·
aegis · fd-netguard · fd-AppManager · fd-droidify · fd-noice · fd-fitness · burgerking(=McDonald's) → **Toutiao**

netguard / AppManager / fitness open on a normal first-run dialog (EULA / KeyStore info / Set-Preferences) —
real app UIs, not errors.

## Results
(see the ACK / the latest `quick-screens/` for the validated on-screen count and the Toutiao finale reveal type)
