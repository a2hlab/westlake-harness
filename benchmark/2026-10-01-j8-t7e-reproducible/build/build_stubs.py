#!/usr/bin/env python3
"""T7e step 1: rebuild adapter-mainline-stubs.jar replacing android.graphics.ColorMatrix (empty stub ->
full AOSP 14 r1). Runs inside dockbuild (a2hlab-b5-java). Proves only ColorMatrix changed. Offline."""
import hashlib, os, re, shutil, subprocess, zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
INPUTS = Path(os.environ.get("J8_INPUTS", str(Path.home() / "a2hlab/build-runs/20260929-oh6.1.0.31-b7/inputs")))
BASE = HERE / "baseline-stubs.jar"
OUTJAR = HERE / "adapter-mainline-stubs-t7e.jar"
WORK = HERE / "work_stubs"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run(a, **k):
    print("+", " ".join(map(str, a))); subprocess.run([str(x) for x in a], check=True, **k)


def jar(n):
    p = INPUTS / n; assert p.exists(), p; return str(p)


def baksmali(dex, out):
    run(["java", "-cp", ":".join(jar(x) for x in ["baksmali-2.5.2.jar", "dexlib2-2.5.2.jar",
         "guava-27.1-android.jar", "jcommander-1.64.jar", "util-2.5.2.jar"]),
         "org.jf.baksmali.Main", "disassemble", str(dex), "-o", str(out)])


def smali(ind, outdex):
    run(["java", "-cp", ":".join(jar(x) for x in ["smali-2.5.2.jar", "dexlib2-2.5.2.jar",
         "guava-27.1-android.jar", "jcommander-1.64.jar", "util-2.5.2.jar",
         "antlr-runtime-3.5.2.jar", "stringtemplate-3.2.1.jar"]),
         "org.jf.smali.Main", "assemble", str(ind), "-o", str(outdex)])


def main():
    print("INPUT  baseline-stubs.jar sha256:", sha(BASE))
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir()
    bexp = WORK / "base"; bexp.mkdir()
    with zipfile.ZipFile(BASE) as z:
        z.extractall(bexp)
    dexes = sorted(p for p in bexp.iterdir() if re.fullmatch(r"classes\d*\.dex", p.name))
    assert dexes, "no dex in stubs jar"
    smt = WORK / "smali"; smt.mkdir()
    for d in dexes:
        baksmali(d, smt)
    base_classes = {str(p.relative_to(smt)) for p in smt.rglob("*.smali")}
    print(f"stubs dex: {[d.name for d in dexes]}; classes: {len(base_classes)}")

    # compile ColorMatrix -> smali
    cdir = WORK / "c"; cdir.mkdir()
    run(["javac", "-source", "8", "-target", "8", "-d", str(cdir), str(HERE / "src" / "ColorMatrix.java")])
    ddir = WORK / "d"; ddir.mkdir()
    run(["java", "-cp", jar("d8.jar"), "com.android.tools.r8.D8", "--min-api", "28",
         "--output", str(ddir), *[str(p) for p in cdir.rglob("*.class")]])
    csm = WORK / "csm"; baksmali(ddir / "classes.dex", csm)
    newcm = csm / "android/graphics/ColorMatrix.smali"
    assert newcm.exists()

    dst = smt / "android/graphics/ColorMatrix.smali"
    assert dst.exists(), "ColorMatrix not in stubs baseline"
    old_body = dst.read_text()
    shutil.copy(newcm, dst)
    assert dst.read_text() != old_body, "ColorMatrix unchanged?"

    outdex = WORK / "out.dex"; smali(smt, outdex)
    if OUTJAR.exists():
        OUTJAR.unlink()
    with zipfile.ZipFile(BASE) as zin, zipfile.ZipFile(OUTJAR, "w", zipfile.ZIP_DEFLATED) as zo:
        for n in zin.namelist():
            if re.fullmatch(r"classes\d*\.dex", n):
                continue
            zo.writestr(n, zin.read(n))
        zo.write(outdex, "classes.dex")

    # verify only ColorMatrix changed
    v = WORK / "v"; v.mkdir()
    with zipfile.ZipFile(OUTJAR) as z:
        z.extractall(v)
    vt = WORK / "vt"; vt.mkdir()
    for d in sorted(p for p in v.iterdir() if re.fullmatch(r"classes\d*\.dex", p.name)):
        baksmali(d, vt)
    new_classes = {str(p.relative_to(vt)) for p in vt.rglob("*.smali")}
    added, removed = new_classes - base_classes, base_classes - new_classes
    print("ADDED:", sorted(added), "REMOVED:", sorted(removed))
    assert not added and not removed, (added, removed)
    print("OUTPUT adapter-mainline-stubs-t7e.jar sha256:", sha(OUTJAR))
    print("STUBS-BUILD OK (has set(ColorMatrix): verify below)")


if __name__ == "__main__":
    main()
