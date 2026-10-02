#!/usr/bin/env python3
"""Wall-2: reproduce the U13 libicuuc.so (f74827d9) and add the 7 _74 aliases tttext dlsyms, in THIS dir.

Mirrors benchmark/2026-10-03-u13-compat-ctype/build.py (read-only recipe + frozen objects in westlake-harness-bms),
but writes all outputs to ./.artifacts here -- never into cx-bms's worktree. The ctype_compat.o compile uses
-ffile-prefix-map=<bms repo>=. (as the recipe does), so building it from bms's read-only source reproduces byte-for-byte
regardless of our output dir. f74827d9 = PRIOR's 10 frozen ICU .o + ctype_compat.o + a version-map (baseline exports +
_ctype_). Our candidate = that + 7 linker aliases <sym>_74=<sym>_72 and the 7 names added to the version-map.

    wall2_build.py          # reproduce b2 (OLD) and f74827d9 (gates), then build the +_74 candidate; nm -D diff
"""
import hashlib, json, subprocess, sys
from pathlib import Path

WS = Path(__import__("os").environ.get("WORKSPACES") or Path(__file__).resolve().parents[4])
BMS = WS / "westlake-harness-bms"
SDK = Path("/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native")
CT = BMS / "benchmark/2026-10-03-u13-compat-ctype"                 # read-only recipe dir
PRIOR = BMS / "benchmark/2026-10-02-u12-vlc-bionic-residue"        # read-only frozen .o + link
HERE = Path(__file__).resolve().parent.parent
ART = HERE / ".artifacts"
OLD = "b2be657ca2c171dd786068e77be90d82ec3a50407df37b1ccbafef94a8db88a6"           # b2 baseline
F74 = "f74827d992d25ffe481873f1b7f4416d97820c443f16bd715102455dbafbcf6f"           # U13 deployed libicuuc.so
ALIASES = ["ubrk_open", "ubrk_close", "ubrk_first", "ubrk_next", "ubrk_setText", "u_charType", "u_hasBinaryProperty"]


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def exp(v): return v.replace("$REPO", str(BMS)).replace("$WORKSPACES", str(WS)).replace("$OHOS_SDK", str(SDK))
def run(cmd):
    r = subprocess.run([str(x) for x in cmd], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"FAIL: {' '.join(map(str,cmd))[:200]}\n{r.stdout}{r.stderr}")


def main():
    ART.mkdir(exist_ok=True)
    link = [exp(v) for v in json.loads((PRIOR / "build-receipt.json").read_text())["commands"][2]["command"]]
    compiler = Path(link[0])
    # --- gate 1: reproduce b2 baseline (relink PRIOR .o + PRIOR map) ---
    base = ART / "icu-baseline.so"
    cmd = list(link); cmd[cmd.index("-o") + 1] = str(base)
    run(cmd)
    print("b2 baseline:", sha(base)[:16], "==OLD" if sha(base) == OLD else "!! MISMATCH")
    if sha(base) != OLD:
        sys.exit("FAIL b2 gate")
    # --- ctype_compat.o (byte-faithful via -ffile-prefix-map=BMS=.) ---
    obj = ART / "ctype_compat.o"
    run([compiler, "--target=aarch64-linux-ohos", "--sysroot=" + str(SDK / "sysroot"), "-std=c11", "-O2", "-g",
         "-fPIC", "-ffile-prefix-map=" + str(BMS) + "=.", "-I" + str(CT / "inputs/shim"),
         "-I" + str(CT / "inputs/aosp/libc/upstream-openbsd/lib/libc/include"), "-c", CT / "ctype_compat.c", "-o", obj])
    # --- gate 2: reproduce f74827d9 (baseline exports + _ctype_ map + ctype_compat.o) ---
    names = subprocess.check_output(["llvm-nm", "-D", "--defined-only", "--format=just-symbols", base], text=True).split()
    f74map = ART / "f74.map"
    f74map.write_text("{ global: " + "; ".join(sorted(set(names + ["_ctype_"]))) + "; local: *; };\n")
    f74so = ART / "icu-f74.so"
    cmd = ["-Wl,--version-script=" + str(f74map) if v.startswith("-Wl,--version-script=") else v for v in link]
    cmd[cmd.index("-o") + 1] = str(f74so); cmd.append(str(obj))
    run(cmd)
    print("f74 reproduce:", sha(f74so)[:16], "==f74827d9" if sha(f74so) == F74 else "!! MISMATCH")
    # --- candidate: + 7 _74 aliases (--defsym) + the 7 names in the map ---
    a74 = [f"{s}_74" for s in ALIASES]
    cmap = ART / "candidate.map"
    cmap.write_text("{ global: " + "; ".join(sorted(set(names + ["_ctype_"] + a74))) + "; local: *; };\n")
    for rep in (1, 2):
        cand = ART / f"libicuuc-u14-{rep}.so"
        cmd = ["-Wl,--version-script=" + str(cmap) if v.startswith("-Wl,--version-script=") else v for v in link]
        cmd[cmd.index("-o") + 1] = str(cand); cmd.append(str(obj))
        for s in ALIASES:
            cmd.append(f"-Wl,--defsym,{s}_74={s}_72")
        run(cmd)
        print(f"candidate{rep}:", sha(cand)[:16])
    c1, c2 = sha(ART / "libicuuc-u14-1.so"), sha(ART / "libicuuc-u14-2.so")
    if c1 != c2:
        sys.exit("FAIL candidate not self-deterministic")
    print("candidate x2 identical:", c1[:16])
    # --- nm -D diff: candidate vs f74827d9 should add ONLY the 7 _74 names ---
    def exports(p): return set(subprocess.check_output(["llvm-nm", "-D", "--defined-only", "--format=just-symbols", p], text=True).split())
    base_exp = exports(f74so) if sha(f74so) == F74 else exports(ART / "icu-f74.so")
    cand_exp = exports(ART / "libicuuc-u14-1.so")
    added = sorted(cand_exp - base_exp); removed = sorted(base_exp - cand_exp)
    print("nm -D added:", added)
    print("nm -D removed:", removed)
    ok = set(added) == set(a74) and not removed
    print("ACCEPT" if ok else "REVIEW", "-- added == the 7 _74 aliases and nothing removed:", ok)


if __name__ == "__main__":
    main()
