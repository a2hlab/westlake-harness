#!/usr/bin/env python3
# Classify probe_scan.json affected libs into the real SIGILL-probe defect tiers.
# A = deliberate ALWAYS-EL0-illegal sysreg probe (anti-tamper: TRC*/S3_6/7/4/5, impl-def) -> THIS defect's true class.
# B = FEATURE-GATED EL0 read (DIT/SVCR/GCSPR_EL0/RNDR): traps ONLY if the board lacks the feature AND the app mis-gates HWCAP.
# C = udf/brk stub only, no sysreg MRS probe -> unrelated (abort/trap codegen noise).
import json, sys
d=json.load(open("probe_scan.json"))["affected"]
ALWAYS=("TRC","S3_6","S3_7","S3_4","S3_5","S2_","S0_","S1_")
FEAT={"DIT","SVCR","GCSPR_EL0","RNDR","RNDRRS"}
def cls(f):
    regs=[r for r,_ in f["illegal_mrs_regs"]]
    always=[r for r in regs if r.startswith(ALWAYS)]
    feat=[r for r in regs if r in FEAT]
    if f["illegal_mrs_total"]>=20 and always: return "A","anti-tamper sysreg sweep"
    if always: return "A","always-illegal sysreg read"
    if feat or f["rndr"]: return "B","feature-gated ("+("/".join(sorted(set(feat))) or "RNDR")+")"
    return "C","udf/brk stub only"
out={"A":[], "B":[], "C":[]}
for key in d:
    for f in d[key]:
        c,why=cls(f)
        out[c].append({"key":key,"lib":f["lib"],"illegal_mrs":f["illegal_mrs_total"],
                       "top_regs":f["illegal_mrs_regs"][:4],"rndr":f["rndr"],"udf":f["udf"],"why":why})
json.dump(out, open("probe_classified.json","w"), indent=1)
kA=sorted({r["key"] for r in out["A"]}); kB=sorted({r["key"] for r in out["B"]}); kC=sorted({r["key"] for r in out["C"]})
print("CLASS-A keys (true defect class):", kA)
print("CLASS-B keys (feature-gated, latent):", kB)
print("lib counts A/B/C:", len(out["A"]), len(out["B"]), len(out["C"]))
