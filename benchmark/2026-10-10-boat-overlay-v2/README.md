# Boat overlay v2 — manifest draft + per-file regression check (cc-t3 #91)

Evidence-first. **Static only, zero board.** Prepares the fix for the v1 Boat-layer aliasing defect; the on-board
proof is a later step.

## What was wrong before (the alias)

The v1 Boat layer (`scripts/lab/boat_layer_stage.sh`) stages six files over the U13 base. One of them,
`liboh_android_runtime.so = adc125f4`, is the defect:

- `adc125f4` is actually the **BoatAttack `libandroid.so` CLASSNAME_FIX** — U13 `libandroid.so` `9ccf64f8` + 49
  bytes, **268/268 exports, 0 export/signature change** (`benchmark/2026-10-09-local-build-check/README.md#4`). The
  boat-assembled bundle even holds it **as `libandroid.so`** (no separate runtime file in that dir).
- The v1 packaging **renamed that blob to `liboh_android_runtime.so`** and binds it at the runtime path. The real
  U13 runtime there is `18763dd4` (787 exports). Overlaying the libandroid blob **removes 520 exports**
  (`abi_diff`: 787→268, 520 removed, 1 added), including the **entire `android::CursorWindow` surface**
  (18763dd4: 24 strong `CursorWindow` exports; adc125f4: **0**). cx-bms `1a1eb6e6bd`
  (`benchmark/2026-10-10-boat-runtime-jni-gap/`): adc's four SQLite/CursorWindow registrars are **WEAK empty
  stubs** → `nativeOpen` DB path dead for **all 128 apps**, not just BoatAttack.

So the v1 render "lever" lit BoatAttack (Unity/il2cpp carries its own path) while silently stripping the shared DB
surface every other app needs — exactly the kind of shared-file regression the full-128 floor exists to catch, and
it is **statically visible** before any board step.

## Rule this sets: compare the exact destination object, and key on SONAME not path

**Before reusing a file at a `/system` path, diff it against the object currently there — exports, JNI
RegisterNatives, class set — and confirm the loader will actually select it.**

### Per-file verdicts (vs U13 base `u13-stageA-91272eaf-20261003`, consumer = appspawn-x `2a87118e`)

| file | boat → base | check | verdict |
|---|---|---|---|
| `liboh_adapter_bridge.so` | `8ab85446` → `84695d62` | abi_diff: 2357→**2359**, 0 removed, **+2**, 0 drift, 0 consumer-break | **KEEP — no regression** (superset) |
| `oh-adapter-runtime.jar` | `6333bcab` → `bbc3f530` | **manifest SHA not locally present**; indicative twin `56e4d473` drops **186 classes** (incl `WestlakeTlsInstall`, conscrypt `OpenSSLProvider`, chromium support-lib) | **GATE — real-artifact class check required** (likely TLS/webview regressor) |
| `liboh_android_runtime.so` | `adc125f4` → `18763dd4` | abi_diff: 787→268, **520 removed**; CursorWindow 24→**0**; weak SQLite stubs (cx-bms) | **REPLACE PLAN — keep 18763dd4; render via ported delta** |
| `libunity.so` / `libil2cpp.so` / `libwestlake_bionic_signal_box.so` | app-private | BoatAttack's own `/data/app` lib dir, no `/system` path | **KEEP — cannot regress other apps** |

Regressors for non-Boat apps: the runtime blob (confirmed) and — pending the real artifact — the jar.
Non-regressing shared file: the adapter.

## The SONAME-dedup risk (cx-bms `1a1eb6e6bd`, verified here)

`llvm-readelf -d` shows **all three** `liboh_android_runtime`-family files declare the **same SONAME
`liboh_android_runtime.so`**: U13 libandroid `9ccf64f8`, U13 runtime `18763dd4`, boat `adc125f4`
(`evidence/soname-and-cursorwindow.txt`).

