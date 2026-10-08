# Slot #282 naming attempt (fluffychat/kitchenowl, engine r28c 495e7110/889a1df3) — INCONCLUSIVE in budget

Follow-up to name ProcTable slot at crash offset `0x8d0` (crash pc +0x4c367c). Methods tried and why each did not close:

1. **Call-site structure**: `adrp x9,0xb2d000; ldr x8,[x9,#0x8d0]; mov x0,x23; blr x8`. The table base is the page
   `0xb2d000`; the fn pointer is at vaddr `0xb2d8d0`.
2. **40-byte GLProc model** (outer hint): with 40 B stride and fn at entry+0x10, `0xb2d8d0` → GLProc #56 base
   `0xb2d8c0`. BUT `0xb2d8c0` is in **.bss** (not in any PT_LOAD filesz) → the array is **runtime-populated**; the
   `.name` cannot be read from the static image.
3. **Init store scan**: no `str xN,[base,#0x8c0/0x8c8/0x8d0]` fn/name store to the 0xb2d000 table exists (the fn store is
   register-indexed `str x0,[proctable, x_off]`, so the offset is not an immediate) → the init is a descriptor/loop, not
   flat stores.
4. **Descriptor-table scan**: scanned the whole image for an 8- or 4-byte field `= 0x8d0` (and `0xea0`) adjacent to a
   `gl*` name pointer → **0 hits**. So there is no `{name, offset}` descriptor table with the raw slot offset.
5. **Arg-register discrimination — NON-CONCLUSIVE**: the slot is called `mov x0,x23; blr` (pointer in x0, not s0/d0).
   This looked like "not a float depth proc" — but **localsend's CONFIRMED glDepthRange slot (#468) uses the identical
   `mov x0,x23; blr`**. So the ProcTable entries are wrappers/trampolines taking a context pointer, NOT raw GL procs with
   the native float ABI. The arg register therefore does NOT rule the depth family in or out.

**Status**: slot #282 is NOT conclusively named within the 30-min budget. The ProcTable @0xb2d000 is a .bss array filled
by a non-trivial init (no flat stores, no raw-offset descriptor table), and the call shape is identical to localsend's
depth slot, so it is neither confirmed nor excluded as a depth-family proc.

**Cheapest definitive next step** (needs one action, not pure static): a one-shot on-board probe that logs the
`eglGetProcAddress(name)` that returns null for the crashing slot (the interposer already sees every query) — or an
LD-level trace of the ProcTable init. Pure-static alternatives that would work but need more time: (a) trace the init
descriptor mechanism (how the loop maps names→0xb2d000 offsets), or (b) recover the GLProc member order from the engine's
own symbol/relocation metadata.

## Zero-cost hilog route (2026-10-08) — also negative; naming SHELVED
Checked whether the DEPLOYED U14 `westlake_flutter/libandroid.so = fff9be31` (which wraps EGL) logs its
`eglGetProcAddress` resolutions. It does NOT: it only logs the EGL **hijack funcs** — `resolve_egl_hijack_funcs`,
`eglCreateWindowSurface`, `eglSwapBuffers(WithDamageKHR)` — under tag `OH_EglHijack` (confirmed by its strings AND by the
actual U14 hilogs). There is no per-GL-proc `eglGetProcAddress(name)->NULL` log.

In fluffychat's and kitchenowl's U14 window-1 candidate hilogs, `OH_EglHijack` shows
`eglCreateWindowSurface … -> EGLSurface=0x…` (surface creation **succeeds**); the SIGSEGV is downstream in libflutter
raster on the null ProcTable slot, and **no proc name is logged for it**. So the hilog cannot name slot #282 either.

**Decision (per outer): STOP.** All zero/low-cost static + log routes are exhausted. Flutter prediction stands at
**confirmed 1 (localsend), upper bound 3** — fluffychat/kitchenowl (#282) neither confirmed nor excluded as depth.
**Resolve by U16 Stage-A actual measurement**: deploy eb90 and re-run — if fluffychat/kitchenowl move, #282 was a
depth-double eb90 covers; if they still crash, the fresh first-fatal names their next (non-depth) proc directly.
