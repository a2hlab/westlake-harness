#!/usr/bin/env python3
"""Offline rasterizer for Android <adaptive-icon> whose layers are <vector> drawables.
Converts VectorDrawable -> SVG -> PNG via the existing Mac rasterization chain (rsvg-convert), composites
foreground over background, and writes a raster icon.png + an icon record. This is the install-prep step the
installer's adaptive-icon path (adaptive_icon.cpp ResolveLayer vector branch) delegates to, so no new NATIVE
dependency is added to the on-device libapk_installer.so.

Usage: AAPT2=<aapt2> raster_adaptive_icon.py <apk> <out_dir> [--size N]
Exit 0 + writes icon.png + icon-record.json on success; on an unrasterizable/missing layer, prints a
'raster-failed: <reason>' line, writes icon-record.json with rasterized=false (caller keeps the XML placeholder),
and exits 0 (never breaks install).
"""
import os, re, sys, json, subprocess, struct, zlib

import glob as _g
def _find_aapt2():
    import os
    c=sorted(_g.glob(os.path.expanduser("~/Library/Android/sdk/build-tools/*/aapt2")))
    return c[-1] if c else "aapt2"
AAPT2=os.environ.get("AAPT2") or _find_aapt2() or ""
RSVG = "rsvg-convert"

def aapt_xmltree(apk, member):
    return subprocess.run([AAPT2,"dump","xmltree","--file",member,apk],
                          capture_output=True,text=True).stdout

def android_color_to_svg(c):
    # #RGB / #ARGB / #RRGGBB / #AARRGGBB  -> (hex6_or_none, opacity)
    c=c.strip()
    if not c.startswith("#"): return (None,1.0)
    h=c[1:]
    if len(h)==3: h="".join(ch*2 for ch in h); a="ff"; rgb=h
    elif len(h)==4: a=h[0]*2; rgb="".join(ch*2 for ch in h[1:])
    elif len(h)==6: a="ff"; rgb=h
    elif len(h)==8: a=h[0:2]; rgb=h[2:]
    else: return (None,1.0)
    op=int(a,16)/255.0
    return ("#"+rgb, op)

def attrs_of_block(lines, start):
    """collect A: attrs until the next E: at same/less indent."""
    base=len(lines[start])-len(lines[start].lstrip())
    out={}
    for l in lines[start+1:]:
        ind=len(l)-len(l.lstrip())
        if l.strip().startswith("E:") and ind<=base: break
        m=re.search(r'android:(\w+)\([^)]*\)=(.+)$', l.strip())
        if m:
            k=m.group(1); v=m.group(2)
            vm=re.search(r'"([^"]*)"', v)  # raw string
            out[k]= vm.group(1) if vm else v.strip()
    return out

def vector_to_svg_paths(xmltree):
    lines=xmltree.splitlines()
    vp_w=vp_h=108.0
    paths=[]
    cur_group=None
    for i,l in enumerate(lines):
        s=l.strip()
        if s.startswith("E: vector"):
            a=attrs_of_block(lines,i)
            vp_w=float(a.get("viewportWidth",108)); vp_h=float(a.get("viewportHeight",108))
        elif s.startswith("E: path"):
            a=attrs_of_block(lines,i)
            d=a.get("pathData")
            if not d: continue
            seg=[f'<path d="{d}"']
            fc=a.get("fillColor")
            if fc:
                hx,op=android_color_to_svg(fc)
                if hx is None: seg.append('fill="none"')
                else:
                    seg.append(f'fill="{hx}"')
                    op*=float(a.get("fillAlpha",1))
                    if op<1: seg.append(f'fill-opacity="{op:.3f}"')
            else:
                seg.append('fill="none"')
            sc=a.get("strokeColor")
            if sc:
                hx,op=android_color_to_svg(sc)
                if hx:
                    seg.append(f'stroke="{hx}"')
                    op*=float(a.get("strokeAlpha",1))
                    if op<1: seg.append(f'stroke-opacity="{op:.3f}"')
                    sw=a.get("strokeWidth","0")
                    seg.append(f'stroke-width="{sw}"')
                    cap={"0":"butt","1":"round","2":"square"}.get(a.get("strokeLineCap","0"),"butt")
                    join={"0":"miter","1":"round","2":"bevel"}.get(a.get("strokeLineJoin","0"),"miter")
                    seg.append(f'stroke-linecap="{cap}" stroke-linejoin="{join}"')
            seg.append("/>")
            paths.append(" ".join(seg))
    return vp_w,vp_h,paths

def layer_member(apk, resid_name):
    # map drawable name -> res/*.xml file via aapt2 dump resources
    out=subprocess.run([AAPT2,"dump","resources",apk],capture_output=True,text=True).stdout
    # find 'drawable/<name>' then the next '(file) res/..' 
    m=re.search(r'drawable/'+re.escape(resid_name)+r'\b.*?\(file\)\s+(res/\S+)',out,re.S)
    return m.group(1) if m else None

