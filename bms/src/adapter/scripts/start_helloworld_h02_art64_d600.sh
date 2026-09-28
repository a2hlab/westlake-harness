#!/system/bin/sh
#
# Manual demo launcher for the sealed HelloWorld H02 ART64 runtime closure.
# This is intentionally package-stack neutral: it neither installs an APK nor
# replaces libapk_installer/libbms/libinstalls.

mkdir -p /data/service/el1/public/appspawnx
mkdir -p /data/misc/appspawnx/dalvik-cache/arm64
mkdir -p /dev/unix/socket

rm -f /dev/unix/socket/AppSpawnX
rm -f /data/local/tmp/h02_asx.out /data/local/tmp/h02_asx.err
rm -f /data/service/el1/public/appspawnx/adapter_child_*.stderr

export APPSPAWNX_NO_JIT=1
export ANDROID_ROOT=/system/android
export ANDROID_DATA=/data
export ANDROID_I18N_ROOT=/system/android
export ANDROID_TZDATA_ROOT=/system/android
export ICU_DATA=/system/android/etc/icu

ANDROID_FRAMEWORK=/system/android/framework
export BOOTCLASSPATH="$ANDROID_FRAMEWORK/core-oj.jar:$ANDROID_FRAMEWORK/core-libart.jar:$ANDROID_FRAMEWORK/core-icu4j.jar:$ANDROID_FRAMEWORK/okhttp.jar:$ANDROID_FRAMEWORK/bouncycastle.jar:$ANDROID_FRAMEWORK/apache-xml.jar:$ANDROID_FRAMEWORK/adapter-mainline-stubs.jar:$ANDROID_FRAMEWORK/framework.jar:$ANDROID_FRAMEWORK/oh-adapter-framework.jar"
export DEX2OATBOOTCLASSPATH="$BOOTCLASSPATH"
export LD_LIBRARY_PATH="/system/android/lib64:/system/lib64:/system/lib64/chipset-sdk-sp:/system/lib64/platformsdk:/system/lib64/chipset-sdk:/system/lib64/ndk"

exec /data/local/tmp/appspawn-x-h02-art64 \
    --socket-name AppSpawnX \
    --sandbox-config /data/local/tmp/appspawn_x_sandbox.json \
    >/data/local/tmp/h02_asx.out \
    2>/data/local/tmp/h02_asx.err
