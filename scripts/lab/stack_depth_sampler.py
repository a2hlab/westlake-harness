"""Sample every thread's native stack depth of one board process, to tell stack exhaustion by a growing
thread from a fault inside a shallow stack. Reads only /proc as root: task/<tid>/syscall carries the thread's
stack pointer when it is blocked (second-to-last field), maps gives the enclosing rw mapping (its top is
the stack base). depth = mapping_end - sp.
usage: stack_depth_sampler.py <serial> <pid> <seconds> <interval>
"""
import subprocess
import sys
import time

HDC = "/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc"
serial, pid, seconds, interval = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])


def shell(cmd):
    return subprocess.run([HDC, "-t", serial, "shell", cmd], capture_output=True).stdout.decode(
        "utf-8", "replace").replace("\r", "")


def sample():
    maps = []
    for line in shell(f"cat /proc/{pid}/maps").splitlines():
        rng, perms = line.split()[:2]
        lo, hi = (int(x, 16) for x in rng.split("-"))
        if perms.startswith("rw"):
            maps.append((lo, hi))
    out = shell(f"for t in /proc/{pid}/task/*; do echo \"$(basename $t) $(cat $t/comm) :: $(cat $t/syscall)\"; done")
    rows = []
    for line in out.splitlines():
        if "::" not in line:
            continue
        head, sc = line.split("::", 1)
        tid, name = head.split(None, 1)[0], head.split(None, 1)[1].strip() if len(head.split(None, 1)) > 1 else "?"
        f = sc.split()
        if len(f) < 3 or f[0] == "running":
            continue
        try:
            sp = int(f[-2], 16)
        except ValueError:
            continue
        region = next(((lo, hi) for lo, hi in maps if lo <= sp < hi), None)
        if region:
            rows.append((region[1] - sp, region[1] - region[0], tid, name))
    return sorted(rows, reverse=True)


start = time.time()
while time.time() - start < seconds:
    alive = shell(f"[ -d /proc/{pid} ] && echo 1").strip() == "1"
    if not alive:
        print(f"t={int(time.time() - start)}s process gone")
        break
    rows = sample()
    top = rows[:3]
    print(f"t={int(time.time() - start):3d}s threads={len(rows)} deepest: " +
          " | ".join(f"{name}[{tid}] {depth // 1024}KB/{size // 1048576}MB" for depth, size, tid, name in top), flush=True)
    time.sleep(interval)
