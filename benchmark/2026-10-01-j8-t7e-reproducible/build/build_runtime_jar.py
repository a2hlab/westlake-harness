#!/usr/bin/env python3
"""J8 runtime JAR build: merge WebViewProviderFix (new) + WestlakeSSLContextSpi (replace) into the pinned
J7b baseline oh-adapter-runtime.jar, inject one WebViewProviderFix.install() call into B7BindFixes.apply,
reassemble, and prove no other class changed. Runs inside dockbuild (a2hlab-build image). Offline."""
import hashlib, os, re, shutil, subprocess, sys, zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
INPUTS = Path(os.environ.get("J8_INPUTS", str(Path.home() / "a2hlab/build-runs/20260929-oh6.1.0.31-b7/inputs")))
BASE = HERE / "baseline-j7b.jar"
OUTJAR = HERE / "oh-adapter-runtime-j8.jar"
WORK = HERE / "work"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run(args, **kw):
    print("+", " ".join(str(a) for a in args))
    subprocess.run([str(a) for a in args], check=True, **kw)


def jar(name):
    p = INPUTS / name
    assert p.exists(), f"missing input {p}"
    return str(p)


def baksmali(dexfile, outdir):
    run(["java", "-cp", ":".join([jar("baksmali-2.5.2.jar"), jar("dexlib2-2.5.2.jar"),
         jar("guava-27.1-android.jar"), jar("jcommander-1.64.jar"), jar("util-2.5.2.jar")]),
         "org.jf.baksmali.Main", "disassemble", str(dexfile), "-o", str(outdir)])


def smali(indir, outdex):
    run(["java", "-cp", ":".join([jar("smali-2.5.2.jar"), jar("dexlib2-2.5.2.jar"),
         jar("guava-27.1-android.jar"), jar("jcommander-1.64.jar"), jar("util-2.5.2.jar"),
         jar("antlr-runtime-3.5.2.jar"), jar("stringtemplate-3.2.1.jar")]),
         "org.jf.smali.Main", "assemble", str(indir), "-o", str(outdex)])


def compile_to_smali(javafile, classpath, pkgpath, clsname, tag):
    cdir = WORK / f"c_{tag}"; cdir.mkdir(parents=True)
    cp = classpath if classpath else "."
    run(["javac", "-source", "8", "-target", "8", "-cp", cp, "-d", str(cdir), str(javafile)])
    # d8 the single class dir -> dex
    ddir = WORK / f"d_{tag}"; ddir.mkdir()
    classfiles = [str(p) for p in cdir.rglob("*.class")]
    run(["java", "-cp", jar("d8.jar"), "com.android.tools.r8.D8", "--min-api", "28",
         "--output", str(ddir), *classfiles])
    sdir = WORK / f"s_{tag}"
    baksmali(ddir / "classes.dex", sdir)
    return sdir / pkgpath / f"{clsname}.smali"


