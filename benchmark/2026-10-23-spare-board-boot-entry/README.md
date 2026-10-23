# T108 — 5cd one software reboot, first desktop icon tap: feed at t60

## Before the reboot
The lock was held from 20:45:49 to 20:50:16. The board was on old boot 62db0627 with the T104 instance still running.

## Reboot and readiness
- `hdc shell reboot` returned rc 0.
- The board reconnected 20 s later on **new boot abf413ed**.
- Readiness came at uptime 27.6 s: `boot.completed=true`, plus wlan0 IPv4, RUNNING and a route.
- Nothing auto-started: no imehost, appspawn-x or Toutiao process was running before the tap.

## The one tap
After waking and unlocking (no credential screen), a full desktop scan found the target `AppIconCommonView_org.westlake.imehost.EntryAbility` on WorkSpace_8 at (736,507). It was tapped **once** at 20:47:45.

| Sample (actual time) | Screen | Processes |
|---|---|---|
| t10 (20:47:56) | white | new host imehost 5171 and appspawn-x 5305 |
| t30 (20:48:15) | white | child `com.ss.android.article.news` 7111 (parent 5305) first seen |
| **t60 (20:48:45)** | **feed**: recommend list with a video card | — |
| t90 | feed kept | — |
| t120 | feed kept | network OK |

No child exit was observed, so the launch-log read was not triggered.

## Screenshot count
From `run/facts.txt`: `shots 5/5`.

## Restore
- Power was restored and read back as 10000/10000, matching the new-boot pre-check.
- The feed was kept on screen.
- The board was unlocked.
- 61b was not touched.

## Scope
This is a software-reboot first launch. It is **not** a physical power-cut signoff. The content's network origin is unknown.

## Outer review

The outer reviewer viewed s120 as a real feed; the sentry viewed white at t30 and feed at t60/t120. Facts were regenerated and matched; held returned rc1 after release. t60 is the first positive sample, not an exact first-frame timestamp. Raw receipts are SHA-indexed in `raw-manifest.json` and retained in its private archive. No physical-power or repaired-code claim.
