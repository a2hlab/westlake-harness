#!/bin/bash
# T8 re-bake jars — EFFECTIVE base (fix for ACK(90) 2026-10-02 10:50:30).
#
# Prior-build bug: adapter-mainline-stubs base came from the generation's native/payload UNDERLAY
# (beb369a1), but the board runs the framework/ EFFECTIVE copy (f3bcc9d7), which carries frozen
# FZ-007 (full tagsoup, Parser super=DefaultHandler), FZ-008 (android.net.ssl.SSLSockets) and
# NetworkInfo$State. Baking from the underlay would drop those on deploy. rb/t4b/G1/G2 missed it
# because they compare against an image reference, not the deployed jar; deployed_class_diff.py catches it.
#
# This build:
#   - adapter-mainline-stubs base = framework/ EFFECTIVE f3bcc9d7, only ADD ① conscrypt SSLParametersImpl
#     presence stub + ③a real AOSP libphonenumber (frozen APIs untouched).
#   - oh-adapter-framework base = the single native/payload copy f38ec312 + ② getInstallSourceInfo.
#   - the other 7 boot jars = native/payload copies, unchanged.
#   GEN paths are explicit (no glob). ③a reuses the persisted, already-compiled libphonenumber dex
#   (t8-rebake/intermediate/libphonenumber.dex dff827b5), so no VM is needed. All smali on the Mac.
set -uo pipefail
WORKSPACES="${WORKSPACES:-$HOME/orca/workspaces}"

T=$WORKSPACES/westlake-inputs/tools
CP="$T/baksmali-2.5.2.jar:$T/dexlib2-2.5.2.jar:$T/util-2.5.2.jar:$T/guava-31.1-jre.jar:$T/jcommander-1.78.jar:$T/failureaccess-1.0.1.jar:$T/smali-2.5.2.jar"
BAK="java -cp $CP org.jf.baksmali.Main"
SMALI="java -cp $CP org.jf.smali.Main"
DEXDUMP=${DEXDUMP:-$HOME/Library/Android/sdk/build-tools/37.0.0/dexdump}

GEN=$WORKSPACES/westlake-generation-u9-j10g-238ffc14
GEN_EFF="$GEN/framework"                           # effective overlay: adapter-mainline-stubs f3bcc9d7
GEN_UND="$GEN/native/payload/android/framework"    # underlay: 8 jars incl oh-adapter-framework f38ec312
OLD=$WORKSPACES/westlake-inputs/generations/t8-rebake
STAGE=$WORKSPACES/westlake-inputs/generations/t8-rebake-effective
LPN_DEX="$OLD/intermediate/libphonenumber.dex"            # dff827b5, reused (compiled earlier in VM)
LPN_DATA_BASE="$OLD/src-snapshot/libphonenumber/src"      # has com/android/i18n/phonenumbers/data (541)
WORK=${WORK:-/tmp/t8eff}

UND_JARS=(core-oj core-libart core-icu4j okhttp bouncycastle apache-xml framework oh-adapter-framework)
sha(){ shasum -a 256 "$1" | cut -d' ' -f1; }

/bin/rm -rf "$WORK"; /bin/mkdir -p "$WORK" "$STAGE/jars9" "$STAGE/receipt"

echo "[t8e] assemble 9-jar EFFECTIVE base set -> $STAGE/jars9/"
cp "$GEN_EFF/adapter-mainline-stubs.jar" "$STAGE/jars9/adapter-mainline-stubs.jar"   # EFFECTIVE f3bcc9d7
for j in "${UND_JARS[@]}"; do cp "$GEN_UND/$j.jar" "$STAGE/jars9/$j.jar" || { echo "FATAL copy $j"; exit 2; }; done
echo "  base mainline-stubs (EFFECTIVE) = $(sha "$STAGE/jars9/adapter-mainline-stubs.jar")  (expect f3bcc9d7..)"
echo "  base oh-adapter-framework       = $(sha "$STAGE/jars9/oh-adapter-framework.jar")    (expect f38ec312..)"

