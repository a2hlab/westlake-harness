#!/usr/bin/env python3
"""Deterministic J10g build = U9 single JAR: J10d baseline + J10eWebView (ViewDelegate/cookie + routes the
WebViewFactoryProvider abstract-class getters to J10gWebExtras) + J10fWebSettings + J10gWebExtras (concrete
empty ServiceWorkerController/TracingController/TokenBindingService/WebStorage/GeolocationPermissions/
ServiceWorkerWebSettings + seeds WebViewFactory.sPackageInfo). All abstract surfaces generated from AOSP 14
source; compile-only android.webkit stubs; d8 only adapter/activity/*.class. Built twice must match.
New-script convention: paths resolve from scripts/lab/lab_paths.py."""
import hashlib, shutil, subprocess, sys, zipfile
from pathlib import Path
import sys as _sys
from pathlib import Path as _P
for _p in _P(__file__).resolve().parents:
    if (_p / "westlake-harness/scripts/lab/lab_paths.py").exists():
        _sys.path.insert(0, str(_p / "westlake-harness/scripts/lab")); break
import lab_paths
WS = lab_paths.workspaces()
T = WS/"westlake-harness-bms-deploy/bms/src/.work/b6-task45/inputs"
SMALI = lab_paths.tools()/"smali-2.5.2.jar"
AJ = Path.home()/"Library/Android/sdk/platforms/android-34/android.jar"
D8_JAVA = "/opt/homebrew/opt/openjdk@17/bin/java"
SRCDIR = WS/"westlake-harness-walls/bms/src/adapter/framework/activity/java"
SPLIT = Path(__file__).resolve().parent/"sources"
SRCS = [SPLIT/"J10eWebView.java", SPLIT/"J10eViewDelegate.java", SPLIT/"J10eCookieManager.java", SRCDIR/"J10fWebSettings.java", SRCDIR/"J10gWebExtras.java"]
BASE = WS/"westlake-generation-j10d-staging/oh-adapter-runtime-j10d.jar"
HERE = Path(__file__).resolve().parent
GEN_WS = HERE.parent.parent/"2026-10-01-j10g-jar/build/gen_websettings.py"; GEN_WX = HERE.parent.parent/"2026-10-01-j10g-jar/build/gen_webextras.py"
OUT = HERE/"oh-adapter-runtime-u10base.jar"
BAK_CP=":".join(str(T/j) for j in ["baksmali-2.5.2.jar","dexlib2-2.5.2.jar","guava-27.1-android.jar","jcommander-1.64.jar","util-2.5.2.jar"])
SMALI_CP=":".join([str(SMALI)]+[str(T/j) for j in ["dexlib2-2.5.2.jar","guava-27.1-android.jar","jcommander-1.64.jar","util-2.5.2.jar","antlr-runtime-3.5.2.jar","stringtemplate-3.2.1.jar"]])
sha=lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(a,**k): subprocess.run([str(x) for x in a],check=True,**k)
COOKIE='''package android.webkit;
public abstract class CookieManager {
    public CookieManager() {}
    public abstract void setAcceptCookie(boolean a); public abstract boolean acceptCookie();
    public abstract void setAcceptThirdPartyCookies(WebView w, boolean a); public abstract boolean acceptThirdPartyCookies(WebView w);
    public abstract void setCookie(String u, String v); public abstract void setCookie(String u, String v, ValueCallback<Boolean> c);
    public abstract String getCookie(String u); public abstract String getCookie(String u, boolean p);
    public abstract void removeSessionCookie(); public abstract void removeSessionCookies(ValueCallback<Boolean> c);
    public abstract void removeAllCookie(); public abstract void removeAllCookies(ValueCallback<Boolean> c);
    public abstract boolean hasCookies(); public abstract boolean hasCookies(boolean p);
    public abstract void removeExpiredCookie(); public abstract void flush();
}
'''
EXTRA_SRCS = []   # set from --extra-sources; merged into the same U9 JAR (one version per round)

