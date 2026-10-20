# Exact T28 bridge: bounded SurfaceTexture / TextureView review

The deployed bridge candidate is SHA256 `dca530eb4b1b53e5dd0ecc41c36953f7463609c5b70bbdf67a49dc3cae17f9d9`, 2,017,104 bytes. LLVM symbol, relocation, JNI-table and limited instruction inspection corroborate the following snapshot semantics in this exact ELF. This is not runtime JNI/PLT-slot binding proof, a full source rebuild, or a black-screen root cause. No device calls, new REA, code changes or builds occurred.

| Method | ELF entry | Actual call / branch |
|---|---|---|
| nativeUpdateTexImage ()V | 0x11f1ec | 0x11f24c calls UpdateSurfaceImage@PLT; zero returns, nonzero logs and throws. Null state/image or released branch to exception path 0x11f29c without object diagnostic. |
| nativeDetachFromGLContext ()I | 0x11f414 | 0x11f46c calls DetachContext@PLT; only rc0 stores detached=1 at state+0x3c. Missing state/image returns -1; no log. |
| nativeAttachToGLContext (I)I | 0x11f490 | 0x11f4f0 calls AttachContext@PLT; only rc0 stores texture name at +0x38 and detached=0 at +0x3c. Missing state/image returns -1; no log. |
| nCreateNativeWindow | 0x11fb2c | Old window unref at 0x11fb70, old Java field cleared, getter at 0x11fb98, new window ref at 0x11fba8, Java field stored at 0x11fbc4. No consumer attach/update call. |
| nDestroyNativeWindow | 0x11fc04 | Existing window unref at 0x11fc38 then Java field cleared; missing field/window returns. |
| oh_surface_texture_get_native_window | 0x11eb94 | Valid state and !released return state+0x10 nativeWindow; otherwise zero. Called through PLT, not a statically bound local direct call. |

`jni-methods.json` decodes the exact ELF relative relocations and name/signature strings for the five JNI table entries; it proves table contents, not which runtime registration won. NativeImage GOT slots are update `0x174068`, detach `0x174078`, attach `0x174080`; the producer getter slot is `0x174030`. These slots have not been read at runtime in this review. Do not call a named imported API the actual selected provider.

The T18 production recipe reuses surface_texture object SHA `39e1be587a295ad1bae7535bf4589092774a8f0de0879936bf14ea35a51ffca0` and texture_view object SHA `132b3547792341b99b47bd71b7b9589131684711ad3b53ffc4bcadd4796a7ead`. Corresponding repository source snapshots are pinned in `source-link-provenance.json`. The recorded build is an incremental relink with an AudioTrack rebuild, not an independent rebuild of these two source files. The disassembly above supplies the narrow deployed-body evidence that the source-only review lacked.

## Three observation seams; no proposed policy repair

1. **Consumer attach/detach entry and return**, including the existing -1 early return: record monotonic time, thread, operation, Java handle (call-local only), trusted state/image/window, texture name, prior/post detached and actual existing-call rc. Preserve the existing call count and result. Use an object/transition-specific budget so the initial clip cannot exhaust all later records.
2. **Consumer update entry/result and invalid-state early return**: record the same state/image/window and released/detached relationship, whether the OH call actually ran, its rc, and existing exception outcome. Do not infer failure from missing success logs or clear/retry the call. Frame-available callbacks prove queue notification only, not successful update.
3. **TextureView producer replacement**: record TextureView handle, SurfaceTexture handle, old field window and returned new window, getter return and existing ref/unref outcomes. Correlate via trusted native state/window, not jobject pointer equality across calls. This method changes producer ownership only; it must not be made to attach the consumer as an assumed repair.

The `eeecaa3d6a` 22-line log excerpt shows old/new producer windows, frame notifications and EGL image destruction/creation but lacks consumer attach/detach rc and update-success identities. Its old OH address returning therefore remains insufficient evidence for stale ownership. Observe those seams before choosing a lifecycle repair. Keep actual JNI/PLT winner identity as a runtime evidence gate if these methods are instrumented later.

Raw outputs are under `$HOME/.local/share/westlake/t28-codex-review/bridge-surface-01`; `raw-index.json` pins every original. Public assembly copies replace only the local artifact pathname. Public files contain no full media logs. Remote archival is delegated, not asserted here.
