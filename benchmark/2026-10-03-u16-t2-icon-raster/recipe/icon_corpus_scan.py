import os, re, subprocess, glob, json
import glob as _g
def _find_aapt2():
    import os
    c=sorted(_g.glob(os.path.expanduser("~/Library/Android/sdk/build-tools/*/aapt2")))
    return c[-1] if c else "aapt2"
AAPT2=os.environ.get("AAPT2") or _find_aapt2()
DIRS=["$WORKSPACES/westlake-inputs/apks/fdroid",
      "$WORKSPACES/westlake-inputs/apks/fdroid100",
      "$WORKSPACES/westlake-inputs/corpus-v2/apks"]
def run(a): return subprocess.run(a,capture_output=True,text=True).stdout
rows=[]
for d in DIRS:
    for apk in sorted(glob.glob(os.path.join(d,"*.apk"))):
        b=run([AAPT2,"dump","badging",apk])
        m=re.search(r"application-icon-\d+:'([^']+)'",b) or re.search(r"application:.*icon='([^']+)'",b)
        pkg=re.search(r"package: name='([^']+)'",b)
        pkg=pkg.group(1) if pkg else os.path.basename(apk)
        icon=m.group(1) if m else ""
        if not icon.endswith(".xml"):
            rows.append((pkg,"raster",icon)); continue
        xt=run([AAPT2,"dump","xmltree","--file",icon,apk])
        resdump=None
        if "adaptive-icon" in xt:
            # resolve fg/bg layer file types
            def ref(which):
                mm=re.search(r'E: '+which+r'[^\n]*\n\s*A: [^\n]*android:drawable\([^)]*\)=@(0x[0-9a-f]+)',xt)
                return mm.group(1) if mm else None
            resdump=run([AAPT2,"dump","resources",apk])
            def idfile(h):
                if not h: return None
                mm=re.search(r'resource '+h+r' \S+\n\s*\(\) \(file\) (res/\S+)',resdump); return mm.group(1) if mm else None
            fg=idfile(ref("foreground")); bg=idfile(ref("background"))
            vlayers=[x for x in (fg,bg) if x and x.endswith(".xml")]
            rlayers=[x for x in (fg,bg) if x and not x.endswith(".xml")]
            if vlayers and not rlayers:
                rows.append((pkg,"adaptive-vector-only",icon))   # BENEFICIARY: current installer fails -> placeholder
            elif vlayers and rlayers:
                rows.append((pkg,"adaptive-mixed",icon))         # partial (fg vector / bg raster or vice versa)
            else:
                rows.append((pkg,"adaptive-raster",icon))        # current installer already composes
        elif "<vector" in xt or "vector" in xt.split("\n")[0:3].__str__():
            rows.append((pkg,"plain-vector",icon))               # XML-only vector icon
        else:
            rows.append((pkg,"other-xml",icon))
import collections
c=collections.Counter(r[1] for r in rows)
print("apks scanned:",len(rows))
for k,v in c.most_common(): print(f"  {k}: {v}")
ben=[r for r in rows if r[1] in ("adaptive-vector-only","plain-vector","adaptive-mixed")]
print(f"\nBENEFICIARIES (XML-only/vector icon, current installer -> placeholder) = {len(ben)}")
for pkg,kind,icon in sorted(ben):
    print(f"  {pkg:52} {kind}")
json.dump({"scanned":len(rows),"by_kind":dict(c),"beneficiaries":[r[0] for r in ben]},
          open("$SCRATCH/icon_corpus.json","w"),indent=1)
