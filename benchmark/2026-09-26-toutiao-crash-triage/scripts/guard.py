import re,glob
files=sorted(glob.glob("/tmp/c3/dex/classes*.txt"))
classes=["Lcom/bytedance/crash/jni/NativeBridge;","Lcom/bytedance/crash/resource/NativeResourceMonitor;","Lcom/bytedance/crash/crash/NativeCrashSummary;"]
natives=set()
for f in files:
    L=open(f,errors="replace").read().split("\n")
    cur=None
    for i,l in enumerate(L):
        m=re.search(r"\(in (L[^;]+;)\)",l)
        if m: cur=m.group(1)
        m=re.match(r"\s+name\s+: \x27(.+)\x27",l)
        if m and cur in classes:
            nm=m.group(1); typ=re.match(r"\s+type\s+: \x27(.+)\x27",L[i+1]).group(1); acc=L[i+2]
            if "NATIVE" in acc: natives.add(cur+"."+nm+":"+typ)
print("native methods:",len(natives))
unguarded=[];guarded=0
for f in files:
    L=open(f,errors="replace").read().split("\n")
    start=None
    for i,l in enumerate(L):
        if re.search(r"\|\[[0-9a-f]+\] ",l): start=i
        if "invoke" in l:
            for n in natives:
                if n in l:
                    body="\n".join(L[start:i])
                    if "isSoLoaded" in body: guarded+=1
                    else: unguarded.append((re.search(r"\|\[[0-9a-f]+\] (\S+)",L[start]).group(1), n.split(".")[-1][:40]))
print("guarded call sites:",guarded,"unguarded:",len(unguarded))
for u in sorted(set(unguarded))[:40]: print("  ",u)
