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
