# Inner static supplement — #91 REA seal preflight (outer/codex)

Evidence-first independent read-only check of the shipped f28 runtime evidence
(dedicated SurfaceView geometry vs main/failed-child fallback), **now including
the reviewer-supplied actual REA Hopper disassembly of `BBQ_nativeUpdate`**.
No devices, no rebuild, no registry/permission changes, no new gate.
Scope: this benchmark directory.

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

---

## REA supplement (reviewer-supplied actual Hopper evidence)

**Artifact identity** (recomputed locally): `inputs/liboh_android_runtime.so`,
3194360 B, SHA `f28bd1b3…` — **bit-exact equal** to the f28 candidate recorded
in `../2026-10-13-runtime-surfaceview-split/results.json` and to the subject
digests in `open.json`/`search.json`. Evidence IDs: `analyze_function` =
`ev_6d726ba3…` (function.json); `search` = `ev_b2c0…` (search.json); provider
Hopper (launcher `dad6f886…`), arm64 ELF.

**Target**: `BBQ_nativeUpdate` @ `0x1989ac`. Machine-code findings (from the
202-instruction assembly window, not pseudocode):

| Branch | PCs | What happens |
|---|---|---|
| Request store | `0x1989d8–0x198a24` | `w22/w20/w19` = fmt/width/height; `stp w20,w19,[x24,#0x44]` stores **requested w@+0x44, h@+0x48**, fmt@+0x4c; struct magic `0x4f484251` checked at `0x198a14` |
| SurfaceView test | `0x198a4c–0x198a5c` | `strstr(name,"SurfaceView")` (literal at 0x63000+0xb10); `cbz x0` → main path |
| Dedicated-child attempt | `0x198a60–0x198a80` | `resolve_oh_wm_funcs`; indirect `blr x8` = `oh_rs_get_child_surface_window(sessionId, bbq, w, h)` with **live requested w/h in w2/w3** |
| **Child success** | `0x198a84→0x198b98`, `0x198be8` | `cbnz x0` → log child anw; then `ldp w26,w27,[x24,#0x44]` **reloads requested geometry** |
| **Main / failed-child fallback** | `0x198a5c`/`0x198a6c`→`0x198ab4–0x198b94` | `oh_wm_get_native_window(sessionId)`; then `mov w27,#0x780` (1920), `mov w26,#0x4b0` (1200) — **hard panel constants**; `b loc_198bec` joins shared call |
| Shared geometry stamp | `0x198bf4–0x198c10` | weak-guard `sub_1fc940` + `csel`; `bl sub_1fc9b0` = `nwfs_apply_window_geometry(nw,"BBQ.update-stamp",w26,h27)` (strings 0x5533c "BBQ.update-stamp", 0x544cb SET_BUFFER_GEOMETRY, 0x4ffc9 OH_NWSeed) |

**Conclusion**: the disassembly independently confirms the source-level design —
dedicated-child success stamps requested geometry; main/ViewRoot and failed-child
fallback hardcode 1200×1920 into the single shared geometry call. No third
geometry path exists in the returned body.

**Unknown coverage**: Hopper body-range API unavailable (window-based analysis);
`sub_1fc9b0`/`sub_1fc940` identity correlated via source + call-site strings,
not independent symbol resolution; only `BBQ_nativeUpdate` targeted (whole-binary
equality to 947 elsewhere not proven); search.json returned 2 matches only;
REA is static — no board execution, runtime acceptance still pending
(`actual-game-completion.json`: INTERACTIVE_GAME_PASS_RETAINED_PENDING_REGRESSION,
same f28 SHA, `final_v2_sealed=false`).

Details: `inner-results.json` → `rea_supplement`.
