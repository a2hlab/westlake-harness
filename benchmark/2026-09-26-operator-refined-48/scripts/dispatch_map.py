import re, collections
from androguard.core.apk import APK
try:
    from androguard.core.dex import DEX
except Exception:
    from androguard.core.bytecodes.dvm import DalvikVMFormat as DEX
apk="/Users/zhaoyue/OrbStack/a2hlab/home/zhaoyue/a2hlab/app-inputs/toutiao/toutiao.apk"
a=APK(apk)

def first_reg(out):
    # "v6 ... v11, L..."  or  "v0, v1, v2, L..."
    head=out.split(", L")[0]
    m=re.search(r'v(\d+)', head)
    return "v"+m.group(1) if m else None

def parse_const(out):
    # "v6, 67108866"  (may be negative/hex)
    m=re.match(r'\s*v(\d+),\s*(-?\d+)', out)
    if m: return "v"+m.group(1), int(m.group(2)) & 0xffffffff
    return None,None

cmd_ret=collections.defaultdict(collections.Counter)
cmd_examples=collections.defaultdict(list)
total=0
for db in a.get_all_dex():
    d=DEX(db)
    for cls in d.get_classes():
        for m in cls.get_methods():
            try: ins=list(m.get_instructions())
            except Exception: continue
            if not ins: continue
            arr=[(i.get_name(), i.get_output()) for i in ins]
            for idx,(nm,out) in enumerate(arr):
                if nm.startswith("invoke") and "Lms/bd/c/m;->a(" in out:
                    total+=1
                    arg0=first_reg(out)
                    cmd=None
                    for j in range(idx-1, max(0,idx-14), -1):
                        pn,po=arr[j]
                        if pn.startswith("const"):
                            r,v=parse_const(po)
                            if r==arg0:
                                cmd=v; break
                    # return usage
                    ret="?"
                    if idx+1<len(arr) and arr[idx+1][0]=="move-result-object":
                        rr=re.match(r'\s*v(\d+)', arr[idx+1][1])
                        rreg="v"+rr.group(1) if rr else None
                        if idx+2<len(arr):
                            n2,o2=arr[idx+2]
                            if n2=="check-cast":
                                mt=re.search(r'(L[\w/$]+;|\[[\w/$;\[]+)', o2)
                                ret=mt.group(1) if mt else o2
                            elif n2.startswith("if-"):
                                ret="Object(null-checked)"
                            else:
                                ret="obj:"+n2
                    elif idx+1<len(arr) and arr[idx+1][0]=="move-result":
                        ret="prim(move-result)"
                    else:
                        ret="ignored"
                    key = cmd
                    cmd_ret[key][ret]+=1
                    if len(cmd_examples[key])<2:
                        cmd_examples[key].append("%s->%s"%(cls.get_name(),m.get_name()))
print("total call sites:", total, " distinct cmd:", len(cmd_ret))
print("\n== cmd (hex) : high-byte : return-type counts : example caller")
for cmd in sorted(k for k in cmd_ret if k is not None):
    hi = (cmd>>24)&0xff
    rets=", ".join("%s×%d"%(t,c) for t,c in cmd_ret[cmd].most_common())
    print("0x%08x  hi=0x%02x  {%s}  e.g. %s" % (cmd, hi, rets, cmd_examples[cmd][0]))
if None in cmd_ret:
    print("\n(unresolved cmd const):", dict(cmd_ret[None]))
# aggregate by high byte
print("\n== by high byte ==")
byhi=collections.defaultdict(collections.Counter)
for cmd,cnt in cmd_ret.items():
    if cmd is None: continue
    for t,c in cnt.items(): byhi[(cmd>>24)&0xff][t]+=c
for hi in sorted(byhi):
    print("hi=0x%02x : %s"%(hi, ", ".join("%s×%d"%(t,c) for t,c in byhi[hi].most_common())))
