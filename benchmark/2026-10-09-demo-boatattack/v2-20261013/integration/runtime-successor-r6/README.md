# Final executable window entry

Use `window-final4-disabled/` as the review example. Earlier local preview directories are superseded and excluded from landing. Re-render on main so all executable/source refs bind the actual landed files:

```sh
export WORKSPACES="$(dirname "$PWD")" MAC_HOME="$HOME"
R=benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/runtime-successor-r6
python3 "$R/prepare_window.py" --out "$R/main-bound-NEW"
# Root fills authorization.required.json with actual reviewed approval/timestamps,
# sets board-run execution_enabled=true in a NEW enabled copy and independently pins it.
export R6_AUTH="<actual authorization path>" R6_AUTH_SHA="<actual authorization SHA>"
python3 scripts/lab/board_run.py "$R/main-bound-NEW/board-run.enabled.json" --detach
```

`after_lock`: exact original947 verification → three-source apply → original legal62-target snapshot + policy → one cold boot → READY56/BOUND7 → full319/seven bind SHA+metadata+owner inode/three source verification → unchanged original cadence Boat runner (only serial and runtime SHA changed) → five popup captures. The ORIGINAL board_run next runs the candidate HW/ZZ smoke gate; it is not duplicated inside after_lock. `before_unlock` always has its independent ten-minute reserve: exact source rollback → snapshot+policy → old947 cold boot if candidate boot was attempted → complete319/seven bindings/three sources → original HW/ZZ. Failure retains the lock. No-intent cleanup only reads and verifies old state, including BOUND7/owner inodes; no worker invocation, app launch or boot.

The window inherits actual r4 held/raw logging/popups/snapshot methods by pinned source. It retains per-line READY stripping and explicit remote status markers. It does not call the old5cd R5 or reuse5cd RouteB assumptions. Source-only rollback accepts boot-before-bind/partial-bind live states without accepting them as recovered: only the final old947 gates permit unlock. Two fake-device subprocess tests invoke the actual successor CLI and original W3 rollback preflight to verify these failure paths and exact restored SHA/mode/UID/GID/label, with zero live-target writes.

# Three-file runtime successor on 5ea

The two-file proposal was incomplete: the captured worker pins both TABLE_SHA and runtime947 in verify-bound. Exactly three board files change: runtime source (947 -> f28), one after-SHA cell in binds.tsv, and the worker's table SHA plus candidate runtime SHA. No recover/cfg byte changes are required: the captured recover calls the worker path without a hash; cfg names both scripts without script hashes. All seven bind rows, original187 apply preimage, ADC, no-parent, namespace, per-bind metadata/inode checks and boot ordering remain intact.

Inputs are root's actual `outer/r6-5ea-readonly/{probe.stdout.txt,control/*}` on boot35da6f13-e7b1-4472-a36a-5c4a69d5f191. `source-pins.json` pins every control capture. Runtime source:755/0/0/system_lib_file, inode66352:67173; table440/data_file, worker550/data_file; recover550/data_file and cfg550/system_etc_file are preserved. Original captured worker3f1a4643, tablea10586a1, recover291451a1, cfg897f9ca0.