The dynamic linker keys its loaded-library cache on **SONAME, not path**. So the naive v2 ("keep the runtime path at
18763dd4, swap only the `libandroid.so` path to adc") does **not** yield a single deterministic owner: if both
`/system/android/lib64/libandroid.so` and `.../liboh_android_runtime.so` are visible in the **same linker
namespace**, a `dlopen` of either path returns whichever soinfo loaded first. Compounding it, `CursorWindow` is
**runtime-only** (U13 libandroid also has 0), so a libandroid-path overlay can never restore the DB surface anyway.

### How to decide it statically (before any board write)

1. **`readelf -d` SONAME** — DONE; precondition met (all three share the SONAME).
2. **`scripts/lab/open_site_scan.py`** on the deployed `appspawn-x` + child: enumerate every `dlopen`/`dlopen_ns`
   site (namespace, path, flags) touching `liboh_android_runtime.so` or `libandroid.so`. Same namespace → dedup to
   one owner by SONAME; different namespaces → two coexisting copies (then non-Boat apps in the app ns get whichever
   is bound there).
3. **Deployed `/proc/<pid>/maps`** of a live app (one Boat, one non-Boat; read-only): grep both on-disk paths. Both
   bound on disk but only **one** in maps ⇒ SONAME dedup confirmed; which path appears ⇒ load order.
4. **Verdict rule**: if the two paths resolve in one namespace, a path-swap cannot place adc as libandroid without
   displacing the runtime's own SONAME entry → path-swap unsafe.

## Recommended v2

Do **not** ship `adc125f4` at any `/system` path. **Port the Boat render delta into the U13 runtime `18763dd4`** —
one artifact with 787 exports + real CursorWindow/SQLite registrars + the render fix, one SONAME, no dedup
ambiguity. Keep the verified adapter `8ab85446`. **Gate the jar** on a `deployed_class_diff` of the *real*
`6333bcab` (must drop 0 deployed classes, especially the frozen TLS ones). cx-bms is producing the runtime-delta
patch spec; this manifest and that spec cross-reference. Until that artifact exists and is single-variable
re-proven for render, the runtime stays U13 base `18763dd4` (render-correct mapping with 18763dd4 is **UNVERIFIED**).

## Files

- `manifest-v2-draft.json` — the per-file verdict table + SONAME risk + decision method (machine-readable).
- `evidence/{adapter-abi,runtime-misuse-abi,libandroid-abi}.json` — the three `abi_diff` runs.
- `evidence/soname-and-cursorwindow.txt` — SONAME of the three + CursorWindow strong-export counts.
- `evidence/jar-classdiff-indicative.txt` — indicative jar class diff (boat-assembled twin; **not** the manifest SHA).
- `results.json` — the numbers.

## Reproduce

```sh
export WORKSPACES=/Users/<you>/orca/workspaces
GEN=$WORKSPACES/westlake-inputs/generations/u13-stageA-91272eaf-20261003/armed-bundle
BASE=$GEN/native/payload/android/lib64
BOAT=$HOME/orca/00.Workspace-games-ad1ab0a7/.bridge-payload/zigzag-candidates/strict-boat-assembled-20260924T074522Z-25403/files
python3 scripts/lab/abi_diff.py --old $BASE/liboh_adapter_bridge.so --new $BOAT/liboh_adapter_bridge.so --consumer $GEN/native/payload/runtime/appspawn-x
python3 scripts/lab/abi_diff.py --old $BASE/liboh_android_runtime.so --new $BOAT/libandroid.so --consumer $GEN/native/payload/runtime/appspawn-x
python3 scripts/lab/abi_diff.py --old $BASE/libandroid.so --new $BOAT/libandroid.so
```

**Verified (static):** the alias (boat dir holds the blob as `libandroid.so`), the 520-export runtime strip,
CursorWindow runtime-only, the shared SONAME, adapter non-regression. **Unverified:** SONAME dedup on a live board;
the real `6333bcab` jar class set; whether the ported-delta runtime reproduces the render fix. **Not done:** any
board step.
