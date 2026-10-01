# libinstalls alignment plan (DRAFT — daytime, user present; do not touch any board here)

#80 follow-up. fd-seal's `com.junkfood.seal` install fails on 5ea/5cd because their `libinstalls.z.so` is the
original **`2c9a5294`**, while 61b carries the #79-accepted **`51e1b525`** (the libinstalls that registers the
native-data exact exceptions for seal's 3 packaged `.zip.so` blobs). This plan aligns 5ea/5cd to `51e1b525`.
installd loads libinstalls, so replacing it **restarts foundation → USB-drop / whole-machine-reboot risk** — hence
"daytime, user present, direct-connect board". This is a system-library change: **outer-ring review required before
any board touch.**

## 1. Source artifact + shas + the two on-board paths
- **Target `51e1b525`** (#79 / b79 build output, the authoritative source — do **not** pull 61b's live copy as the source):
  `$WORKSPACES/oh61-bms-kit-b79/out/wukong100/bundlemanager/bundle_framework/libinstalls.z.so`
  sha256 `51e1b52538b3198d2a8a3236a9479bf8512f51acc74c0d68e34acca358f39be5`
  (identical copy also at `$WORKSPACES/oh61-bms-kit-background-launcher/out/wukong100/bundlemanager/bundle_framework/libinstalls.z.so`).
- **Current on 5ea/5cd `2c9a5294`** (rollback target):
  sha256 `2c9a5294a253acb57394cc79956a4b30182a7a0ecad570844c395b38d34d82e0`
  (e.g. `.../b68-generation/platform-pool/system/lib64/libinstalls.z.so`).
- **Two device paths** (both must be replaced and read back, same as the installer pair):
  `/system/lib64/libinstalls.z.so` and `/system/lib64/platformsdk/libinstalls.z.so`.
- Pre-flight: read back both paths on 5ea **and** 5cd and confirm each is `2c9a5294` before any write (`sha256sum`);
  record the exact starting hashes in the transaction state (the rollback baseline).

## 2. Difference vs `2c9a5294` (abi_diff + --calls)
`abi_diff.py --old 2c9a5294 --new 51e1b525 --calls` (LLVM_OBJDUMP = DevEco llvm-objdump):
```
exports: old 1096, new 1096; removed 0, added 0; signature drift 0; consumer breaks 0
call-set diffs: 1 function(s) differ
  CALLS+ non-virtual thunk to OHOS::AppExecFwk::InstalldLoadCallback::OnLoadSystemAbilityFail(int): ['strlen']
```
So the two libraries are **ABI-identical** (same 1096 exports, zero signature drift, zero consumer breaks) and the
only call-graph delta is one `strlen` in an installd load-callback. **The native-data exception acceptance is
data-/validation-driven, not an ABI or call-graph change** — it does not show up in this static diff. That is good
for regression surface (tiny), but it means the static diff does **not** prove the behavioural change; the
"accept seal's 3 `.zip.so` by exact bundle+ABI+name+SHA" behaviour is validated **empirically** by #79 (61b installs
seal; 5ea/5cd `2c9a5294` fail at `installd_operator:3222` native CRC/ELF/owner/mode check) and must be re-verified
on 5ea/5cd after the swap (step 5), not assumed from the diff. The registered exceptions (#79
`install-wall-validation/native-data-exceptions.json`): `com.junkfood.seal` arm64-v8a `libaria2c.zip.so`
(d3c2dc0a, 4.22 MB), `libffmpeg.zip.so` (68359d6c, 16.71 MB), `libpython.zip.so` (0210b122, 11.70 MB); apk
`7070a3d4`.

## 3. Single-file replace + rollback (reuse `scripts/lab/swap_installer.py`'s transaction)
`swap_installer.py` already does the exact two-path, backup→atomic-replace-under-rw-remount→`begetctl` restart→
read-back-SHA transaction, but for the **installer pair** (`libbms.z.so` + `libapk_installer.so`); its `PATHS` =
`{libbms.z.so, libapk_installer.so} × {/system/lib64, /system/lib64/platformsdk}`. **Extend it (or a sibling
transaction) to carry `libinstalls.z.so`** — add `libinstalls.z.so` to `LIBS` (or a `--libs` arg) and supply a kit
dir whose `manifest.json` names the `51e1b525` candidate. Keep everything else unchanged. Steps per board
(5ea then 5cd; use `--transaction-name libinstalls-51e1b525` to isolate backup/state from the installer-pair rollout):
1. `swap_installer.py dry-run  --serial <board> --kit <libinstalls-kit>` → prints the 2 paths + candidate sha, no write.
2. `swap_installer.py apply    --serial <board> --kit <libinstalls-kit> --lane <lane> --transaction-name libinstalls-51e1b525`
   → verified backup of both live `libinstalls.z.so` (must be `2c9a5294`) to `backup/`, atomic replace with
   `51e1b525` under rw remount, state `installed_not_restarted`.
3. `swap_installer.py restart  --serial <board> …` → `begetctl stop_service installs; begetctl stop_service
   foundation; sleep 3; begetctl start_service foundation` (foundation restart — see §4).
4. `swap_installer.py verify   --serial <board> …` → both device paths read back `51e1b525`; exactly one
   `foundation` process; installd healthy.
