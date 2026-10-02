#!/bin/bash
# run_gcm.sh <runtime jar> : GcmAndroidTest on host ART (android-14.0.0_r1) with the boards boot class path (U12/U13 BCP jars, board order)
R=${GCM_RUN_DIR:?set GCM_RUN_DIR: hw248 dir with boot/ (board BCP jars) and jars/ (test, shim, runtime jars)}
O=${ART_HOST_OUT:?set ART_HOST_OUT: android-14.0.0_r1 host ART out/host/linux-x86}
export ANDROID_ROOT=$O ANDROID_ART_ROOT=$O/com.android.art ANDROID_I18N_ROOT=$O/com.android.i18n ANDROID_TZDATA_ROOT=$O/com.android.tzdata
export ANDROID_DATA=$R/data; mkdir -p $ANDROID_DATA/dalvik-cache/x86_64
export LD_LIBRARY_PATH=$O/lib64
BCP=$R/boot/core-oj.jar:$R/boot/core-libart.jar:$R/boot/okhttp.jar:$R/boot/bouncycastle.jar:$R/boot/apache-xml.jar:$R/boot/core-icu4j.jar:$R/jars/host-log-shim.jar:$R/boot/framework.jar:$R/boot/adapter-mainline-stubs.jar:$R/boot/oh-adapter-framework.jar
timeout 300 $O/bin/dalvikvm64 -Xuse-stderr-logger -Xint -Ximage:$R/no-image.art -Xbootclasspath:$BCP -Xbootclasspath-locations:$BCP \
  -cp $R/jars/gcm-android-test.jar:$1 GcmAndroidTest
echo "rc=$?"