`successor.py` reuses the SHA-pinned W3 core.apply backup/intent/failure-observation transaction and original W3 rollback_preflight. The original core.place sends directly to ordinary targets and is unsuitable for a mapped runtime inode. This adapter sends only to a unique sibling staging path, verifies SHA/metadata, then atomically renames that new inode. It never overwrites or unmounts the live bound inode. Apply and rollback both preserve the current seven live hashes; neither changes processes, mounts, config, nor boot. SHA/meta preimages, full319 membership (with W3's four explicit replacements), Boat BMS UID20011062, RouteB absence, original controls, full held line and current boot are checked. Transport retains numbered raw logs and its remote exit marker. All backups pass before the first replacement; rollback checks exact transaction membership and failed intent/observation through the original function.

## Offline commands

```sh
export WORKSPACES="$(dirname "$PWD")"
R=benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/runtime-successor-r6
python3 "$R/successor.py" prepare \
  --runtime "$WORKSPACES/westlake-inputs/generations/boat-v2-runtime-f28bd1b3-20261013/liboh_android_runtime.so" \
  --runtime-sha256 f28bd1b3d44e2944f77911c2ad71376869f7f3ebc6dcd8434dfea869f4056db0 \
  --hdc /Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc \
  --out "$R/NEW-package-disabled"
python3 "$R/successor.py" run --plan "$R/NEW-package-disabled/plan.disabled.json" \
  --action apply --out /tmp/unused-r6-preview
```

Actual stable-archive f28 disabled prepare and CLI preview passed, with zero transport construction. Main landing must re-run prepare from main, against T0's final archived artifact location; historical t4 package refs are not main execution inputs. No binary is copied into this landing.

## Root-owned window entry

Root creates a separately pinned enabled plan from the prepared plan (only execution_enabled=true), and an independent authorization. No signed approval is fabricated here. Use the same board_run lock and reserved rollback time as the previous window. `holder` is the COMPLETE `board_note.sh held SERIAL` line, including PID/timestamp; not the owner token alone.

Authorization keys:
`approved_by="outer(codex)"`, `plan_sha256`, `serial="5ea34a4500000000000000001123012c"`, `origin_boot_id="35da6f13-e7b1-4472-a36a-5c4a69d5f191"`, `boot_id` (actual current boot), `expires_epoch`, `holder`, `action="apply"|"rollback"`, `live_runtime_sha256` (947 for preboot apply, f28 for rollback after successful candidate boot; 947 if rolling back before reboot). Rollback additionally requires `source_restore_only=true`. Boot-before-bind or a partial bind prefix does not block exact source restoration: only the transaction backups, signed/observed source preimages, boot/holder and untouched persistent members gate that action. Full live identity remains mandatory after the rollback cold boot, before unlock.

```sh
python3 "$R/successor.py" run --plan "$ENABLED_PLAN" --action apply \
  --out "$FRESH_TRANSACTION" --execute --authorization "$APPLY_AUTH" \
  --authorization-sha256 "$APPLY_AUTH_SHA"
# Root: preboot snapshot + policy; one authorized cold boot. Do not hot-run worker.
# Root: wait for this boot's BOUND7, global ready, worker --verify-bound,
#       current boot/seven hashes/owner inodes, then images and interaction.
# Root: test Boat original cadence with source-derived coordinates, all five
#       popup controls (Seal, StudyTracker, DropCount, ClipboardEditor,
#       LifeCounter), and HW/ZZ. Keep the reviewed original launch/UID guards.
python3 "$R/successor.py" run --plan "$ENABLED_PLAN" --action rollback \
  --out "$FRESH_TRANSACTION" --execute --authorization "$ROLLBACK_AUTH" \
  --authorization-sha256 "$ROLLBACK_AUTH_SHA"
# Root: separately authorized cold boot and original W3 BOUND7/947 identity.
```

A source-restore receipt says **SOURCE_RESTORED_COLD_BOOT_REQUIRED**, not runtime rollback complete. Live f28 remains mapped until root performs the rollback cold boot. Restore all three sources even when apply stopped before reboot. Do not run the original W3 uninstall rollback: it would remove the entire Boat overlay to stock, whereas this window returns to W3/947. Keep the original W3 transaction untouched. Each command creates a fresh raw transport directory. Failed staging files are retained at their unique logged sibling paths for audit; this adapter does not recursively delete unknown files or claim audit-tree cleanup.

Validation: eleven local tests, actual-capture preparation, actual CLI preview, shell syntax of the derived worker. These are offline execution-path checks, not an OH ABI or UI acceptance. `SYNC-T0.md` contains the geometry call-chain and counterexamples for root relay. No device, VM, SSH, runtime build, or seal signing was performed by t4.