- **Rollback**: `swap_installer.py rollback --serial <board> … --transaction-name libinstalls-51e1b525` then
  `restart` → restores both paths to the backed-up `2c9a5294` and restarts foundation. On any mid-apply failure the
  tool self-attempts the per-file rollback (`.b89-rollback` tmp) and marks `apply_failed_rollback_attempted`;
  operator confirms both paths are back to `2c9a5294` before leaving the board.
- Do **not** `-r`/incremental; do **not** `kill -9` appspawn-x (RUNBOOK): foundation restart is via `begetctl`
  only. This swap touches only libinstalls — the runtime/bridge/appspawn-x bind-mounts are not re-deployed, but a
  whole-machine reboot (§4) would drop them, so have the v3a recovery (appspawn-x `--replace` + v4 remount) ready.

## 4. Foundation restart + USB-drop risk (RUNBOOK §"Mac 控制端")
Replacing an installd dependency restarts **foundation** (`begetctl stop installs; stop foundation; start
foundation`). Per RUNBOOK: on 2026-09-29 a 61b installer swap triggered a foundation restart that cascaded into a
**whole-machine reboot**, after which 61b **disappeared from USB enumeration** (`ioreg -p IOUSB` had no such serial)
and needed a **manual physical re-plug** by the user. So:
- Do 5ea/5cd **only when the user is present** and, if possible, with the board **direct-connected** (not via the
  hub); announce on the blackboard before the write; tell the user a manual re-plug may be needed.
- One board at a time; finish+verify (or roll back) 5ea before starting 5cd.
- If a board whole-machine-reboots: the appspawn-x / v4 bind-mounts are lost → follow v3a README (recover the
  generation, `--replace` appspawn-x via `begetctl` restart with socket owner `0:6005` / `0660` /
  `u:object_r:appspawn_socket:s0`, re-mount v4) and re-read all fingerprints before declaring the board back.

## 5. Re-verify apps after the swap
On each swapped board, install + launch and read results (screenshots = ground truth, outer-ring reads):
- **fd-seal** (`com.junkfood.seal`, apk `7070a3d4`) — the target: install must now **succeed** (no
  `installd_operator` native CRC/ELF/owner/mode failure on the 3 `.zip.so`), launch + screenshot.
- **#79 original evidence apps** (`install-wall-validation/results.json`): `com.junkfood.seal`,
  `com.ss.android.article.news` (toutiao), `com.twitter.android` — confirm each still installs as in #79 (no new
  install wall from the libinstalls bump). (toutiao's first-frame is separately blocked by #90's libflipped→
  libstdc++ wall; that is not a libinstalls regression — judge toutiao on *install*, not lit.)
- **U9 already-lit controls** (a few, from the 61b U9 shard alive-at-t20 set) — e.g. `anki`, `markor`,
  `fd-minetest`, `fd-reader`, `fd-tusky` — must still install **and light** = the libinstalls swap did not regress
  the working path. (`helloworld` as the non-flaky smoke control.)
- Compare to the board's own pre-swap run where available; a fresh install (`bm uninstall → install`, not `-r`) is
  required for any app whose install-time checks changed.

## 6. Add libinstalls to the unified-state identity + runtime-fingerprint
Root cause of this whole split (board #80): `libinstalls.z.so` is **not** in the unified-state identity — it is
absent from `FINGERPRINT_PATHS` in `scripts/lab/sweep_bind_deploy.py` (which currently lists `appspawn-x`,
`oh-adapter-runtime.jar`, `/system/android/lib64/*.so`, `/system/lib64/westlake/route-a/*/*.so`,
`/system/lib64/libbms.z.so`, `/system/lib64/libapk_installer.so` — note it names libbms/libapk_installer from
`/system/lib64` explicitly but **not** libinstalls, and `/system/lib64/*.so` is not globbed). So three-board
libinstalls drift was invisible to the activation-smoke fingerprint gate.
- **Add both paths** to `FINGERPRINT_PATHS` (and the matching set in `bms_batch.py` — "keep in sync with bms_batch
  FINGERPRINT_PATHS / BOOT_IMAGE_PATHS"): `/system/lib64/libinstalls.z.so /system/lib64/platformsdk/libinstalls.z.so`.
- After aligning all three boards to `51e1b525`, recompute the unified-state `runtime_fp` (it changes once
  libinstalls is in the set) and update the 316-identity / RUNTIME list so any future board that drifts on
  libinstalls is caught by the smoke fingerprint check at window time. Record the `51e1b525` entry (both paths +
  sha) in the identity manifest.

## Open items for outer-ring review before scheduling
- Confirm the `51e1b525` source is the b79 kit output above (not 61b's live copy).
- Approve extending `swap_installer.py` `LIBS` to libinstalls (vs a separate transaction).
- Confirm board order (5ea then 5cd), direct-connect vs hub, and the user-present window.
- Confirm the identity/fingerprint change lands with the three-board alignment (so the smoke gate flips on
  immediately after).
Evidence: #79 `bms-deploy/benchmark/2026-09-29-install-wall-validation/` (native-data-exceptions.json, results.json,
abi-diff.json); board #80 entries 2026-10-01 19:49–19:54.
