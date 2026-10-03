// [U17 fd-plus A2] GLOBAL-scope declarations (spliced right after the ALOGE #define, BEFORE
// `namespace android {`). These must sit at global scope so they are the SAME types as the
// shim's own GLOBAL decls (oh_anw_get_oh / OHNativeWindow live at global scope, after the
// `} // namespace android` around line 1048). Declaring them inside android::(anon) instead
// makes android::(anon)::OHNativeWindow != ::OHNativeWindow and the extern-"C" oh_anw_get_oh
// decls "differ only in return type" -> compile error. The inner libsurface fns are declared
// here because the shim does not declare them anywhere; oh_anw_get_oh matches the shim's
// existing global decl (token-identical) so it is a harmless redeclaration.
struct ANativeWindow;
struct OHNativeWindow;
struct OHNativeWindowBuffer;
typedef struct {
    int32_t fd; int32_t width; int32_t stride; int32_t height;
    int32_t size; int32_t format; uint64_t usage; void* virAddr;
    uint64_t phyAddr; uint32_t reserveFds; uint32_t reserveInts; int32_t reserve[0];
} OHBufferHandleA2;
struct OHFlushRectA2   { int32_t x; int32_t y; uint32_t w; uint32_t h; };
struct OHFlushRegionA2 { OHFlushRectA2* rects; int32_t rectNumber; };
// liboh_adapter_bridge (already NEEDED + already imported UND): AdapterAnw('ANW1') -> a->oh.
// The runtime-EXPORTED stable unwrap entry (per outer: no raw +0xc0 offset in the formal
// artifact). oh_anw_get_oh does the magic('ANW1')+directPathLive check and returns a->oh.
extern "C" struct OHNativeWindow* oh_anw_get_oh(struct ANativeWindow* aosp);
// inner libsurface (already NEEDED; native_window.cpp -> ohos_shared_library("surface")):
extern "C" int32_t NativeWindowRequestBuffer(struct OHNativeWindow*, struct OHNativeWindowBuffer**, int*);
extern "C" int32_t NativeWindowFlushBuffer(struct OHNativeWindow*, struct OHNativeWindowBuffer*, int, OHFlushRegionA2);
extern "C" OHBufferHandleA2* GetBufferHandleFromNative(struct OHNativeWindowBuffer*);
