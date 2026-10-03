#!/bin/bash
# Deterministic build of oh-adapter-runtime-u16-t3.jar (t1 recipe):
#   baksmali -> unique needle patch (asserted) -> smali assemble --jobs 1 -a 29
#   (jcommander 1.64 on CP; 1.78's PositiveInteger crashes on JDK 21)
#   -> python-zipfile repack onto the U15 base jar (classes.dex STORED, timestamps 1980-01-01).
# GATE: two passes -> identical jar bytes; deployed_class_diff --frozen vs U15: 0/0/0/0;
# smali file diff vs base: exactly adapter/activity/AppSchedulerBridge.smali changed.
set -euo pipefail
WS=${WORKSPACES:-$HOME/orca/workspaces}
BASE=$WS/westlake-inputs/generations/u15-jar-v1/oh-adapter-runtime-u15-v1.jar
T=$WS/westlake-inputs/tools
JC=$WS/westlake-harness-bms-deploy/bms/src/.work/b6-task45/inputs/jcommander-1.64.jar
CP="$T/baksmali-2.5.2.jar:$T/dexlib2-2.5.2.jar:$T/util-2.5.2.jar:$T/guava-31.1-jre.jar:$JC:$T/failureaccess-1.0.1.jar:$T/smali-2.5.2.jar"
JDK=$(ls -d "$HOME"/.local/share/mise/installs/java/temurin-21*/bin | head -1); export PATH="$JDK:$PATH"
W=$(mktemp -d /tmp/u16t3-build.XXXXXX); trap 'rm -rf "$W"' EXIT
unzip -oq "$BASE" classes.dex -d "$W"
java -cp "$CP" org.jf.baksmali.Main disassemble "$W/classes.dex" -o "$W/smali"
python3 - "$W/smali/adapter/activity/AppSchedulerBridge.smali" << 'PY'
import sys
p = sys.argv[1]
t = open(p).read()
needle = ("    .line 1696\n"
          "    invoke-virtual {v1, v3}, Landroid/app/servertransaction/ClientTransaction;->addCallback(Landroid/app/servertransaction/ClientTransactionItem;)V\n")
assert t.count(needle) == 1, 'needle not unique: %d' % t.count(needle)
ins = (needle +
       "\n"
       "    # U16 t3: advance launch transaction to ON_START (AOSP handleLaunchActivity order):\n"
       "    # onCreate -> onStart run in ONE main-thread transaction; onStart inflates fragment views\n"
       "    # (weatherView lateinit) before the Looper resumes. onResume stays phase-2 (G2.14m intact).\n"
       "    invoke-static {}, Landroid/app/servertransaction/StartActivityItem;->obtain(Landroid/app/ActivityOptions;)Landroid/app/servertransaction/StartActivityItem;\n"
       "\n    move-result-object v3\n\n"
       "    invoke-virtual {v1, v3}, Landroid/app/servertransaction/ClientTransaction;->setLifecycleStateRequest(Landroid/app/servertransaction/ClientTransactionItem;)V\n")
open(p, 'w').write(t.replace(needle, ins))
PY
java -cp "$CP" org.jf.smali.Main a --jobs 1 -a 29 "$W/smali" -o "$W/classes-new.dex"
python3 - "$BASE" "$W/classes-new.dex" "$1" << 'PY'
import sys, zipfile
base, dex, out = sys.argv[1:4]
zin = zipfile.ZipFile(base)
with zipfile.ZipFile(out, 'w') as zout:
    for i in zin.infolist():
        zi = zipfile.ZipInfo(i.filename, date_time=(1980, 1, 1, 0, 0, 0))
        zi.compress_type = zipfile.ZIP_STORED if i.filename == 'classes.dex' else i.compress_type
        zout.writestr(zi, open(dex, 'rb').read() if i.filename == 'classes.dex' else zin.read(i.filename))
PY
echo "built $1"
