# Inner static supplement — #91 REA seal preflight (outer/codex)

Evidence-first independent read-only check of the shipped f28 runtime evidence
(dedicated SurfaceView geometry vs main/failed-child fallback). No devices,
no rebuild, no registry/permission changes. Scope: this benchmark directory.

## What was checked (with hashes)

| Artifact | Path | SHA-256 (prefix) |
|---|---|---|
| Shim source | `../2026-10-13-runtime-surfaceview-split/source/android_graphics_compat_shim.cpp` | c208788a… (78283 B; **matches** `results.json source.sha256`) |
| Results | `../2026-10-13-runtime-surfaceview-split/results.json` | 39c11f45… |
| README | `../2026-10-13-runtime-surfaceview-split/README.md` | 8c717086… |
| Predictions | `../2026-10-13-runtime-surfaceview-split/predictions.json` | b77300b2… |
| Patch vs 947 | `../2026-10-13-runtime-surfaceview-split/source-over-947.patch` | 30db37ce… |
| ABI vs 947 (root) | `../../2026-10-09-demo-boatattack/v2-20261013/outer/r6-source-review/abi-vs-947.json` | verified structurally (0/0/0/0 diffs) |
| Offline receipts | `evidence/offline/*.{receipt.json,stdout.txt}` ×6 | rc=0, argv recorded |

## Verified facts

1. **Source identity confirmed**: recomputed SHA of the in-repo shim equals the
   `source.sha256` recorded in `results.json`; byte count 78283 matches.
2. **The geometry change is minimal and as claimed**: `source-over-947.patch`
   adds only a `hasDedicatedChildWindow` flag (8 added lines). In
   `BBQ_nativeUpdate`, requested `b->width/b->height` is stamped **only** when
   the dedicated child surface resolved; main/ViewRoot and failed-child
   fallback keep the 1200×1920 panel policy (shim lines ~600–610). No new
   name/package/aspect heuristic — SurfaceView routing already existed.
3. **Offline six-case host checks pass** (`evidence/offline/results.json`):
   dedicated-child selects the child (child_writes=1, main_writes=0);
   popup-main, named-child-fallback, and boat-main-counterexample stamp
   1200×1920 on main; unavailable/no-session write nothing. Receipts rc=0.
4. **Lazy getSurface and the three other geometry functions are unchanged**
   with per-function hashes recorded in the offline results.
5. **Build/ABI evidence**: rc=0, 787 exports unchanged, empty
   removed/added/new_undefined/attribute_drift, 4 SQLite/CursorWindow
   registrars, 6347-file source closure `all_match` before and after.
6. **Root's ABI-vs-947**: removed/added/drift/consumer_breaks all empty for
   all three consumers; old≠new SHA confirms a rebuilt artifact was compared.

## Unknowns (not fabricatable here)

- **Runtime behavior on hardware** — everything the README lists as pending
  (strict same-PID Boat AB: buffers/HUD/five-touch/LAP/reset; Seal /
  StudyTracker / DropCount restoration; ClipboardEditor; LifeCounter negative).
- **Actual artifact bytes**: candidate `.so`, build log, source archive, and
  toolchain live under `$WORKSPACES/westlake-harness-t0` / `westlake-inputs`,
  which are **absent in this workspace** — their recorded SHAs cannot be
  recomputed here.
- **REA itself**: root obtains actual REA artifact evidence separately. It was
  **not** called and is **not** claimed verified by this supplement.
- Host offline binary/compiler were not re-run (read-only mandate).

## Critical-path judgment

**No new action on the critical path is justified.** All locally checkable
static evidence is internally consistent; the open items are exactly the
hardware AB and board controls already tracked as pending and gated on root's
device access. Proceed with the same-PID AB when hardware is available; no
source change is warranted before that result.

Details: `inner-results.json` (machine-readable, same directory).