# ---------------- ② oh-adapter-framework.jar : getInstallSourceInfo -> all-null InstallSourceInfo ----
echo "[t8e 2] oh-adapter-framework / PackageManagerAdapter.getInstallSourceInfo"
cd "$WORK"; /bin/mkdir -p ohaf; cd ohaf
unzip -oq "$STAGE/jars9/oh-adapter-framework.jar" classes.dex
$BAK d classes.dex -o smali >/dev/null 2>&1 || { echo "FATAL baksmali ohaf"; exit 3; }
PMA=smali/adapter/packagemanager/PackageManagerAdapter.smali
test -f "$PMA" || { echo "FATAL: PackageManagerAdapter.smali missing"; exit 3; }
python3 - "$PMA" <<'PY'
import re,sys
p=sys.argv[1]; s=open(p).read()
new=(".method public getInstallSourceInfo(Ljava/lang/String;I)Landroid/content/pm/InstallSourceInfo;\n"
"    .locals 5\n"
"    .annotation system Ldalvik/annotation/Throws;\n"
"        value = {\n"
"            Landroid/os/RemoteException;\n"
"        }\n"
"    .end annotation\n\n"
'    const-string v0, "getInstallSourceInfo"\n\n'
'    const-string v1, ""\n\n'
"    invoke-direct {p0, v0, v1}, Ladapter/packagemanager/PackageManagerAdapter;->logStub(Ljava/lang/String;Ljava/lang/String;)V\n\n"
"    new-instance v0, Landroid/content/pm/InstallSourceInfo;\n\n"
"    const/4 v1, 0x0\n\n"
"    const/4 v2, 0x0\n\n"
"    const/4 v3, 0x0\n\n"
"    const/4 v4, 0x0\n\n"
"    invoke-direct {v0, v1, v2, v3, v4}, Landroid/content/pm/InstallSourceInfo;-><init>(Ljava/lang/String;Landroid/content/pm/SigningInfo;Ljava/lang/String;Ljava/lang/String;)V\n\n"
"    return-object v0\n"
".end method")
pat=re.compile(r'\.method public getInstallSourceInfo\(Ljava/lang/String;I\)Landroid/content/pm/InstallSourceInfo;.*?\.end method', re.S)
m=pat.search(s); assert m, "getInstallSourceInfo not found"
s2=s[:m.start()]+new+s[m.end():]; assert s2!=s
open(p,'w').write(s2); print("  [2] method replaced (4-arg all-null ctor, Throws kept)")
PY
[ $? -eq 0 ] || { echo "FATAL python edit 2"; exit 3; }
$SMALI a -a 29 smali -o classes.dex.new >/dev/null 2>&1 || { echo "FATAL smali ohaf"; exit 3; }
mv classes.dex.new classes.dex
( cd "$WORK/ohaf" && zip -q "$STAGE/jars9/oh-adapter-framework.jar" classes.dex ) || { echo "FATAL zip ohaf"; exit 3; }
echo "  patched SHA oh-adapter-framework = $(sha "$STAGE/jars9/oh-adapter-framework.jar")"

