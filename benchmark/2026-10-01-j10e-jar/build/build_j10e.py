#!/usr/bin/env python3
"""Deterministic J10e build: J10d baseline jar + adapter.activity.J10eWebView, with the install() call
injected right after the WebViewProviderFix.install() call in B7BindFixes.apply. Compile-only
android.webkit.CookieManager stub (16 abstract incl 2 @hide) so the concrete WlCookieManager overrides
the full runtime abstract surface; d8 only the adapter classes (stub stays compile-only). Builds twice
must be byte-identical. Run on the Mac (javac 1.8, local smali/baksmali/d8 jars)."""
import hashlib, os, re, shutil, subprocess, sys, zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts/lab"))
import lab_paths  # noqa: E402
WS = lab_paths.workspaces()
T = WS / "westlake-harness-bms-deploy/bms/src/.work/b6-task45/inputs"
SMALI = WS / "westlake-inputs/tools/smali-2.5.2.jar"
AJ = Path(os.environ.get("ANDROID_JAR") or Path.home() / "Library/Android/sdk/platforms/android-34/android.jar")
# d8/r8 require Java 11+ (class file 55.0); the default `java` here is 1.8. baksmali/smali run on 8.
D8_JAVA = "/opt/homebrew/opt/openjdk@17/bin/java"
SRC = WS / "westlake-harness-walls/bms/src/adapter/framework/activity/java/J10eWebView.java"
BASE = WS / "westlake-generation-j10d-staging/oh-adapter-runtime-j10d.jar"
HERE = Path(__file__).resolve().parent
OUT = HERE / "oh-adapter-runtime-j10e.jar"

BAK_CP = ":".join(str(T / j) for j in ["baksmali-2.5.2.jar","dexlib2-2.5.2.jar","guava-27.1-android.jar","jcommander-1.64.jar","util-2.5.2.jar"])
SMALI_CP = ":".join([str(SMALI)] + [str(T / j) for j in ["dexlib2-2.5.2.jar","guava-27.1-android.jar","jcommander-1.64.jar","util-2.5.2.jar","antlr-runtime-3.5.2.jar","stringtemplate-3.2.1.jar"]])
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(a, **k): subprocess.run([str(x) for x in a], check=True, **k)

STUB = '''package android.webkit;
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
    # 1. baksmali J10d baseline
    bj = work/"basejar"; bj.mkdir()
    with zipfile.ZipFile(BASE) as z: z.extractall(bj)
    base_smali = work/"smali"
    run(["java","-cp",BAK_CP,"org.jf.baksmali.Main","disassemble",bj/"classes.dex","-o",base_smali])
    base_classes = {str(p.relative_to(base_smali)) for p in base_smali.rglob("*.smali")}
    # 2. compile stub then J10eWebView
    sd = work/"stub/android/webkit"; sd.mkdir(parents=True)
    (sd/"CookieManager.java").write_text(STUB)
    sc = work/"stubclasses"; sc.mkdir()
    run(["javac","-source","8","-target","8","-cp",str(AJ),"-d",sc,sd/"CookieManager.java"])
    cc = work/"classes"; cc.mkdir()
    run(["javac","-source","8","-target","8","-cp",f"{sc}:{AJ}","-d",cc,SRC])
    # 3. d8 ONLY adapter/activity/J10eWebView*.class with android.jar as lib
    mine = sorted(str(p) for p in (cc/"adapter/activity").glob("J10eWebView*.class"))
    assert mine, "no J10eWebView classes compiled"
    dd = work/"dex"; dd.mkdir()
    run([D8_JAVA,"-cp",str(T/"d8.jar"),"com.android.tools.r8.D8","--min-api","28","--lib",str(AJ),"--output",str(dd),*mine])
    # 4. baksmali j10e dex, copy J10eWebView*.smali into base tree
    js = work/"j10e-smali"
    run(["java","-cp",BAK_CP,"org.jf.baksmali.Main","disassemble",dd/"classes.dex","-o",js])
    added=[]
    for p in (js/"adapter/activity").glob("J10eWebView*.smali"):
        dst = base_smali/"adapter/activity"/p.name
        shutil.copy2(p, dst); added.append(p.name)
    # 5. inject install() call after WebViewProviderFix.install() in B7BindFixes.apply
    b7 = base_smali/"adapter/activity/B7BindFixes.smali"
    txt = b7.read_text()
    needle = "    invoke-static {}, Ladapter/activity/WebViewProviderFix;->install()V\n"
    assert txt.count(needle) == 1, "WebViewProviderFix.install call site not unique"
    inject = needle + "\n    invoke-static {}, Ladapter/activity/J10eWebView;->install()V\n"
    b7.write_text(txt.replace(needle, inject, 1))
    # 6. smali assemble -j 1 (deterministic)
    outdex = work/"classes.dex"
    run(["java","-cp",SMALI_CP,"org.jf.smali.Main","assemble","-j","1",base_smali,"-o",outdex])
    # 7. repackage jar: MANIFEST.MF + classes.dex, fixed zip date_time
    man = (bj/"META-INF/MANIFEST.MF").read_bytes()
    if OUT.exists(): OUT.unlink()
    with zipfile.ZipFile(OUT,"w",zipfile.ZIP_DEFLATED) as z:
        zi = zipfile.ZipInfo("META-INF/MANIFEST.MF",(1980,1,1,0,0,0)); zi.external_attr=0o644<<16
        z.writestr(zi, man)
        zi = zipfile.ZipInfo("classes.dex",(1980,1,1,0,0,0)); zi.external_attr=0o644<<16
        z.writestr(zi, outdex.read_bytes())
    new_classes = {str(p.relative_to(base_smali)) for p in base_smali.rglob("*.smali")}
    return sha(OUT), sorted(new_classes-base_classes), added

if __name__ == "__main__":
    print("BASELINE j10d:", sha(BASE))
    s1, delta, added = build(HERE/"work1")
    s2, _, _ = build(HERE/"work2")
    print("INJECT  Ladapter/activity/J10eWebView;->install()V after WebViewProviderFix.install in B7BindFixes.apply")
    print("CLASS delta (added):", delta)
    print("SMALI copied:", added)
    print("OUTPUT j10e sha256:", s1)
    print("DETERMINISTIC:", "YES" if s1==s2 else f"NO ({s1} vs {s2})")
    print("ARTIFACT:", OUT)
