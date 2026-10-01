#!/usr/bin/env python3
"""J10c offline gate (self-contained smali-evidence). J10c = J10b + the applied-line diagnostic that also
reports the app's OWN androidx windowActionBar/windowNoTitle (what AppCompatDelegateImpl.createSubDecor
actually reads). Proves the bootstrap wiring (unchanged from J10b) + the new app-attr diagnostic."""
import sys
from pathlib import Path
E=Path(__file__).resolve().parent/"smali-evidence"
boot=(E/"J10bAppBootstrap.smali").read_text(); cbk=(E/"J10bAppBootstrap$Callbacks.smali").read_text()
inj=(E/"AppSchedulerBridge.schedule-inject.txt").read_text()
kac=(E/"knot-AppCompatDelegateImpl.createSubDecor.smali").read_text()
fails=[]
def ck(n,c):
    print(("PASS " if c else "FAIL ")+n); 
    if not c: fails.append(n)
ck("schedule() injected at nativeOnScheduleLaunchAbility entry", "nativeOnScheduleLaunchAbility(" in inj and "J10bAppBootstrap;->schedule()V" in inj)
ck("bootstrap -> makeApplicationInner", "makeApplicationInner" in boot)
ck("bootstrap -> getPackageInfoNoCheck", "getPackageInfoNoCheck" in boot)
ck("bootstrap sets mInitialApplication", "mInitialApplication" in boot)
ck("bootstrap -> SelfComponentFallback.boundInfo", "SelfComponentFallback;->boundInfo" in boot)
ck("registers NoTitle callback", "registerActivityLifecycleCallbacks" in boot)
ck("J10c diagnostic resolves app attr by name (getIdentifier)", "getIdentifier" in cbk)
ck("applied line prints app windowActionBar", "app windowActionBar=" in cbk)
ck("marker [J10b-APP]", "[J10b-APP] mInitialApplication set" in boot)
ck("marker [J10b-NOTITLE] installed", "[J10b-NOTITLE] installed" in boot)
ck("marker [J10b-NOTITLE] applied", "[J10b-NOTITLE] applied" in cbk)
ck("EVIDENCE knot createSubDecor reads androidx AppCompatTheme_windowActionBar", "AppCompatTheme_windowActionBar" in kac)
n=12; print(f"RESULT: {'ALL PASS' if not fails else str(len(fails))+' FAIL'} ({n-len(fails)}/{n})")
sys.exit(1 if fails else 0)
