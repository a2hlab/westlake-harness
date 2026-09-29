/* libGLESv2.so soname shim (r16-native-walls 2): Android app DSOs DT_NEEDED
 * this soname; the board ships only libGLESv3.so (ndk-namespace-gated).
 * Empty DSO satisfies the loader; upgrade to a forwarding shim if apps
 * call real GLES symbols through it. */