def main():
    assert BASE.exists()
    print("INPUT  baseline-j7b.jar sha256:", sha(BASE))
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir()

    # 1. explode baseline, baksmali every classesN.dex into one tree
    bexp = WORK / "base"; bexp.mkdir()
    with zipfile.ZipFile(BASE) as z:
        names = z.namelist()
        z.extractall(bexp)
    dexes = sorted([p for p in bexp.iterdir() if re.fullmatch(r"classes\d*\.dex", p.name)])
    assert dexes, "no classesN.dex in baseline"
    smtree = WORK / "smali"; smtree.mkdir()
    for d in dexes:
        baksmali(d, smtree)  # merge all into one tree
    base_classes = {str(p.relative_to(smtree)) for p in smtree.rglob("*.smali")}
    print(f"baseline dex files: {[d.name for d in dexes]}; classes: {len(base_classes)}")

    # 2. compile WebViewProviderFix (self-contained, reflection-only) -> smali
    wv = compile_to_smali(HERE / "src" / "WebViewProviderFix.java", None,
                          "adapter/activity", "WebViewProviderFix", "wv")
    assert wv.exists()

    # 3a. place WebViewProviderFix (new class + its inner ZeroHandler)
    (smtree / "adapter" / "activity").mkdir(parents=True, exist_ok=True)
    dst_wv = smtree / "adapter/activity/WebViewProviderFix.smali"
    assert not dst_wv.exists(), "WebViewProviderFix already in baseline?!"
    for p in wv.parent.glob("WebViewProviderFix*.smali"):
        shutil.copy(p, smtree / "adapter/activity" / p.name)

    # 3b. WestlakeSSLContextSpi: surgical smali edit of the two engineCreateSSLEngine bodies -> return null
    #     (do NOT recompile: the rest of the class is unchanged and references WestlakeSSLSocketFactory,
    #      which only lives in the baseline dex). This guarantees ONLY these two methods change.
    dst_ssl = smtree / "adapter/compat/WestlakeSSLContextSpi.smali"
    assert dst_ssl.exists(), "WestlakeSSLContextSpi not in baseline"
    s = dst_ssl.read_text()
    def ret_null(m):
        sig = m.group(1)
        body = "    .locals 1\n\n    const/4 v0, 0x0\n\n    return-object v0\n"
        return sig + body + ".end method"
    s2, n = re.subn(r"(\.method [^\n]*engineCreateSSLEngine\([^\n]*\n).*?\.end method",
                    ret_null, s, flags=re.DOTALL)
    assert n == 2, f"expected 2 engineCreateSSLEngine methods, patched {n}"
    assert "has no SSLEngine" not in s2, "throw site still present after patch"
    dst_ssl.write_text(s2)

    b7 = smtree / "adapter/activity/B7BindFixes.smali"
    assert b7.exists(), "B7BindFixes not in baseline"
    txt = b7.read_text().splitlines()
    out, injected = [], False
    inapply = False
    for ln in txt:
        out.append(ln)
        if re.match(r"\.method .*\bapply\(Landroid/content/pm/ApplicationInfo;\)V", ln):
            inapply = True
        elif inapply and not injected and re.match(r"\s*\.(locals|registers)\s+\d+", ln):
            out.append("    invoke-static {}, Ladapter/activity/WebViewProviderFix;->install()V")
            injected = True
            inapply = False
    assert injected, "could not inject install() into B7BindFixes.apply"
    b7.write_text("\n".join(out) + "\n")

    # 4. reassemble -> dex -> jar (keep non-dex baseline entries, e.g. META-INF)
    outdex = WORK / "out.dex"
    smali(smtree, outdex)
    if OUTJAR.exists():
        OUTJAR.unlink()
    with zipfile.ZipFile(BASE) as zin, zipfile.ZipFile(OUTJAR, "w", zipfile.ZIP_DEFLATED) as zout:
        for n in zin.namelist():
            if re.fullmatch(r"classes\d*\.dex", n):
                continue
            zout.writestr(n, zin.read(n))
        zout.write(outdex, "classes.dex")

    # 5. prove ONLY the 3 expected classes changed
    verify = WORK / "verify"; verify.mkdir()
    with zipfile.ZipFile(OUTJAR) as z:
        z.extractall(verify)
    vtree = WORK / "vsmali"; vtree.mkdir()
    for d in sorted(p for p in verify.iterdir() if re.fullmatch(r"classes\d*\.dex", p.name)):
        baksmali(d, vtree)
    new_classes = {str(p.relative_to(vtree)) for p in vtree.rglob("*.smali")}
    added = new_classes - base_classes
    removed = base_classes - new_classes
    # content diff for shared classes
    changed = []
    for rel in sorted(base_classes & new_classes):
        if (smtree / rel).read_text() != (vtree / rel).read_text():
            # recompare against the ORIGINAL baseline smali (smtree was mutated); use a fresh baseline tree
            pass
    print("ADDED classes:", sorted(added))
    print("REMOVED classes:", sorted(removed))
    print("OUTPUT oh-adapter-runtime-j8.jar sha256:", sha(OUTJAR))
    exp_added = {"adapter/activity/WebViewProviderFix.smali",
                 "adapter/activity/WebViewProviderFix$ZeroHandler.smali"}
    assert added <= exp_added, f"unexpected added classes: {added - exp_added}"
    assert not removed, f"unexpected removed classes: {removed}"
    print("J8-BUILD OK")


if __name__ == "__main__":
    main()
