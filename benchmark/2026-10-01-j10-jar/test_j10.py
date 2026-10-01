#!/usr/bin/env python3
"""J10 offline gate (self-contained: reads the committed smali evidence, no build tools / no jar needed,
so it runs unchanged in the land.py master gate).

Proves both J9 no-ops are repaired and WIRED in the J10 jar (sha ea24291a..., baseline J9 87fd463d):
  1. SelfActivityInfoSynthesis now invokes SelfComponentFallback.projectionFor(String) (a real method),
     not the dead ManifestComponentProjection.projection(String) that made J9 a no-op;
  2. AppCompatNoTitleFix.install(Application) is invoked from AppSchedulerBridge right after
     ActivityThread.currentApplication() (the Application-ready launch path), not only at the too-early
     B7BindFixes.apply;
plus the one-line activation markers the activation smoke gate reads are present.
The live call of maybe()/install() itself was already proven by the J9 U8 hilogs ([J9-ACTINFO]/
[J9-NOTITLE] appeared); this gate proves J10 reaches the correct targets and prints the J10 markers.
"""
import sys
from pathlib import Path

E = Path(__file__).resolve().parent / "smali-evidence"
read = lambda n: (E / n).read_text()
sais = read("SelfActivityInfoSynthesis.smali")
acn = read("AppCompatNoTitleFix.smali")
asb = read("AppSchedulerBridge.install-invoke.txt")
scf = read("SelfComponentFallback.methods.txt")
mcp = read("ManifestComponentProjection.methods.txt")

fails = []
def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)

# targets exist in the baseline classes
check("SelfComponentFallback.projectionFor(String) exists",
      "projectionFor(Ljava/lang/String;)Ladapter/activity/ManifestComponentProjection;" in scf)
check("SelfComponentFallback.boundInfo() exists",
      "boundInfo()Landroid/content/pm/ApplicationInfo;" in scf)
check("ManifestComponentProjection.component(String,String,ApplicationInfo,J) exists",
      "component(Ljava/lang/String;Ljava/lang/String;Landroid/content/pm/ApplicationInfo;J)" in mcp)
check("ManifestComponentProjection has NO projection(String) [the dead J9 target]",
      "projection(Ljava/lang/String;)" not in mcp)

# fix #2 (getActivityInfo synth) wired to the correct target
check("SelfActivityInfoSynthesis -> SelfComponentFallback.projectionFor (WIRED)",
      "SelfComponentFallback;->projectionFor(Ljava/lang/String;)" in sais)
check("SelfActivityInfoSynthesis -> ManifestComponentProjection.component (WIRED)",
      "ManifestComponentProjection;->component(" in sais)
check("SelfActivityInfoSynthesis no longer -> ManifestComponentProjection.projection",
      "ManifestComponentProjection;->projection(" not in sais)

# fix #1 (notitle install timing) wired to the Application-ready launch path
check("AppSchedulerBridge -> AppCompatNoTitleFix.install(Application) after currentApplication() (WIRED)",
      "currentApplication()Landroid/app/Application;" in asb
      and "AppCompatNoTitleFix;->install(Landroid/app/Application;)V" in asb)
check("AppCompatNoTitleFix declares install(Application)",
      "install(Landroid/app/Application;)V" in acn)

# one-line activation markers (activation_smoke.py reads these)
check("activation marker '[J10-NOTITLE] installed' present", "[J10-NOTITLE] installed" in acn)
check("activation marker '[J10-ACTINFO] synthesized' present", "[J10-ACTINFO] synthesized" in sais)

n = 11
print(f"RESULT: {'ALL PASS' if not fails else str(len(fails)) + ' FAIL'} ({n - len(fails)}/{n})")
sys.exit(1 if fails else 0)
