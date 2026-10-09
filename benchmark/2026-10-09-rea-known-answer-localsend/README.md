# REA + Hopper known-answer test on localsend's Flutter crash: the "known answer" was wrong

**What was wrong.** DIGEST (2026-10-03, cc-t3, U16) recorded localsend's first fatal as follows:

- crash at `libflutter.so+0x4b655c` (build-id `0d216f3f`) = Impeller GLES ProcTable slot #468 = `glDepthRange`;
- reasoning: the crash loads `[x9, #0xea0]` after `adrp x9, 0xaee000`, and ProcTable entry `0xe88` carries the name
  `glDepthRange`, so `0xe88 + 0x18 = 0xea0`.

U16's Flutter fix `eb90` (a `glDepthRange` → `glDepthRangef` semantic stub) and its prediction "localsend +1 certain"
rest on that mapping.

That mapping matches two equal offsets in two different objects:

- **The GLES ProcTable is a heap object.** Its only initialiser `sub_7fc994` is called once from `0x4a5e5c`, with
  `this` returned by `mov w0, #0x1298; bl <operator new>`. So it is a heap object of 0x1298 bytes, not a `.bss`
  table. Entry `0xe88` does hold `glDepthRange` (string `0x1bcc64`), and the slot is `+0x18`.
- **The crash reads a global variable.** `0xaeeea0` lies in `.bss` (`0xaea8c0..0xafe6b0`). Its only code access is
  the crash load.
- **That global is a Vulkan dispatcher slot.** It is written at `0x814d9c..0x814dac`: the result of resolving the
  string `"vkCreateAndroidSurfaceKHR"` (`0x1cfc94`) is stored to `[x20, #0x828]`, with
  `x20 = 0xaee000 + 0x678` (`0x8139f0..0x8139f4`, no reassignment before the store). `0xaee678 + 0x828 = 0xaeeea0`.
- **The call site has the Vulkan create shape.** It is `(handle, &createInfo, NULL, &out)` with
  `createInfo.sType = 0x3B9AE940 = 1000008000` = `VK_STRUCTURE_TYPE_ANDROID_SURFACE_CREATE_INFO_KHR`
  (extension #9: 1000000000 + 8×1000).

**Corrected first fatal (static).** localsend crashes calling a NULL `vkCreateAndroidSurfaceKHR`. Impeller took the
Vulkan path and created an Android surface, but OH's Vulkan does not resolve the `VK_KHR_android_surface` entry. The
`glDepthRange` NULL slot is a real fact (driver oracle), but it is not this crash.

Consequences:

- U16 `eb90` is not expected to move localsend's first fatal. Its Flutter prediction drops from "1 certain / 3 max"
  to "0 certain for localsend". fluffychat / kitchenowl (`+0x4c367c`, other engine builds) must be re-checked the
  same way.
- The fix direction is Vulkan-side. Either Impeller must see Vulkan as unusable and fall back to GLES, or an
  Android-surface entry must be provided that maps to OH's surface extension. This is to be decided by a lane with
  evidence.

## How REA + Hopper did

The tool chain is REA 6.1.0, Hopper (`HOPPER_LAUNCHER_PATH=~/Applications/...`) and a saved snapshot.

| Step | Result |
|---|---|
| `decompile 0x4b655c` | `r0 = qword_aeeea0(r23, r1, 0x0, r3)`. Shows an indirect call through a **global** with four args, which is the first hint that this is not `glDepthRange(double, double)`. |
| `trace glDepthRange` | Strings `0x1bcc64` / `0x1b8176` (`glDepthRangef`), refs `0x7fd3d8` / `0x7fd39c` inside `sub_7fc994`. Matches the DIGEST string and entry. |
| `function 0x7fc994` | Single caller `0x4a5e5c`; referenced strings are all GLES proc names. |
| `instructions 0x4a5c14` | The caller passes a freshly allocated 0x1298-byte object as `this`. This exposed the heap-vs-`.bss` mismatch. |
| `trace vkCreateAndroidSurfaceKHR` | String `0x1cfc94`, ref `0x814da0`. Led to the dispatcher store. |
| `trace qword_aeeea0` | Empty, because REA traces strings and procedure names, not data addresses. |

The writer of `0xaeeea0` was found with a plain `llvm-objdump` scan of all `.text` (`evidence/disassembly.txt`).

**Verdict on the tool.**

- Useful as a second pair of eyes: the decompiler's argument shape and the caller lookup are what broke the wrong
  mapping.
- It does not replace our scans: data-address xrefs still need objdump.
- Every claim it leads to must be re-derived from raw instructions, as done here.

## Rules this sets

1. Matching an offset is not matching an object. A slot claim must bind the base register to the same object
   (global address, or the same `this` lineage) on both the writer and the reader side.
2. Check the call shape against the claimed callee's signature: argument count, types, and struct `sType` values.
3. Known-answer tests for a new analysis tool must be allowed to fail the answer, not just the tool.
