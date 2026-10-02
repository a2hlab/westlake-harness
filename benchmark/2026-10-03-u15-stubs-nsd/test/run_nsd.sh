#!/bin/bash
# run_nsd.sh <adapter-mainline-stubs.jar> : NsdTest on host ART (android-14.0.0_r1) with the boards' BCP, only the
# stubs jar swapped (host-shim-v1.jar = test-only Log + SystemClock before framework.jar, as in 2026-10-03-u14-jar-v1)
R=${NSD_RUN_DIR:?set NSD_RUN_DIR: hw248 dir with boot/ (board BCP jars) and jars/ (test, shim)}
O=${ART_HOST_OUT:?set ART_HOST_OUT: android-14.0.0_r1 host ART out/host/linux-x86}
export ANDROID_ROOT=$O ANDROID_ART_ROOT=$O/com.android.art ANDROID_I18N_ROOT=$O/com.android.i18n ANDROID_TZDATA_ROOT=$O/com.android.tzdata
export ANDROID_DATA=$R/data; mkdir -p $ANDROID_DATA/dalvik-cache/x86_64
export LD_LIBRARY_PATH=$O/lib64
BCP=$R/boot/core-oj.jar:$R/boot/core-libart.jar:$R/boot/okhttp.jar:$R/boot/bouncycastle.jar:$R/boot/apache-xml.jar:$R/boot/core-icu4j.jar:$R/jars/host-shim-v1.jar:$R/boot/framework.jar:$1:$R/boot/oh-adapter-framework.jar
timeout 300 $O/bin/dalvikvm64 -Xuse-stderr-logger -Xint -Ximage:$R/no-image.art -Xbootclasspath:$BCP -Xbootclasspath-locations:$BCP \
  -cp $R/jars/nsd-test.jar NsdTest
echo "rc=$?"
