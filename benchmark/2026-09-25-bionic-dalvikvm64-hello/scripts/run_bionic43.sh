#!/system/bin/sh
# #43 M2 — run a Java hello on AOSP14 arm64 ART + boot image + BCP, brought up by the
# #39 Bionic linker64/libc, entirely under /data/local/tmp/bionic43 (no /system write).
# dalvikvm64 is started via the Bionic linker64 (executable mode, absolute path) because
# its baked PT_INTERP (/system/bin/linker64) would otherwise hit the OH musl linker.
set -u
RD=/data/local/tmp/bionic43
LP=$RD/lib64:$RD/lib64/bionic
BCP=$RD/bcp
# real jar files (order matches the boot image's recorded bootclasspath)
CP=$BCP/core-oj.jar:$BCP/core-libart.jar:$BCP/okhttp.jar:$BCP/bouncycastle.jar:$BCP/apache-xml.jar:$BCP/framework.jar:$BCP/framework-graphics.jar:$BCP/ext.jar:$BCP/telephony-common.jar:$BCP/voip-common.jar:$BCP/ims-common.jar:$BCP/core-icu4j.jar
# locations recorded inside boot.oat (must match for the image to be accepted)
LOC=/apex/com.android.art/javalib/core-oj.jar:/apex/com.android.art/javalib/core-libart.jar:/apex/com.android.art/javalib/okhttp.jar:/apex/com.android.art/javalib/bouncycastle.jar:/apex/com.android.art/javalib/apache-xml.jar:/system/framework/framework.jar:/system/framework/framework-graphics.jar:/system/framework/ext.jar:/system/framework/telephony-common.jar:/system/framework/voip-common.jar:/system/framework/ims-common.jar:/apex/com.android.i18n/javalib/core-icu4j.jar

export ANDROID_ART_ROOT=$RD/apex/com.android.art
export ANDROID_I18N_ROOT=$RD/apex/com.android.i18n
export ANDROID_TZDATA_ROOT=$RD/apex/com.android.tzdata
export ANDROID_ROOT=$RD/system
export ANDROID_DATA=$RD/data
export LD_LIBRARY_PATH=$LP
export LD_CONFIG_FILE=$RD/ld.config.txt

mkdir -p $ANDROID_DATA/dalvik-cache/arm64 2>/dev/null

exec $RD/linker64 $RD/bin/dalvikvm64 \
  -Xbootclasspath:$CP \
  -Xbootclasspath-locations:$LOC \
  -Xuse-stderr-logger \
  -Ximage:$RD/framework/boot.art \
  -verbose:image,startup,oat,class \
  -cp $RD/hello.jar Hello
