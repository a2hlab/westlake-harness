# Window lock candidate: static build preflight

The earlier proposed whole-shim rebuild would mix the required window fix with unrelated libc, loader, EGL, audio and NDK behavior. The reusable unit is the paired lock/unlock state machine and its small helper closure. This audit performs **0 builds, 0 device calls and 0 runtime/API changes**. Source availability is not deployment or playback acceptance.

## Available source and exact inputs

The full source is already in `sources/api-implementations/source-build-native691/westlake/`, origin `a2hlab/westlake@691433b967ba01365a382d30fbd820c1231c0811`. `results.json` pins each recipe input, compares it with `sources.lock.json`, and records the local SDK compiler/linker/CRT/library hashes. The f12c donor is `framework/webview-shim/webview_bionic_shim.c`.

Original build entry: `tools/build_bionic_shim.sh <oh-sdk-native> <fresh-output> [description]`. It produces the full `libwebview_bionic_shim.so`, `libaaudio.so`, and `artifacts.json`; it deletes its output directory first. It compiles seven primary units (webview C, OpenSL ES, AAudio, Android relocations, config JNI, fts, setjmp assembly), then a separate libaaudio stub. Do not run it on an existing directory or use its whole output as the minimal candidate.

Original link: aarch64-linux-ohos, PIC/O2, SDK sysroot, lld, `-nostdlib -shared -z defs`, explicit crti/crtbegin/builtins/crtend/crtn, SONAME and version map; `--no-as-needed -lOpenSLES`, then `-ldl -lc`. The map exports `*` under LIBC with additional version nodes. It does not restrict the output to the two window functions. The local SDK provides `libdl.a` (88 bytes), not `libdl.so`; the missing shared filename alone is not a build blocker. Expected link inputs are source-derived; no candidate ELF DT_NEEDED/export claims are made.

## Minimal extraction closure (no extraction performed)

| Donor unit | Required material | Limit |
|---|---|---|
| webview C lines 3898–4078 | lock/unlock; WlWindowBuffer/WlWindowRect/WlBufferHandle/WlRegion; format and bytes-per-pixel switches; 8-slot state and mutex; native-buffer resolver | Pair must stay together; never route unlock to another provider's lock state |
| webview C lines 3740–3745 | native-window dlopen/dlsym helper | Actual target namespace and library identity must be admitted |
| webview C lines 3765–3778 | WlAnwGetOh, pthread_once and resolver | RTLD_DEFAULT then existing bridge via RTLD_NOLOAD; first failure caches NULL permanently |
| android_relocs.c lines 37–46 | only hidden wl_relocs_log body | vsnprintf/write closure only; do not pull the RELR loader module into the small candidate |
| sysroot | dlfcn, pthread, poll, errno, stdint, string, stdarg, stdio, unistd and their transitive headers; CRT and builtins | Lock full compiler/sysroot input closure before a reproducibility claim |

A new standalone source and restrictive export map can implement this closure without changing the donor or frozen files. Its build entry must also be new, with persistent original stdout/stderr and rc. No OpenSL ES, AAudio, config JNI, fts or setjmp code is needed by this extracted lock/unlock closure. `-ldl -lc` plus the pinned CRT/builtins are the proposed minimal link inputs, pending actual strict link. No new provider is constructed or admitted by this report.

## ABI and resolver contract

The authority is main-tree `static/r10-window-contract-review/bridge-unwrap.stdout.txt` for **d4fae8e5**, entry `0x125a00`, size 60: NULL input returns NULL; `u32(window+0)==0x5f776e64`; `u32(window+0xc8)==0x414e5731`; success loads pointer at `+0xc0`, otherwise NULL. It has **no directPathLive branch**. The current bms/related-source resolver has that extra condition and cannot stand in for this ELF. This disassembly establishes code semantics, not the R13 call object's validity or the actual dynamic resolver instance.

| ABI | Source shape on AArch64 LP64 | Required gate |
|---|---|---|
| ANativeWindow_Buffer | int32 width/height/stride/format at 0/4/8/12; bits pointer at16; reserved[6] at24; size48 | Static assertions against target Android headers; stride passed in pixels |
| ARect | 4 int32 fields, size16 | Input/output bounds are overwritten to full buffer |
| OH BufferHandle prefix | fd,width,stride,height,size,format int32; usage uint64 at24; virAddr pointer at32 | Current SDK header agrees with donor prefix; board-version ABI still needs identity |
| OH Region | rect pointer at0 and int32 count at8, size16 | Flush takes Region by value; `{NULL,0}` means full-buffer dirty |
| request/abort/flush | request(window, buffer**, fence*); abort(window,buffer); flush(window,buffer,fence,Region) | Runtime symbol provider and callable target ABI must match |
| map conversion | FromNativeWindowBuffer(buffer,native_buffer**), Map(native_buffer,bits**), Unmap(native_buffer) | Optional lookup/fallback behavior needs explicit review |

The getter/geometry providers are separate from lock. A valid lock-only fix does not establish that the player's dimensions/format/geometry have become correct. Preserve original wrapper ownership for acquire/release and do not pass raw OH pointers to wrapper release. Candidate publication must be caller-scoped to the observed player; exporting two functions globally is not proof of that scope.

## Admission blockers and source audit notes

1. R13 object and exact provider/namespace binding remain the gate. Do not select raw-OH fallback on unwrap NULL; it may instead mean invalid wrapper or wrong provider instance.
2. An isolated provider's routing/lookup precedence is not yet selected. Whole-shim replacement introduces unrelated behavior and is not recommended.
3. No full build, export/version/DT_NEEDED verification, output SHA or raw producing log exists for the narrow module. The full delivered recipe is source-complete, but it does not produce the narrow module as-is.
4. The donor ignores poll's 3000ms return/revents before writing and closes the fence even on timeout; this is an explicit fence-readiness review item, not a proven current crash cause. It also ignores Map/Unmap returns, falls back to virAddr, and clears the slot before flush; failure cleanup and slot/concurrency behavior need targeted tests before reuse. Do not silently edit these while calling it a byte-preserving extraction.
5. Current registry has 8 entries and no direct source/artifact path overlap with this donor or webview shim. `check_frozen.py` returned rc0 with **0 checked**: registry validity only. Changing a shared process provider can still alter frozen behavior; exact final manifest and regression scope must be checked. Preserve frozen files and all baseline callers.

## Next build preparation after admission

Bind observed object/provider to a selected-change record; copy the audited closure to new candidate files; seal SDK/sysroot input hashes and explicit symbol map; compile with strict unresolved-symbol rejection; inspect actual exports/versions/NEEDED and run fence/error/pairing tests; record output SHA and original logs. Only then ask the outer for its already-authorized device window and rollback plan. No API capability grade changes before actual dynamic playback/audio validation.
