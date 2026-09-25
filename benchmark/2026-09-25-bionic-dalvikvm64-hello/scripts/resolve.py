import subprocess, re, os, sys
B="/home/zhaoyue/a2hlab/bionic43"; A="/home/zhaoyue/a2hlab/bionic39/src/arm64-v8a"
RE=A+"/../../ws/toolchains/clang-15/bin/llvm-readelf"
RE="/home/zhaoyue/a2hlab/ws/toolchains/clang-15/bin/llvm-readelf"
STAGE=B+"/stage/lib64"; os.makedirs(STAGE, exist_ok=True)
# index: soname -> list of (img, tag, path)
idx={}
for line in open(B+"/soidx.txt"):
    line=line.strip()
    if not line: continue
    img,rest=line.split("|",1); tag,path=rest.split("/",1); path="/"+path
    so=os.path.basename(path)
    idx.setdefault(so,[]).append((img,tag,path))
BIONIC={"libc.so","libm.so","libdl.so","libdl_android.so","ld-android.so"}
def pick(so):
    c=idx.get(so)
    if not c: return None
    order = ["RT"] if so in BIONIC else ["ART","I18N","SYS","RT"]
    for t in order:
        for img,tag,path in c:
            if tag==t: return (img,tag,path)
    return c[0]
def dump(img,path,out):
    # strip leading /SYS or /ART etc from path back to real image path
    real=path
    for t in ("SYS/","ART/","RT/","I18N/"):
        real=real.replace("/"+t,"/",1) if real.startswith("/"+t) else real
    # path stored as /SYS/system/lib64/x.so etc -> real fs path inside image
    p=path
    for t in ("/SYS","/ART","/RT","/I18N"):
        if p.startswith(t): p=p[len(t):]; break
    subprocess.run(["/usr/sbin/debugfs","-R","dump %s %s"%(p,out),img],capture_output=True)
def needed(f):
    o=subprocess.run([RE,"-d",f],capture_output=True,text=True).stdout
    return re.findall(r"Shared library: \[(.*?)\]",o)
# seed: dalvikvm64 + runtime-dlopened libs
seeds_bin={"dalvikvm64":(B+"/apex/art_payload.img","/bin/dalvikvm64")}
extra=["libopenjdk.so","libjavacore.so","libnativehelper.so","libopenjdkjvm.so","libandroidio.so","libexpat.so","libartpalette-system.so","libicu_jni.so","libandroidicu.so","libart-compiler.so"]
done=set(); missing=set(); q=[]
# stage seed binary
os.makedirs(B+"/stage/bin",exist_ok=True)
dump(seeds_bin["dalvikvm64"][0], seeds_bin["dalvikvm64"][1], B+"/stage/bin/dalvikvm64")
for n in needed(B+"/stage/bin/dalvikvm64"): q.append(n)
q+=extra
while q:
    so=q.pop()
    if so in done: continue
    done.add(so)
    pk=pick(so)
    if not pk: missing.add(so); continue
    out=STAGE+"/"+so
    dump(pk[0],pk[2],out)
    if not os.path.exists(out) or os.path.getsize(out)==0: missing.add(so); continue
    for n in needed(out): 
        if n not in done: q.append(n)
print("staged libs:",len(os.listdir(STAGE)))
print("MISSING:",sorted(missing))
# provenance: tag per lib
prov={}
for so in sorted(os.listdir(STAGE)):
    pk=pick(so); prov[so]=pk[1] if pk else "?"
from collections import Counter
print("by source:",Counter(prov.values()))
open(B+"/stage/lib-provenance.txt","w").write("\n".join(f"{v}  {k}" for k,v in sorted(prov.items())))
