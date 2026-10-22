# T42 — ordinary launch-request observation on the owned host app (5cd), then b189 restore

A single same-signature update of the T41-accepted host-observer candidate onto **5cd1e3dd** followed by at
most three ordinary `aa start` launch requests, then restore of the current **b189** host. Temporary owned-host deployment/observation only — **no retained deployment or white-screen fix claim, no Toutiao operations, no third-party modifications, no
runtime/guardian/REA/debugger, no reboot.** The passive receipt checker runs **no device commands**.

## What actually happened (evidence-first)

1. **Read-only identity (pre-lock).** Device `entry.hap` = **b189** `b18978b8…9ff0`; bundle `org.westlake.imehost`
   v1.0.0/code 2, appId `…BNtg4JBClbl…`, fingerprint `8E93863FC3…`, accessToken `537137511`, provision release;
   data dir `/data/app/el2/100/base/org.westlake.imehost` owner `20011300:20011300`; host **not running**
   (pid NONE); only `window-state.json` (`2da245e0…`, from 2026-10-21) present, `launch-observation.json` absent.
2. **Exclusive lock** on 5cd (`board_note.sh`, lane `t42-host-observer`); re-checked identity still b189 before writing.
3. **Same-sign update.** Sent the T41 release-02 candidate (`02f56d18…`, 59008 B) → device-side SHA matched →
   `bm install -r -p` → `install bundle successfully.` (shell rc 0). Device `entry.hap` is now **`02f56d18…`**
   (byte-identical to the signed candidate); **bundle identity (name, versionCode, appId, signing-certificate fingerprint, accessToken, provision) and the el1/el2
   dir owner UID/GID unchanged.** (The bm-dump fingerprint is the signing CERTIFICATE fingerprint, not a native/runtime
   fingerprint; a runtime/native fingerprint was not captured. Only UID/GID was read, not inode or full dir metadata.)
4. **Three ordinary `aa start` requests** (`aa start -b org.westlake.imehost -a EntryAbility`), each explicitly an
   **`automated_request`** (tool-issued, **not** a human tap). **All three were refused at the ability permission
   gate:** `Error Code:10107101 Permission check failed when launching the ability / No permission to start this
   ability`. The shell exit code was `0` in every case, but the ability **failed to launch** — the host never
   started (pid NONE), `window-state.json` was unchanged, and `launch-observation.json` was never created.
5. **Restore.** Sent b189 (`b18978b8…`, 54215 B) → device-side SHA matched → `bm install -r -p` → device
   `entry.hap` back to **b189**; bundle identity (incl. signing-cert fingerprint) and dir owner UID/GID unchanged; host pid NONE.
6. **Lock released**, then this report written (no document authored while holding the lock).

## Honest framing (what this does and does not mean)

- **This is a launch FAILURE, not a callback-absence after a successful launch.** The launch was denied at the
  permission gate, so no callback path was ever reached. `callback_status = unknown`.
- **No inference about `onNewWant` or any callback behaviour** is drawn — the code path did not execute.
- **shell rc 0 is not success.** The real result is the `aa start` stdout (10107101), not the shell exit code.
- No white-screen / Toutiao / reentry claim. `white_screen_fixed = false`, `manual_origin = unverified`,
  `eligible_for_reentry = false`.

## Evidence scope (what was and was NOT captured)

- **Captured / confirmed:** device `entry.hap` SHA before→after→restore; bm-dump bundle identity fields (name,
  versionCode, appId, **signing-certificate** fingerprint, accessToken, provision) byte-equal; data-dir owner
  **UID/GID** (`20011300:20011300`); host pid NONE at every checkpoint.
- **Not captured (reported as unknown, not acceptance):** a **native/runtime fingerprint** — the bm-dump
  fingerprint is a signing-certificate fingerprint only; **inode / full directory metadata** of the data dir —
  only UID/GID was read; request #1 screenshot. These gaps mean this card is **not** a full-contract acceptance;
  the scenario is human-reviewed and the automated checker verifies only failure-evidence completeness + HAP recovery.

## Recovery is confirmed (not disk-only)

Device `entry.hap == b189`, bundle identity (signing-cert fingerprint) and data-dir owner **UID/GID** unchanged, **and the candidate host process
never existed** — pid was NONE at install, at each of the three requests, and after restore. There was no running
candidate to leave behind.

## Screenshots — private only (privacy)

`snapshot_display` captures of requests #2 and #3 show the device's **WLAN settings page** (incidental device
state, not the host or Toutiao). They contain nearby Wi-Fi names. **The original images and any SSIDs are NOT in
this public repository** — only the SHA, byte size, private persistent path and the page classification are
recorded (see `results.json`). Request #1 was not screenshotted. Screenshots are not callback evidence and no
visual conclusion is drawn.

| screenshot | sha256 | bytes | classification | original |
|---|---|---|---|---|
| req #2 | `690d02bf…225879` | 107143 | wlan-settings-page | private: `$HOME/.local/share/westlake/t42-host-observer-device-20261022/raw-obs-req2/screen.jpeg` |
| req #3 | `ac225d9c…b7f258` | 110424 | wlan-settings-page | private: `$HOME/.local/share/westlake/t42-host-observer-device-20261022/raw-obs-req3/screen.jpeg` |

## Layout

| path | what |
|---|---|
| `results.json` | full structured record: identity before/after, update + 3 refused requests, recovery, claims, `raw_pins` (every raw argv/stdout/stderr/rc/time SHA-pinned, `$HOME`-aliased) |
| `evidence/aa_start-req{1,2,3}.{stdout,stderr,rc}` | the three ordinary requests' real output — shell rc `0` alongside the `10107101` permission failure |
| `evidence/identity-before.json`, `identity-after-restore.json` | bundle identity (public fields) before and after, byte-equal |
| `check_observation.py` | read-only checker (no device commands) + production negatives |
| `SHA256SUMS` | SHA index of committed card files |

**Not in git** (persistent, binaries/raw/screens): `$HOME/.local/share/westlake/t42-host-observer-device-20261022/`
holds every raw command record and the two private screenshots, SHA-pinned in `results.json → raw_pins`.

## Verify

```
python3 check_observation.py        # reads results.json + committed evidence only; runs NO device command
cargo test --test toutiao_host_observer_device   # from tools/spec-checks
```

The checker's verdict is **`FAILURE_RECORDED_AND_RECOVERED` with `task_pass = false`** — it does not mark the task as
passed (human review required). It asserts the launch-failure framing (permission_denied + host not launched + callback_status unknown,
never "callback-absent-after-success"), shell-rc-0-is-not-success, identity unchanged, recovery confirmed with the
candidate never running, no screenshot committed and no `onNewWant`/white-screen claim; and drives the real
`check()` to refuse forged success, a fabricated callback, a wrong "observed_absent" framing, an identity mismatch,
an unconfirmed recovery sign-off and a committed screenshot. Delivery is **path-list + SHA only — no commit, no push.**
