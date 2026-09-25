#!/usr/bin/env python3
"""Assert the metasec relocation closure is complete against a candidate libandroid.

The whole point (#48): metasec resolves its UND against ONLY its 5 direct
DT_NEEDED. Of those, westlake controls libandroid (and liblog); libc/libm/libdl
are OH musl (sysroot libc.so covers all three on musl). So the closure is
complete iff:

    UND_hard(libmetasec_ml.so) - DEFINED(libandroid U liblog U musl-libc) == {}

Usage:
    assert_metasec_closure.py <libandroid.so> [extra.o ...]

extra .o files are unioned into the provider set, so the fully-linked libandroid
can be simulated from a sensor-patched libandroid.so plus the not-yet-linked
compat objects. Exit 0 = PASS (zero UND-missing), 1 = FAIL (prints the gaps).
"""
import subprocess, os, re, sys

APK = os.path.expanduser("~/a2hlab/app-inputs/toutiao/lib/arm64-v8a/libmetasec_ml.so")
SYSROOT_LIBC = os.path.expanduser(
    "~/a2hlab/ws/toolchains/ohos-sdk/native/sysroot/usr/lib/aarch64-linux-ohos/libc.so")
LIBLOG = os.path.expanduser("~/a2hlab/ws/out-all0925/native-runtime/liblog.so")

# The 15 symbols the two westlake source files must add to libandroid.
EXPECT = [
    "ASensorManager_getInstance", "ASensorManager_getDefaultSensor",
    "ASensorManager_createEventQueue", "ASensorManager_destroyEventQueue",
    "ASensorEventQueue_getEvents", "ASensorEventQueue_enableSensor",
    "ASensorEventQueue_disableSensor",
    "__errno", "__openat_2", "__sF", "__system_property_find",
    "__system_property_read", "android_set_abort_message",
    "strtoll_l", "strtoull_l",
]


def defined(path):
    """GLOBAL/WEAK, non-UND symbol names from .so (dyn-syms) or .o (symtab)."""
    out = subprocess.check_output(["readelf", "-W", "--dyn-syms", "-s", path],
                                  text=True, stderr=subprocess.DEVNULL)
    names = set()
    for line in out.splitlines():
        r = line.split()
        if (len(r) >= 8 and r[0].endswith(":") and
                r[3] in ("FUNC", "OBJECT", "IFUNC", "TLS", "NOTYPE") and
                r[4] in ("GLOBAL", "WEAK") and r[6] != "UND"):
            names.add(r[7].split("@")[0])
    return names


def metasec_und():
    out = subprocess.check_output(["readelf", "-W", "--dyn-syms", APK],
                                  text=True, stderr=subprocess.DEVNULL)
    hard = {}
    for line in out.splitlines():
        r = line.split()
        if (len(r) >= 8 and r[0].endswith(":") and
                r[3] in ("FUNC", "OBJECT", "IFUNC", "TLS", "NOTYPE") and
                r[4] in ("GLOBAL", "WEAK") and r[6] == "UND"):
            name = r[7].split("@")[0]
            weak = (r[4] == "WEAK")
            hard[name] = hard.get(name, True) and weak
    return sorted(n for n, w in hard.items() if not w)


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: assert_metasec_closure.py <libandroid.so> [extra.o ...]")
    libandroid = sys.argv[1]
    prov = defined(libandroid) | defined(LIBLOG) | defined(SYSROOT_LIBC)
    for extra in sys.argv[2:]:
        prov |= defined(extra)

    und = metasec_und()
    missing = [s for s in und if s not in prov]

    # Report presence of the 15 expected additions in the candidate provider set.
    print("== expected 15 additions present in provider set ==")
    for s in EXPECT:
        print("  %-34s %s" % (s, "OK" if s in prov else "MISS"))
    print()
    print("metasec hard-UND: %d   provider defined: %d" % (len(und), len(prov)))
    if missing:
        print("FAIL: %d UND still unresolved by metasec's direct deps:" % len(missing))
        for s in missing:
            print("   -", s)
        sys.exit(1)
    print("PASS: metasec closure complete — zero UND-missing against direct deps")
    sys.exit(0)


if __name__ == "__main__":
    main()
