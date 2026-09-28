#pragma once
// Stub: jni_macros for fast JNI method registration.
#define MAKE_JNI_NATIVE_METHOD(name, sig, fnPtr) {(char*)name, (char*)sig, reinterpret_cast<void*>(fnPtr)}
#define MAKE_JNI_FAST_NATIVE_METHOD(name, sig, fnPtr) {(char*)name, (char*)sig, reinterpret_cast<void*>(fnPtr)}
#define MAKE_JNI_CRITICAL_NATIVE_METHOD(name, sig, fnPtr) {(char*)name, (char*)sig, reinterpret_cast<void*>(fnPtr)}
#define MAKE_JNI_NATIVE_METHOD_AUTOSIG(name, fnPtr) {(char*)name, (char*)"()V", reinterpret_cast<void*>(fnPtr)}
