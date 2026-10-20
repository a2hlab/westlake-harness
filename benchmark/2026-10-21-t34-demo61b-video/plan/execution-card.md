# T34 61b video-migration execution card (LOCAL prep; not executed; lock only after cx pkg + outer approval)

cc-video = unique 61b lane. 5cd read-only, 5ea untouched. No device op in this card — it is the pre-studied
plan + recovery so nothing is researched at window-open time. Ground truth = `snapshot_display` screenshot.

## 0. Guardrails
- Lock 61b ONLY after cx's fresh/unsigned data pkg arrives AND outer approves. **Single same window**: stop
  experiments by `START+1200`, restore and close by `START+1800` (executor61b.py enforces age<1200 for
  non-rollback and 0<=age<1800 overall). **No separate recovery window, no reset start.** Every device
  command: persist argv/stdout/stderr/rc; a `Connect server failed`
  with rc0 is NOT success. All file replacements use **atomic rename, not in-place write** (physical ==
  parent-private proven in intake, so an in-place write would be seen through the /data/local/tmp/asx bind).

## 1. Apply-time BEFORE snapshot (must re-verify fresh, not reuse stale)
- Re-run cx `render_supplement.py --boot <fresh> --parent 5066 --birth 6658 --host 4859 --hostbirth 6415`;
  its before/after boot+birth+uid+TracerPid guards MUST pass. If boot_id or birth changed (reboot/respawn),
  STOP and re-pin from the live board — do not apply against a stale identity.
- Full before-image already captured (intake-01 + supplement-01):
  host HAP **b18978b8** (b189, the T33 retained baseline), uid/gid 20011206, token 537243994, WID30,
  4 SO at before (bridge d4fae8e5, mffmpeg fecf91e1, ttmplayer b427614d, shim 85c789f4), **compat absent**,
  run.sh **6afd6fba** (= T33 *after*, WID30; the earlier "≠ reference d3518cef" is T33 before(WID33) vs
  after(WID30), not a conflict), cfg 91e31b95, guardian 18/18, power 30000/86400000, debug unset (errNum106),
  providers OpenSLES 05d8ac90 / liblog d8ad176b / network_compat f6c354d1.

## 2. Migration (video) — SO-only, host HAP unchanged
T30 final-01 artifacts move the **5 SO + run.sh**; the host HAP stays **b189** (video does NOT touch the HAP):
| object | before | after |
|---|---|---|
| liboh_adapter_bridge.so | d4fae8e5 | **b0e5602a** |
| libwebview_bionic_shim.so | 85c789f4 | **7f8d75bb** |
| lib/arm64-v8a/libmffmpeg.so | fecf91e1 | **d2882303** |
| lib/arm64-v8a/libttmplayer.so | b427614d | **0b4d95c5** |
| libopensles_android_compat.so | (absent) | **6e83e924** (added) |
| run.sh | 6afd6fba (WID30) | **8d996f946e36de839280c7524dbb53d0538f922e3d8886a9895f522cac5f4954** — cx-derived for THIS board (reuses the T31 environment config, then derives 61b UID/WID; this is more than a WID change, and is NOT the 5cd 11d3d671) |
- After-source = cx unsigned pkg `../westlake-harness-t4/benchmark/2026-10-21-t34-demo61b-video/bound-data-01`
  (fresh SHA `5adc67be88308adb4758e60dfe3639ce4b3238e8e8a48f78250df79ba427accc`); apply via executor61b.py
  `apply` (preview default, `--execute` to run) with the admission/plan from COMMANDS.md.
- Keep uid 20011206 / token / el2 data; no uninstall; atomic rename each SO into the RT; then normal restart.

## 3. Same-window recovery — ONLY T34 executor61b.py rollback (NOT T31 recovery.py)
- **Forbidden:** `benchmark/2026-10-20-t31-demo-retain/recovery/recovery.py` — it pins 5cd UID / WID29 and
  cannot serve 61b.
- **Use** `benchmark/2026-10-21-t34-demo61b-video/deployment/executor61b.py rollback` within the SAME window
  (recovery reserve START+1200..START+1800). Recovery restores the **original backup bytes** (the on-device
  `.t34-61b-before-<original boot8>` backups, including the original WID), host HAP b189 / UID 20011206 /
  token / guardian 18 / providers preserved; compat returns to absent. This is identity recovery, not feed
  recovery; a failed recovery is retained and does NOT change the verdict (outer decides acceptance).
