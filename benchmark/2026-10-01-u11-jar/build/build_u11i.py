#!/usr/bin/env python3
"""Deterministic U11 JAR v9 = U11 (phone TelephonyFetcher) + WlSSLEngine (ssl-engine cluster: createSSLEngine
returns a non-null stub engine instead of null). New feature in new files (TelephonyFetcher.java, WlSSLEngine.java);
no frozen file edited. Wiring = smali needles (no frozen source touched):
  1. J10eWebView.install()      -> B7BindFixes.smali
  2. TelephonyFetcher.install() -> SystemServiceFetcherStubs.smali (after WifiFetcher.install())
  3. WlSSLEngine.create()       -> WestlakeSSLContextSpi.engineCreateSSLEngine() x2 (replace `return null`)
Built twice must match. Paths resolve from scripts/lab/lab_paths.py."""
import hashlib, shutil, subprocess, zipfile
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
SPLIT = WS/"westlake-harness-t3/benchmark/2026-10-01-j10-freeze-draft/split/sources"
U11 = WS/"westlake-harness-t3/benchmark/2026-10-01-u11-jar"
PREDICATE = WS/"westlake-harness-t3/benchmark/2026-10-01-j10-prep/src/Predicate.java"
SRCS = [SPLIT/"J10eWebView.java", SPLIT/"J10eViewDelegate.java", SPLIT/"J10eCookieManager.java",
        SRCDIR/"J10fWebSettings.java", SRCDIR/"J10gWebExtras.java",
        PREDICATE, U11/"src/TelephonyFetcher.java", U11/"src/WlSSLEngine.java", U11/"src/AppContentProviders.java", U11/"src/KeystoreBoardProbe.java"]
BASE = WS/"westlake-generation-j10d-staging/oh-adapter-runtime-j10d.jar"
HERE = Path(__file__).resolve().parent
GEN_WS = HERE.parent.parent/"2026-10-01-j10g-jar/build/gen_websettings.py"
GEN_WX = HERE.parent.parent/"2026-10-01-j10g-jar/build/gen_webextras.py"
OUT = HERE/"oh-adapter-runtime-u11i.jar"
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
ENGINE_CALL = ("    invoke-static {}, Ladapter/compat/WlSSLEngine;->create()Ljavax/net/ssl/SSLEngine;\n\n"
               "    move-result-object v0\n\n    return-object v0\n")
SSL_OLD_0 = (".method protected engineCreateSSLEngine()Ljavax/net/ssl/SSLEngine;\n    .registers 2\n\n"
             "    const/4 v0, 0x0\n\n    return-object v0\n.end method")
SSL_NEW_0 = (".method protected engineCreateSSLEngine()Ljavax/net/ssl/SSLEngine;\n    .registers 2\n\n"
             + ENGINE_CALL + ".end method")
SSL_OLD_2 = (".method protected engineCreateSSLEngine(Ljava/lang/String;I)Ljavax/net/ssl/SSLEngine;\n    .registers 4\n\n"
             "    const/4 v0, 0x0\n\n    return-object v0\n.end method")
J10D_OLD = (".method public static restore(Landroid/content/pm/ActivityInfo;)V\n    .registers 8\n\n    .line 36\n")
J10D_NEW = (".method public static restore(Landroid/content/pm/ActivityInfo;)V\n    .registers 8\n\n"
            "    iget-object v0, p0, Landroid/content/pm/ActivityInfo;->targetActivity:Ljava/lang/String;\n"
            "    if-eqz v0, :cond_j10d_run\n"
            "    invoke-virtual {v0}, Ljava/lang/String;->isEmpty()Z\n"
            "    move-result v1\n"
            "    if-nez v1, :cond_j10d_run\n"
            "    iget-object v1, p0, Landroid/content/pm/ActivityInfo;->name:Ljava/lang/String;\n"
            "    invoke-virtual {v0, v1}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z\n"
            "    move-result v2\n"
            "    if-nez v2, :cond_j10d_run\n"
            "    sget-object v0, Ljava/lang/System;->err:Ljava/io/PrintStream;\n"
            "    new-instance v1, Ljava/lang/StringBuilder;\n"
            "    invoke-direct {v1}, Ljava/lang/StringBuilder;-><init>()V\n"
            "    const-string v2, \"[J10d-THEME] \"\n"
            "    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;\n"
            "    move-result-object v1\n"
            "    iget-object v2, p0, Landroid/content/pm/ActivityInfo;->name:Ljava/lang/String;\n"
            "    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;\n"
            "    move-result-object v1\n"
            "    const-string v2, \" skipped: alias target theme owned by AliasTargetTheme\"\n"
            "    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;\n"
            "    move-result-object v1\n"
            "    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;\n"
            "    move-result-object v1\n"
            "    invoke-virtual {v0, v1}, Ljava/io/PrintStream;->println(Ljava/lang/String;)V\n"
            "    return-void\n\n    :cond_j10d_run\n    .line 36\n")
