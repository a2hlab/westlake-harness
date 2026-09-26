#!/usr/bin/env python3
"""Generic: neuter a lib's bytehook/shadowhook hook-INSTALL calls to fake-success.

For a SOURCE-NATIVE-LOAD monitor lib that inline-hooks (and so cannot be stopped
by the shim dlopen-refuse), replace every `bl <hook-install PLT>` with `mov x0,#1`
(d2800020). The lib still loads and initializes (JNI_OnLoad succeeds), but installs
NO inline hook — so it never rewrites hot functions and cannot corrupt musl
mallocng. Same idea as patch_npth_hooks.py, generalized: it locates the PLT stub
for each hook-install import from .rela.plt + the .plt disassembly, then finds and
patches every bl that targets one of those stubs.

usage: patch_hook_installs.py <in.so> <out.so> [--objdump PATH]
"""
import subprocess, sys, re, struct, hashlib

HOOK_IMPORTS = {
    "bytehook_hook_all", "bytehook_hook_single", "bytehook_hook_partial",
    "shadowhook_hook_sym_name", "shadowhook_hook_sym_name_callback",
    "shadowhook_hook_sym_addr", "shadowhook_hook_func_addr",
}
MOV_X0_1 = bytes.fromhex("200080d2")  # mov x0, #1 (LE)

def sh(*a):
    return subprocess.check_output(a, text=True, stderr=subprocess.DEVNULL)

def main():
    args = sys.argv[1:]
    objdump = "llvm-objdump"
    if "--objdump" in args:
        i = args.index("--objdump"); objdump = args[i+1]; del args[i:i+2]
    inf, outf = args[0], args[1]
    data = bytearray(open(inf, "rb").read())

    # 1. hook import -> GOT slot (from .rela.plt JUMP_SLOT)
    got_of = {}
    for line in sh("readelf", "-W", "-r", inf).splitlines():
        if "JUMP_SLOT" in line:
            p = line.split()
            name = p[-1] if p[-1] not in ("+", "0") else p[-3]
            name = name.split("@")[0]
            if name in HOOK_IMPORTS:
                got_of[int(p[0], 16)] = name

    # 2. disassemble; find PLT stubs that reference a hook GOT slot, then bl-> those stubs.
    dis = sh(objdump, "-d", inf)
    # parse "   <addr>: <hex> <mnem> <ops>"
    rows = []
    for line in dis.splitlines():
        m = re.match(r"\s*([0-9a-f]+):\s+([0-9a-f]{8})\s+(\S+)\s*(.*)", line)
        if m:
            rows.append((int(m.group(1), 16), m.group(2), m.group(3), m.group(4)))
    # map stub: scan for adrp x16,#imm ; ldr x17,[x16,#off] ; (br x17) computing a hook GOT addr
    hook_stubs = {}   # stub_entry_addr -> hook name
    for i in range(len(rows) - 1):
        a, hx, mn, op = rows[i]
        if mn == "adrp" and ("x16" in op or "x17" in op):
            mm = re.search(r"(x1[67]),\s*0x([0-9a-f]+)", op)
            if not mm: continue
            page = int(mm.group(2), 16)
            # next ldr x17,[x16,#off]
            for j in range(i+1, min(i+3, len(rows))):
                _, _, mn2, op2 = rows[j]
                mo = re.search(r"ldr\s+x1[67],\s*\[x1[67](?:,\s*#(\d+))?\]", "%s %s" % (mn2, op2))
                if mo:
                    off = int(mo.group(1) or 0)
                    tgt = page + off
                    if tgt in got_of:
                        # stub entry begins at the adrp (or the preceding aligned entry)
                        hook_stubs[a] = got_of[tgt]
                    break
    # a PLT stub is entered at its first insn; bl targets that addr. Also handle the
    # common case where the stub's first insn is the adrp (a==stub entry).
    # 3. find bl -> hook stub, patch
    patched = []
    for a, hx, mn, op in rows:
        if mn != "bl": continue
        mm = re.search(r"0x([0-9a-f]+)", op)
        if not mm: continue
        tgt = int(mm.group(1), 16)
        if tgt in hook_stubs:
            off = a  # file offset == vaddr for .text (verified for these libs)
            if bytes(data[off:off+4]) == bytes.fromhex(hx[6:8]+hx[4:6]+hx[2:4]+hx[0:2]):
                data[off:off+4] = MOV_X0_1
                patched.append((off, hook_stubs[tgt]))

    if not patched:
        print("NO hook-install bl found (lib may call via blr/GOT indirectly) — inspect manually")
    for off, name in patched:
        print("  patched 0x%08x  bl %s -> mov x0,#1" % (off, name))
    open(outf, "wb").write(data)
    print("neutered:", ", ".join(sorted({n for _, n in patched})) or "(none)")
    print("sha256:", hashlib.sha256(data).hexdigest())

if __name__ == "__main__":
    main()