- Binding = main-tree `COMMANDS.md` original text (§"Same-window rollback, including no-parent physical
  recovery"). No-parent physical recovery:
  ```
  python3 "$D/executor61b.py" rollback --execute --recovery-no-parent \
    --boot <fresh> --hdc <hdc> --holder <holder> --start <START> --repo <repo> --inputs <inputs> \
    --data <data> --apply-plan "$W/apply/plan.json" --origin-admission "$W/admission.json" \
    --admission "$W/rollback-admission.json" --out "$W/rollback-01"
  ```
  Live-parent rollback: omit `--recovery-no-parent`, pass the fresh `--parent`/`--birth`. `rollback-admission.json`
  is built from the original **actual** admission (preserve `origin_apply_plan_sha256`, origin admission keys,
  `deployment_scope=T34_61B_VIDEO`, `approved_by=outer(codex)`; set `recovery_run_sha256`/`recovery_wid` to the
  current captured physical run). Retain the same original apply plan + backup names.

## 4. reboot / normal-icon / UI screenshot — SMOKE only (ground truth)
- After apply: normal restart (guardian re-spawns; fresh identity is expected — do NOT replicate old PIDs);
  one desktop icon tap → Toutiao feed. Capture `snapshot_display`.
- **This round = normal-desktop-icon lit-screen SMOKE only** for BoatAttack + one ordinary app. NO full game
  race / LAP / GAME_PASS, NO `interaction_steps.py` runner, NO `plan.disabled.json` (disabled ≠ authorization).
  Entries are REFERENCES from base5 `entrypoints.json`; pick per the ACTUAL desktop:
  - **BoatAttack**: launch via its **normal desktop host icon** (NOT an Android UnityActivity aa ability) →
    lit screen → `snapshot_display`. Operating limits per `benchmark/2026-10-09-demo-boatattack/v2-20261013/
    outer/final61b-v2-seal/OPERATIONS.zh.md`.
  - **One ordinary app (not Toutiao)**: a known-working key from `benchmark/2026-10-14-final61b-full128-outer/
    demo-list.json` `ordinary_app_keys` (e.g. `cv2-com-kaajjo-libresudoku`), via its normal desktop icon → lit
    → `snapshot_display`. No install / data-clear / runtime-relaunch shortcut.
- Screenshots are the acceptance; process-alive / rc0 / bm dump are NOT lit. Card promise is bounded to the
  normal-icon lit-screen smoke; functional/game validation is out of scope this round.

## 5. power / debug restore (as T33)
- Restore power ScreenOffTimeout 30000 / OverrideTimeout 86400000; keep debug.ttplayer.log.enable UNSET
  (errNum106) unless an experiment temporarily set it — then clear it before retain.

## 6. Acceptance — audio (this round's contract: NO repeated human sound)
- The current contract FORBIDS repeated human-sound re-attestation. Human sound is **NOT a blocker** for this
  window and the user is **NOT asked**. The T31 audio addendum does NOT override this round's constraint.
- 61b new human-sound verification = **NOT DONE / unknown** (recorded as unknown, not a gate).
- The 5cd old sound receipt does **NOT** migrate to 61b.
- Audio acceptance this round = THIS board's **software audio evidence** (decode / AudioRenderer·OpenSLES
  submit markers in hilog) **+ visual acceptance** (screenshot feed + pause/resume/exit-reentry). Software
  submit != proven speaker output; that limit stays **unknown** (not re-tested by asking the user).

## 7. Unsigned retain template (mirror T33 accepted/results.json; SO-delta not HAP-delta; UNSIGNED)
See `retain-template.unsigned.json` — same fields as T33 (status, boot_before/after, identity, uid/token,
host_hap, runtime_before/after, guardian_files_unchanged, run_only_delta) but the delta is the 5 SO + run.sh
(+compat added), host HAP unchanged (b189). `signed_by: null` until cx binds + outer signs.

Receipts root (device exec, when approved): `$HOME/.local/share/westlake/t34-demo61b-video-20261021/`.
No lock / no device write / no REA in this prep. Supplement scanning is complete — not expanded.
