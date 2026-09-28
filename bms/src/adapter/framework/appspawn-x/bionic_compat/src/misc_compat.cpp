// bionic_compat/src/misc_compat.cpp
// Miscellaneous Bionic compatibility functions.

#include <unistd.h>

// Route A is forked and specialized by stock OH appspawn, so it never enters
// AOSP's native zygote-fork reset edge. The adapter-owned WLTG post-stock
// boundary establishes Bionic's canonical process guard without touching
// Musl's process-global stack protector. If an unsupported path invokes this
// legacy Bionic entry, terminate without returning through a protected frame;
// never install a fixed value and never mutate Musl __stack_chk_guard.
extern "C" __attribute__((noreturn)) void android_reset_stack_guards(void) {
    _exit(127);
}

// ---------------------------------------------------------------------------
// android_dlwarning — Bionic linker API used by AOSP libandroid_runtime to
// report deprecated library usage. On OH/musl we have no warning source;
// implement as a no-op that does not invoke the callback. This matches the
// documented contract: "calls f(obj, msg) for each deprecated lib"; with
// zero deprecated libs reported, f is never invoked.
// ---------------------------------------------------------------------------
extern "C" void android_dlwarning(void* /*obj*/,
                                   void (* /*f*/)(void* /*obj*/, const char* /*msg*/)) {
    // nothing to report
}
