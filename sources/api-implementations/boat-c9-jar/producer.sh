#!/bin/bash
# C9-ONLY jar: our U13 oh-adapter-runtime.jar (bbc3f530) + ONLY C9 touch (InputEventDeviceProjection + the
# AppSchedulerBridge.dispatchOnMainThread wiring our native already calls). NO C8 CapybaraLetterboxProjection, NO
# ensureBindApplication install splice (the C8 ADAPTER 8ab85446 owns landscape now; the jar must NOT letterbox).
# x2 byte-identical, STORED. Deployed with the C8 adapter -> expected full-screen landscape + touch, no white band.
set -euo pipefail
SC=${SC:?set SC to the jarbuild scratch dir (has our/smali, boat/smali)}
WORKSPACES=${WORKSPACES:-$HOME/orca/workspaces}   # the dir holding westlake-inputs/ (gate: check_user_paths.py)
T="$WORKSPACES/westlake-inputs/tools"
BASE_JAR=${BASE_JAR:?U13 jar bbc3f530}
BOAT_SMALI="$SC/boat/smali/adapter/activity"
SMALICP="$T/smali-2.5.2.jar:$T/dexlib2-2.5.2.jar:$T/util-2.5.2.jar:$T/guava-31.1-jre.jar:$T/jcommander-1.78.jar"
build_pass(){
  local O="$SC/$1"; /bin/rm -rf "$O"; mkdir -p "$O/jar"; cp -r "$SC/our/smali" "$O/smali"
  local AA="$O/smali/adapter/activity"
  # C9 class only (+ inner). NO CapybaraLetterboxProjection.
  cp "$BOAT_SMALI/InputEventDeviceProjection.smali" "$BOAT_SMALI/InputEventDeviceProjection\$1.smali" "$AA/"
  # C9 wiring: add dispatchOnMainThread to AppSchedulerBridge (NO install splice).
  python3 - "$AA/AppSchedulerBridge.smali" <<'PY'
import sys
p=sys.argv[1]; s=open(p).read()
assert 'dispatchOnMainThread' not in s, 'already present'
m='''.method public static dispatchOnMainThread(Landroid/view/InputEventReceiver;ILandroid/view/InputEvent;)V
    .registers 3

    invoke-static {p0, p1, p2}, Ladapter/activity/InputEventDeviceProjection;->dispatchOnMainThread(Landroid/view/InputEventReceiver;ILandroid/view/InputEvent;)V

    return-void
.end method

'''
i=s.index('.method ')
open(p,'w').write(s[:i]+m+s[i:])
print('AppSchedulerBridge: dispatchOnMainThread added (C9 only, no install splice)')
PY
  java -cp "$SMALICP" org.jf.smali.Main assemble "$O/smali" --api 23 --jobs 1 -o "$O/jar/classes.dex"
  ( cd "$O/jar" && unzip -o -q "$BASE_JAR" META-INF/MANIFEST.MF )
  python3 - "$O/jar" "$O/oh-adapter-runtime.jar" <<'PY'
import sys,zipfile,os
root,out=sys.argv[1],sys.argv[2]; zo=zipfile.ZipFile(out,"w")
for n in ["META-INF/MANIFEST.MF","classes.dex"]:
    zi=zipfile.ZipInfo(n,(1980,1,1,0,0,0)); zi.external_attr=0o644<<16; zi.compress_type=zipfile.ZIP_STORED
    zo.writestr(zi,open(os.path.join(root,n),"rb").read())
zo.close()
PY
  shasum -a 256 "$O/oh-adapter-runtime.jar" | cut -d' ' -f1
}
A=$(build_pass c9A | tail -1); B=$(build_pass c9B | tail -1)
echo "passA=$A"; echo "passB=$B"
[ "$A" = "$B" ] || { echo "NOT byte-identical"; exit 9; }
cp "$SC/c9A/oh-adapter-runtime.jar" "$SC/oh-adapter-runtime.c9only.jar"
echo "C9-only jar sha256: $A (x2 byte-identical)"
