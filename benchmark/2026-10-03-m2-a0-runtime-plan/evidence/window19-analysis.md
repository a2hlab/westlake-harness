# Window 19 static analysis: the ANW1 wrapper (AdapterAnw) layout — unwrap mNativeObject to the real OHNativeWindow

Window 18 proved the SurfaceView holder Surface's `mNativeObject` is an **AdapterAnw** (magic 'ANW1'), not a bare
OHNativeWindow, so `OH_NativeWindow_GetSurfaceId(mNativeObject)` = rc 40001000. This is the static hunt for the wrapper
layout so the worker can unwrap it.

## Source (authoritative): `_cc-wiki-b1-src/adapter/framework/window/jni/oh_anativewindow_shim.{h,cpp}`
```cpp
constexpr uint32_t kAdapterAnwMagic = 0x414E5731u; /* 'ANW1' */
struct AdapterAnw {
    struct ANativeWindow aosp;   // AOSP ABI face — must be first (offset 0)
    OHNativeWindow*      oh;      // OH side handle
    uint32_t             magic;
    std::atomic<int32_t> refCount;
    std::mutex           bufCacheLock; ...
};
extern "C" OHNativeWindow* oh_anw_get_oh(struct ANativeWindow* aosp) {
    auto* a = as_adapter(aosp);                       // magic check
    return a && directPathLive(a) ? a->oh : nullptr;  // NB: directPathLive gate
}
```
Header: "allocates a real AOSP-compatible ANativeWindow struct, fills the 10 function pointers … and stores the OH handle
in a trailing field." The shim's own queueBuffer calls `OH_NativeWindow_GetSurfaceId(a->oh, …)` — i.e. GetSurfaceId is
correct only on the UNWRAPPED `a->oh`.

## Disassembly double-check (liboh_adapter_bridge.so, oh_anw_get_oh @0xf33b8; bridge DEFINES it, T)
```
ldr  w8, [x0, #0xc8]              ; magic  @ offset 0xc8 (200)
mov  w9,#0x5731 ; movk w9,#0x414e,lsl#16   ; w9 = 0x414E5731 = 'ANW1'
cmp  w8, w9 ; b.ne -> return null
add  x20, x19, #0x120 ; mutex.lock         ; directPathLive lock @ 0x120
ldrb w21, [x19, #0x149]           ; direct-path state byte @ 0x149
cmp  w21,#1 ; b.hi -> return null          ; gate: state must be <=1
ldr  x0, [x19, #0xc0]             ; oh  @ offset 0xc0 (192) = sizeof(ANativeWindow)
```
**Confirmed offsets: `oh` @ 0xc0 (192), `magic`='ANW1' @ 0xc8 (200).** `sizeof(struct ANativeWindow)` on arm64 = 192
(android_native_base_t 56 + flags/pad 8 + min/max/xdpi/ydpi 16 + oem[4] 32 + 10 fn-ptrs 80). Source field order
(aosp, oh, magic) matches the disasm (oh before magic).

## The directPathLive gate — why a DIRECT read, not oh_anw_get_oh
`oh_anw_get_oh` returns `a->oh` only when the direct-path state byte @0x149 is <=1 (configured via
oh_anw_configure_direct_path). For a SurfaceView AdapterAnw produced by `oh_rs_get_child_surface_window` the state may not
be set, so the exported function could return null even though `a->oh` is valid. A direct, magic-validated read of `a->oh`
@0xc0 avoids the gate. (sizeof(ANativeWindow)=192 is AOSP-fixed and magic sits right after the 8-byte oh, so 0xc0/0xc8 is
stable across bridge generations; a wrong magic → clean FAIL, never a bad deref past the check.)

## Window-19 fix (worker GetSurfaceViewSurface)
WL_A0_SV_OHWIN (published by the entry = Surface.mNativeObject = the AdapterAnw*). Validate `*(uint32_t*)(p+0xc8) ==
0x414E5731`; if not, log + FAIL (not an AdapterAnw). Else real oh = `*(void**)(p+0xc0)` → OH_NativeWindow_GetSurfaceId →
SurfaceUtils::GetSurface → NWeb. Also dlsym oh_anw_get_oh and log its result as a cross-check.

## For cc-wiki
SurfaceView's mNativeObject = AdapterAnw (ANW1), oh @+0xc0 / magic @+0xc8. GetSurfaceId must be on the unwrapped oh. The
exported oh_anw_get_oh gates on directPathLive(@0x149) — fine for hwui's own windows (configured) but may reject a plain
SurfaceView child; SurfaceFromJava should either configure the direct path or read oh @+0xc0 directly after the magic check.
