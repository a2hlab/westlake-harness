#!/usr/bin/env python3
"""Find JNINativeMethod tables in libmetasec_ml.so via relocations (readelf only).

JNINativeMethod = { const char* name; const char* signature; void* fnPtr } = 3
pointers (24 bytes, arm64). In a PIE these are filled by 3 consecutive
R_AARCH64_RELATIVE relocs whose addends point at [name cstr][sig cstr starting
'('][fn in an executable section]. Scanning the RELATIVE relocs for that shape
enumerates every registered native regardless of an obfuscated class name.
"""
import subprocess, sys, re

path = sys.argv[1] if len(sys.argv) > 1 else \
    "/home/zhaoyue/a2hlab/app-inputs/toutiao/lib/arm64-v8a/libmetasec_ml.so"
blob = open(path, "rb").read()

# section table: name, addr, off, size, flags
sects = []
out = subprocess.check_output(["readelf", "-S", "-W", path], text=True)
for line in out.splitlines():
    m = re.match(r"\s*\[\s*\d+\]\s+(\S+)\s+(\S+)\s+([0-9a-f]+)\s+([0-9a-f]+)\s+([0-9a-f]+)\s+\S+\s+(\S*)", line)
    if m:
        name, typ, addr, off, size, flags = m.group(1), m.group(2), int(m.group(3), 16), int(m.group(4), 16), int(m.group(5), 16), m.group(6)
        sects.append((addr, addr + size, off, name, flags, typ))
sects.sort()


def voff(addr):
    for lo, hi, off, name, flags, typ in sects:
        if lo <= addr < hi and typ != "NOBITS":
            return off + (addr - lo)
    return None


def is_text(addr):
    for lo, hi, off, name, flags, typ in sects:
        if lo <= addr < hi:
            return "X" in flags
    return False


def cstr(addr, maxlen=200):
    o = voff(addr)
    if o is None:
        return None
    end = blob.find(b"\x00", o)
    if end < 0 or end - o > maxlen:
        return None
    try:
        return blob[o:end].decode("ascii")
    except UnicodeDecodeError:
        return None


# RELATIVE relocs: offset + addend
addends = {}
out = subprocess.check_output(["readelf", "-r", "-W", path], text=True)
for line in out.splitlines():
    if "R_AARCH64_RELATIVE" in line:
        parts = line.split()
        # Offset Info Type ... Addend  (addend after 'RELATIVE' or last token)
        try:
            off = int(parts[0], 16)
        except ValueError:
            continue
        # addend is the field after the type; format: <off> <info> R_AARCH64_RELATIVE <addend>
        add = None
        for tok in parts[3:]:
            try:
                add = int(tok, 16)
                break
            except ValueError:
                continue
        if add is not None:
            addends[off] = add

offset_set = set(addends)
found = []
for base in sorted(addends):
    o1, o2 = base + 8, base + 16
    if o1 in offset_set and o2 in offset_set:
        nm = cstr(addends[base])
        sg = cstr(addends[o1])
        fn = addends[o2]
        if nm and sg and sg.startswith("(") and is_text(fn):
            found.append((base, nm, sg, fn))

print("RELATIVE relocs: %d ; candidate JNINativeMethod entries: %d" % (len(addends), len(found)))
print("%-12s %-30s %-46s %s" % ("@slot", "name", "signature", "fn"))
seen = set()
for base, nm, sg, fn in found:
    key = (nm, sg, fn)
    if key in seen:
        continue
    seen.add(key)
    print("0x%08x %-30s %-46s 0x%x" % (base, nm, sg, fn))
print("\ndistinct entries: %d ; distinct fn: %d" %
      (len(seen), len({fn for _, _, _, fn in found})))