def build(work):
    if work.exists(): shutil.rmtree(work)
    work.mkdir(parents=True)
    bj=work/"basejar"; bj.mkdir()
    with zipfile.ZipFile(BASE) as z: z.extractall(bj)
    base=work/"smali"
    run(["java","-cp",BAK_CP,"org.jf.baksmali.Main","disassemble",bj/"classes.dex","-o",base])
    base_cl={str(p.relative_to(base)) for p in base.rglob("*.smali")}
    sd=work/"stub/android/webkit"; sd.mkdir(parents=True)
    (sd/"CookieManager.java").write_text(COOKIE)
    run(["python3",GEN_WS,sd/"WebSettings.java",work/"ws.throwaway.java"])
    run(["python3",GEN_WX,str(sd),work/"wx.throwaway.java"])
    sc=work/"stubclasses"; sc.mkdir()
    run(["javac","-source","8","-target","8","-cp",str(AJ),"-d",sc,*sd.glob("*.java")])
    cc=work/"classes"; cc.mkdir()
    run(["javac","-source","8","-target","8","-cp",f"{sc}:{AJ}","-d",cc,*SRCS,*EXTRA_SRCS])
    mine=sorted(str(p) for p in (cc/"adapter/activity").glob("*.class"))
    dd=work/"dex"; dd.mkdir()
    run([D8_JAVA,"-cp",str(T/"d8.jar"),"com.android.tools.r8.D8","--min-api","28","--lib",str(AJ),"--output",str(dd),*mine])
    js=work/"js"
    run(["java","-cp",BAK_CP,"org.jf.baksmali.Main","disassemble",dd/"classes.dex","-o",js])
    added=[]
    for p in (js/"adapter/activity").glob("*.smali"):
        shutil.copy2(p, base/"adapter/activity"/p.name); added.append(p.name)
    b7=base/"adapter/activity/B7BindFixes.smali"; txt=b7.read_text()
    needle="    invoke-static {}, Ladapter/activity/WebViewProviderFix;->install()V\n"
    assert txt.count(needle)==1
    b7.write_text(txt.replace(needle, needle+"\n    invoke-static {}, Ladapter/activity/J10eWebView;->install()V\n",1))
    outdex=work/"classes.dex"
    run(["java","-cp",SMALI_CP,"org.jf.smali.Main","assemble","-j","1",base,"-o",outdex])
    man=(bj/"META-INF/MANIFEST.MF").read_bytes()
    if OUT.exists(): OUT.unlink()
    with zipfile.ZipFile(OUT,"w",zipfile.ZIP_DEFLATED) as z:
        for nm,data in (("META-INF/MANIFEST.MF",man),("classes.dex",outdex.read_bytes())):
            zi=zipfile.ZipInfo(nm,(1980,1,1,0,0,0)); zi.external_attr=0o644<<16; z.writestr(zi,data)
    new_cl={str(p.relative_to(base)) for p in base.rglob("*.smali")}
    return sha(OUT), sorted(new_cl-base_cl), sorted(added)
if __name__=="__main__":
    import argparse
    ap = argparse.ArgumentParser(description="J10g build (U9 jar); --extra-sources merges next-round J-layer fixes into the same jar")
    ap.add_argument("--extra-sources", nargs="*", default=[],
                    help="additional .java source files (e.g. no-fatal-fixplan J-layer fixes) to compile into the same U9 jar; "
                         "each may need a compile-only stub -- add it to this build dir if so. Empty = the canonical J10g jar.")
    _a = ap.parse_args()
    EXTRA_SRCS = [str(Path(x).resolve()) for x in _a.extra_sources]
    if EXTRA_SRCS: print("EXTRA SOURCES:", EXTRA_SRCS)
    print("BASELINE j10d:", sha(BASE))
    s1,delta,added=build(HERE/"work1"); s2,_,_=build(HERE/"work2")
    print("CLASS delta added:", len(delta), "classes"); [print("  ",d) for d in delta]
    print("OUTPUT j10g sha256:", s1); print("DETERMINISTIC:", "YES" if s1==s2 else f"NO {s1} {s2}")
    print("ARTIFACT:", OUT)
