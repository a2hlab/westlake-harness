# Flutter U16 slot check: can the pending eb90 westlake_flutter move fluffychat / kitchenowl / localsend?

#90, offline, static. cc-t3. Does U16's pending `westlake_flutter/libandroid.so = eb90` (the b1c9→eb90 depth-proc
slot-fill, `benchmark/2026-10-03-u16-assembly-draft/`, owner cc-t3, approval-packet staged) clear the U14 Flutter
first-fatal cluster (3 keys: fd-fluffychat, fd-kitchenowl, localsend)?

## Root-cause class (all 3)
OH's GLES driver exports the ES **float** depth variants `glDepthRangef`/`glClearDepthf` but NOT the desktop **double**
variants `glDepthRange`/`glClearDepth`. Flutter/Impeller's GL ProcTable resolves BOTH via `eglGetProcAddress`; the double
variants return null; the engine later calls a null ProcTable slot → `blr` on 0 → SIGSEGV inside libflutter raster.
This is the U14 cluster `signal-SIGSEGV|libflutter.so` (2026-10-08-u14-first-fatal-clusters).

## eb90 coverage (CONFIRMED)
`eb90a640` exports `eglGetProcAddress` and its only `gl*` name strings are **`glDepthRange, glDepthRangef, glClearDepth,
glClearDepthf`** — it resolves the depth family only, as **double→float semantic stubs** (glDepthRange→glDepthRangef,
glClearDepth→glClearDepthf; NOT no-ops). (b1c9→eb90 `flutter-replacement-proof.json`: only `westlake_flutter/libandroid.so`
changed.)

## Per-key crash slot (4 engine builds do not share offsets — each decoded in its own libflutter)
Crash pattern at the PC: `ldr x8, [x9, #OFF]; blr x8` (x9 = the static ProcTable @~0xb2d000). `OFF/8 = slot index`.
| key | libflutter build-id | size | crash pc | slot off | slot # | slot name | eb90 covers? |
|---|---|---|---|---|---|---|---|
| localsend | `0d216f3f` | 11052 KB | +0x4b655c | 0xea0 | **468** | **glDepthRange** (outer-known) | **YES** |
| fd-fluffychat | `495e7110` | 11310 KB (r28c) | +0x4c367c | 0x8d0 | **282** | **UNCONFIRMED** (see gap) | likely, unproven |
| fd-kitchenowl | `889a1df3` | 11310 KB (r28c) | +0x4c367c | 0x8d0 | **282** | **UNCONFIRMED** (same engine as fluffychat) | likely, unproven |

fluffychat and kitchenowl are the SAME engine build (identical 11310 KB + identical crash offset 0x4c367c/slot 0x8d0);
localsend is a different build (11052 KB). The depth-double strings ARE present in the r28c engine. I could not statically
name slot #282 within budget: the ProcTable is a static global (`adrp x9,0xb2d000; ldr x8,[x9,#0x8d0]`) whose init store
to +0x8d0 is not a simple `str x0,[base,#0x8d0]` (the parallel 0xb35880 table at +0x8d0 holds a dart string, not a GL name).

## Predicted Flutter move after U16 (eb90 deployed)
- **CONFIRMED +1: localsend** — slot #468 = glDepthRange, eb90 resolves it.
- **LIKELY +2: fd-fluffychat, fd-kitchenowl** — same crash cluster + the OH-GLES-double-variant root cause + depth
  strings present make slot #282 very likely a depth-double proc (glDepthRange or glClearDepth), both of which eb90 covers.
  **NOT statically proven here.**
- **Range: 1 (confirmed) … 3 (if #282 is a depth-double).**

### Gap to close (if predicted <3)
Statically name ProcTable slot #282 (offset 0x8d0) in the r28c engine (`495e7110`/`889a1df3`): follow the 0xb2d000
ProcTable init store to +0x8d0 (not found by the simple `str [base,#0x8d0]` scan — the init may fill via a resolved-array
loop), OR a one-shot on-board probe logging the eglGetProcAddress name of the null slot. If #282 ∈ {glDepthRange,
glClearDepth} → eb90 already covers it (+2). If it is a DIFFERENT null GL proc → that proc must be added to the interposer
(eb90 is depth-only), and that proc is the missing slot.

### Next-wall candidate
Unknown until a post-depth run: the next null GL proc the engine calls after the depth slot resolves (Impeller resolves
many extension procs; the OH GLES driver may lack others). Re-check first-fatal after eb90 to find it.

## Files
slots.json (the slot table), repro.sh (`repro.sh <app-inputs-dir> <eb90-libandroid.so>`).
