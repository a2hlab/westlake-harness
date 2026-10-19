# Exact SurfaceBufferImpl getters: raw-handle offsets and widths

The preceding internals audit left width, height, stride, format and full usage offsets unresolved because OH_NativeBuffer_GetConfig dispatches getters and writes a separate output struct. This pass analyzes **only the five approved getter bodies**, directly following the raw handle pointer. It closes their offsets and widths for `libsurface.z.so` SHA256 `8f1879f82a307d3a95555067575132918a05244fbdeee1c2f2db37834a58f4a3` (566568 bytes). It does not establish live resolver selection, object identity, allocation extent or byte units.

Each complete function is 72 bytes / 18 AArch64 instructions: **5 REA dossiers and 5 independent LLVM bodies, 360 bytes / 90 instructions per engine**. Original unfiltered REA Evidence, original LLVM stdout/stderr and command receipts are durable in `$HOME/.local/share/westlake/toutiao-resume-20261020/provider-surface-readonly/analysis-r3/`. `source-index.json` hashes originals and prior evidence. Public pseudocode/instruction files are explicitly derived views; LLVM's input path is aliased, and pseudocode trailing whitespace is trimmed. Earlier audit directories and raw r1/r2 files were not modified.

All cited PCs are **ELF VAs**, not runtime addresses. Each REA dossier independently reports the corresponding Ghidra address as ELF VA plus `0x100000` (e.g. width `0x78810` → `0x178810`).

## Exact raw-handle access

Each getter locks the mutex at SurfaceBufferImpl `+0x50`, loads the handle pointer at object `+0x10`, checks it for null, reads the field below, unlocks and returns. This is a direct handle read, **not** an inference from config output offsets.

| Getter entry | Field-load PC | Raw handle offset | Exact load / return | Null-handle result |
|---|---|---:|---|---|
| GetWidth `0x78810` | `0x78834` | `0x04` | `ldr w20,[x8,#4]`; `mov w0,w20` at `0x78848` | `w20=0xffffffff` at `0x7883c` |
| GetHeight `0x78858` | `0x7887c` | `0x0c` | `ldr w20,[x8,#12]`; `mov w0,w20` at `0x78890` | `w20=0xffffffff` at `0x78884` |
| GetStride `0x788a0` | `0x788c4` | `0x08` | `ldr w20,[x8,#8]`; `mov w0,w20` at `0x788d8` | `w20=0xffffffff` at `0x788cc` |
| GetFormat `0x788e8` | `0x7890c` | `0x14` | `ldr w20,[x8,#20]`; `mov w0,w20` at `0x78920` | `w20=0xffffffff` at `0x78914` |
| GetUsage `0x78930` | `0x78954` | `0x18` | `ldr x20,[x8,#24]`; `mov x0,x20` at `0x78968` | `x20=0xffffffffffffffff` at `0x7895c` |

Together with the previous exact internals evidence for fd at `+0x00` (32 bits), size at `+0x10` (32 bits) and virAddr at `+0x20` (64 bits), these accesses now account for the field offsets/widths spanning the **first 40 bytes** of this file's handle profile. This does not prove a live pointer is valid or that the complete handle is exactly 40, 56 or 64 bytes. The `key`, physical-address and reserve tail remain outside the evidence.

## Signedness and widening: keep source type and register effect distinct

There is **no LDRSW or SXTW** in these five complete bodies. The first four read 32 bits into W20 and return via W0; an AArch64 W-register write clears the upper half of the corresponding X register. Thus their null-handle path leaves X0 bits `0x00000000ffffffff`, whereas usage returns X0 bits `0xffffffffffffffff`. These are exact register effects; they do not imply that the four 32-bit source fields are unsigned.

The retained source profile `../source-profile/graphic-surface/buffer_handle.h:26–33` declares fd/width/stride/height/size/format as `int32_t` and usage as `uint64_t`. The older SDK profile has the same prefix declarations. Source-declared signedness is distinct from what these load instructions alone prove. A correctly typed signed32 consumer interprets `0xffffffff` as -1; treating the register as a signed64 return would instead produce 4294967295. Ghidra's `undefined4`/`undefined8` pseudotypes are not evidence for source signedness.

For a future R14 handle adapter, read each established signed32 field into an `int32_t` value before widening to the module's int64 fields; keep format int32 and usage, if required, as the separate 64-bit field. Do not load width/stride/height/size as native 64-bit quantities or cast the handle to `struct r14_handle`. This is the existing source-profile type contract plus newly confirmed offsets/widths, **not newly implemented production code**. R14's existing positive/range checks still apply after proper conversion.

## Remaining unknowns and limits

- GetStride copies the stored 32-bit field unchanged. No arithmetic here proves byte stride versus pixel stride. Archived header documentation describes bytes, but exact-driver unit/format relation and a live returned value remain unobserved.
- Size's location/width was confirmed in the prior pass; these getters add no proof that its value denotes mapped byte capacity. R14's `stride_bytes * height <= size_bytes` still depends on a correctly bound provider contract.
- Handle fixed extent, optional key, phyAddr and reserve layout remain unknown. No HDI provider, allocation, clone implementation or additional getter was analyzed.
- Accessor mutexes do not prove aggregate consistency across five separate calls, nor extend pointer lifetime after return. The borrowed request owner and runtime dispatch chain still require independent evidence.
- No device operation, production build/modification, deployment, playback claim, API freeze or seal follows from this static increment. Expected-help key remains **toutiao, conditional** on actual execution reaching this exact implementation.

This package supersedes only the five raw-field-offset/width unknowns listed by `../exact-surface-internals/`; it preserves all other boundaries and does not rewrite previously signed evidence.
