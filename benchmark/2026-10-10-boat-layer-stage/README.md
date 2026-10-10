# Installer-free Boat-layer staging — `scripts/lab/boat_layer_stage.sh`

**The Boat layer can be added/removed with NO installer, NO `/system/android` re-archive, NO `/system` remount — just stage (or remove) 6 files under `$ROOT/sources-boat` and reboot.**

## Why (origin: 5ea #91)
The U13 autostart **installer** step 2 re-archives the live `/system/android` into `sources/seqN`. On an already-recovered board that archived an unbound/empty base and deleted ~200 physical files — the 5ea incident. During the 5ea SIGILL hunt we confirmed the **Boat overlay is a *separate* init job** (`00_westlake_u13_recover.cfg` param `sys.westlake.demo.u13.ready` → `westlake-u13-boat-overlay.sh`), which only reads `$ROOT/sources-boat` and binds over the restored base. Moving `sources-boat` aside + reboot gave a clean pure-base boot with `seq1` **byte-untouched** — the safe single-variable lever. This script generalizes that into an audited tool.

## Contract (pinned by `scripts/lab/test_boat_layer_stage.py`, 17/17)
- **Dry-run by default**; mutates the board only with `--execute`.
- Stages exactly the **6 signed Boat files** (SHA-gated, source-of-truth = the payload overlay):
  `liboh_adapter_bridge.so 8ab85446`, `oh-adapter-runtime.jar 6333bcab`, `liboh_android_runtime.so adc125f4`, `libunity.so 1bea0fae`, `libil2cpp.so f6b806b5`, `libwestlake_bionic_signal_box.so 7a931c79`.
- Labels each staged file via the **single recipe** (`selinux_label_recipe.sh context <target>`): `.so`→`system_lib_file`, the jar→`system_file`, the 3 app-private→`data_app_el1_file`.
- **Confirms** the board already carries the boat job in the recover cfg; **never edits the cfg** (fails closed if absent).
- Hard negative invariants (all asserted): never touches `sources/seq1`, never calls the installer, never remounts `/system`, never `setenforce`; forward only adds `sources-boat`, reverse only moves it aside; the script **prints** `target boot`, never runs it.

## Usage
```
# add the Boat layer (dry-run first, then execute, then reboot):
boat_layer_stage.sh --serial <sn> --src <signed-boat-artifacts-dir>
boat_layer_stage.sh --serial <sn> --src <signed-boat-artifacts-dir> --execute
hdc -t <sn> target boot

# remove the Boat layer (back to pure base):
boat_layer_stage.sh --serial <sn> --reverse --execute
hdc -t <sn> target boot
```

## Intended use
1. **5cd**: run the full-128 regression WITH the Boat layer (after the cx-t0 baseline) — 5cd is 128-complete, same fingerprint as 61b; no longer depends on 5ea.
2. **61b**: v2 re-seal after v1 is frozen — stage + one reboot.

Tests: `python3 -m unittest scripts/lab/test_boat_layer_stage.py` (17/17). user-paths gate: 0 violations.
