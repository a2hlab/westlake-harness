#!/usr/bin/env python3
# Scan the U11-native per-key APK native corpus for "SIGILL/SIGSEGV-guarded probe" libs:
# a lib that (a) imports a signal-handler installer AND (b) contains probe instructions
# (mrs of EL0-illegal system registers, rndr/rndrrs, PAC sign/auth, udf/brk).
# Output: per-key affected libs + a JSON. Deterministic, offline, no board.
import os, re, subprocess, json, sys
from pathlib import Path

# WORKSPACES-anchored (no user-bound absolute path): script is <WS>/westlake-harness-t3/benchmark/<d>/probe_scan.py
WS = Path(__file__).resolve().parents[3]
ROOT = WS/"westlake-harness-bms"/"benchmark"/"2026-10-01-u11-native"/".artifacts"
SCAN_DIRS = [ROOT/"window-r3-scan"/"consumers", ROOT/"window-r2-scan"/"consumers", ROOT/"window-r1-scan"/"consumers"]

HANDLER_IMPORTS = re.compile(r'\b(sigaction|bsd_signal|sigprocmask|sigaltstack)\b|\bU signal\b')
# EL0-legal regs readable from userspace (trap-emulated or genuinely EL0): do NOT flag these
EL0_OK = {"CNTVCT_EL0","CNTVCTSS_EL0","CNTFRQ_EL0","CNTPCT_EL0","TPIDR_EL0","TPIDRRO_EL0",
          "DCZID_EL0","CTR_EL0","MIDR_EL1","MPIDR_EL1","REVIDR_EL1","NZCV","FPCR","FPSR",
          "DAIF","TPIDR2_EL0","RNDR","RNDRRS","PMCCNTR_EL0","PMUSERENR_EL0","FPMR","SSBS"}
MRS = re.compile(r'\bmrs\b\s+\w+,\s*([A-Za-z0-9_]+)', re.I)
RNDR = re.compile(r'\bmrs\b\s+\w+,\s*(RNDR|RNDRRS)\b', re.I)
PAC = re.compile(r'\b(paci[ab]?z?|pacd[ab]|pacga|auti[ab]|autd[ab]|xpaci?d?)\b', re.I)
UDF = re.compile(r'\budf\b')

def sh(args):
    try: return subprocess.run(args, capture_output=True, text=True, timeout=120).stdout
    except Exception: return ""

def handler_imports(so):
    out = sh(["llvm-nm","-Du",str(so)])
    hits=set()
    for ln in out.splitlines():
        if " U " not in ln: continue
        m=re.search(r'U (\w+)', ln)
        if m and re.search(r'^(sigaction|bsd_signal|sigprocmask|sigaltstack|signal)$', m.group(1)):
            hits.add(m.group(1))
    return sorted(hits)

def probes(so):
    out = sh(["llvm-objdump","-d",str(so)])
    illegal_mrs={}; rndr=0; pac=0; udf=0
    for ln in out.splitlines():
        if RNDR.search(ln): rndr+=1; continue
        m=MRS.search(ln)
        if m:
            reg=m.group(1).upper()
            if reg not in EL0_OK and not reg.startswith("ID_") and not reg.startswith("MIDR"):
                # S3_*, TRC*, DBG*, PMxxx(EL1), impl-def -> EL0-illegal from a bionic app
                illegal_mrs[reg]=illegal_mrs.get(reg,0)+1
            continue
        if PAC.search(ln): pac+=1
        if UDF.search(ln): udf+=1
    top=sorted(illegal_mrs.items(), key=lambda x:-x[1])[:8]
    return {"illegal_mrs_total":sum(illegal_mrs.values()),"illegal_mrs_regs":top,"rndr":rndr,"pac":pac,"udf":udf}

# dedup by (key, soname) preferring r3>r2>r1
seen=set(); libs=[]
for d in SCAN_DIRS:
    if not d.is_dir(): continue
    for so in d.rglob("*.so"):
        parts=so.relative_to(d).parts
        key=parts[0]
        name=so.name
        if (key,name) in seen: continue
        seen.add((key,name)); libs.append((key,name,so))

print(f"corpus: {len(libs)} unique (key,lib) across {len(seen)} ; scanning handler imports...", file=sys.stderr)
# stage1: handler filter
hcand=[]
for key,name,so in libs:
    h=handler_imports(so)
    if h: hcand.append((key,name,so,h))
print(f"stage1: {len(hcand)} libs install a signal handler", file=sys.stderr)

# stage2: disasm handler-installing libs for probes
affected={}  # key -> list of lib findings
for key,name,so,h in hcand:
    p=probes(so)
    is_probe = p["illegal_mrs_total"]>0 or p["rndr"]>0 or p["udf"]>0
    if is_probe:
        affected.setdefault(key,[]).append({"lib":name,"handlers":h, **p})

out={"corpus_libs":len(libs),"handler_installing":len(hcand),"probe_and_handler_keys":len(affected),"affected":affected}
json.dump(out, open("probe_scan.json","w"), indent=1)
# human summary
print("\n=== keys with (signal-handler install + probe instruction) ===")
for key in sorted(affected):
    for f in affected[key]:
        regs=",".join(f"{r}×{c}" for r,c in f["illegal_mrs_regs"][:4])
        print(f"{key:40s} {f['lib']:28s} h={'+'.join(f['handlers'])} illMRS={f['illegal_mrs_total']}({regs}) rndr={f['rndr']} pac={f['pac']} udf={f['udf']}")