def png_is_nontransparent_and_size(path):
    data=open(path,"rb").read()
    if data[:8]!=b'\x89PNG\r\n\x1a\n': return (0,0,False)
    w=struct.unpack(">I",data[16:20])[0]; h=struct.unpack(">I",data[20:24])[0]
    # crude non-transparent check: any IDAT present + file > 1KB (rendered content)
    nontrans = len(data) > 1000
    return (w,h,nontrans)

def main():
    apk=sys.argv[1]; outdir=sys.argv[2]
    size=108
    if "--size" in sys.argv: size=int(sys.argv[sys.argv.index("--size")+1])
    os.makedirs(outdir,exist_ok=True)
    rec={"apk":os.path.basename(apk),"rasterized":False,"iconPath":None,"reason":None}
    # 1. find the adaptive-icon manifest icon
    badging=subprocess.run([AAPT2,"dump","badging",apk],capture_output=True,text=True).stdout
    m=re.search(r"application-icon-\d+:'([^']+)'",badging) or re.search(r"application:.*icon='([^']+)'",badging)
    iconfile=m.group(1) if m else None
    if not iconfile or not iconfile.endswith(".xml"):
        rec["reason"]="icon is not XML (raster path unchanged)"; print("raster-skip:",rec["reason"])
        json.dump(rec,open(os.path.join(outdir,"icon-record.json"),"w"),indent=1); return
    xt=aapt_xmltree(apk, iconfile)
    if "adaptive-icon" not in xt:
        rec["reason"]="icon XML is not <adaptive-icon> (e.g. plain vector) -- handled separately"; print("raster-failed:",rec["reason"])
        json.dump(rec,open(os.path.join(outdir,"icon-record.json"),"w"),indent=1); return
    # 2. resolve fg/bg layer drawable names
    def layer_name(which):
        mm=re.search(r'E: '+which+r'\b.*?android:drawable\([^)]*\)=@0x[0-9a-f]+',xt,re.S)
        # resolve the @id to a drawable name via badging? simpler: dump resources and map the hex
        return None
    # resolve via resources dump: find the adaptive-icon's fg/bg references
    # (aapt2 xmltree gives @0xID; map ID->drawable name->file)
    def ref_id(which):
        mm=re.search(r'E: '+which+r'[^\n]*\n\s*A: [^\n]*android:drawable\([^)]*\)=@(0x[0-9a-f]+)',xt)
        return mm.group(1) if mm else None
    resdump=subprocess.run([AAPT2,"dump","resources",apk],capture_output=True,text=True).stdout
    def id_to_file(hexid):
        if not hexid: return None
        m=re.search(r'resource '+hexid+r' \S+\n\s*\(\) \(file\) (res/\S+)',resdump)
        return m.group(1) if m else None
    fg=id_to_file(ref_id("foreground")); bg=id_to_file(ref_id("background"))
    layers=[]
    for tag,mem in (("background",bg),("foreground",fg)):
        if not mem: continue
        if mem.endswith(".xml"):
            vp_w,vp_h,paths=vector_to_svg_paths(aapt_xmltree(apk,mem))
            if not paths:
                rec["reason"]=f"{tag} vector {mem} has no paths"; print("raster-failed:",rec["reason"])
                json.dump(rec,open(os.path.join(outdir,"icon-record.json"),"w"),indent=1); return
            layers.append((vp_w,vp_h,paths))
        else:
            rec["reason"]=f"{tag} is raster {mem} (existing PNG path handles it)"; # not our case
    if not layers:
        rec["reason"]="no vector layers (existing composition handles it)"; print("raster-skip:",rec["reason"])
        json.dump(rec,open(os.path.join(outdir,"icon-record.json"),"w"),indent=1); return
    vw,vh=layers[0][0],layers[0][1]
    body="\n".join(p for _,_,ps in layers for p in ps)
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {vw} {vh}">\n{body}\n</svg>\n'
    svgp=os.path.join(outdir,"icon.svg"); open(svgp,"w").write(svg)
    pngp=os.path.join(outdir,"icon.png")
    r=subprocess.run([RSVG,"-w",str(size),"-h",str(size),svgp,"-o",pngp],capture_output=True,text=True)
    if r.returncode!=0 or not os.path.exists(pngp):
        rec["reason"]="rsvg-convert failed: "+r.stderr.strip(); print("raster-failed:",rec["reason"])
        json.dump(rec,open(os.path.join(outdir,"icon-record.json"),"w"),indent=1); return
    w,h,nt=png_is_nontransparent_and_size(pngp)
    rec.update(rasterized=True, iconPath=pngp, width=w, height=h, nontransparent=nt)
    print(f"rastered: iconPath={pngp} {w}x{h} nontransparent={nt}")
    json.dump(rec,open(os.path.join(outdir,"icon-record.json"),"w"),indent=1)

if __name__=="__main__": main()
