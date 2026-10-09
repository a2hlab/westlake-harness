# Why `aa start imehost` → 10107101, and the minimal background-start grant (reuse FZ-001, no frozen)

Static analysis for #91 t2 on-screen gap. Answers: how `imehost0` fronted on 9-27, why `aa start` fails today, and the
minimal authorization — a **runtime `atm` grant of `START_ABILITIES_FROM_BACKGROUND`**, reusing FZ-001's permission without
re-signing the HAP or touching any frozen binary.

## How imehost0 came up on 9-27 (foreground caller, not a bare shell launch)
The Sept demo brings the host window up through a **foreground OH app caller**, so no background-start permission is needed:
- `persist_demo.sh up` → `open_broker.sh` runs **as root**, triggered by the launcher HAP `org.westlake.applauncher` whose
  window `applauncher0` is **on top (foreground)** when the broker calls `aa start -b org.westlake.imehost -a EntryAbility`
  (`open_broker.sh` `open_app()` + the "re-front the host window" comment). A launch requested while a foreground app is
  active passes AMS's foreground check.
- FZ-001's second half ("prefers the app's **own launcher entry**") is exactly this: the launch comes from a launcher
  entry/foreground context.

So on 9-27 the host was fronted via a foreground launcher/broker chain. The bare `provision_toutiao.sh` watchdog
(`watchdog.sh:95` does the same `aa start imehost`) only works when the board session is already foreground/active — not on
a freshly-rebooted board sitting at the keyguard.

## Why 10107101 today (bare post-reboot board)
`aa start -b org.westlake.imehost -a EntryAbility` from an `hdc` shell → **ErrCode 10107101 "Permission check failed when
launching the ability"**, even after dismissing the keyguard. Cause, pinned statically:
- **imehost's `module.json` requestPermissions = only `INTERNET` + `GET_NETWORK_INFO`** — it does **not** declare
  `ohos.permission.START_ABILITIES_FROM_BACKGROUND`.
- An `hdc` shell is **not a foreground app**, so launching imehost is a **background** start. AMS runs
  `canStartAbilityFromBackground`; without the permission it **denies** → 10107101. (Same failure the watchdog hits.)
- `persist_demo.sh` / `open_broker.sh` would provide the foreground caller, but `persist_demo.sh` **refuses 5ea** (protected
  board), so that path is unavailable here.

## FZ-001's grant mechanism (and why imehost doesn't get it today)
FZ-001 (frozen) gives **BMS-installed Android bundles** `START_ABILITIES_FROM_BACKGROUND` so they go from WMS denial to
`canStartAbilityFromBackground:1`. Mechanism (FZ-001 README + HANDOFF): the resource HAP **declares the background-start
request in module.json**, and the **installer** (`libbms.z.so 6aadb8b4`, `libapk_installer.so 7048c7c5`) applies an
**ACL/preAuthorization block (APL_NORMAL) + a fresh token**. imehost is an **OHOS HAP installed via plain `bm install`**, not
through that installer, so none of that grant is applied — hence no permission.

## Minimal authorization — ON-BOARD PROVEN: runtime `atm` grant is NOT enough; FZ-001's ACL re-sign is the real minimal
I tested the runtime grant on 5ea and it is **blocked**, which pins the exact reason FZ-001 lives in the installer:
```
atm dump -d -p ohos.permission.START_ABILITIES_FROM_BACKGROUND  ->
  { grantMode: SYSTEM_GRANT, availableLevel: SYSTEM_BASIC, availableType: SYSTEM, provisionEnable: true }
imehost token 536980001 is APL_NORMAL (isSystemApp=false)
atm perm -g -i 536980001 -p ohos.permission.START_ABILITIES_FROM_BACKGROUND  ->  Failure  (grantStatus stays 0)
aa start -b org.westlake.imehost  ->  still 10107101
```
The permission is **SYSTEM_BASIC**; imehost is **APL_NORMAL**. A runtime `atm perm -g` **cannot cross the APL boundary** —
only an **ACL grant carried in the signing provision** (`availableType: SYSTEM`, `provisionEnable: true`) can give a
NORMAL-APL app a SYSTEM_BASIC permission. **That is exactly FZ-001's mechanism**: the installer applies the ACL/preAuthorization
from the resource HAP's provision profile. So "reuse FZ-001" cannot be a runtime hack — it must be the same provision/ACL path.

### The minimal grant (reuse FZ-001's provision/ACL, touch no frozen binary)
Re-sign `source-host.hap` so the installer grants it at `bm install`, reusing FZ-001's ACL/preauth path verbatim:
1. **module.json**: add `{"name":"ohos.permission.START_ABILITIES_FROM_BACKGROUND"}` to imehost's `requestPermissions`
   (alongside INTERNET/GET_NETWORK_INFO).
2. **Signing provision profile**: add `ohos.permission.START_ABILITIES_FROM_BACKGROUND` to the profile's
   `acls.allowed-acls` (the permission is `availableType:SYSTEM, provisionEnable:true`, so it is grantable via the ACL list).
