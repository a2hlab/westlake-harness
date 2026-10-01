#!/usr/bin/env python3
"""J10b offline gate (self-contained: reads committed smali-evidence; runs in the land.py master gate).
Proves the design-3' fix is wired into J10b (cb392c96, baseline J10 ea24291a): schedule() injected at
nativeOnScheduleLaunchAbility entry; bootstrap uses makeApplicationInner/getPackageInfoNoCheck/
mInitialApplication/SelfComponentFallback.boundInfo + registers the NoTitle callback; the three
[J10b-*] activation markers the activation smoke gate reads are present."""
import sys
from pathlib import Path
E = Path(__file__).resolve().parent / "smali-evidence"
boot = (E / "J10bAppBootstrap.smali").read_text()
cbk = (E / "J10bAppBootstrap$Callbacks.smali").read_text()
inj = (E / "AppSchedulerBridge.schedule-inject.txt").read_text()
fails = []
def ck(n, c):
    print(("PASS " if c else "FAIL ") + n)
    if not c: fails.append(n)
ck("schedule() injected at nativeOnScheduleLaunchAbility entry",
   "nativeOnScheduleLaunchAbility(" in inj and "J10bAppBootstrap;->schedule()V" in inj)
ck("bootstrap -> LoadedApk.makeApplicationInner", "makeApplicationInner" in boot)
ck("bootstrap -> ActivityThread.getPackageInfoNoCheck", "getPackageInfoNoCheck" in boot)
ck("bootstrap sets mInitialApplication", "mInitialApplication" in boot)
ck("bootstrap -> SelfComponentFallback.boundInfo", "SelfComponentFallback;->boundInfo" in boot)
ck("registers NoTitle ActivityLifecycleCallbacks", "registerActivityLifecycleCallbacks" in boot)
ck("Callbacks.onActivityPreCreated applies Theme_NoTitleBar", "applyStyle" in cbk)
ck("marker [J10b-APP] mInitialApplication set", "[J10b-APP] mInitialApplication set" in boot)
ck("marker [J10b-NOTITLE] installed", "[J10b-NOTITLE] installed" in boot)
ck("marker [J10b-NOTITLE] applied", "[J10b-NOTITLE] applied" in cbk)
n = 10
print(f"RESULT: {'ALL PASS' if not fails else str(len(fails))+' FAIL'} ({n-len(fails)}/{n})")
sys.exit(1 if fails else 0)
