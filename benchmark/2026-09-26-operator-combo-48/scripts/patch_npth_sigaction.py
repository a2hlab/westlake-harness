#!/usr/bin/env python3
"""#48 r5 fix: neuter libnpth's sigaction calls that pass a non-NULL `old`.

r5 root cause: musl's `struct sigaction` is 152 bytes (sigset_t = 128 B / 1024
signals) vs Bionic's ~40 (sigset_t 8 B). When libnpth (Bionic ABI) calls
sigaction(sig, act, old) with a non-NULL `old` pointing at a Bionic-sized buffer,
musl writes its full 152-byte struct there and overruns the buffer; if that buffer
sits within 152 B of a page boundary the write hits a read-only page ->
SEGV_ACCERR (board pure-r5: npth-worker, musl sigaction+0x1a4 `str x8,[x19,#144]`,
si_addr page-aligned). The slot-array loop that saves many old handlers into
fixed-size slots is the worst offender.

Fix: for every `bl sigaction` whose `old` (x2) is NOT xzr, replace the bl with
`mov x0, #0` (a fake success — real sigaction returns 0 on success). The call is
skipped entirely: musl never writes the oversized `old`, so no overrun; the base
register that carries the slot pointer is untouched (unlike patching x2, which
would break the `add x2, x2, #off` chain). Calls with old=NULL are left alone —
they install their handler harmlessly (musl writes no `old`). npth loses only the
saved-old / chaining for the neutered calls; its crash catching is redundant with
the westlake recorder (out-crash42), and no handler runs after a skipped install.

Stacks on the hook-neutered libnpth (4f7cc3a6), which itself stacks on class-3
(8b8d559c). usage: patch_npth_sigaction.py <in.so> <out.so> [--objdump PATH]
"""
import subprocess, sys, re, hashlib

MOV_X0_0 = bytes.fromhex("000080d2")  # mov x0, #0  (movz x0,#0) LE

def main():
    args = sys.argv[1:]
    objdump = "llvm-objdump"
    if "--objdump" in args:
        i = args.index("--objdump"); objdump = args[i+1]; del args[i:i+2]
    inf, outf = args[0], args[1]
    data = bytearray(open(inf, "rb").read())
    dis = subprocess.check_output([objdump, "-d", inf], text=True, stderr=subprocess.DEVNULL)
    rows = []
    for l in dis.splitlines():
        m = re.match(r"\s*([0-9a-f]+):\s+([0-9a-f]{8})\s+(\S+)\s*(.*)", l)
        if m:
            rows.append((int(m.group(1), 16), m.group(2), m.group(3), m.group(4)))
    idx = {a: i for i, (a, *_ ) in enumerate(rows)}

    patched, skipped_null = [], 0
    for a, hx, mn, op in rows:
        if mn != "bl" or "<sigaction" not in op:
            continue
        i = idx[a]
        # find the last writer of x2 (the `old` arg) in the preceding window
        x2_null = None
        for j in range(i - 1, max(0, i - 9), -1):
            _, _, mn2, op2 = rows[j]
            head = op2.split(",")[0].strip()
            if re.match(r"(mov|add|sub|orr|ldr|adr|adrp)$", mn2) and head in ("x2", "w2"):
                x2_null = ("xzr" in op2 or "wzr" in op2)
                break
        if x2_null is True:
            skipped_null += 1
            continue
        # non-NULL old (or unresolved -> treat as non-NULL, conservative) -> neuter
        le = bytes.fromhex(hx[6:8] + hx[4:6] + hx[2:4] + hx[0:2])
        if bytes(data[a:a + 4]) == le:
            data[a:a + 4] = MOV_X0_0
            patched.append(a)

    for a in patched:
        print("  patched 0x%08x  bl sigaction(non-NULL old) -> mov x0,#0" % a)
    print("neutered non-NULL-old sigaction calls: %d ; left old=NULL calls: %d"
          % (len(patched), skipped_null))
    open(outf, "wb").write(data)
    print("sha256:", hashlib.sha256(data).hexdigest())

if __name__ == "__main__":
    main()
