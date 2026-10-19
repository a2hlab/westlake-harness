# Exact surface internals: seven-function boundary audit

The earlier audit did not prove raw handle fields, Map/Unmap internals or byte-size semantics. This pass analyzed **exactly seven authorized functions** of the same 566568-byte `libsurface.z.so`, SHA256 `8f1879f82a307d3a95555067575132918a05244fbdeee1c2f2db37834a58f4a3`. It confirms the handle pointer, size-word and mapping-address accesses, but **does not close the complete BufferHandle layout, extent or size-in-bytes proof**. No device command, production build, production modification or additional function analysis occurred.

Original unfiltered REA function Evidence (including pseudocode, all instructions, references and limitations), LLVM output and rc receipts are durable under `$HOME/.local/share/westlake/toutiao-resume-20261020/provider-surface-readonly/analysis-r2/`. `source-index.json` records exact input/output hashes and pinned R14 source blobs. The prior ELF read/boot evidence remains in `../exact-surface/`. Public `llvm.txt` changes only the input path to a HOME alias; `ghidra-instructions.txt` and whitespace-trimmed `pseudocode.txt` are explicitly **derived views**, not original Evidence envelopes.

## Instruction evidence takes precedence over incorrect pseudocode

REA/Ghidra completes all 7 function dossiers with body sizes matching LLVM (288, 424, 136, 56, 72, 104, 412 bytes). However Map and Unmap pseudocode each contain **13 “Removing unreachable block” warnings** and incorrectly reduce the function to a single error-return path. LLVM and the same Ghidra dossier's full instruction lists show the branches are present. The helper at ELF `0x77c4c` receives its aggregate output address in x8; the pseudocode does not model that effect correctly. We have not analyzed that helper or edited Ghidra types. Do not turn the decompiler's constant-error rendering into a runtime or file-behavior conclusion.

Every PC below is an **ELF VA**. All seven REA dossier entry addresses independently equal their ELF entry plus `0x100000`; e.g. Map ELF `0x77f18` is Ghidra `0x177f18`. Neither is an absolute runtime address.

## Exact field access versus unresolved layout

| Object/field | Exact instruction evidence | What it proves, and what it does not |
|---|---|---|
| SurfaceBufferImpl mutex | GetBufferHandle `0x785f4` adds `0x50`; lock/unlock calls bracket pointer load | Object mutex is used for this accessor. Returned pointer is not held under a lock after return. |
| SurfaceBufferImpl handle pointer | GetBufferHandle `0x78608`, Map `0x77f60`, Unmap `0x78080` load 8 bytes at object `+0x10` | Same pointer flows into lower mapping calls. Getter adds no SurfaceBuffer or handle ownership reference. |
| Handle fd | Clone `0x79f70..0x79f74` reads 32 bits at handle `+0x0` and rejects bit31 set | Signed-negative rejection is exact. Clone also rejects null handle. |
| Handle size | GetSize `0x78a94` reads 32 bits at handle `+0x10`; null handle returns 0 | Size-word location/width is exact. The source profile declares int32; instructions alone do not prove signedness or byte units. This function does no multiplication or unit conversion. |
| Handle virAddr | Map `0x77f68`, Unmap `0x78088`, GetVirAddr `0x789fc`: 8 bytes at handle `+0x20` | Mapping-address location/width is exact. Unmap writes zero there at `0x78168` after lower success. |
| Mapping skip bit | Map `0x77f70..0x77f74`: byte handle `+0x19`, bit3 | Matches bit11 of the source profile's usage-at-0x18 field. This alone does not prove the entire 64-bit usage layout or the bit's named semantics. |
| width/height/format/usage/stride | GetConfig `0x64698..0x646f0` dispatches vtable `+0x48/+0x50/+0x60/+0x68/+0x58`, writes five 32-bit results to config `+0/+4/+8/+12/+16` | Exact prior relocations name GetWidth/GetHeight/GetFormat/GetUsage/GetStride. This config output layout is **not** the raw handle layout. The five getter bodies were outside this pass, so raw handle offsets remain unresolved. |
| Fixed extent, key, phyAddr, reserve fields | Clone `0x79f9c..0x79fa0` calls display-provider vtable `+0x90`; `0x7a070` returns its output pointer after rc0 | Clone delegates copy/allocation; it contains no fixed-extent memcpy or reserve-field access. 56 versus 64 bytes remains unknown for the exact provider. Source header agreement is not proof. |

The previous two source-profile headers agree on their first 40 bytes but disagree on the tail. This pass directly verifies only the accesses listed above; it does not authenticate all 40 bytes. Never memcpy/cast that native prefix into R14's int64 record. Individually loading source-declared signed32 width/height/stride/size then widening is still a **conditional adapter obligation**, not an admitted implementation.

## Map, GetVirAddr and Unmap state boundaries