# ---------------- ① + ③a adapter-mainline-stubs.jar on EFFECTIVE f3bcc9d7 base ----------------------
echo "[t8e 1+3a] adapter-mainline-stubs (effective f3bcc9d7): add conscrypt stub + real libphonenumber"
cd "$WORK"; /bin/mkdir -p mls; cd mls
unzip -oq "$STAGE/jars9/adapter-mainline-stubs.jar" classes.dex
$BAK d classes.dex -o smali >/dev/null 2>&1 || { echo "FATAL baksmali mls"; exit 4; }
# 3a: remove the top-level phonenumbers shells (keep geocoding/ subdir), drop in the real libphonenumber
find smali/com/android/i18n/phonenumbers -maxdepth 1 -name '*.smali' -delete
$BAK d "$LPN_DEX" -o lpn_smali >/dev/null 2>&1 || { echo "FATAL baksmali lpn"; exit 4; }
cp -r lpn_smali/com/android/i18n/phonenumbers/. smali/com/android/i18n/phonenumbers/
# 1: conscrypt SSLParametersImpl presence stub (private throwing ctor; okhttp only Class.forName's it)
/bin/mkdir -p smali/com/android/org/conscrypt
cat > smali/com/android/org/conscrypt/SSLParametersImpl.smali <<'SMALI'
.class public Lcom/android/org/conscrypt/SSLParametersImpl;
.super Ljava/lang/Object;
.source "SSLParametersImpl.java"
.method private constructor <init>()V
    .locals 2
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V
    new-instance v0, Ljava/lang/UnsupportedOperationException;
    const-string v1, "westlake presence-only stub for okhttp platform detection; not real Conscrypt"
    invoke-direct {v0, v1}, Ljava/lang/UnsupportedOperationException;-><init>(Ljava/lang/String;)V
    throw v0
.end method
SMALI
$SMALI a -a 29 smali -o classes.dex.new >/dev/null 2>&1 || { echo "FATAL smali mls"; exit 4; }
mv classes.dex.new classes.dex
# fresh effective jar -> replace classes.dex -> add 541 metadata resources
cp "$GEN_EFF/adapter-mainline-stubs.jar" "$STAGE/jars9/adapter-mainline-stubs.jar"
( cd "$WORK/mls" && zip -q "$STAGE/jars9/adapter-mainline-stubs.jar" classes.dex ) || { echo "FATAL zip mls dex"; exit 4; }
( cd "$LPN_DATA_BASE" && zip -qr "$STAGE/jars9/adapter-mainline-stubs.jar" com/android/i18n/phonenumbers/data ) || { echo "FATAL zip metadata"; exit 4; }
echo "  patched SHA adapter-mainline-stubs = $(sha "$STAGE/jars9/adapter-mainline-stubs.jar")"

# ---------------- verify (frozen APIs must survive) ----------------
echo "[t8e] dexdump verify:"
cd "$WORK/mls"; rm -rf chk; unzip -oq "$STAGE/jars9/adapter-mainline-stubs.jar" 'classes*.dex' -d chk 2>/dev/null
for d in chk/classes*.dex; do "$DEXDUMP" -l plain "$d" 2>/dev/null; done > chk/dump.txt
echo -n "  [1] SSLParametersImpl present (want >=1): "; LC_ALL=C grep -c "Lcom/android/org/conscrypt/SSLParametersImpl;" chk/dump.txt
echo -n "  [3a] getInstance present (want >=1): "; LC_ALL=C grep -cE "name +: +'getInstance'" chk/dump.txt
echo -n "  FZ-007 tagsoup Parser super=DefaultHandler (want 1): "; LC_ALL=C grep -A3 "descriptor  : 'Lorg/ccil/cowan/tagsoup/Parser;'" chk/dump.txt | LC_ALL=C grep -c "Superclass.*Lorg/xml/sax/helpers/DefaultHandler;"
echo -n "  FZ-008 SSLSockets present (want >=1): "; LC_ALL=C grep -Fc 'Landroid/net/ssl/SSLSockets;' chk/dump.txt
echo -n "  NetworkInfo\$State present (want >=1): "; LC_ALL=C grep -Fc 'Landroid/net/NetworkInfo$State;' chk/dump.txt
echo -n "  android/compat leak (want 0): "; LC_ALL=C grep -c "Landroid/compat/annotation" chk/dump.txt
echo -n "  dex version (want 039): "; LC_ALL=C head -c 8 chk/classes.dex | xxd | awk '{print $3$4}'
echo "[t8e] jars done -> $STAGE/jars9/"
