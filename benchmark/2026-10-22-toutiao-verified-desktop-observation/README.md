# T44 — host callbacks observed from a verified live desktop (5cd, 2026-10-22)

**What was wrong before.** T43 counted six page-swipe layouts as "six desktop pages without the imehost icon"; all six
were the same `ScreenLockRootComponent` dump (SHA 736ea89a…), with a recorded 10 s screen-off override. That run reached valid desktop page 0 but subsequent page samples were locked; the full timeout causal sequence was not established. It made 0 clicks and observed no callback.

**Rule applied this round.** A desktop counts only when the current layout has `SwiperPage_Grid_WorkSpace_N`,
ordinary `AppIconCommonView_*` tiles and no `ScreenLockRootComponent`, confirmed with a `snapshot_display` screenshot.
After *every* `uitest` call (swipe, dumpLayout, Home, click) `power-shell timeout -o 600000` is re-applied and read
back from PowerManagerService. Pages are identified by the `WorkSpace_N` id, never by whole-layout bytes.

## Facts (board 5cd1e3dd…, boot 8b64b087, LOCK 14:55:31 → UNLOCK 15:02:25, 414 s)

| step | observation |
|---|---|
| admission | HAP b18978b8…, bundle uid 20011300 / token 537137511, host not running, no prior lock holder |
| preimage | power `Timeout=10000ms OverrideTimeout=10000ms`; runtime 124 + boot image 36 files, 0 MISSING; datadir dev/ino/mode/uid/gid; `launch-observation.json` absent |
| b189 desktop | first valid desktop WorkSpace_0 (Settings/Photos), 0 lock-screen swipes; 8 "next" swipes → WorkSpace_1…8, all distinct; exact `AppIconCommonView_org.westlake.imehost.EntryAbility` unique/visible/enabled/clickable `[600,371][873,644]` on WorkSpace_8 (outer read d0/p8 screenshots). Not clicked. |
| install | `bm install -r` T41 release-02 02f56d18… (59008 B): device HAP = 02f56d18, bundle uid/token and datadir unchanged |
| click 1 (automated_desktop_click) | relocated on WorkSpace_8 from a fresh layout; host pid 20722 started; `launch-observation.json` created: **onCreate** seq 1, instance ca09a4f8, launchReason 1, manual_origin `unverified`, eligible_for_reentry false; window-state event 2, WMS focus WID 51 (imehost0); screenshot: white host page |
| click 2 (automated_desktop_click) | Home → valid WorkSpace_8 → same node re-located; record replaced: **onNewWant** seq 2, same instance ca09a4f8, host pid 20722 same starttime (sampled); WMS focus WID 55 owned by pid 22549 `com.ss.android.article.news` (existing bridge reaction, only observed); screenshot at 15:00:45: white, layout returned to host; WMS focus sample at 15:00:12 was 33 s earlier |
| recovery | `bm install -r` b189 → device HAP b18978b8; candidate host not running at two samples; runtime/boot-image manifests and datadir stat byte-identical to preimage; same boot; power back to `Timeout=10000ms OverrideTimeout=10000ms`; `/data/local/tmp/t44-*` removed; final screenshot WorkSpace_0 desktop |

Residuals (not hidden): `launch-observation.json` (seq 2) stays in the host filesDir after the b189 restore — not deleted,
the card does not authorize app-data deletion; `window-state.json` content changed by the callbacks; a Toutiao child
(pid 27648) was running after restore and Toutiao process state was not sampled before the lock, so whether it
pre-existed is unknown; it was not stopped.

## Not claimed
White-screen fix, feed or video on screen, human-tap origin, reentry eligibility, a continuous PID over the whole window.
The callbacks show only that a desktop-icon click produced onCreate and a second one onNewWant on the same JS instance.
`task_pass` stays `pending_human_review`.

## Files
- `results.json` — every number above, extracted from the raw records.
- `evidence/launch-observations.json` — the two recorded observation lines.
- `check_observation.py` — structure checker (re-hashes the private raw root when present; refuses 11 forged variants);
  Rust entry `tools/spec-checks/tests/toutiao_verified_desktop_observation.rs`.
- Private raw (argv/start/end/stdout/stderr/rc per command, layouts, screenshots):
  `$HOME/.local/share/westlake/t44-verified-desktop-observation-20261022/`, `MANIFEST.sha256` (1062 files) SHA in `results.json`.

Outer review: `outer-review.json` verifies the recorded observation and recovery, not a white-screen fix or human review. The contract test requires original raw records; receipt-only inspection is a distinct mode.