SSL_NEW_2 = (".method protected engineCreateSSLEngine(Ljava/lang/String;I)Ljavax/net/ssl/SSLEngine;\n    .registers 4\n\n"
             + ENGINE_CALL + ".end method")

def inject_after(smali_path, needle, addition, tag):
    txt = smali_path.read_text()
    assert txt.count(needle) == 1, f"{tag}: needle count {txt.count(needle)} != 1"
    smali_path.write_text(txt.replace(needle, needle + addition, 1))

def replace_block(smali_path, old, new, tag):
    txt = smali_path.read_text()
    assert txt.count(old) == 1, f"{tag}: block count {txt.count(old)} != 1 in {smali_path.name}"
    smali_path.write_text(txt.replace(old, new, 1))

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
    ks=work/"ksstub/adapter/core"; ks.mkdir(parents=True)
    (ks/"SoftwareAndroidKeyStore.java").write_text("package adapter.core;\npublic final class SoftwareAndroidKeyStore { public static final String NAME = \"AndroidKeyStore\"; private SoftwareAndroidKeyStore(){} }")
    run(["javac","-source","8","-target","8","-cp",str(AJ),"-d",sc,*sd.glob("*.java"),*ks.glob("*.java")])
    cc=work/"classes"; cc.mkdir()
    run(["javac","-source","8","-target","8","-cp",f"{sc}:{AJ}","-d",cc,*SRCS])
    mine=sorted(str(p) for p in cc.rglob("*.class"))
    dd=work/"dex"; dd.mkdir()
    run([D8_JAVA,"-cp",str(T/"d8.jar"),"com.android.tools.r8.D8","--min-api","28","--lib",str(AJ),"--output",str(dd),*mine])
    js=work/"js"
    run(["java","-cp",BAK_CP,"org.jf.baksmali.Main","disassemble",dd/"classes.dex","-o",js])
    added=[]
    for p in js.rglob("*.smali"):
        rel=p.relative_to(js); dst=base/rel; dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dst); added.append(str(rel))
    inject_after(base/"adapter/activity/B7BindFixes.smali",
           "    invoke-static {}, Ladapter/activity/WebViewProviderFix;->install()V\n",
           "\n    invoke-static {}, Ladapter/activity/J10eWebView;->install()V\n", "B7/J10e")
    inject_after(base/"adapter/activity/SystemServiceFetcherStubs.smali",
           "    invoke-static {}, Ladapter/activity/WifiFetcher;->install()V\n",
           "\n    invoke-static {}, Ladapter/activity/TelephonyFetcher;->install()V\n", "SSFS/Telephony")
    ssr=base/"adapter/compat/WestlakeSSLContextSpi.smali"
    replace_block(ssr, SSL_OLD_0, SSL_NEW_0, "SSL/engine0")
    replace_block(ssr, SSL_OLD_2, SSL_NEW_2, "SSL/engine2")
    replace_block(base/"adapter/activity/J10dTheme.smali", J10D_OLD, J10D_NEW, "J10d/alias-guard")
    inject_after(base/"adapter/activity/AppSchedulerBridge.smali",
           "    const-string v1, \"[B43-BIND] handleBindApplication returned OK\"\n\n"
           "    invoke-virtual {v0, v1}, Ljava/io/PrintStream;->println(Ljava/lang/String;)V\n",
           "\n    invoke-static {}, Ladapter/activity/AppContentProviders;->install()V\n", "SchedBridge/AppProviders-postBind")
    inject_after(base/"adapter/activity/AppSchedulerBridge.smali",
           "    invoke-static {}, Ladapter/activity/AppContentProviders;->install()V\n",
           "\n    const-string v0, \"_androidx_security_master_key_\"\n\n    invoke-static {v0}, Ladapter/core/KeystoreBoardProbe;->run(Ljava/lang/String;)V\n", "SchedBridge/KeystoreProbe")
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
    print("BASELINE j10d:", sha(BASE))
    s1,delta,added=build(HERE/"work1i"); s2,_,_=build(HERE/"work2i")
    print("CLASS delta added:", len(delta)); [print("  ",d) for d in delta]
    print("OUTPUT u11i sha256:", s1); print("DETERMINISTIC:", "YES" if s1==s2 else f"NO {s1} {s2}")
    print("ARTIFACT:", OUT)