| Operation / branch | Exact file behavior | Required interpretation |
|---|---|---|
| Map: display helper output null | `0x77f50` branch, returns `50002000` | No mapping proof. Helper internals and why it returns null are outside scope. |
| Map: handle null | `0x77f64` branch, returns `41201000` | No usable handle. |
| Map: virAddr already nonzero OR skip bit set | `0x77f6c/0x77f74` branches to rc0 `0x77fb4` | Lower Map is not called. Success does not by itself establish writable CPU memory. |
| Map: lower display vtable+0x30 | `0x77f84` calls with handle; `0x77f8c..0x77f98` rejects returned pointer 0 and all-ones, returning `50007000`; other pointers return0 | This function does not itself assign virAddr. The lower provider's writes and side effects on failure remain unknown. |
| GetVirAddr | `0x789d8` invokes virtual Map again; accepts unsigned `(rc+999)<1999`, i.e. signed rc in [-999,999], then locks and reads handle+0x20; other rc returns null | It is not a pure getter. Combined with the prior public Map wrapper, a successful public call can invoke SurfaceBufferImpl::Map twice and still publish rc0+null if the second call fails. This is a file path, not an observed runtime incident. |
| Unmap: display/handle missing | Returns `50002000` / `41201000` respectively | Public OH_NativeBuffer_Unmap normalizes any such nonzero lower rc to `50002000`, as already shown in the prior audit. |
| Unmap: virAddr null | `0x7808c` branch; logs, returns0, no lower call | Idempotent no-address path, not proof a buffer was ever mapped. |
| Unmap: lower display vtable+0x38 fails | Call `0x7809c`, nonzero branch `0x780a0`, returns `50007000` | No local clearing of handle+0x20. The lower provider could still mutate state; “unchanged address” is not guaranteed. |
| Unmap: lower returns0 | `0x78160..0x78168` reloads handle and clears its +0x20 | Local success transition is confirmed. Lower cache flush, actual VM unmapping and queue ownership are unproved. |

Neither Map nor Unmap acquires a new reference to the input SurfaceBufferImpl. The shared-count release instructions concern the display-helper result, not a newly owned input-buffer reference. Together with the previous exact conversion returning `this`, the borrowed conversion contract is consistent with this file. **The window-buffer/request owner's lifetime across callbacks still has to be established**; mutex coverage of an accessor does not extend pointer lifetime after it returns.

## R14 comparison and admission limits

The pinned `window_module.h/.c` blobs are indexed at main commit `6c06bcbf50040d777fca4c1f27c5663ee17cadf3`:

- Header lines18–21 describes borrowed conversion and no ownership ref operations. This matches the exact SurfaceBufferImpl conversion path; it does not prove actual runtime object class or request-cache lifetime.
- C lines78–81 checks conversion and Map rc plus non-null bits. This is necessary because GetVirAddr can fail after the first Map succeeded. Lines87–91 clean up after rc0+invalid bits and retain every failure; `complete(...,0)` cannot free a slot based on Abort's swallowed lower rc.
- C lines103–106 stops before Flush if Unmap fails. This is consistent with unknown lower mapping state. Successful Unmap and Flush are required for the success transition.
- C line81 compares `stride_bytes * height <= size_bytes`; line82 converts byte stride to pixels using format bytes-per-pixel. **This pass establishes neither exact-provider byte semantics nor actual handle values**, so these arithmetic checks do not validate a yet-unbound provider. A physical/stride byte-length proof must precede admission.
- A further provider precondition remains: reject invalid mapping sentinels, not merely null. Map's existing-address fast path accepts any nonzero virAddr, GetVirAddr reads it unchanged, and R14 only checks `bits != NULL`. We have not observed an all-ones address or proved that the lower provider can leave one. This is an admission obligation, not a current bug diagnosis or permission to change R14.

One **review-pending implementation option** for a future typed provider Map thunk is to preserve OH rc0 but normalize `bits == (void*)-1` to NULL. Unchanged R14 would then set `mapped=1`, reject null bits and enter Unmap → conditional Abort → retained failure. Returning an error instead would leave R14 `mapped=0`, skip Unmap and attempt Abort directly. These are materially different cleanup paths. This option is not implemented or approved here: whether lower Unmap safely handles such a state is still unproved, and public Abort rc0 does not establish lower release. Do not infer a live sentinel fault from this proposed adapter behavior.

## Remaining smallest evidence gaps (not executed)

Raw width/height/stride/format offsets require the exact getter bodies (ELF `0x78810`, `0x78858`, `0x788a0`, `0x788e8`); complete usage would require `0x78930`. Those are new functions and were **not** analyzed. Fixed extent and reserve-tail proof must follow an actual exact-provider handle allocation/serialization/clone implementation; this file's Clone wrapper does not contain it. Mapping side effects, cache semantics and size-byte usage require the selected display-provider method implementations. The helper at `0x77c4c` and its runtime-selected provider remain outside scope; do not pick another library/version merely to fill the gap.

Actual dlsym winner, namespace, input object/vtable, live handle dimensions/stride/size and successful request→map→unmap→flush remain unobserved. This is an offline provider-evidence increment, not a deployable candidate, playback result, API freeze or seal. Expected-help key remains **toutiao, conditional** on the observed path reaching this implementation.
