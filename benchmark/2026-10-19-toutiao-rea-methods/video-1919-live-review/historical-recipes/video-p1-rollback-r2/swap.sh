test "$(cat /proc/sys/kernel/random/boot_id)" = db544de8-d26b-4c19-95d9-75ed10b34aae
row=$(cat /proc/5785/stat); rest=${row##*) }; set -- $rest; test "${20}" = 15100
test "$(sha256sum /proc/5785/exe | cut -d' ' -f1)" = a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c
test "$(stat -L -c %d:%i /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh)" = "$(stat -L -c %d:%i /proc/5785/root/data/local/tmp/asx/run.sh)"
test "$(sha256sum /system/etc/init/01_westlake_u13_toutiao.cfg | cut -d' ' -f1)" = 91e31b959995772d305d5b034c9a5ebdbf3f8371495e3964185ada928db4ee2e
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test -f /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh
test "$(sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh | cut -d' ' -f1)" = ea98494255b05699ca24b134e6ada8849b023b4ab59d3d7e291194cfa8425f73
test "$(stat -c %a:%u:%g /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh)" = 755:20011206:20011206
ls -Zd /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh | grep -F u:object_r:appdat:s0 >/dev/null
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test -f /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so
test "$(sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so | cut -d' ' -f1)" = 9f558aaf1d48cedbc10e6774073d71177efb6d1e196fe528f0203505d1ee761f
test "$(stat -c %a:%u:%g /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so)" = 644:20011206:20011206
ls -Zd /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so | grep -F u:object_r:appdat:s0 >/dev/null
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-before-7bf09d80; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test -f /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-before-7bf09d80
test "$(sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-before-7bf09d80 | cut -d' ' -f1)" = d3518cefb37a81be01f386ac7ac54193ab47da3475bdb00d16803853c80077d4
test "$(stat -c %a:%u:%g /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-before-7bf09d80)" = 755:20011206:20011206
ls -Zd /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-before-7bf09d80 | grep -F u:object_r:appdat:s0 >/dev/null
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test -f /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh
test "$(sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh | cut -d' ' -f1)" = ea98494255b05699ca24b134e6ada8849b023b4ab59d3d7e291194cfa8425f73
test "$(stat -c %a:%u:%g /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh)" = 755:20011206:20011206
ls -Zd /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh | grep -F u:object_r:appdat:s0 >/dev/null
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-db544de8.tmp; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test ! -e /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-db544de8.tmp
cp /data/local/tmp/ttvideo-rollback-db544de8-c035757b/run.sh /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-db544de8.tmp
chown 20011206:20011206 /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-db544de8.tmp
chmod 755 /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-db544de8.tmp
chcon u:object_r:appdat:s0 /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-db544de8.tmp
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-db544de8.tmp; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test -f /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-db544de8.tmp
test "$(sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-db544de8.tmp | cut -d' ' -f1)" = d3518cefb37a81be01f386ac7ac54193ab47da3475bdb00d16803853c80077d4
test "$(stat -c %a:%u:%g /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-db544de8.tmp)" = 755:20011206:20011206
ls -Zd /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-db544de8.tmp | grep -F u:object_r:appdat:s0 >/dev/null
mv /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-db544de8.tmp /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test -f /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh
test "$(sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh | cut -d' ' -f1)" = d3518cefb37a81be01f386ac7ac54193ab47da3475bdb00d16803853c80077d4
test "$(stat -c %a:%u:%g /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh)" = 755:20011206:20011206
ls -Zd /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh | grep -F u:object_r:appdat:s0 >/dev/null
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test -f /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so
test "$(sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so | cut -d' ' -f1)" = 9f558aaf1d48cedbc10e6774073d71177efb6d1e196fe528f0203505d1ee761f
test "$(stat -c %a:%u:%g /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so)" = 644:20011206:20011206
ls -Zd /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so | grep -F u:object_r:appdat:s0 >/dev/null
rm /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so
test ! -e /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so
test "$(cat /proc/sys/kernel/random/boot_id)" = db544de8-d26b-4c19-95d9-75ed10b34aae
row=$(cat /proc/5785/stat); rest=${row##*) }; set -- $rest; test "${20}" = 15100
test "$(sha256sum /proc/5785/exe | cut -d' ' -f1)" = a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c
test "$(stat -L -c %d:%i /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh)" = "$(stat -L -c %d:%i /proc/5785/root/data/local/tmp/asx/run.sh)"
test "$(sha256sum /system/etc/init/01_westlake_u13_toutiao.cfg | cut -d' ' -f1)" = 91e31b959995772d305d5b034c9a5ebdbf3f8371495e3964185ada928db4ee2e
echo VIDEO_FILES_SWAPPED_FRESH_BOOT_REQUIRED
