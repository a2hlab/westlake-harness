#!/usr/bin/env python3
"""Compute the default-namespace unresolved-symbol closure for libmetasec_ml.so.

Model: musl dlopen resolves a library's UND against its DT_NEEDED transitive
closure (+ RTLD_GLOBAL). metasec's fatal set = UND(metasec) minus the union of
DEFINED symbols reachable through metasec's DT_NEEDED closure. Providers are
westlake native-runtime/native-platform .so plus OH firmware libs (firmware-abi
entries carry their own needed + symbol list).
"""
import json, subprocess, os, glob, re

APK = os.path.expanduser("~/a2hlab/app-inputs/toutiao/lib/arm64-v8a")
OUT = os.path.expanduser("~/a2hlab/ws/out-all0925")
FWABI = os.path.expanduser("~/a2hlab/ws/westlake/native/oh61-firmware-abi.json")


def readelf(path):
    out = subprocess.check_output(["readelf", "-W", "-d", "--dyn-syms", path],
                                  text=True, stderr=subprocess.DEVNULL)
    needed = []
    defined = {}
    und = {}
    for line in out.splitlines():
        m = re.search(r"\(NEEDED\).*\[(.+?)\]", line)
        if m:
            needed.append(m.group(1))
            continue
        r = line.split()
        if (len(r) >= 8 and r[0].endswith(":") and
                r[3] in ("FUNC", "OBJECT", "IFUNC", "TLS", "NOTYPE") and
                r[4] in ("GLOBAL", "WEAK")):
            name = r[7].split("@")[0]
            if r[6] == "UND":
                weak = (r[4] == "WEAK")
                if name in und:
                    und[name] = und[name] and weak
                else:
                    und[name] = weak
            else:
                defined[name] = r[3]
    return needed, defined, und


prov_needed = {}
prov_def = {}
prov_path = {}
for d in ("native-runtime", "native-platform"):
    for f in glob.glob(os.path.join(OUT, d, "*.so")):
        son = os.path.basename(f)
        n, de, _ = readelf(f)
        prov_needed[son] = n
        prov_def[son] = de
        prov_path[son] = f

fw = json.load(open(FWABI))["firmware"]
for son, ent in fw.items():
    if son in prov_def:
        continue
    prov_needed[son] = ent.get("needed", [])
    syms = ent.get("symbols", {})
    if isinstance(syms, dict):
        prov_def[son] = {k: (v.get("type", "FUNC") if isinstance(v, dict) else "FUNC")
                         for k, v in syms.items()}
    else:
        prov_def[son] = {k: "FUNC" for k in syms}
    prov_path[son] = "[firmware:%s]" % ent.get("path", "")

mneed, mdef, mund = readelf(os.path.join(APK, "libmetasec_ml.so"))

seen = set()
order = []
stack = list(mneed)
missing_libs = set()
while stack:
    son = stack.pop(0)
    if son in seen:
        continue
    seen.add(son)
    if son not in prov_needed:
        missing_libs.add(son)
        continue
    order.append(son)
    for nx in prov_needed[son]:
        if nx not in seen:
            stack.append(nx)

reachable = {}
for son in order:
    for s in prov_def[son]:
        reachable.setdefault(s, son)

missing = []
weak_missing = []
for s, is_weak in sorted(mund.items()):
    if s in reachable:
        continue
    (weak_missing if is_weak else missing).append(s)

all_def = {}
for son, de in prov_def.items():
    for s in de:
        all_def.setdefault(s, []).append(son)

print("=== METASEC CLOSURE REPORT (providers: out-all0925) ===")
print("metasec UND total:", len(mund),
      " weak-UND:", sum(1 for v in mund.values() if v))
print("closure libs (%d): %s" % (len(order), " ".join(order)))
if missing_libs:
    print("!! NEEDED libs absent from providers:", sorted(missing_libs))
print("reachable defined syms:", len(reachable))
print()
print("=== HARD-MISSING (fatal, non-weak): %d ===" % len(missing))
for s in missing:
    elsewhere = all_def.get(s, [])
    tag = "NOWHERE" if not elsewhere else "exists-in:" + ",".join(elsewhere)
    print("  %-42s %s" % (s, tag))
print()
print("=== WEAK-MISSING (non-fatal -> 0): %d ===" % len(weak_missing))
for s in weak_missing:
    print("  %-42s exists-in:%s" % (s, ",".join(all_def.get(s, [])) or "NOWHERE"))

json.dump({"hard_missing": missing, "weak_missing": weak_missing,
           "hard_detail": {s: all_def.get(s, []) for s in missing},
           "closure_libs": order, "reachable_count": len(reachable),
           "und_total": len(mund)},
          open(os.path.expanduser("~/a2hlab/tmp/metaclosure/closure.json"), "w"),
          indent=2)
print("\nwrote closure.json")
