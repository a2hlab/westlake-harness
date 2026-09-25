import re,struct,sys
lib=sys.argv[1]; dis=sys.argv[2]; lo=int(sys.argv[3],16); hi=int(sys.argv[4],16)
f=open(lib,"rb").read()
e=struct.unpack_from("<Q",f,0x20)[0]; n=struct.unpack_from("<H",f,0x38)[0]
loads=[]
for i in range(n):
    t,fl,off,va,pa,fs,ms,al=struct.unpack_from("<IIQQQQQQ",f,e+i*56)
    if t==1: loads.append((va,off,fs))
def s(va):
    for v,o,fs in loads:
        if v<=va<v+fs:
            o2=o+va-v
            end=f.find(b"\0",o2)
            if end<0 or end-o2>100: return None
            r=f[o2:end]
            if len(r)>=3 and all(32<=c<127 for c in r): return r.decode()
    return None
pages={}
for line in open(dis):
    m=re.match(r"\s+([0-9a-f]+):",line)
    if not m: continue
    a=int(m.group(1),16)
    if not (lo<=a<=hi): continue
    out=line.rstrip()
    m=re.search(r"adrp\s+(x\d+), 0x([0-9a-f]+)",line)
    if m: pages[m.group(1)]=int(m.group(2),16)
    m=re.search(r"add\s+(x\d+), (x\d+), #(\d+)",line)
    if m and m.group(2) in pages:
        v=s(pages[m.group(2)]+int(m.group(3)))
        if v: out+="   ; \""+v+"\""
    m=re.search(r"adr\s+(x\d+), #(-?\d+)",line)
    if m:
        v=s(a+int(m.group(2)))
        if v: out+="   ; \""+v+"\""
    if ("bl\t" in line) or ("\"" in out) or re.search(r"\bret\b|blr|b\.\w+|cbn?z|tbn?z",line): print(out)
