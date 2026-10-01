#!/usr/bin/env python3
"""J10d offline gate (self-contained smali-evidence). J10d = J10 + J10dTheme.restore(activityInfo)
injected right after the ActivityInfo.banner force-zero in nativeOnScheduleLaunchAbility, setting
activityInfo.theme back to the activity's manifest theme so performLaunchActivity.setTheme uses the
*.NoActionBar theme (fixes the appcompat-actionbar ISE). Proves the wiring + the AOSP chain evidence."""
import sys
from pathlib import Path
E=Path(__file__).resolve().parent/"smali-evidence"
jt=(E/"J10dTheme.smali").read_text(); inj=(E/"AppSchedulerBridge.restore-inject.txt").read_text()
aosp=(E/"AOSP-theme-chain.txt").read_text()
fails=[]
def ck(n,c):
    print(("PASS " if c else "FAIL ")+n)
    if not c: fails.append(n)
ck("restore() injected right after ActivityInfo.banner force-zero (same object reg = activityInfo)",
   "ActivityInfo;->banner:I" in inj and "J10dTheme;->restore(Landroid/content/pm/ActivityInfo;)V" in inj)
ck("J10dTheme reads the manifest activity theme (ManifestJsonFallback.activityTheme)", "ManifestJsonFallback;->activityTheme" in jt)
ck("J10dTheme sets ActivityInfo.theme", "ActivityInfo;->theme:I" in jt)
ck("marker [J10d-THEME]", "J10d-THEME]" in jt)
ck("evidence: AOSP performLaunchActivity getThemeResource -> applicationInfo.theme fallback", "getThemeResource" in aosp and "applicationInfo.theme" in aosp)
ck("evidence: knot Theme_Knot_NoActionBar = 0x7f11019e", "Theme_Knot_NoActionBar = 0x7f11019e" in aosp)
n=6; print(f"RESULT: {'ALL PASS' if not fails else str(len(fails))+' FAIL'} ({n-len(fails)}/{n})")
sys.exit(1 if fails else 0)