3. **Re-sign** the HAP with `hap-sign-tool` using the demo app-signing keys, then `bm install -p` it. The installer applies
   the ACL at provision → `canStartAbilityFromBackground:1` → `aa start imehost` (and the watchdog's launch) succeed.
- **No frozen item touched**: `libbms`/`libapk_installer` (FZ-001's binaries) are unchanged; only the imehost HAP is
  re-packaged. This is a **build-side** change (needs the signing profile/keys), not an on-board runtime op — hence it was
  out of scope for this on-board window.
- **Reversible**: rollback uninstalls the re-signed imehost.
- **Alternative (no re-sign, demo-board only)**: the 9-27 **foreground-launcher chain** — the `org.westlake.launcher13`
  HAP in the foreground triggers `open_broker.sh` (root), whose `aa start imehost` then has a foreground caller and needs no
  background-start permission. This needs the launcher's correct ability + the broker's `manifest.txt` set up (normally by
  the 5ea-protected `persist_demo.sh`), so it is a demo-harness bring-up, not a one-liner.

## On-board result (5ea, this window)
- **Grant attempt**: `atm perm -g` → **Failure** (SYSTEM_BASIC vs APL_NORMAL, proven above). `aa start imehost` stays 10107101.
- **On-screen**: **not captured** — the host window still cannot front without the ACL-granted permission (build-side re-sign)
  or the full foreground-launcher/broker demo bring-up. The Toutiao child was alive again (ICU cleared, unchanged finding).
- **Verdict for the outer**: the minimal grant is **re-sign imehost with the START_ABILITIES_FROM_BACKGROUND ACL (reuse
  FZ-001's provision)** — a one-time HAP re-package, then the on-screen 3× + 10-key run can proceed on any board. The runtime
  `atm` shortcut is ruled out by the APL boundary.

---

# Re-sign executed (outer-approved (a)) — ACL half works, but the grant needs the preauth half on read-only /system

Built `resign/source-host-sab-5ea.hap` (SHA `2884a8bf…`, same bundleName, public OH SDK, 5ea UDID) via `resign/resign-local.sh`
(= `bms/src/tools/wl-tools/resign.sh` + a module.json `app.bundleName` fallback, since `source-host.hap` has no `pack.info`):
- `module.json` requestPermissions += `START_ABILITIES_FROM_BACKGROUND`; signing profile `acls.allowed-acls` = that permission
  (`resign/profile-template-sab.json`); `verify-app` → codesign success. Manifest: `resign/manifest.json`.

On-board (5ea, HOST_HAP override installs the re-signed HAP):
- Install OK, new token `536976088`; the permission is **now present in imehost's token** (the ACL/profile half worked).
- **BUT `grantStatus:0`, `grantFlag:4` (SYSTEM_FIXED)** — declared/allowed, **not granted**. `atm perm -g` retry → **Failure**
  (SYSTEM_FIXED, atm can't override). `aa start imehost` → **still 10107101**. On-screen still 0.

**Root cause (sharper than before): FZ-001's grant has TWO halves and re-sign only supplies one.**
1. **ACL in the signing profile** — reused via re-sign; it puts the permission in the token. ✓
2. **preAuthorizationInfo at install** — what actually sets `grantStatus=1`. It lives in
   `/system/etc/app/install_list_permissions.json` (bundleName + app_signature + permissions), which on these boards is on
   the **read-only** rootfs (`touch` → "Read-only file system"; imehost is not listed), **or** inside the frozen BMS
   installer (Android-bundles only). A plain `bm install` of an OHOS HAP supplies neither. ✗

So the re-sign is **necessary but not sufficient**; the board blocks the second half without a /system write.

## Remaining options (for the outer to choose)
- **(a) Reuse FZ-001's preauth entry**: add imehost (bundleName + the re-signed cert's `app_signature` + the permission) to
  `install_list_permissions.json` and have it in place at install — needs the entry on `/system/etc/app/` which is
  read-only, so it requires a **/system remount or a bind-mount** of a modified file (board-drop risk per RUNBOOK; a /system
  change). This is the faithful FZ-001 preauth reuse.
- **(b) Foreground-launcher chain** (no grant at all): the 9-27 path — `org.westlake.launcher13` foreground →
  `open_broker.sh` → `aa start imehost` with a foreground caller. Needs the launcher ability + broker manifest set up
  (normally by the 5ea-protected `persist_demo.sh`). No /system change.
- **(c) Diagnose the regression**: the Sept demo ran the **same** `aa start imehost` from a root shell successfully; today it
  is 10107101. The permission may not be the true lever — an environmental/AMS state change between then and the unified-era
  boot could be the real cause. Worth a focused static/log diff before more grant work.

Verdict: re-sign (ACL) is landed and correct for FZ-001's profile half, but on-screen needs either the /system preauth
(remount/bind — board risk) or the foreground-launcher path. On-screen 3× + 10-key remain uncaptured; Route B runtime
viability (Toutiao runs, ICU cleared) is unchanged.
