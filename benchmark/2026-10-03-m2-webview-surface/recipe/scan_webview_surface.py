#!/usr/bin/env python3
"""M2 WebView-surface scan (offline, static). Parses the DEX method_ids table of every corpus APK and
reports which android.webkit.* methods each app CALLS (method refs = calls into the framework), plus the
WebViewClient/WebChromeClient callbacks it overrides. Pure-Python dex parser; no apktool/baksmali needed.

Usage:  WORKSPACES=/path/to/orca/workspaces python3 scan_webview_surface.py
Reads:  $WORKSPACES/westlake-inputs/corpus100.json (key->apk,package,stack),
        $WORKSPACES/westlake-inputs/corpus-v2/app-inputs/cv2-*/ (cv2 apks),
        $WORKSPACES/westlake-harness/benchmark/2026-10-03-u13-reference/u13-ref-{5cd,5ea,61b}.txt (lit status).
Writes: surface.csv

Key definitions:
  renders_webview = the app references a WebView-embedding method (WebView.<init>/loadUrl/setWebViewClient/
    getSettings/loadDataWithBaseURL/evaluateJavascript/addJavascriptInterface or extends WebViewClient/
    WebChromeClient). The static utilities MimeTypeMap.* and WebView.findAddress/findAll are NOT a render
    signal (they don't instantiate a WebView) and are reported in a separate column.
"""
import json, os, struct, zipfile, io, csv, collections

WS = os.environ.get("WORKSPACES") or os.path.expanduser("~/orca/workspaces")
INP = os.path.join(WS, "westlake-inputs")

def u32(b,o): return struct.unpack_from("<I",b,o)[0]
def u16(b,o): return struct.unpack_from("<H",b,o)[0]
def read_uleb(b,o):
    r=0;s=0
    while True:
        x=b[o];o+=1;r|=(x&0x7f)<<s
        if not(x&0x80): break
        s+=7
    return r,o

def dex_method_refs(data):
    if data[:3]!=b'dex': return
    sid_size=u32(data,0x38); sid_off=u32(data,0x3C)
    tid_size=u32(data,0x40); tid_off=u32(data,0x44)
    mid_size=u32(data,0x58); mid_off=u32(data,0x5C)
    soff=struct.unpack_from("<%dI"%sid_size,data,sid_off)
    def rstr(i):
        o=soff[i]; _,o=read_uleb(data,o); e=data.index(b'\x00',o); return data[o:e].decode('latin-1')
    tstr=struct.unpack_from("<%dI"%tid_size,data,tid_off); tc={}
    def tdesc(i):
        if i not in tc: tc[i]=rstr(tstr[i])
        return tc[i]
    base=mid_off
    for _ in range(mid_size):
        c=u16(data,base); n=u32(data,base+4); base+=8
        yield tdesc(c), rstr(n)

def iter_dex(path):
    try: z=zipfile.ZipFile(path)
    except Exception: return
    dexes=[n for n in z.namelist() if n.endswith('.dex') and '/' not in n]
    if dexes:
        for n in dexes:
            try: yield z.read(n)
            except Exception: pass
        return
    inner=sorted([n for n in z.namelist() if n.endswith('.apk')],
                 key=lambda n:(('config' in n or 'split' in n),len(n)))
    for n in inner[:1]:
        try:
            iz=zipfile.ZipFile(io.BytesIO(z.read(n)))
            for m in iz.namelist():
                if m.endswith('.dex') and '/' not in m: yield iz.read(m)
        except Exception: pass

CALLBACKS={"shouldOverrideUrlLoading","shouldInterceptRequest","onPageStarted","onPageFinished",
 "onPageCommitVisible","onReceivedError","onReceivedHttpError","onReceivedSslError","onReceivedClientCertRequest",
 "onReceivedHttpAuthRequest","onLoadResource","doUpdateVisitedHistory","onProgressChanged","onReceivedTitle",
 "onReceivedIcon","onJsAlert","onJsConfirm","onJsPrompt","onShowFileChooser","onConsoleMessage",
 "onGeolocationPermissionsShowPrompt","onPermissionRequest","onShowCustomView","onHideCustomView",
 "onCreateWindow","onCloseWindow","onJsBeforeUnload","onDownloadStart","onRenderProcessGone",
 "onSafeBrowsingHit","onFormResubmission","onScaleChanged"}
RENDER={"webkit.WebView.<init>","webkit.WebView.loadUrl","webkit.WebView.loadData","webkit.WebView.loadDataWithBaseURL",
 "webkit.WebView.postUrl","webkit.WebView.setWebViewClient","webkit.WebView.setWebChromeClient","webkit.WebView.getSettings",
 "webkit.WebView.evaluateJavascript","webkit.WebView.addJavascriptInterface","webkit.WebViewClient.<init>","webkit.WebChromeClient.<init>"}
def is_util(m): return m.startswith("webkit.MimeTypeMap.") or m in ("webkit.WebView.findAddress","webkit.WebView.findAll") or m.startswith("webkit.URLUtil.")

def scan(path):
    methods=set(); cb=set(); ax=set()
    for blob in iter_dex(path):
        try:
            for cls,name in dex_method_refs(blob):
                if cls.startswith("Landroid/webkit/"):
                    methods.add(cls[9:].rstrip(';').replace('/','.')+"."+name)
                elif cls.startswith("Landroidx/webkit/"):
                    ax.add(cls[10:].rstrip(';').replace('/','.')+"."+name)
                if name in CALLBACKS: cb.add(name)
        except Exception: pass
    return methods, cb, ax

def main():
    roster={}
    apps=json.load(open(os.path.join(INP,"corpus100.json")))["apps"]
    for k,v in apps.items(): roster[k]=(v.get("input"),v.get("package",""),v.get("stack",""))
    cv2=os.path.join(INP,"corpus-v2","app-inputs")
    for d in os.listdir(cv2):
        p=os.path.join(cv2,d)
        if not os.path.isdir(p): continue
        a=[f for f in os.listdir(p) if f.endswith('.apk')]
        if a: roster[d]=(os.path.join(p,a[0]), d[4:].replace('-','.') if d.startswith('cv2-') else "", "cv2")
    lit={}
    for b in ("5cd","5ea","61b"):
        f=os.path.join(WS,"westlake-harness","benchmark","2026-10-03-u13-reference","u13-ref-%s.txt"%b)
        if not os.path.exists(f): continue
        for line in open(f):
            if not line.startswith("row "): continue
            p=line.split()
            try: key=p[4]; verd=[x for x in p if x.startswith("verdict=")][0].split("=")[1]
            except Exception: continue
            if verd=="lit": lit[key]=True
            else: lit.setdefault(key,False)
    with open("surface.csv","w",newline="") as fo:
        w=csv.writer(fo)
        w.writerow(["key","stack","package","u13_status","renders_webview","n_render_webkit_methods",
                    "callbacks_overridden","render_webkit_methods","androidx_webkit","util_only_webkit"])
        for key,(apk,pkg,stack) in sorted(roster.items()):
            if not apk or not os.path.exists(apk):
                w.writerow([key,stack,pkg,"no-apk",0,0,"","","",""]); continue
            m,cb,ax=scan(apk)
            st=("lit" if lit[key] else "not-lit") if key in lit else "unmeasured"
            renders=bool(m & RENDER)
            surf=sorted(x for x in m if not is_util(x)); util=sorted(x for x in m if is_util(x))
            w.writerow([key,stack,pkg,st,int(renders),len(surf),"|".join(sorted(cb)),
                        "|".join(surf),"|".join(sorted(ax)),"|".join(util)])

if __name__=="__main__": main()
