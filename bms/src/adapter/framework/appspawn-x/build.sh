#!/bin/bash
set -e
export JAVA_HOME=/opt/build-trees/aosp/prebuilts/jdk/jdk17/linux-x86
export PATH=$JAVA_HOME/bin:$PATH
A=/opt/build-trees/aosp
D8=$A/out/host/linux-x86/bin/d8
B=/tmp/rtbuild
ADP=/opt/build-trees/adapter/out/adapter/classes
CP=$A/out/soong/.intermediates/frameworks/base/framework-minus-apex/android_common/turbine/framework-minus-apex.jar:$A/out/soong/.intermediates/libcore/core-oj/android_common/turbine/core-oj.jar:$A/out/soong/.intermediates/libcore/core-libart/android_common/turbine/core-libart.jar:$ADP:$B/stubs

cd $B
cp /tmp/ApkSignatureBridge.selftest.java $B/src/ApkSignatureBridge.java

echo "== javac =="
rm -rf $B/cnew; mkdir -p $B/cnew
javac --release 17 -cp "$CP" -sourcepath $B/stubs -d $B/cnew $B/src/ApkSignatureBridge.java 2> $B/javac.log || { echo JAVAC_FAIL; cat $B/javac.log; exit 1; }
ls $B/cnew/com/android/internal/os/

echo "== d8 bridge dex =="
rm -rf $B/cnew_dex; mkdir -p $B/cnew_dex
$D8 --min-api 26 --output $B/cnew_dex $B/cnew/com/android/internal/os/*.class 2> $B/d8.log || { echo D8_FAIL; cat $B/d8.log; exit 1; }
ls -la $B/cnew_dex/

echo "== d8 merge board20 + bridge =="
rm -rf $B/merged; mkdir -p $B/merged
$D8 --min-api 26 --output $B/merged $B/board20/classes.dex $B/cnew_dex/classes.dex 2> $B/merge.log || { echo MERGE_FAIL; cat $B/merge.log; exit 1; }
ls -la $B/merged/

echo "== jar =="
(cd $B/merged && jar cf $B/oh-adapter-runtime.selftest.jar classes.dex)
ls -la $B/oh-adapter-runtime.selftest.jar
echo "BUILD_OK"
