// U15: the NDK ATrace entry points for the Flutter-private libandroid (westlake_flutter/libandroid.so).
// Semantics = AOSP android-14.0.0_r1 frameworks/base/native/android/trace.cpp (299fe6f5, sha256 7c4a1504):
//   ATrace_isEnabled()        -> atrace_is_tag_enabled(ATRACE_TAG_APP)
//   ATrace_beginSection(name) -> atrace_begin(ATRACE_TAG_APP, name)
//   ATrace_endSection()       -> atrace_end(ATRACE_TAG_APP)
// with the inline helpers of system/core/libcutils/include/cutils/trace.h (sha256 341eed8d, lines 149-178):
//   atrace_is_tag_enabled(tag) = atrace_get_enabled_tags() & tag; begin/end call the *_body only when the tag is on.
// The three body functions are exported by liboh_android_runtime.so, which this library already NEEDs; they bind
// through that existing DT_NEEDED to the one runtime instance of the Flutter domain (no dlopen/dlsym, no new NEEDED).
#include <stdint.h>

#define ATRACE_TAG_APP (1 << 12)

extern "C" uint64_t atrace_get_enabled_tags();
extern "C" void atrace_begin_body(const char*);
extern "C" void atrace_end_body();

static inline uint64_t atrace_is_tag_enabled(uint64_t tag) {
    return atrace_get_enabled_tags() & tag;
}

extern "C" bool ATrace_isEnabled() {
    return atrace_is_tag_enabled(ATRACE_TAG_APP);
}

extern "C" void ATrace_beginSection(const char* sectionName) {
    if (__builtin_expect(atrace_is_tag_enabled(ATRACE_TAG_APP) != 0, 0)) {
        atrace_begin_body(sectionName);
    }
}

extern "C" void ATrace_endSection() {
    if (__builtin_expect(atrace_is_tag_enabled(ATRACE_TAG_APP) != 0, 0)) {
        atrace_end_body();
    }
}
