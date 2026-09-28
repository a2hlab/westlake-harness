#pragma once
// Adapter shim: delegate to AOSP canonical JNIPlatformHelp.h.
//
// 2026-04-22 (Blocker A.6): previously this file had stub inline definitions
// for jniGetNioBufferPointer (void*) / jniGetNioBufferBaseArray (nullptr) /
// jniGetNioBufferBaseArrayOffset (0) that masked the real AOSP API, causing
// AutoBufferPointer to compile to a 660-byte empty .o under an #if 0 wrapper
// (since the real AOSP code expected jlong return from getPointer but the
// shim returned void*).
//
// Resolution: include the real AOSP JNIPlatformHelp.h. It provides:
//   - jlong jniGetNioBufferPointer(C_JNIEnv*, jobject)
//   - jarray jniGetNioBufferBaseArray(C_JNIEnv*, jobject)
//   - jint jniGetNioBufferBaseArrayOffset(C_JNIEnv*, jobject)
// plus JNIEnv* inline wrappers. The underlying extern symbols are provided by
// libnativehelper.so which adapter already links against (out/aosp_lib/
// libnativehelper.so exports all 3, verified 2026-04-22 via pyelftools).
//
// File descriptor helpers (jniCreateFileDescriptor / jniGetFDFromFileDescriptor /
// jniSetFileDescriptorOfFD) are also provided by the AOSP header; adapter shim
// does not override.
// #include_next (not #include) is required: this file itself is found via
// -I.../skia_compat_headers, which is earlier on the include search path
// than -I$AOSP_ROOT/libnativehelper/include_platform (added by
// build/inner/compile_libhwui.sh specifically after skia_compat_headers for
// this delegation). A plain #include <nativehelper/JNIPlatformHelp.h> would
// just re-resolve to this same shim file (infinite recursion); #include_next
// continues the search from the next -I directory and picks up the real
// AOSP header instead.
#include_next <nativehelper/JNIPlatformHelp.h>

#ifndef NELEM
#define NELEM(x) (sizeof(x) / sizeof(*(x)))
#endif
