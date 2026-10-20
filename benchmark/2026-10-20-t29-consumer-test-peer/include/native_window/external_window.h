#pragma once
#include <cstdint>
struct OHNativeWindow { int id; };
constexpr int SET_BUFFER_GEOMETRY=1;
extern "C" {
int32_t OH_NativeWindow_NativeObjectReference(void*);
int32_t OH_NativeWindow_NativeObjectUnreference(void*);
int32_t OH_NativeWindow_NativeWindowHandleOpt(OHNativeWindow*,int,...);
}
