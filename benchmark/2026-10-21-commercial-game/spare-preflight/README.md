# COMMERCIAL-G05 — 5ea fresh read-only preflight + minimal Genshin first-launch plan

**Outer disposition:** fresh observations accepted; the disabled plan and rollback are not executable approvals. See [outer-review.md](outer-review.md) for known defects and the G06 successor boundary.

Contract: `specs/commercial-game-round1/t5-spare-preflight.spec.md` @ `b3971d0379`. Device writes **0**: no lock, install,
click, reboot, file write or REA; 61b untouched. Input: official APK `abd3c4d5…` (COMMERCIAL-G03). Runtime NOT_TESTED.

## What was wrong first (kept)

- `p01–p06`: the first six samples passed the hdc prefix as one zsh word, so they failed **locally** with rc 127
  (device not contacted). Kept as `INVALID_LOCAL`; re-run as `q01–q06`.
- `q09`: `hilog -x … -z` is the RUNBOOK-documented invalid combination (CODE -31); kept as a failure. Successors use
  only the T23-verified single tail mode.
- `o02/o03`: first plan had `before_unlock` as a list of argv lists; `board_run.py` requires one argv list. Kept.
- `hdc shell` does not return the remote rc, so an inline `bm uninstall` cannot gate unlock; the rollback verdict is
  computed locally by `tools/rollback_genshin.sh` (rc 0 only if the package is absent afterwards).

## Fresh state (this run's receipts only)

| Item | Value |
|---|---|
| connection | USB Connected (`hdc list targets -v`) |
| boot_id before / after | `45339478-78d4-4211-ac17-6975440de5ce` / same; uptime ≈ 190 746 s |
| lock | no holder (`board_note.sh held` rc 1); last board LOCK/UNLOCK 2026-10-19 17:08 |
| system | OpenHarmony-6.1.0.31, API 23, kernel 5.15.180 aarch64, SELinux Permissive |
| memory / disk | MemTotal 7 570 984 kB, MemAvailable 5 680 148 kB; data 232 G, 158 G free |
| host / parent / child | **no appspawn-x process** at sample time; native `appspawn` pid 395; `/system/bin/appspawn-x` is bind-mounted |
| runtime deploy | 40 runtime bind mounts (`/system/android/**`, child `.so`, two `route-a` digests `74d1d6d4…`, `74e6f759…`); no on-board `runtime-fingerprint.txt` |
| installed | Genshin **not** installed; `com.Unity3d.BoatAttackDay` and `com.a2hlab.bridge.zigzag` present; 218 bundle-dump lines |

### Supplement (outer request: fresh per-file FP, launch config, full bm dump, foreground, power, install dirs)

Same boot `45339478…` before (`r01`) and after (`r08`).

- **Fresh fingerprints** — `tools/fresh_fp.py` imports the *original* `bms_batch.runtime_fingerprint` /
  `boot_image_fingerprint` unchanged and feeds them a read-only hdc shim that only allows their `sha256sum …` read
  (remote rc 0, 0). RUNTIME **`fd464714645b`** (124 members, `fresh-fp/runtime-fingerprint.txt`), BOOTIMAGE
  **`ee927db88a67`** (36 members). Versus the 2026-10-13 record: runtime `9745004d10ce` → `fd464714645b`, exactly one
  member differs — `/system/android/lib64/liboh_android_runtime.so` `f28bd1b3d44e` → `94718e0d0b61`; boot unchanged.
  The plan's smoke spec now expects the fresh pair; the 10-13 value was never used to try a smoke.
- **Launch config** — init cfgs naming appspawn-x: `00_westlake_u13_recover-v3.cfg` (`897f9ca0…`, U13 recover:
  post-fs-data baseline mounts + BoatAttack demo overlay) and `appspawn_x.cfg` (`5a499244…`); `/system/bin/appspawn-x`
  `2a87118e…`; `pidof appspawn-x` empty (ondemand, not running).
- **bm dump -a** — complete, non-empty, 218 lines starting `ID: 100:`; Genshin absent.
- **Foreground** — WMS `Focus window: 15` = `SCBScreenLock10` (lock screen).
- **Power** — `Current State: SLEEP`; original values `ScreenOffTime Timeout=30000ms`, `OverrideTimeout=10000ms`.
  Waking/unlocking is a device write owned by G06, not done here.
- **Install-dir before-image** — absent: `/data/app/el1/bundle/public/com.miHoYo.Yuanshen`,
  `/data/app/el2/100/base/…`, `/data/app/el2/100/database/…`, `/data/storage/el2/base/haps/…`; 220 public bundle
  dirs; 743 leftover `/data/local/tmp/bms-batch-*` stage dirs; data 158 G free.
- Installer native-lib extraction: not reviewed here (delegated by outer to peer `base5_delta_review`).

## Minimal first-launch plan (`plan/`, disabled)

Existing tools only: `scripts/lab/board_run.py` → `activation_smoke.py` → `benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py`.

- Entry (repo root, after outer approval flips `execution_enabled`):
  `python3 scripts/lab/board_run.py benchmark/2026-10-21-commercial-game/spare-preflight/plan/board-run-genshin-5ea.disabled.json --detach`
- board_run fixes: LOCK → smoke gate (fingerprints + zigzag launch-only control) → shard
  `bms_batch --execute --serial 5ea… --lane cc-video --manifest plan/manifest-genshin.json --input-root $HOME/…/spare-preflight/input-root --keys genshin --reinstall --hilog --shots 5,20 --stop-new-keys-at <lock+1200 s>`
  → `before_unlock` → UNLOCK. Window 30 min, no new tests after 20 min (1200 s).
- Input root (private): `genshin/app-input.json` pins package, APK SHA and launch activity
  `com.miHoYo.GetMobileInfo.MainActivity`; `bms_batch --resolve-inputs` resolved it offline, rc 0.
- Rollback: `tools/rollback_genshin.sh 5ea…` (uninstall + `bm dump` readback; lock retained if still present).
  Nothing else is written, so no runtime/data reset.
- Collected in-window: install readback, child PID, t5/t20 focused screenshots, hilog reset+dump, new faultlogs.
- Offline checks: `--dispatch` rc 0; disabled plan → `REFUSE … no lock taken`.

**Unknown:** whether fingerprints still match at window start; screen wake/unlock (G06 write); whether t20 already shows Genshin (board_run hard-codes `--shots 5,20`, no plan
override → flagged to Codex); whether the installer extracts the 32 arm64 libs itself (no sidecars); whether
appspawn-x starts on demand after this boot (the zigzag control answers it first). Not in scope: login, clicks
beyond launch, full content, runtime replacement, 61b.

## Files

`results.json` (fresh state, plan, 22 receipts with aliased argv/rc/class/raw refs), `plan/` (board_run plan,
smoke spec, manifest, keys), `tools/` (`rec.sh`, `gen.py`, `fresh_fp.py`, `rollback_genshin.sh`), `fresh-fp/` (fresh member lists). Raw: `$COMMERCIAL_G05_PRIVATE` =
`$HOME/.local/share/westlake/commercial-game-20261021/spare-preflight/`. Check: `cargo test --test commercial_game_spare_preflight`.
