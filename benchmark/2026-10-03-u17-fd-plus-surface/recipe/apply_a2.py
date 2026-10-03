#!/usr/bin/env python3
"""Splice the A2 software-lockCanvas implementation into android_graphics_compat_shim.cpp.

Two anchored edits (both asserted to match EXACTLY once; refuses otherwise so a changed base
is caught, not silently mis-patched):
  1. GLOBALS: insert a2-globals.inc.cpp right AFTER the ALOGE #define (global scope, BEFORE
     `namespace android {`). Needed because the shim's own oh_anw_get_oh / OHNativeWindow are
     at GLOBAL scope; declaring them inside android::(anon) makes the extern-"C" types differ.
  2. IMPL: replace the two hard stubs (in android::(anon), matching the RegisterNatives table)
     with a2-lockcanvas.inc.cpp (helpers + the two function definitions, ::-qualified globals).

Usage: apply_a2.py <shim_in.cpp> <a2-globals.inc.cpp> <a2-lockcanvas.inc.cpp> <shim_out.cpp>
"""
import sys

ALOGE = '#define ALOGE(...) HiLogPrint(3, 6, 0xD000F00u, "OH_GfxShim", __VA_ARGS__)\n'

STUB = (
    "jlong S_nativeLockCanvas(JNIEnv*, jclass, jlong /*nativeObject*/, jobject /*canvas*/, jobject /*dirtyRect*/) {\n"
    "    // Without a real surface buffer to lock, lockCanvas can't return a real\n"
    "    // canvas.  HelloWorld doesn't use Surface.lockCanvas (hwui owns drawing).\n"
    "    return 0;\n"
    "}\n"
    "void S_nativeUnlockCanvasAndPost(JNIEnv*, jclass, jlong /*nativeObject*/, jobject /*canvas*/) { }\n"
)

def splice_once(src, anchor, payload, *, after, what):
    n = src.count(anchor)
    if n != 1:
        sys.stderr.write("[apply_a2] FATAL: %s anchor found %d times (expected 1)\n" % (what, n))
        sys.exit(2)
    if after:
        return src.replace(anchor, anchor + payload)
    return src.replace(anchor, payload)

def main():
    shim_in, globals_inc, lock_inc, shim_out = sys.argv[1:5]
    src = open(shim_in, encoding="utf-8").read()
    gl = open(globals_inc, encoding="utf-8").read()
    im = open(lock_inc, encoding="utf-8").read()
    src = splice_once(src, ALOGE, gl, after=True,  what="ALOGE(globals)")
    src = splice_once(src, STUB,  im, after=False, what="stub(impl)")
    for marker in ("[SWLOCK] lockCanvas", "NativeWindowRequestBuffer", "oh_anw_get_oh"):
        if marker not in src:
            sys.stderr.write("[apply_a2] FATAL: post-splice marker missing: %s\n" % marker)
            sys.exit(3)
    open(shim_out, "w", encoding="utf-8").write(src)
    sys.stderr.write("[apply_a2] OK: globals + A2 impl spliced\n")

if __name__ == "__main__":
    main()
