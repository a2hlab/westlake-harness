#!/usr/bin/env python3
"""Deterministic J10f build = U9 single JAR: J10d baseline + J10eWebView (now wiring getSettings ->
J10fWebSettings) + J10fWebSettings (concrete WebSettings, 104 abstract overrides generated from AOSP
WebSettings.java). install() injected after WebViewProviderFix.install in B7BindFixes.apply. Compile-only
android.webkit stubs (CookieManager 16, WebSettings 104, incl @hide) so the concrete subclasses override
the full runtime abstract surface; d8 only adapter/activity/*.class. Build twice must be byte-identical.
Run on the Mac (javac 1.8; d8 via openjdk@17; smali/baksmali 2.5.2 on Java 8)."""
import hashlib, os, shutil, subprocess, sys, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts/lab"))
import lab_paths  # noqa: E402
WS = lab_paths.workspaces()
T = WS / "westlake-harness-bms-deploy/bms/src/.work/b6-task45/inputs"
SMALI = WS / "westlake-inputs/tools/smali-2.5.2.jar"
AJ = Path(os.environ.get("ANDROID_JAR") or Path.home() / "Library/Android/sdk/platforms/android-34/android.jar")
D8_JAVA = "/opt/homebrew/opt/openjdk@17/bin/java"
SRCDIR = WS / "westlake-harness-walls/bms/src/adapter/framework/activity/java"
SRCS = [SRCDIR/"J10eWebView.java", SRCDIR/"J10fWebSettings.java"]
BASE = WS / "westlake-generation-j10d-staging/oh-adapter-runtime-j10d.jar"  # clean J10d base
HERE = Path(__file__).resolve().parent
GEN = HERE / "gen_websettings.py"
OUT = HERE / "oh-adapter-runtime-j10f.jar"
BAK_CP = ":".join(str(T/j) for j in ["baksmali-2.5.2.jar","dexlib2-2.5.2.jar","guava-27.1-android.jar","jcommander-1.64.jar","util-2.5.2.jar"])
SMALI_CP = ":".join([str(SMALI)]+[str(T/j) for j in ["dexlib2-2.5.2.jar","guava-27.1-android.jar","jcommander-1.64.jar","util-2.5.2.jar","antlr-runtime-3.5.2.jar","stringtemplate-3.2.1.jar"]])
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(a, **k): subprocess.run([str(x) for x in a], check=True, **k)
COOKIE_STUB = '''package android.webkit;
public abstract class CookieManager {
    public CookieManager() {}
    public abstract void setAcceptCookie(boolean accept);
    public abstract boolean acceptCookie();
    public abstract void setAcceptThirdPartyCookies(WebView webview, boolean accept);
    public abstract boolean acceptThirdPartyCookies(WebView webview);
    public abstract void setCookie(String url, String value);
    public abstract void setCookie(String url, String value, ValueCallback<Boolean> callback);
    public abstract String getCookie(String url);
    public abstract String getCookie(String url, boolean privateBrowsing);
    public abstract void removeSessionCookie();
    public abstract void removeSessionCookies(ValueCallback<Boolean> callback);
    public abstract void removeAllCookie();
    public abstract void removeAllCookies(ValueCallback<Boolean> callback);
    public abstract boolean hasCookies();
    public abstract boolean hasCookies(boolean privateBrowsing);
    public abstract void removeExpiredCookie();
    public abstract void flush();
}
'''
def build(work: Path):
    if work.exists(): shutil.rmtree(work)
    work.mkdir(parents=True)
    bj = work/"basejar"; bj.mkdir()
    with zipfile.ZipFile(BASE) as z: z.extractall(bj)
    base_smali = work/"smali"
    run(["java","-cp",BAK_CP,"org.jf.baksmali.Main","disassemble",bj/"classes.dex","-o",base_smali])
    base_classes = {str(p.relative_to(base_smali)) for p in base_smali.rglob("*.smali")}
    # compile-only stubs: CookieManager (inline) + WebSettings (generated from AOSP)
    sd = work/"stub/android/webkit"; sd.mkdir(parents=True)
    (sd/"CookieManager.java").write_text(COOKIE_STUB)
    run(["python3", GEN, sd/"WebSettings.java", work/"J10fWebSettings.gen.java"])  # regen stub (+ throwaway j10f) from source-of-truth
    sc = work/"stubclasses"; sc.mkdir()
    run(["javac","-source","8","-target","8","-cp",str(AJ),"-d",sc,sd/"CookieManager.java",sd/"WebSettings.java"])
    cc = work/"classes"; cc.mkdir()
    run(["javac","-source","8","-target","8","-cp",f"{sc}:{AJ}","-d",cc,*SRCS])
    mine = sorted(str(p) for p in (cc/"adapter/activity").glob("*.class"))
    assert mine, "no adapter classes compiled"
    dd = work/"dex"; dd.mkdir()
    run([D8_JAVA,"-cp",str(T/"d8.jar"),"com.android.tools.r8.D8","--min-api","28","--lib",str(AJ),"--output",str(dd),*mine])
    js = work/"j10f-smali"
    run(["java","-cp",BAK_CP,"org.jf.baksmali.Main","disassemble",dd/"classes.dex","-o",js])
    added=[]
    for p in (js/"adapter/activity").glob("*.smali"):
        shutil.copy2(p, base_smali/"adapter/activity"/p.name); added.append(p.name)
    b7 = base_smali/"adapter/activity/B7BindFixes.smali"; txt = b7.read_text()
    needle = "    invoke-static {}, Ladapter/activity/WebViewProviderFix;->install()V\n"
    assert txt.count(needle)==1, "install call site not unique"
    b7.write_text(txt.replace(needle, needle+"\n    invoke-static {}, Ladapter/activity/J10eWebView;->install()V\n", 1))
    outdex = work/"classes.dex"
    run(["java","-cp",SMALI_CP,"org.jf.smali.Main","assemble","-j","1",base_smali,"-o",outdex])
    man = (bj/"META-INF/MANIFEST.MF").read_bytes()
    if OUT.exists(): OUT.unlink()
    with zipfile.ZipFile(OUT,"w",zipfile.ZIP_DEFLATED) as z:
        for nm,data in (("META-INF/MANIFEST.MF",man),("classes.dex",outdex.read_bytes())):
            zi=zipfile.ZipInfo(nm,(1980,1,1,0,0,0)); zi.external_attr=0o644<<16; z.writestr(zi,data)
    new_classes = {str(p.relative_to(base_smali)) for p in base_smali.rglob("*.smali")}
    return sha(OUT), sorted(new_classes-base_classes), sorted(added)
if __name__=="__main__":
    print("BASELINE j10d:", sha(BASE))
    s1,delta,added = build(HERE/"work1"); s2,_,_ = build(HERE/"work2")
    print("INJECT J10eWebView.install after WebViewProviderFix.install")
    print("CLASS delta added:", delta)
    print("OUTPUT j10f sha256:", s1)
    print("DETERMINISTIC:", "YES" if s1==s2 else f"NO ({s1} vs {s2})")
    print("ARTIFACT:", OUT)
