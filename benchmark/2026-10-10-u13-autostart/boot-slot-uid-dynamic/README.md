# Toutiao Route B boot slot — uid-DYNAMIC alignment (#91 cc-wiki, 2026-10-10)

Aligns the master Toutiao boot slot (`cfab66ae8c`, `benchmark/2026-10-10-toutiao-boot-slot/`) with the
**proven 61b full-reprovision flow** (`../RESULT-61b-toutiao.md` UPDATE3, screenshots outer-signed).
Offline only; nothing here touches a board. For cx-bms's `demo_seal_61b` orchestration to call.

## The problem this fixes

OpenHarmony assigns the imehost host app a uid at install time, does **not** preserve it across
uninstall+reinstall, and does **not** reclaim the original. The Route B donor bundle was built for uid
`20010053` and pins it in **three** kinds of place — so after any reinstall the child spawns under the
old uid, cannot render into the (new-uid) host window, and the feed is black (proven #91):

| pin kind | where | reconcile |
|---|---|---|
| text | `*.sh` (run.sh `ASX_RUNTIME_OWNER_UID`, start-parent.sh `source_app_namespace` arg, watchdog.sh, preseed_metasec48.sh, prepare_jit50.sh) | `sed OLD→U` on every `*.sh` under RT/F/ROOT (portable, no `sed -i`) |
| **binary** | `request.bin` — uid+gid as **two little-endian uint32** at offsets **312 & 316** (ASCII grep cannot see it) | `dd` the LE bytes of U at the pinned offsets (octal `printf`, read-back verified) |
| ownership | the RT tree | `chown -R U:U` |
| self-heal guard | `route-b-owner.sh` `rb_owned` uid match | `RB_OWNER_UID` read from the installed host |

The host uid `U` is read at boot: `stat -c %u /data/app/el2/100/base/org.westlake.imehost`.

## Boot flow (ENABLEd slot, after U13 READY)

1. Gates (unchanged from master): DISABLED, U13 ready + receipt + boot_id, `immutable.tsv` identity
   **for the files reconcile does not touch**, host present. **No hardcoded uid gate** — any numeric uid.
2. **`reconcile_uid.sh`** → all four pins above set to `U`. Idempotent, fail-closed.
3. `private-tmp` owner checked `= U:U` (dynamic).
4. **keeper starts at boot** (before the tap) so SCBScreenLock does not cover the desktop and the
   今日头条 icon stays tappable. (Master started it only after the tap.)
5. Wait for the real foreground desktop tap → imehost0 (no `aa start`; it is 10107101-blocked).
6. Start the donor watchdog → child spawns into imehost0 via the uid-reconciled `request.bin` → feed.
   `ARMED`. Screenshots, not this state, decide lighting.

Unchanged safety contract: no HAP install/extract, no global mount, no `aa start`, no service
start/stop, no U13 mutation, no `setenforce`, no name-based kill, appspawn-x never touched (RUNBOOK #12).

## Files

- `reconcile_uid.sh` — the uid reconciler (stat/find/sed/dd/printf/od only; no python/awk/tr/xxd).
- `westlake-u13-toutiao-overlay.sh` — the uid-dynamic boot worker (supersedes master's).
- `route-b-owner.sh` — master's guard with a dynamic `RB_OWNER_UID` (was hardcoded `20010053`).
- `tests/test_boot_slot_uid.py` — 14 offline KA (binary-patch byte-equivalence to `struct.pack`,
  text reconcile, idempotent-for-any-uid, overlay contract, dynamic self-heal match). `python3 -m unittest`.

## Integration for cx-bms `demo_seal_61b`

1. Stage `reconcile_uid.sh` + `route-b-owner.sh` + this `westlake-u13-toutiao-overlay.sh` to
   `/data/westlake-demo/toutiao/scripts/` (mode 0550), and the worker also at
   `/system/etc/westlake-u13-toutiao-overlay.sh` (the cfg path). Reuse master's
   `01_westlake_u13_toutiao.cfg.disabled` unchanged (same service/job contract).
2. **`immutable.tsv`**: do **not** pin the content SHA of the six reconciled files
   (`run.sh`, `preseed_metasec48.sh`, `prepare_jit50.sh`, `start-parent.sh`, `watchdog.sh`, `request.bin`)
   — the overlay excludes them from the identity gate and verifies them via the reconcile step instead.
   Keep pinning the archives, `appspawn-x`, `screen-gate`, the worker and the owner guard.
3. **ENABLE** = `rm /data/westlake-demo/toutiao/DISABLED` + place the (renamed-active) cfg, per the
   existing seal step order. Boot-slot stays disabled until that step; the single v1-seal reboot then
   auto-brings-up keeper + (on the user tap) the watchdog, uid self-consistent for whatever uid 61b's
   imehost holds.
4. `prepare_payload.py`: drop the `exact host UID 20010053` precondition; the slot is uid-agnostic now.
   The request.bin uid offsets are pinned in `reconcile_uid.sh` (`312 316`) for the donor request.bin
   (len 672); if the request payload is ever rebuilt, re-derive offsets with
   `python3 -c "import struct;b=open('request.bin','rb').read();import re;print([i for i in range(len(b)-3) if struct.unpack('<I',b[i:i+4])[0]==20010053])"`.

## For the t5 demo-runbook (头条 section) — line for cx-bms to add

> 冷启后头条可能弹「登录领现金/提现」浮层,点浮层**左上角的 ✕** 关掉即回到 feed(不要点「立即登录」);关掉后刷首页/点文章正常。

(The t5 demo-runbook is cx-bms's generated artifact `benchmark/2026-10-09-demo-baseline/t5/demo-runbook.md`
via `build_runbook.py`; add this to the runbook source, not the generated file.)
