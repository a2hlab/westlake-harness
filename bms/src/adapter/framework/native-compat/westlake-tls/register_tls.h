/* Standalone registration entry for liboh_tls_boundary.so (#93-native).
 * Same binding as AndroidRuntime.cpp L3285 wl_register_tls_natives:
 * adapter/compat/WestlakeSSLSocket {nativeHandshake, nativeRead, nativeWrite,
 * nativePeerCert, nativePeerChain, nativeInfo, nativeClose}. Call once per
 * child after the runtime jar (which declares the class) is on the classpath. */
#ifndef REGISTER_TLS_H
#define REGISTER_TLS_H
#include <jni.h>
#ifdef __cplusplus
extern "C" {
#endif
int westlake_tls_child_register(JNIEnv* env);
#ifdef __cplusplus
}
#endif
#endif
