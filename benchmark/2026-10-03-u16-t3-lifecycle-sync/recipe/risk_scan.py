import os, re, glob
import os as _os
WS=_os.environ.get("WORKSPACES", _os.path.expanduser("~/orca/workspaces"))
SA=f"{WS}/westlake-harness-u7-executor/benchmark/2026-10-03-u13-stage-a-plan"
# lit keys from u13-reference (verdict=lit on any board)
lit=set()
for b in ("5cd","5ea","61b"):
    f=f"{WS}/westlake-harness/benchmark/2026-10-03-u13-reference/u13-ref-{b}.txt"
    if not os.path.exists(f): continue
    for ln in open(f):
        if ln.startswith("row ") and "verdict=lit" in ln:
            lit.add(ln.split()[4])
# index stage-A hilogs by key
hil={}
for h in glob.glob(f"{SA}/**/hilog.txt", recursive=True):
    k=h.split("/")[-2]
    hil.setdefault(k, h)  # first run per key

PC=re.compile(r'performCreate')
RES=re.compile(r'handleResumeActivity|performResume|RESUMED\+300ms|dispatchByActivityTokenOnMainLooper.*RESUMED|ClientTransaction scheduled.*RESUMED|state=.*-> RESUMED')
def cols(line):
    m=re.match(r'\S+\s+\S+\s+(\d+)\s+(\d+)\s+[A-Z]\s+(\S+):', line)
    return m  # m.group(1)=pid m.group(2)=tid m.group(3)=tag

def scan(h):
    try: lines=open(h,errors='replace').read().splitlines()
    except: return None
    pc=res=None
    for i,l in enumerate(lines):
        if pc is None and PC.search(l): pc=i
        elif pc is not None and res is None and RES.search(l): res=i; break
    if pc is None: return ("no-performCreate",0)
    if res is None: return ("no-resume-marker",0)
    # main-thread app lines in the gap (pid==tid), excluding pure OH-adapter infra tags
    gap=lines[pc+1:res]
    app_main=0; stderr_main=0
    for l in gap:
        m=cols(l)
        if not m: continue
        pid,tid,tag=m.group(1),m.group(2),m.group(3)
        if pid!=tid: continue  # not main thread
        # app signal: [stderr] relayed app output, or a non-adapter tag
        if '[stderr]' in l and 'AppSpawnXJava' in tag:
            stderr_main+=1
        elif not re.search(r'C0[0-9a-f]{4}/(OH_|AppSpawnX|AppSpawn|AMS|WMS|WindowManager|Arkui|AbilityManager)', l) \
             and not tag.startswith('C01') and not tag.startswith('C04') and not tag.startswith('A04'):
            app_main+=1
    return ("gap", stderr_main, app_main, res-pc)

rows=[]
for k in sorted(lit):
    h=hil.get(k)
    if not h: continue  # lit key that didn't run in stage-A
    r=scan(h)
    if r is None: continue
    rows.append((k,)+r)

ran=[r for r in rows]
print(f"lit keys total={len(lit)} ; with a stage-A hilog={len(ran)}")
# calibrate: breezyweather (dead, not lit) for reference
bw=hil.get("fd-breezyweather")
if bw: print("CALIBRATION fd-breezyweather(dead):", scan(bw))
gapped=[r for r in ran if r[1]=="gap"]
risk=[r for r in gapped if (r[2]>0 or r[3]>0)]
print(f"lit keys with performCreate+resume window measured={len(gapped)}")
print(f"RISK SET (main-thread app work in the onCreate->RESUMED gap)={len(risk)}")
print("\n=== risk-set keys (key, stderr_main_lines, app_main_lines, gap_lines) ===")
for k,tag,sm,am,gl in sorted(risk, key=lambda x:-(x[2]+x[3])):
    print(f"  {k:46} stderr_main={sm:3d} app_main={am:3d} gap_lines={gl}")
import json
json.dump({"lit_total":len(lit),"lit_with_hilog":len(ran),"measured":len(gapped),
           "risk_set":[r[0] for r in risk]},
          open("/tmp/risk.json","w"),indent=1)
