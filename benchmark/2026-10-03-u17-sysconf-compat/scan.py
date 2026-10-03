#!/usr/bin/env python3
"""U17 sysconf-compat corpus scanner (cc-t3): find every app-native sysconf import + the constant each call site passes.

    scan.py <corpus_dir> [--out <dir>]

corpus_dir holds <key>/lib/arm64-v8a/*.so (the fd app corpus; path is a lab input, NOT hardcoded). For each arm64 .so
that imports sysconf (dynsym UND), disassemble, find every `bl` to the sysconf PLT stub, and backtrack <=12 instructions
for the w0 immediate (mov/movz w0,#imm). Indirect/unresolved -> "unknown". Classify each constant against the bionic _SC_*
table (what the app meant) vs what OH musl interprets it as, flag divergence. Emits sysconf-scan.json + sysconf-scan.csv.

Tables are source-verified (see README / evidence): bionic NDK23 bits/sysconf.h, OH musl usr/include/unistd.h.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

# bionic _SC_* : number -> name (NDK 23 bits/sysconf.h, hex values). Only the numbers we need to interpret app calls.
BIONIC = {
    0x00: "_SC_ARG_MAX", 0x06: "_SC_CLK_TCK", 0x07: "_SC_COLL_WEIGHTS_MAX", 0x0b: "_SC_OPEN_MAX",
    0x27: "_SC_PAGESIZE", 0x28: "_SC_PAGE_SIZE", 0x60: "_SC_NPROCESSORS_CONF", 0x61: "_SC_NPROCESSORS_ONLN",
    0x62: "_SC_PHYS_PAGES", 0x63: "_SC_AVPHYS_PAGES", 0x064: "_SC_MONOTONIC_CLOCK", 0x6e: "_SC_CPUTIME",
}
# OH musl : number -> name (usr/include/unistd.h). Used to show what musl RETURNS for a bionic number.
MUSL = {
    0: "_SC_ARG_MAX", 2: "_SC_CLK_TCK", 30: "_SC_PAGESIZE/_SC_PAGE_SIZE", 38: "_SC_BC_SCALE_MAX",
    39: "_SC_BC_STRING_MAX(=1000)", 40: "_SC_COLL_WEIGHTS_MAX", 83: "_SC_NPROCESSORS_CONF",
    84: "_SC_NPROCESSORS_ONLN", 85: "_SC_PHYS_PAGES", 96: "(musl: unassigned/other)",
    97: "(musl: unassigned/other)", 6: "(musl: _SC_2_C_* region)",
}
# The musl number that MATCHES the bionic selector's MEANING (for the remap table). None = no safe mapping needed/known.
BIONIC_TO_MUSL = {0x27: 30, 0x28: 30, 0x60: 83, 0x61: 84, 0x62: 85, 0x06: 2, 0x00: 0, 0x07: 40}
SIZE_CAP_MB = 12              # libs larger than this are recorded upper-bound-only (full disasm too slow in-window)
FATAL = {0x27, 0x28}          # page size: wrong value -> allocator/mmap crash
SIGNIFICANT = {0x27, 0x28, 0x60, 0x61, 0x62}  # value actually used for sizing/parallelism


def tool(*names):
    for n in names:
        if subprocess.run(["which", n], capture_output=True).returncode == 0:
            return n
    return names[0]


NM = tool("llvm-nm", "nm")
OBJDUMP = tool("llvm-objdump", "objdump")


def imports_sysconf(so):
    try:
        out = subprocess.run([NM, "-Du", str(so)], capture_output=True, text=True, timeout=120).stdout
    except Exception:
        return False
    return bool(re.search(r"\bU\s+sysconf\b", out))


def scan_so(so):
    """Return list of {pc, const, const_hex, bionic, musl_as, significant, fatal} for each sysconf call site."""
    try:
        dis = subprocess.run([OBJDUMP, "-d", str(so)], capture_output=True, text=True, timeout=600).stdout
    except Exception:
        return [{"pc": "?", "const": None, "note": "objdump failed"}]
    lines = dis.splitlines()
    # find the sysconf PLT stub target(s): a label line like "0000.. <sysconf@plt>:" or "<sysconf>:"
    plt_addrs = set()
    for ln in lines:
        m = re.match(r"^([0-9a-f]+)\s+<sysconf(@plt)?>:", ln)
        if m:
            plt_addrs.add(m.group(1).lstrip("0") or "0")
    results = []
    insn = []  # (addr, text)
    for ln in lines:
        m = re.match(r"^\s+([0-9a-f]+):\s+[0-9a-f ]+\t(.*)$", ln)
        if m:
            insn.append((m.group(1).lstrip("0") or "0", m.group(2).strip()))
    # index bl -> sysconf
    for i, (addr, text) in enumerate(insn):
        mb = re.match(r"bl\s+0x([0-9a-f]+)\s+<sysconf(@plt)?>", text) or re.match(r"bl\s+0x([0-9a-f]+)", text)
        is_sysconf = "<sysconf" in text and text.startswith("bl")
        if not is_sysconf:
            continue
        const = None
        for j in range(i - 1, max(-1, i - 13), -1):
            t = insn[j][1]
            mm = re.match(r"mov\s+w0,\s+#(-?0x[0-9a-f]+|-?\d+)", t) or re.match(r"movz\s+w0,\s+#(0x[0-9a-f]+|\d+)", t)
            if mm:
                const = int(mm.group(1), 0)
                break
            # w0 clobbered by something else first -> can't attribute
            if re.match(r"(mov|movz|movn|ldr|add|sub|and|orr)\s+w0,", t) or re.match(r"bl\s+", t):
                break
        row = {"pc": "0x" + addr}
        if const is None:
            row.update({"const": None, "note": "unknown (indirect/clobbered)"})
        else:
            c = const & 0xffffffff
            row.update({
                "const": c, "const_hex": hex(c), "bionic": BIONIC.get(c, "(bionic: other/" + hex(c) + ")"),
                "musl_interprets_as": MUSL.get(c, "(musl: other/" + str(c) + ")"),
                "remap_to_musl": BIONIC_TO_MUSL.get(c),
                "significant": c in SIGNIFICANT, "fatal": c in FATAL,
            })
        results.append(row)
    return results


def main():
    if len(sys.argv) < 2:
        print("usage: scan.py <corpus_dir> [--out <dir>]"); sys.exit(2)
    corpus = Path(sys.argv[1])
    out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else Path(__file__).resolve().parent / "evidence"
    out.mkdir(parents=True, exist_ok=True)
    report = {}
    for keydir in sorted(corpus.iterdir()):
        libdir = keydir / "lib" / "arm64-v8a"
        if not libdir.is_dir():
            continue
        for so in sorted(libdir.glob("*.so")):
            if not imports_sysconf(so):
                continue
            size_mb = so.stat().st_size / (1024 * 1024)
            if size_mb > SIZE_CAP_MB:
                # upper-bound-only: too large for a full static disasm in-window; sysconf import counted, constants unscanned
                sites = [{"pc": "?", "const": None, "note": "unscanned (lib %.0fMB > %dMB cap)" % (size_mb, SIZE_CAP_MB),
                          "size_mb": round(size_mb, 1)}]
            else:
                sites = scan_so(so)
            report.setdefault(keydir.name, {})[so.name] = sites
    # summary
    affected = {}  # key -> set of significant/fatal consts
    for key, libs in report.items():
        for lib, sites in libs.items():
            for s in sites:
                if s.get("significant"):
                    affected.setdefault(key, set()).add(s["const_hex"])
    summary = {
        "corpus": str(corpus),
        "keys_scanned_with_sysconf_import": len(report),
        "keys_with_significant_const": sorted(affected.keys()),
        "keys_with_page_size_const": sorted(k for k, libs in report.items()
                                            for lib, sites in libs.items() for s in sites if s.get("fatal")),
        "tool": {"nm": NM, "objdump": OBJDUMP},
    }
    (out / "sysconf-scan.json").write_text(json.dumps({"summary": summary, "by_key": report,
                                                       "affected": {k: sorted(v) for k, v in affected.items()}},
                                                      indent=1))
    rows = ["key,lib,pc,const_hex,bionic,musl_interprets_as,remap_to_musl,significant,fatal"]
    for key, libs in sorted(report.items()):
        for lib, sites in sorted(libs.items()):
            for s in sites:
                rows.append(",".join(str(x) for x in [key, lib, s["pc"], s.get("const_hex", ""), s.get("bionic", s.get("note", "")),
                                                      s.get("musl_interprets_as", ""), s.get("remap_to_musl", ""),
                                                      s.get("significant", ""), s.get("fatal", "")]))
    (out / "sysconf-scan.csv").write_text("\n".join(rows) + "\n")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
