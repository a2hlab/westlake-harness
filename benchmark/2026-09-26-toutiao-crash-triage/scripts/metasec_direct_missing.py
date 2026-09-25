#!/usr/bin/env python3
"""Direct-DT_NEEDED (depth-1) missing-symbol set for libmetasec_ml.so.

Board evidence (sensor then __system_property_read appearing one at a time)
shows metasec resolves against ONLY its 5 direct DT_NEEDED, not their transitive
closure. So the fatal set = UND(metasec) minus DEFINED(union of the 5 direct
needed as deployed): libandroid, liblog, and the OH musl libc.so (which also
carries libm.so + libdl.so exports on OH musl).
"""
import subprocess, os, re, sys, json

APK = os.path.expanduser("~/a2hlab/app-inputs/toutiao/lib/arm64-v8a/libmetasec_ml.so")
SYSROOT_LIBC = os.path.expanduser(
    "~/a2hlab/ws/toolchains/ohos-sdk/native/sysroot/usr/lib/aarch64-linux-ohos/libc.so")
LIBLOG = os.path.expanduser("~/a2hlab/ws/out-all0925/native-runtime/liblog.so")
LIBANDROID_PATCHED = os.path.expanduser("~/a2hlab/ws/out-operator-sensor48/libandroid.so")
LIBANDROID_STOCK = os.path.expanduser("~/a2hlab/ws/out-operator-sensor48/libandroid.stock.so")


def syms(path):
    out = subprocess.check_output(["readelf", "-W", "--dyn-syms", path],
                                  text=True, stderr=subprocess.DEVNULL)
    defined = {}
    und = {}
    for line in out.splitlines():
        r = line.split()
        if (len(r) >= 8 and r[0].endswith(":") and
                r[3] in ("FUNC", "OBJECT", "IFUNC", "TLS", "NOTYPE") and
                r[4] in ("GLOBAL", "WEAK")):
            name = r[7].split("@")[0]
            if r[6] == "UND":
                weak = (r[4] == "WEAK")
                und[name] = und.get(name, True) and weak
            else:
                defined[name] = r[3]
    return defined, und


_, mund = syms(APK)


def provider_union(libandroid):
    u = {}
    for p in (SYSROOT_LIBC, LIBLOG, libandroid):
        d, _ = syms(p)
        u.update(d)
    return u


def missing_against(libandroid):
    prov = provider_union(libandroid)
    hard = sorted(s for s, w in mund.items() if not w and s not in prov)
    weak = sorted(s for s, w in mund.items() if w and s not in prov)
    return hard, weak, prov


hard_p, weak_p, prov_p = missing_against(LIBANDROID_PATCHED)
hard_s, weak_s, _ = missing_against(LIBANDROID_STOCK)

# where each still-missing symbol exists across the wider westlake providers
WIDE = [os.path.expanduser("~/a2hlab/ws/out-all0925/native-runtime/" + b) for b in
        ("libwestlake_bionic.so", "libbase.so", "libnativehelper.so", "libc++.so")]
wide_def = {}
for p in WIDE:
    if os.path.exists(p):
        d, _ = syms(p)
        for s in d:
            wide_def.setdefault(s, []).append(os.path.basename(p))

print("metasec UND: %d (hard non-weak: %d)" %
      (len(mund), sum(1 for w in mund.values() if not w)))
print()
print("MODEL CHECK: stock->patched delta (should be exactly the 7 sensor no-ops)")
delta = sorted(set(hard_s) - set(hard_p))
print("  removed by sensor patch: %d" % len(delta))
for s in delta:
    print("    -", s)
print()
print("=== REMAINING HARD-MISSING after sensor patch: %d ===" % len(hard_p))
for s in hard_p:
    where = wide_def.get(s, [])
    print("  %-40s %s" % (s, "exists-in:" + ",".join(where) if where else "NOWHERE(new impl/no-op)"))
print()
print("=== WEAK-MISSING (non-fatal): %d ===" % len(weak_p))
for s in weak_p[:40]:
    print("  %-40s %s" % (s, "exists-in:" + ",".join(wide_def.get(s, [])) if wide_def.get(s) else "(weak->0)"))

json.dump({"metasec_und": len(mund),
           "remaining_hard_missing": hard_p,
           "sensor_delta": delta,
           "weak_missing": weak_p,
           "hard_where": {s: wide_def.get(s, []) for s in hard_p}},
          open(os.path.expanduser("~/a2hlab/tmp/metaclosure/direct_missing.json"), "w"),
          indent=2)
print("\nwrote direct_missing.json")
