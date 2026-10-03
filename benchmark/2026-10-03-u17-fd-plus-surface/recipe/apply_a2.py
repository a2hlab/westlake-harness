#!/usr/bin/env python3
"""Splice the A2 software-lockCanvas implementation into android_graphics_compat_shim.cpp.

Anchored on the exact two-stub block (not line numbers), so it applies cleanly on the
post-split.patch source regardless of minor line drift. Asserts the anchor is present
EXACTLY once; refuses otherwise (so a changed base is caught, not silently mis-patched).

Usage: apply_a2.py <shim_in.cpp> <a2-lockcanvas.inc.cpp> <shim_out.cpp>
"""
import sys

ANCHOR = (
    "jlong S_nativeLockCanvas(JNIEnv*, jclass, jlong /*nativeObject*/, jobject /*canvas*/, jobject /*dirtyRect*/) {\n"
    "    // Without a real surface buffer to lock, lockCanvas can't return a real\n"
    "    // canvas.  HelloWorld doesn't use Surface.lockCanvas (hwui owns drawing).\n"
    "    return 0;\n"
    "}\n"
    "void S_nativeUnlockCanvasAndPost(JNIEnv*, jclass, jlong /*nativeObject*/, jobject /*canvas*/) { }\n"
)

def main():
    shim_in, inc_file, shim_out = sys.argv[1], sys.argv[2], sys.argv[3]
    src = open(shim_in, encoding="utf-8").read()
    inc = open(inc_file, encoding="utf-8").read()
    n = src.count(ANCHOR)
    if n != 1:
        sys.stderr.write("[apply_a2] FATAL: anchor found %d times (expected 1)\n" % n)
        sys.exit(2)
    out = src.replace(ANCHOR, inc)
    # sanity: both function definitions must now carry the A2 marker
    if "[SWLOCK] lockCanvas" not in out or "NativeWindowRequestBuffer" not in out:
        sys.stderr.write("[apply_a2] FATAL: post-splice markers missing\n")
        sys.exit(3)
    open(shim_out, "w", encoding="utf-8").write(out)
    sys.stderr.write("[apply_a2] OK: spliced A2 lockCanvas/unlock (%d -> %d bytes)\n" % (len(src), len(out)))

if __name__ == "__main__":
    main()
