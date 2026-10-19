test "$(cat /proc/sys/kernel/random/boot_id)" = da213fc2-9010-4906-8578-ea242e8394ab
row=$(cat /proc/5279/stat); rest=${row##*) }; set -- $rest; test "${20}" = 11376
test "$(sha256sum /proc/5279/exe | cut -d' ' -f1)" = a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c
test "$(stat -L -c %d:%i /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh)" = "$(stat -L -c %d:%i /proc/5279/root/data/local/tmp/asx/run.sh)"
test "$(sha256sum /system/etc/init/01_westlake_u13_toutiao.cfg | cut -d' ' -f1)" = 91e31b959995772d305d5b034c9a5ebdbf3f8371495e3964185ada928db4ee2e
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test -f /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh
test "$(sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh | cut -d' ' -f1)" = d3518cefb37a81be01f386ac7ac54193ab47da3475bdb00d16803853c80077d4
test "$(stat -c %a:%u:%g /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh)" = 755:20011206:20011206
ls -Zd /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh | grep -F u:object_r:appdat:s0 >/dev/null
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test -f /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so
test "$(sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so | cut -d' ' -f1)" = fecf91e1fcda600661f501ce76a97456ad7e330b584013f2b742afb680b337c9
test "$(stat -c %a:%u:%g /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so)" = 644:20011206:20011206
ls -Zd /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so | grep -F u:object_r:appdat:s0 >/dev/null
test "$(stat -L -c %d:%i /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so)" = "$(stat -L -c %d:%i /proc/5279/root/data/local/tmp/asx/lib/arm64-v8a/libmffmpeg.so)"
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test ! -e /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-before-da213fc2; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test ! -e /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-before-da213fc2
cp -p /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-before-da213fc2
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-before-da213fc2; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test -f /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-before-da213fc2
test "$(sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-before-da213fc2 | cut -d' ' -f1)" = d3518cefb37a81be01f386ac7ac54193ab47da3475bdb00d16803853c80077d4
test "$(stat -c %a:%u:%g /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-before-da213fc2)" = 755:20011206:20011206
ls -Zd /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-before-da213fc2 | grep -F u:object_r:appdat:s0 >/dev/null
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so.ttvideo-before-da213fc2; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test ! -e /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so.ttvideo-before-da213fc2
cp -p /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so.ttvideo-before-da213fc2
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so.ttvideo-before-da213fc2; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test -f /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so.ttvideo-before-da213fc2
test "$(sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so.ttvideo-before-da213fc2 | cut -d' ' -f1)" = fecf91e1fcda600661f501ce76a97456ad7e330b584013f2b742afb680b337c9
test "$(stat -c %a:%u:%g /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so.ttvideo-before-da213fc2)" = 644:20011206:20011206
ls -Zd /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so.ttvideo-before-da213fc2 | grep -F u:object_r:appdat:s0 >/dev/null
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so.ttvideo-da213fc2-271051b5.tmp; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test ! -e /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so.ttvideo-da213fc2-271051b5.tmp
cp /data/local/tmp/ttvideo-apply-da213fc2-271051b5/libmffmpeg.so /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so.ttvideo-da213fc2-271051b5.tmp
chown 20011206:20011206 /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so.ttvideo-da213fc2-271051b5.tmp
chmod 644 /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so.ttvideo-da213fc2-271051b5.tmp
chcon u:object_r:appdat:s0 /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so.ttvideo-da213fc2-271051b5.tmp
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so.ttvideo-da213fc2-271051b5.tmp; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test -f /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so.ttvideo-da213fc2-271051b5.tmp
test "$(sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so.ttvideo-da213fc2-271051b5.tmp | cut -d' ' -f1)" = d2882303bf5dc34e297a404e4b57a214d9c30ddaf0f496eb2ef9f7dcac09c4b4
test "$(stat -c %a:%u:%g /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so.ttvideo-da213fc2-271051b5.tmp)" = 644:20011206:20011206
ls -Zd /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so.ttvideo-da213fc2-271051b5.tmp | grep -F u:object_r:appdat:s0 >/dev/null
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test -f /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so
test "$(sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so | cut -d' ' -f1)" = fecf91e1fcda600661f501ce76a97456ad7e330b584013f2b742afb680b337c9
test "$(stat -c %a:%u:%g /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so)" = 644:20011206:20011206
ls -Zd /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so | grep -F u:object_r:appdat:s0 >/dev/null
mv /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so.ttvideo-da213fc2-271051b5.tmp /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test -f /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so
test "$(sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so | cut -d' ' -f1)" = d2882303bf5dc34e297a404e4b57a214d9c30ddaf0f496eb2ef9f7dcac09c4b4
test "$(stat -c %a:%u:%g /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so)" = 644:20011206:20011206
ls -Zd /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so | grep -F u:object_r:appdat:s0 >/dev/null
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so.ttvideo-da213fc2-271051b5.tmp; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test ! -e /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so.ttvideo-da213fc2-271051b5.tmp
cp /data/local/tmp/ttvideo-apply-da213fc2-271051b5/libopensles_android_compat.so /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so.ttvideo-da213fc2-271051b5.tmp
chown 20011206:20011206 /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so.ttvideo-da213fc2-271051b5.tmp
chmod 644 /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so.ttvideo-da213fc2-271051b5.tmp
chcon u:object_r:appdat:s0 /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so.ttvideo-da213fc2-271051b5.tmp
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so.ttvideo-da213fc2-271051b5.tmp; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test -f /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so.ttvideo-da213fc2-271051b5.tmp
test "$(sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so.ttvideo-da213fc2-271051b5.tmp | cut -d' ' -f1)" = 9f558aaf1d48cedbc10e6774073d71177efb6d1e196fe528f0203505d1ee761f
test "$(stat -c %a:%u:%g /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so.ttvideo-da213fc2-271051b5.tmp)" = 644:20011206:20011206
ls -Zd /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so.ttvideo-da213fc2-271051b5.tmp | grep -F u:object_r:appdat:s0 >/dev/null
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test ! -e /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so
mv /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so.ttvideo-da213fc2-271051b5.tmp /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test -f /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so
test "$(sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so | cut -d' ' -f1)" = 9f558aaf1d48cedbc10e6774073d71177efb6d1e196fe528f0203505d1ee761f
test "$(stat -c %a:%u:%g /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so)" = 644:20011206:20011206
ls -Zd /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so | grep -F u:object_r:appdat:s0 >/dev/null
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test -f /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh
test "$(sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh | cut -d' ' -f1)" = d3518cefb37a81be01f386ac7ac54193ab47da3475bdb00d16803853c80077d4
test "$(stat -c %a:%u:%g /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh)" = 755:20011206:20011206
ls -Zd /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh | grep -F u:object_r:appdat:s0 >/dev/null
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-da213fc2-271051b5.tmp; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test ! -e /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-da213fc2-271051b5.tmp
cp /data/local/tmp/ttvideo-apply-da213fc2-271051b5/run.sh /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-da213fc2-271051b5.tmp
chown 20011206:20011206 /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-da213fc2-271051b5.tmp
chmod 755 /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-da213fc2-271051b5.tmp
chcon u:object_r:appdat:s0 /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-da213fc2-271051b5.tmp
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-da213fc2-271051b5.tmp; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test -f /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-da213fc2-271051b5.tmp
test "$(sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-da213fc2-271051b5.tmp | cut -d' ' -f1)" = 79275cf9f9a72be72beb551b978ee5f2faaed84129980aa5c79d2f51acd040d5
test "$(stat -c %a:%u:%g /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-da213fc2-271051b5.tmp)" = 755:20011206:20011206
ls -Zd /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-da213fc2-271051b5.tmp | grep -F u:object_r:appdat:s0 >/dev/null
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test -f /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh
test "$(sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh | cut -d' ' -f1)" = d3518cefb37a81be01f386ac7ac54193ab47da3475bdb00d16803853c80077d4
test "$(stat -c %a:%u:%g /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh)" = 755:20011206:20011206
ls -Zd /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh | grep -F u:object_r:appdat:s0 >/dev/null
mv /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-da213fc2-271051b5.tmp /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test -f /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh
test "$(sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh | cut -d' ' -f1)" = 79275cf9f9a72be72beb551b978ee5f2faaed84129980aa5c79d2f51acd040d5
test "$(stat -c %a:%u:%g /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh)" = 755:20011206:20011206
ls -Zd /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh | grep -F u:object_r:appdat:s0 >/dev/null
test "$(cat /proc/sys/kernel/random/boot_id)" = da213fc2-9010-4906-8578-ea242e8394ab
row=$(cat /proc/5279/stat); rest=${row##*) }; set -- $rest; test "${20}" = 11376
test "$(sha256sum /proc/5279/exe | cut -d' ' -f1)" = a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c
test "$(stat -L -c %d:%i /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh)" = "$(stat -L -c %d:%i /proc/5279/root/data/local/tmp/asx/run.sh)"
test "$(sha256sum /system/etc/init/01_westlake_u13_toutiao.cfg | cut -d' ' -f1)" = 91e31b959995772d305d5b034c9a5ebdbf3f8371495e3964185ada928db4ee2e
echo VIDEO_FILES_SWAPPED_FRESH_BOOT_REQUIRED
