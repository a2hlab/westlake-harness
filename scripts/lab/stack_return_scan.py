"""Find what a runaway thread is recursing through, without an unwinder: read a window of its native stack from
/proc/<pid>/mem as root, keep every 8-byte word that points into an executable mapping (candidate return addresses),
and histogram them by library + offset. A recursion shows as a handful of addresses repeated hundreds of times.
usage: stack_return_scan.py <serial> <pid> <tid> [window_kb=256]
Offsets are printed as vaddr within the library (map start - map file offset + load bias handled via the r--p
mapping at offset 0), ready for llvm-symbolizer --obj=<lib>.
"""
import collections
import struct
import subprocess
import sys

HDC = "/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc"
serial, pid, tid = sys.argv[1], sys.argv[2], sys.argv[3]
window = int(sys.argv[4]) * 1024 if len(sys.argv) > 4 else 256 * 1024


def shell(cmd, binary=False):
    out = subprocess.run([HDC, "-t", serial, "shell", cmd], capture_output=True).stdout
    return out if binary else out.decode("utf-8", "replace").replace("\r", "")


maps, bases = [], {}
for line in shell(f"cat /proc/{pid}/maps").splitlines():
    f = line.split()
    if len(f) < 5:
        continue
    lo, hi = (int(x, 16) for x in f[0].split("-"))
    path = f[5] if len(f) > 5 else ""
    if path and int(f[2], 16) == 0 and path not in bases:
        bases[path] = lo  # load bias: first mapping of the file at offset 0
    if "x" in f[1]:
        maps.append((lo, hi, path))

sc = shell(f"cat /proc/{pid}/task/{tid}/syscall").split()
if len(sc) < 3 or sc[0] == "running":
    sys.exit(f"thread {tid} is running (no sp available): {' '.join(sc)}")
sp = int(sc[-2], 16)
start = sp & ~0xFFF
blocks = window // 4096
raw = shell(f"dd if=/proc/{pid}/mem bs=4096 skip={start // 4096} count={blocks} 2>/dev/null | od -An -v -tx8 -w8",
            binary=False)
words = [int(w, 16) for w in raw.split()]
hist = collections.Counter()
for w in words:
    for lo, hi, path in maps:
        if lo <= w < hi:
            base = bases.get(path, lo)
            hist[(path.rsplit("/", 1)[-1] or "[anon-exec]", w - base)] += 1
            break
print(f"thread {tid} sp=0x{sp:x} scanned {len(words) * 8 // 1024} KB, {sum(hist.values())} code pointers")
for (lib, off), n in hist.most_common(25):
    print(f"{n:6d}  {lib}  0x{off:x}")
