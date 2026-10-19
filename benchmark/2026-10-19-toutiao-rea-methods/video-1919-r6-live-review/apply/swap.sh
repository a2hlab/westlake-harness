test "$(cat /proc/sys/kernel/random/boot_id)" = d90678dd-bc14-49b3-a714-a83931b35794
row=$(cat /proc/5496/stat); rest=${row##*) }; set -- $rest; test "${20}" = 7495
test "$(sha256sum /proc/5496/exe | cut -d' ' -f1)" = a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c
test "$(stat -L -c %d:%i /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh)" = "$(stat -L -c %d:%i /proc/5496/root/data/local/tmp/asx/run.sh)"
test "$(sha256sum /system/etc/init/01_westlake_u13_toutiao.cfg | cut -d' ' -f1)" = 91e31b959995772d305d5b034c9a5ebdbf3f8371495e3964185ada928db4ee2e
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test -f /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh
test "$(sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh | cut -d' ' -f1)" = d3518cefb37a81be01f386ac7ac54193ab47da3475bdb00d16803853c80077d4
test "$(stat -c %a:%u:%g /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh)" = 755:20011206:20011206
test "$(ls -Zd /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh | cut -d' ' -f1)" = u:object_r:appdat:s0
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test -f /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so
test "$(sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so | cut -d' ' -f1)" = fecf91e1fcda600661f501ce76a97456ad7e330b584013f2b742afb680b337c9
test "$(stat -c %a:%u:%g /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so)" = 644:20011206:20011206
test "$(ls -Zd /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so | cut -d' ' -f1)" = u:object_r:appdat:s0
test "$(stat -L -c %d:%i /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so)" = "$(stat -L -c %d:%i /proc/5496/root/data/local/tmp/asx/lib/arm64-v8a/libmffmpeg.so)"
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libttmplayer.so; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test -f /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libttmplayer.so
test "$(sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libttmplayer.so | cut -d' ' -f1)" = b427614d57e4a7279f362b3f341de3cdd4b9f9a8859257016bcda24e5f6d3a02
test "$(stat -c %a:%u:%g /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libttmplayer.so)" = 644:20011206:20011206
test "$(ls -Zd /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libttmplayer.so | cut -d' ' -f1)" = u:object_r:appdat:s0
test "$(stat -L -c %d:%i /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libttmplayer.so)" = "$(stat -L -c %d:%i /proc/5496/root/data/local/tmp/asx/lib/arm64-v8a/libttmplayer.so)"
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test ! -e /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-before-d90678dd; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test ! -e /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-before-d90678dd
cp -p /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-before-d90678dd
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-before-d90678dd; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test -f /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-before-d90678dd
test "$(sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-before-d90678dd | cut -d' ' -f1)" = d3518cefb37a81be01f386ac7ac54193ab47da3475bdb00d16803853c80077d4
test "$(stat -c %a:%u:%g /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-before-d90678dd)" = 755:20011206:20011206
test "$(ls -Zd /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-before-d90678dd | cut -d' ' -f1)" = u:object_r:appdat:s0
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so.ttvideo-before-d90678dd; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test ! -e /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so.ttvideo-before-d90678dd
cp -p /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so.ttvideo-before-d90678dd
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so.ttvideo-before-d90678dd; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test -f /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so.ttvideo-before-d90678dd
test "$(sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so.ttvideo-before-d90678dd | cut -d' ' -f1)" = fecf91e1fcda600661f501ce76a97456ad7e330b584013f2b742afb680b337c9
test "$(stat -c %a:%u:%g /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so.ttvideo-before-d90678dd)" = 644:20011206:20011206
test "$(ls -Zd /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so.ttvideo-before-d90678dd | cut -d' ' -f1)" = u:object_r:appdat:s0
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libttmplayer.so.ttvideo-before-d90678dd; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test ! -e /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libttmplayer.so.ttvideo-before-d90678dd
cp -p /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libttmplayer.so /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libttmplayer.so.ttvideo-before-d90678dd
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libttmplayer.so.ttvideo-before-d90678dd; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test -f /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libttmplayer.so.ttvideo-before-d90678dd
test "$(sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libttmplayer.so.ttvideo-before-d90678dd | cut -d' ' -f1)" = b427614d57e4a7279f362b3f341de3cdd4b9f9a8859257016bcda24e5f6d3a02
test "$(stat -c %a:%u:%g /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libttmplayer.so.ttvideo-before-d90678dd)" = 644:20011206:20011206
test "$(ls -Zd /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libttmplayer.so.ttvideo-before-d90678dd | cut -d' ' -f1)" = u:object_r:appdat:s0
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so.ttvideo-d90678dd-df3e15bb.tmp; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test ! -e /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so.ttvideo-d90678dd-df3e15bb.tmp
cp /data/local/tmp/ttvideo-apply-d90678dd-df3e15bb/libmffmpeg.so /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so.ttvideo-d90678dd-df3e15bb.tmp
chown 20011206:20011206 /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so.ttvideo-d90678dd-df3e15bb.tmp
chmod 644 /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so.ttvideo-d90678dd-df3e15bb.tmp
chcon u:object_r:appdat:s0 /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so.ttvideo-d90678dd-df3e15bb.tmp
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so.ttvideo-d90678dd-df3e15bb.tmp; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test -f /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so.ttvideo-d90678dd-df3e15bb.tmp
test "$(sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so.ttvideo-d90678dd-df3e15bb.tmp | cut -d' ' -f1)" = d2882303bf5dc34e297a404e4b57a214d9c30ddaf0f496eb2ef9f7dcac09c4b4
test "$(stat -c %a:%u:%g /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so.ttvideo-d90678dd-df3e15bb.tmp)" = 644:20011206:20011206
test "$(ls -Zd /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so.ttvideo-d90678dd-df3e15bb.tmp | cut -d' ' -f1)" = u:object_r:appdat:s0
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test -f /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so
test "$(sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so | cut -d' ' -f1)" = fecf91e1fcda600661f501ce76a97456ad7e330b584013f2b742afb680b337c9
test "$(stat -c %a:%u:%g /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so)" = 644:20011206:20011206
test "$(ls -Zd /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so | cut -d' ' -f1)" = u:object_r:appdat:s0
mv /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so.ttvideo-d90678dd-df3e15bb.tmp /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test -f /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so
test "$(sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so | cut -d' ' -f1)" = d2882303bf5dc34e297a404e4b57a214d9c30ddaf0f496eb2ef9f7dcac09c4b4
test "$(stat -c %a:%u:%g /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so)" = 644:20011206:20011206
test "$(ls -Zd /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so | cut -d' ' -f1)" = u:object_r:appdat:s0
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libttmplayer.so.ttvideo-d90678dd-df3e15bb.tmp; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test ! -e /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libttmplayer.so.ttvideo-d90678dd-df3e15bb.tmp
cp /data/local/tmp/ttvideo-apply-d90678dd-df3e15bb/libttmplayer.so /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libttmplayer.so.ttvideo-d90678dd-df3e15bb.tmp
chown 20011206:20011206 /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libttmplayer.so.ttvideo-d90678dd-df3e15bb.tmp
chmod 644 /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libttmplayer.so.ttvideo-d90678dd-df3e15bb.tmp
chcon u:object_r:appdat:s0 /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libttmplayer.so.ttvideo-d90678dd-df3e15bb.tmp
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libttmplayer.so.ttvideo-d90678dd-df3e15bb.tmp; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test -f /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libttmplayer.so.ttvideo-d90678dd-df3e15bb.tmp
test "$(sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libttmplayer.so.ttvideo-d90678dd-df3e15bb.tmp | cut -d' ' -f1)" = 5fba80506cd1a494de5fb6aee63930192d6d0539657cca51e99381ff8a052ee4
test "$(stat -c %a:%u:%g /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libttmplayer.so.ttvideo-d90678dd-df3e15bb.tmp)" = 644:20011206:20011206
test "$(ls -Zd /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libttmplayer.so.ttvideo-d90678dd-df3e15bb.tmp | cut -d' ' -f1)" = u:object_r:appdat:s0
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libttmplayer.so; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test -f /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libttmplayer.so
test "$(sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libttmplayer.so | cut -d' ' -f1)" = b427614d57e4a7279f362b3f341de3cdd4b9f9a8859257016bcda24e5f6d3a02
test "$(stat -c %a:%u:%g /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libttmplayer.so)" = 644:20011206:20011206
test "$(ls -Zd /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libttmplayer.so | cut -d' ' -f1)" = u:object_r:appdat:s0
mv /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libttmplayer.so.ttvideo-d90678dd-df3e15bb.tmp /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libttmplayer.so
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libttmplayer.so; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test -f /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libttmplayer.so
test "$(sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libttmplayer.so | cut -d' ' -f1)" = 5fba80506cd1a494de5fb6aee63930192d6d0539657cca51e99381ff8a052ee4
test "$(stat -c %a:%u:%g /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libttmplayer.so)" = 644:20011206:20011206
test "$(ls -Zd /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libttmplayer.so | cut -d' ' -f1)" = u:object_r:appdat:s0
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so.ttvideo-d90678dd-df3e15bb.tmp; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test ! -e /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so.ttvideo-d90678dd-df3e15bb.tmp
cp /data/local/tmp/ttvideo-apply-d90678dd-df3e15bb/libopensles_android_compat.so /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so.ttvideo-d90678dd-df3e15bb.tmp
chown 20011206:20011206 /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so.ttvideo-d90678dd-df3e15bb.tmp
chmod 644 /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so.ttvideo-d90678dd-df3e15bb.tmp
chcon u:object_r:appdat:s0 /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so.ttvideo-d90678dd-df3e15bb.tmp
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so.ttvideo-d90678dd-df3e15bb.tmp; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test -f /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so.ttvideo-d90678dd-df3e15bb.tmp
test "$(sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so.ttvideo-d90678dd-df3e15bb.tmp | cut -d' ' -f1)" = 9f558aaf1d48cedbc10e6774073d71177efb6d1e196fe528f0203505d1ee761f
test "$(stat -c %a:%u:%g /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so.ttvideo-d90678dd-df3e15bb.tmp)" = 644:20011206:20011206
test "$(ls -Zd /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so.ttvideo-d90678dd-df3e15bb.tmp | cut -d' ' -f1)" = u:object_r:appdat:s0
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test ! -e /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so
mv /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so.ttvideo-d90678dd-df3e15bb.tmp /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test -f /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so
test "$(sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so | cut -d' ' -f1)" = 9f558aaf1d48cedbc10e6774073d71177efb6d1e196fe528f0203505d1ee761f
test "$(stat -c %a:%u:%g /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so)" = 644:20011206:20011206
test "$(ls -Zd /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so | cut -d' ' -f1)" = u:object_r:appdat:s0
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test -f /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh
test "$(sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh | cut -d' ' -f1)" = d3518cefb37a81be01f386ac7ac54193ab47da3475bdb00d16803853c80077d4
test "$(stat -c %a:%u:%g /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh)" = 755:20011206:20011206
test "$(ls -Zd /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh | cut -d' ' -f1)" = u:object_r:appdat:s0
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-d90678dd-df3e15bb.tmp; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test ! -e /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-d90678dd-df3e15bb.tmp
cp /data/local/tmp/ttvideo-apply-d90678dd-df3e15bb/run.sh /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-d90678dd-df3e15bb.tmp
chown 20011206:20011206 /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-d90678dd-df3e15bb.tmp
chmod 755 /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-d90678dd-df3e15bb.tmp
chcon u:object_r:appdat:s0 /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-d90678dd-df3e15bb.tmp
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-d90678dd-df3e15bb.tmp; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test -f /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-d90678dd-df3e15bb.tmp
test "$(sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-d90678dd-df3e15bb.tmp | cut -d' ' -f1)" = 79275cf9f9a72be72beb551b978ee5f2faaed84129980aa5c79d2f51acd040d5
test "$(stat -c %a:%u:%g /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-d90678dd-df3e15bb.tmp)" = 755:20011206:20011206
test "$(ls -Zd /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-d90678dd-df3e15bb.tmp | cut -d' ' -f1)" = u:object_r:appdat:s0
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test -f /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh
test "$(sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh | cut -d' ' -f1)" = d3518cefb37a81be01f386ac7ac54193ab47da3475bdb00d16803853c80077d4
test "$(stat -c %a:%u:%g /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh)" = 755:20011206:20011206
test "$(ls -Zd /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh | cut -d' ' -f1)" = u:object_r:appdat:s0
mv /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh.ttvideo-d90678dd-df3e15bb.tmp /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh
walk=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test -f /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh
test "$(sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh | cut -d' ' -f1)" = 79275cf9f9a72be72beb551b978ee5f2faaed84129980aa5c79d2f51acd040d5
test "$(stat -c %a:%u:%g /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh)" = 755:20011206:20011206
test "$(ls -Zd /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh | cut -d' ' -f1)" = u:object_r:appdat:s0
test "$(cat /proc/sys/kernel/random/boot_id)" = d90678dd-bc14-49b3-a714-a83931b35794
row=$(cat /proc/5496/stat); rest=${row##*) }; set -- $rest; test "${20}" = 7495
test "$(sha256sum /proc/5496/exe | cut -d' ' -f1)" = a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c
test "$(stat -L -c %d:%i /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh)" = "$(stat -L -c %d:%i /proc/5496/root/data/local/tmp/asx/run.sh)"
test "$(sha256sum /system/etc/init/01_westlake_u13_toutiao.cfg | cut -d' ' -f1)" = 91e31b959995772d305d5b034c9a5ebdbf3f8371495e3964185ada928db4ee2e
echo VIDEO_FILES_SWAPPED_FRESH_BOOT_REQUIRED
