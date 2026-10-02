#!/bin/bash
# Add the android.net stub members (members.tsv) to a DEPLOYED adapter-mainline-stubs.jar, nothing else.
#
#   build_patch.sh <deployed adapter-mainline-stubs.jar> <out.jar> [work dir]
#
# donor/ (Java, AOSP android-14.0.0_r1 sources cited per member) -> javac -> d8 -> baksmali; the deployed jar's
# classes.dex -> baksmali; merge_smali.py adds only the listed members / new classes (refuses anything else); smali
# -> classes.dex; the out jar is the deployed jar with only classes.dex replaced (resources such as T8's
# libphonenumber metadata stay). Same baksmali/smali 2.5.2 and API level as T8 (build_t8_effective.sh).
# This is a BCP jar: deploying it means an ART boot-image rebake (FZ-005 toolchain), as for T8.
set -euo pipefail
BASE=${1:?usage: build_patch.sh <deployed adapter-mainline-stubs.jar> <out.jar> [work dir]}
OUT=${2:?usage: build_patch.sh <deployed adapter-mainline-stubs.jar> <out.jar> [work dir]}
HERE=$(cd "$(dirname "$0")" && pwd)
WORKSPACES="${WORKSPACES:-$HOME/orca/workspaces}"
WORK=${3:-$(mktemp -d)}
T=$WORKSPACES/westlake-inputs/tools
CP="$T/baksmali-2.5.2.jar:$T/dexlib2-2.5.2.jar:$T/util-2.5.2.jar:$T/guava-31.1-jre.jar:$T/jcommander-1.78.jar:$T/failureaccess-1.0.1.jar:$T/smali-2.5.2.jar"
SDK=${ANDROID_SDK:-$HOME/Library/Android/sdk}
ANDROID_JAR=$SDK/platforms/android-34/android.jar
D8=$SDK/build-tools/37.0.0/d8
sha(){ shasum -a 256 "$1" | cut -d' ' -f1; }
# Pin the JDK instead of trusting PATH: a bare PATH finds the system JDK 1.8 (no --release) -- that is how land.py's
# gate run failed on 2026-10-02. Use $JAVA_HOME when it is >= 11, else the mise-pinned temurin-21 that env-mac.sh uses.
jdk_ok(){ [ -x "$1/javac" ] && "$1/javac" -version 2>&1 | grep -Eq 'javac (1[1-9]|[2-9][0-9])'; }
if [ -n "${JAVA_HOME:-}" ] && jdk_ok "$JAVA_HOME/bin"; then JDK_BIN=$JAVA_HOME/bin
else JDK_BIN=$(ls -d "$HOME"/.local/share/mise/installs/java/temurin-21*/bin 2>/dev/null | head -1); fi
jdk_ok "${JDK_BIN:-/nonexistent}" || { echo "FATAL: need a JDK >= 11 (JAVA_HOME or mise temurin-21)" >&2; exit 2; }
export PATH="$JDK_BIN:$PATH"

/bin/rm -rf "$WORK"/{classes,donor.dex.d,base,donor_smali,merged.dex}
mkdir -p "$WORK/classes" "$WORK/donor.dex.d" "$WORK/base"
echo "[net-stubs] base $(sha "$BASE")  $BASE"

# donor: compile against android.jar for android.os / java types; the donor's own android.net sources win
find "$HERE/donor" -name '*.java' > "$WORK/sources.txt"
javac --release 11 -nowarn -encoding UTF-8 -cp "$ANDROID_JAR" -d "$WORK/classes" @"$WORK/sources.txt"
( cd "$WORK/classes" && find . -name '*.class' ) > "$WORK/classfiles.txt"
"$D8" --release --min-api 29 --lib "$ANDROID_JAR" --output "$WORK/donor.dex.d" \
      $(sed "s#^\./#$WORK/classes/#" "$WORK/classfiles.txt")
java -cp "$CP" org.jf.baksmali.Main d "$WORK/donor.dex.d/classes.dex" -o "$WORK/donor_smali"

# deployed base -> merge -> dex
( cd "$WORK/base" && unzip -oq "$BASE" classes.dex )
java -cp "$CP" org.jf.baksmali.Main d "$WORK/base/classes.dex" -o "$WORK/base/smali"
python3 "$HERE/merge_smali.py" "$WORK/base/smali" "$WORK/donor_smali" "$HERE/members.tsv" --report "$WORK/merge-report.json"
java -cp "$CP" org.jf.smali.Main a -a 29 "$WORK/base/smali" -o "$WORK/merged.dex"

cp "$BASE" "$OUT"
chmod u+w "$OUT"
mkdir -p "$WORK/pack" && cp "$WORK/merged.dex" "$WORK/pack/classes.dex"
( cd "$WORK/pack" && zip -q "$OUT" classes.dex )
# smali 2.5.2 lays out type_list / annotation items in a run-dependent order (code and class_data are identical
# run to run, baksmali output identical), so the jar SHA is per build; the merged smali tree hash is the
# reproducible content identity -- a rebuild must reproduce it.
TREE=$(cd "$WORK/base/smali" && find . -type f -name '*.smali' | LC_ALL=C sort | while read -r f; do printf '%s\n' "$f"; cat "$f"; done | shasum -a 256 | cut -d' ' -f1)
cat > "$OUT.receipt.json" <<EOF
{"base_jar_sha256": "$(sha "$BASE")", "out_jar_sha256": "$(sha "$OUT")",
 "out_classes_dex_sha256": "$(sha "$WORK/merged.dex")", "merged_smali_tree_sha256": "$TREE",
 "members_tsv_sha256": "$(sha "$HERE/members.tsv")", "merge_smali_py_sha256": "$(sha "$HERE/merge_smali.py")",
 "donor_sources_sha256": "$(cd "$HERE/donor" && find . -name '*.java' | LC_ALL=C sort | xargs cat | shasum -a 256 | cut -d' ' -f1)",
 "smali_jar_sha256": "$(sha "$T/smali-2.5.2.jar")", "baksmali_jar_sha256": "$(sha "$T/baksmali-2.5.2.jar")",
 "android_jar_sha256": "$(sha "$ANDROID_JAR")", "d8": "$("$D8" --version 2>&1 | head -1)", "javac": "$(javac -version 2>&1)"}
EOF
echo "[net-stubs] out  $(sha "$OUT")  $OUT"
echo "[net-stubs] merged smali tree $TREE (reproducible content identity); receipt $OUT.receipt.json"
echo "[net-stubs] merge report $WORK/merge-report.json"
