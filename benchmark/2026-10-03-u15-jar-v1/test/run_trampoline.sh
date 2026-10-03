#!/bin/bash
# run_trampoline.sh <boot dir> <runtime jar> : TrampolineOrderTest on host ART (android-14.0.0_r1) with a board boot class
# path (9 BCP jars in board order; host-shim-v1.jar = test-only Log + SystemClock before framework.jar)
R=${TFO_RUN_DIR:?set TFO_RUN_DIR: hw248 dir with jars/ (test, shim, runtime jars)}
O=${ART_HOST_OUT:?set ART_HOST_OUT: android-14.0.0_r1 host ART out/host/linux-x86}
B=${1:?boot dir}
export ANDROID_ROOT=$O ANDROID_ART_ROOT=$O/com.android.art ANDROID_I18N_ROOT=$O/com.android.i18n ANDROID_TZDATA_ROOT=$O/com.android.tzdata
export ANDROID_DATA=$R/data; mkdir -p $ANDROID_DATA/dalvik-cache/x86_64
export LD_LIBRARY_PATH=$O/lib64
BCP=$B/core-oj.jar:$B/core-libart.jar:$B/okhttp.jar:$B/bouncycastle.jar:$B/apache-xml.jar:$B/core-icu4j.jar:$R/jars/host-shim-v1.jar:$B/framework.jar:$B/adapter-mainline-stubs.jar:$B/oh-adapter-framework.jar
timeout 300 $O/bin/dalvikvm64 -Xuse-stderr-logger -Xint -Ximage:$R/no-image.art -Xbootclasspath:$BCP -Xbootclasspath-locations:$BCP \
  -cp $R/jars/trampoline-order-test.jar:$2 TrampolineOrderTest
echo "rc=$?"
