import re,sys,glob,bisect
files=sorted(glob.glob("/tmp/c3/dex/classes*.txt"))
# index methods: per file, list of (lineno, header, addr), and try/catch info
data={}
for f in files:
    lines=open(f,errors="replace").read().split("\n")
    data[f]=lines
def enclosing(lines,n):
    for i in range(n,0,-1):
        m=re.search(r"\|\[([0-9a-f]+)\] (\S+)",lines[i])
        if m: return i,m.group(2)
    return None,None
def tries(lines,start):
    # parse catches block after method start
    res=[];i=start
    while i<len(lines) and "catches" not in lines[i]: i+=1
    j=i+1
    cur=None
    while j<len(lines) and not lines[j].strip().startswith("positions"):
        m=re.match(r"\s+0x([0-9a-f]+) - 0x([0-9a-f]+)",lines[j])
        if m: cur=(int(m.group(1),16),int(m.group(2),16)); 
        elif cur and "->" in lines[j]: res.append((cur,lines[j].strip()))
        j+=1
    return res
target=sys.argv[1]; depth=int(sys.argv[2])
seen=set()
def walk(t,d):
    if d>depth or t in seen: return
    seen.add(t)
    for f,lines in data.items():
        for n,l in enumerate(lines):
            if "invoke" in l and t in l:
                s,name=enclosing(lines,n)
                off=int(re.search(r"\|([0-9a-f]{4}):",l).group(1),16)
                cs=[c for (r,c) in tries(lines,s) if r[0]<=off<r[1]]
                print("  "*d+f"{name} @{off:#x} catches={cs}")
                # convert name to invoke form
                cls,meth=name.rsplit(".",1) if "(" not in name.split(":")[0] else (None,None)
                m=re.match(r"(.+)\.([^.:]+):(.*)",name)
                if m:
                    sig="L"+m.group(1).replace(".","/")+";."+m.group(2)+":"+m.group(3)
                    walk(sig,d+1)
walk(target,0)
