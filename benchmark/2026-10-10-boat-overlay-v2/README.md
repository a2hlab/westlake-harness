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
| `oh-adapter-runtime.jar` | `6333bcab` → `bbc3f530` | real jar (found local): deployed_class_diff 216→**218**, 0 dropped, **+2**, **0 frozen broken** | **KEEP — no regression** (superset) |
| `liboh_android_runtime.so` | `adc125f4` → `18763dd4` | abi_diff: 787→268, **520 removed**; CursorWindow 24→**0**; weak SQLite stubs (cx-bms) | **REPLACE PLAN — keep 18763dd4; render via ported delta** |
| `libunity.so` / `libil2cpp.so` / `libwestlake_bionic_signal_box.so` | app-private | BoatAttack's own `/data/app` lib dir, no `/system` path | **KEEP — cannot regress other apps** |

Regressor for non-Boat apps: the runtime blob only (confirmed). Non-regressing shared files: adapter **and** jar
(both supersets of base). The jar gate is in `jar-6333bcab-gate.md`; the earlier indicative red flag (twin
`56e4d473`, 186 dropped incl TLS) is **withdrawn** — that was a different, stripped jar the manifest does not use.

## The SONAME dedup is the steady state — Boat made the deficient copy win (cx-bms `1a1eb6e6bd`, verified here; corrected per outer 2026-10-10)

`llvm-readelf -d` shows **all three** `liboh_android_runtime`-family files declare the **same SONAME
`liboh_android_runtime.so`**: U13 libandroid `9ccf64f8`, U13 runtime `18763dd4`, boat `adc125f4`
(`evidence/soname-and-cursorwindow.txt`). The dynamic linker keys its loaded-library cache on **SONAME, not path**,
so two on-disk paths with that SONAME dedup to **one** loaded owner per linker namespace.

**This is not a new risk — it is the existing, benign steady state.** U13 base already ships `libandroid.so`
(`9ccf64f8`) **and** `liboh_android_runtime.so` (`18763dd4`) side by side with the same SONAME, and all 128 apps
light. So the dedup has always been in effect and the **full runtime (`18763dd4`, 787 exports incl `CursorWindow`)
is the first-loaded winner** today. Boat's defect is narrow and specific: by binding the stripped blob `adc125f4`
(268 exports, no `CursorWindow`) at the runtime path, it makes the **deficient copy the first-loaded owner** — the
SONAME dedup then serves adc's stripped surface to everything. The mechanism didn't change; the winner did.

Corollary for a path-swap: moving adc to the `libandroid.so` path does **not** help, because `CursorWindow` is
**runtime-only** (U13 libandroid also has 0) and the SONAME winner is still decided by load order, not by which path
you wrote. The only clean fix is to keep the full runtime object as the owner.

### How to confirm the owner statically (which copy wins load order)

1. **`readelf -d` SONAME** — DONE; all three share the SONAME, so dedup applies.
2. **`scripts/lab/open_site_scan.py`** on the deployed `appspawn-x` + child: enumerate every `dlopen`/`dlopen_ns`
   site (namespace, path, flags) touching `liboh_android_runtime.so` or `libandroid.so`, to see which path is opened
   first in each namespace (that is the SONAME winner).
3. **Deployed `/proc/<pid>/maps`** of a live app (one Boat, one non-Boat; read-only): both paths bound on disk but
   only **one** in maps ⇒ the dedup winner; which path appears ⇒ load order. On a healthy U13 base this is the full
   runtime `18763dd4`; the check is how you confirm Boat flipped the winner to adc.
4. **Verdict rule**: the owner must be the full runtime object. Any overlay that makes a stripped copy the
   first-loaded SONAME winner (what v1 does) is unsafe regardless of which path it is written to.

## Recommended v2

Do **not** ship `adc125f4` at any `/system` path. **Port the Boat render delta into the U13 runtime `18763dd4`** —
one artifact with 787 exports + real CursorWindow/SQLite registrars + the render fix, one SONAME, no dedup
ambiguity. Keep the verified adapter `8ab85446` **and** the verified jar `6333bcab` (both supersets of base, 0
dropped, 0 frozen broken — see `jar-6333bcab-gate.md`). cx-bms is producing the runtime-delta patch spec; this
manifest and that spec cross-reference. Until that artifact exists and is single-variable re-proven for render, the
runtime stays U13 base `18763dd4` (render-correct mapping with 18763dd4 is **UNVERIFIED**).

## Files

- `manifest-v2-draft.json` — the per-file verdict table + SONAME steady-state analysis + owner-confirm method (machine-readable).
- `jar-6333bcab-gate.md` + `evidence/jar-6333bcab-search.log` — the real-jar gate: SHA search log + class-diff (or locked-artifact finding).
- `evidence/{adapter-abi,runtime-misuse-abi,libandroid-abi}.json` — the three `abi_diff` runs.
- `evidence/soname-and-cursorwindow.txt` — SONAME of the three + CursorWindow strong-export counts.
- `evidence/jar-6333bcab-classdiff.txt` — real jar gate (6333bcab vs base, --frozen). `evidence/jar-6333bcab-search.log` — SHA search trail. `evidence/jar-classdiff-indicative.txt` — the withdrawn indicative twin (56e4d473).
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
CursorWindow runtime-only, the shared SONAME, adapter non-regression, jar 6333bcab non-regression (real artifact, found local). **Unverified:** the SONAME winner on a live board (expected 18763dd4); whether the ported-delta runtime reproduces
the render fix. **Not done:** any board step.
