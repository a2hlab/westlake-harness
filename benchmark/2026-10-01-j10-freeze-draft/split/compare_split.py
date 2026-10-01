#!/usr/bin/env python3
"""Prove the split U10-base jar is behaviour-identical to J10g 238ffc14: baksmali both, map the two
renamed classes, normalise class-name tokens, and diff every method body. Only class-name differences
(and the documented sLoggedDelegate relocation) are allowed."""
import re, subprocess, sys
from pathlib import Path
for _p in Path(__file__).resolve().parents:
    if (_p/"westlake-harness/scripts/lab/lab_paths.py").exists():
        sys.path.insert(0, str(_p/"westlake-harness/scripts/lab")); break
import lab_paths
WS = lab_paths.workspaces()
T = WS/"westlake-harness-bms-deploy/bms/src/.work/b6-task45/inputs"
BAK=":".join(str(T/j) for j in ["baksmali-2.5.2.jar","dexlib2-2.5.2.jar","guava-27.1-android.jar","jcommander-1.64.jar","util-2.5.2.jar"])
OLD = WS/"westlake-generation-j10g-staging/oh-adapter-runtime-j10g.jar"   # 238ffc14
NEW = Path(__file__).resolve().parent/"oh-adapter-runtime-u10base.jar"    # split
HERE = Path(__file__).resolve().parent
import tempfile, zipfile
def baksmali(jar, out):
    bj=out/"j"; bj.mkdir(parents=True)
    with zipfile.ZipFile(jar) as z: z.extractall(bj)
    s=out/"s"; subprocess.run(["java","-cp",BAK,"org.jf.baksmali.Main","disassemble",str(bj/"classes.dex"),"-o",str(s)],check=True)
    return s
# class rename map old->new (and we normalise both to a neutral token)
RENAME = {"J10eWebView$DelegateForward":"J10eViewDelegate", "J10eWebView$WlCookieManager":"J10eCookieManager"}
NEUT = {"J10eWebView$DelegateForward":"<DELEGATE>","J10eViewDelegate":"<DELEGATE>",
        "J10eWebView$WlCookieManager":"<COOKIE>","J10eCookieManager":"<COOKIE>"}
import re as _re
def norm(text):
    for k,v in NEUT.items(): text=text.replace(f"Ladapter/activity/{k};", v)
    lines=[]
    for l in text.splitlines():
        s=l.strip()
        if not s or s.startswith(("#",".line",".local ",".locals",".prologue",".param",".registers",".restart","    .line")): continue
        lines.append(s)
    body="\n".join(lines)
    # canonicalise label tokens (:cond_82 / :goto_7f / :try_start_3e / :catch_80 / :catchall_7e) by first-seen order
    labs={}
    def repl(m):
        tok=m.group(0)
        if tok not in labs: labs[tok]=f":L{len(labs)}"
        return labs[tok]
    body=_re.sub(r":[a-z_]+_[0-9a-f]+", repl, body)
    return body
def methods(smali_file):
    t=smali_file.read_text()
    out={}
    for m in re.finditer(r"\.method (.+?)\n(.*?)\.end method", t, re.S):
        out[m.group(1).strip()]=norm(m.group(2))
    return out
tmp=Path(tempfile.mkdtemp())
olds=baksmali(OLD, tmp/"old"); news=baksmali(NEW, tmp/"new")
AA="adapter/activity"
pairs=[("J10eWebView$DelegateForward","J10eViewDelegate"),("J10eWebView$WlCookieManager","J10eCookieManager"),
       ("J10eWebView","J10eWebView"),("J10eWebView$ProviderEnrich","J10eWebView$ProviderEnrich"),
       ("J10eWebView$ProviderInstance","J10eWebView$ProviderInstance"),("J10eWebView$ZeroH","J10eWebView$ZeroH"),
       ("J10fWebSettings","J10fWebSettings"),("J10fWebSettings$WlWebSettings","J10fWebSettings$WlWebSettings"),
       ("J10gWebExtras","J10gWebExtras")]
report=["# split-equivalence — split U10-base jar vs J10g 238ffc14 (method-body diff, class names normalised)\n",
        f"OLD (J10g) sha256 238ffc14… = `{__import__('hashlib').sha256(OLD.read_bytes()).hexdigest()}`",
        f"NEW (split U10-base) sha256 = `{__import__('hashlib').sha256(NEW.read_bytes()).hexdigest()}`\n",
        "Class tokens `J10eWebView$DelegateForward`↔`J10eViewDelegate` and `J10eWebView$WlCookieManager`↔"
        "`J10eCookieManager` are normalised to `<DELEGATE>`/`<COOKIE>`. A method is **IDENTICAL** if its body"
        " matches after that normalisation.\n","| old class | method | verdict |","|---|---|---|"]
ndiff=0; nident=0; notes=[]
for oc,nc in pairs:
    of=olds/AA/f"{oc}.smali"; nf=news/AA/f"{nc}.smali"
    if not of.exists() or not nf.exists():
        report.append(f"| {oc} | (class) | MISSING old={of.exists()} new={nf.exists()} |"); continue
    om=methods(of); nm=methods(nf)
    for sig in sorted(set(om)|set(nm)):
        if sig not in om: report.append(f"| {nc} | {sig} | NEW-ONLY |"); continue
        if sig not in nm: report.append(f"| {oc} | {sig} | OLD-ONLY (removed) |"); notes.append(f"{oc}.{sig} removed"); continue
        if om[sig]==nm[sig]: nident+=1
        else:
            ndiff+=1
            # characterise the diff
            ol=[l.strip() for l in om[sig].splitlines() if l.strip() and not l.strip().startswith(("#",".line",".local",".prologue",".param"))]
            nl=[l.strip() for l in nm[sig].splitlines() if l.strip() and not l.strip().startswith(("#",".line",".local",".prologue",".param"))]
            only_old=[x for x in ol if x not in nl]; only_new=[x for x in nl if x not in ol]
            report.append(f"| {oc} | {sig} | DIFFERS → old:{only_old} new:{only_new} |")
            notes.append(f"{oc}.{sig}: old {only_old} vs new {only_new}")
report.insert(5, f"\n**{nident} methods IDENTICAL (mod class names); {ndiff} differ (detailed below).**\n")
(HERE/"split-equivalence.md").write_text("\n".join(report)+"\n")
print(f"IDENTICAL(mod class-names): {nident}  DIFFER: {ndiff}")
for n in notes: print(" -", n)
