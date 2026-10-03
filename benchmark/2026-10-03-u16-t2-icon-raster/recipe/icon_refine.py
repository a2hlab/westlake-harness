import os,re,subprocess,glob,json
import glob as _g
def _find_aapt2():
    import os
    c=sorted(_g.glob(os.path.expanduser("~/Library/Android/sdk/build-tools/*/aapt2")))
    return c[-1] if c else "aapt2"
AAPT2=os.environ.get("AAPT2") or _find_aapt2()
cand=json.load(open("$SCRATCH/icon_corpus.json"))["beneficiaries"]
DIRS=["$WORKSPACES/westlake-inputs/apks/fdroid","$WORKSPACES/westlake-inputs/apks/fdroid100","$WORKSPACES/westlake-inputs/corpus-v2/apks"]
apkfor={}
for d in DIRS:
    for a in glob.glob(os.path.join(d,"*.apk")):
        b=subprocess.run([AAPT2,"dump","badging",a],capture_output=True,text=True).stdout
        m=re.search(r"package: name='([^']+)'",b)
        if m: apkfor.setdefault(m.group(1),a)
def run(x): return subprocess.run(x,capture_output=True,text=True).stdout
true_ben=[]; has_raster=[]
for pkg in cand:
    apk=apkfor.get(pkg)
    if not apk: continue
    # manifest android:icon id
    mani=run([AAPT2,"dump","xmltree","--file","AndroidManifest.xml",apk])
    mm=re.search(r'application[^\n]*\n(?:\s+A:[^\n]*\n)*?\s+A: [^\n]*android:icon\([^)]*\)=@(0x[0-9a-f]+)',mani)
    if not mm:
        mm=re.search(r'android:icon\([^)]*\)=@(0x[0-9a-f]+)',mani)
    if not mm: true_ben.append((pkg,"no-icon-id")); continue
    iid=mm.group(1)
    res=run([AAPT2,"dump","resources",apk])
    # block for resource iid: lines until next 'resource 0x'
    blk=re.search(r'resource '+iid+r' .*?(?=\n\s*resource 0x|\Z)',res,re.S)
    body=blk.group(0) if blk else ""
    files=re.findall(r'\(file\) (res/\S+)',body)
    raster=[f for f in files if f.lower().endswith((".png",".webp",".jpg"))]
    if raster: has_raster.append(pkg)
    else: true_ben.append((pkg, "all-xml:"+",".join(sorted(set(os.path.splitext(f)[1] for f in files)) or ["?"])))
print(f"candidates={len(cand)}  has-raster-config(NOT beneficiary)={len(has_raster)}  TRUE beneficiaries={len(true_ben)}")
print("\n=== TRUE beneficiaries (icon resource has NO raster config in any bucket) ===")
for pkg,info in sorted(true_ben): print(f"  {pkg:52} {info}")
json.dump({"candidates":len(cand),"has_raster":sorted(has_raster),"true_beneficiaries":[p for p,_ in true_ben]},
          open("$SCRATCH/icon_true.json","w"),indent=1)
