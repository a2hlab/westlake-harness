#!/system/bin/sh
set -eu
test ! -L /system/android
test -d /system/android
test "$(stat -c %a:%u:%g:%C /system/android)" = 750:0:0:u:object_r:system_file:s0
test ! -L /data/westlake-demo/u13/sources/seq1
test -d /data/westlake-demo/u13/sources/seq1
test "$(stat -c %a:%u:%g:%C /data/westlake-demo/u13/sources/seq1)" = 750:0:0:u:object_r:system_file:s0
test "$(stat -c %d:%i /system/android)" = "$(stat -c %d:%i /data/westlake-demo/u13/sources/seq1)"
test ! -L /system/android/etc
test -d /system/android/etc
test "$(stat -c %a:%u:%g:%C /system/android/etc)" = 750:0:0:u:object_r:system_file:s0
test ! -L /data/westlake-demo/u13/sources/seq1/etc
test -d /data/westlake-demo/u13/sources/seq1/etc
test "$(stat -c %a:%u:%g:%C /data/westlake-demo/u13/sources/seq1/etc)" = 750:0:0:u:object_r:system_file:s0
test "$(stat -c %d:%i /system/android/etc)" = "$(stat -c %d:%i /data/westlake-demo/u13/sources/seq1/etc)"
test ! -L /system/android/etc/icu
test -d /system/android/etc/icu
test "$(stat -c %a:%u:%g:%C /system/android/etc/icu)" = 750:0:0:u:object_r:system_file:s0
test ! -L /data/westlake-demo/u13/sources/seq1/etc/icu
test -d /data/westlake-demo/u13/sources/seq1/etc/icu
test "$(stat -c %a:%u:%g:%C /data/westlake-demo/u13/sources/seq1/etc/icu)" = 750:0:0:u:object_r:system_file:s0
test "$(stat -c %d:%i /system/android/etc/icu)" = "$(stat -c %d:%i /data/westlake-demo/u13/sources/seq1/etc/icu)"
test ! -L /system/android/etc/security
test -d /system/android/etc/security
test "$(stat -c %a:%u:%g:%C /system/android/etc/security)" = 750:0:0:u:object_r:system_file:s0
test ! -L /data/westlake-demo/u13/sources/seq1/etc/security
test -d /data/westlake-demo/u13/sources/seq1/etc/security
test "$(stat -c %a:%u:%g:%C /data/westlake-demo/u13/sources/seq1/etc/security)" = 750:0:0:u:object_r:system_file:s0
test "$(stat -c %d:%i /system/android/etc/security)" = "$(stat -c %d:%i /data/westlake-demo/u13/sources/seq1/etc/security)"
test ! -L /system/android/etc/security/cacerts
test -d /system/android/etc/security/cacerts
test "$(stat -c %a:%u:%g:%C /system/android/etc/security/cacerts)" = 750:0:0:u:object_r:system_file:s0
test ! -L /data/westlake-demo/u13/sources/seq1/etc/security/cacerts
test -d /data/westlake-demo/u13/sources/seq1/etc/security/cacerts
test "$(stat -c %a:%u:%g:%C /data/westlake-demo/u13/sources/seq1/etc/security/cacerts)" = 750:0:0:u:object_r:system_file:s0
test "$(stat -c %d:%i /system/android/etc/security/cacerts)" = "$(stat -c %d:%i /data/westlake-demo/u13/sources/seq1/etc/security/cacerts)"
test ! -L /system/android/framework
test -d /system/android/framework
test "$(stat -c %a:%u:%g:%C /system/android/framework)" = 750:0:0:u:object_r:system_file:s0
test ! -L /data/westlake-demo/u13/sources/seq1/framework
test -d /data/westlake-demo/u13/sources/seq1/framework
test "$(stat -c %a:%u:%g:%C /data/westlake-demo/u13/sources/seq1/framework)" = 750:0:0:u:object_r:system_file:s0
test "$(stat -c %d:%i /system/android/framework)" = "$(stat -c %d:%i /data/westlake-demo/u13/sources/seq1/framework)"
test ! -L /system/android/framework/arm64
test -d /system/android/framework/arm64
test "$(stat -c %a:%u:%g:%C /system/android/framework/arm64)" = 750:0:0:u:object_r:system_file:s0
test ! -L /data/westlake-demo/u13/sources/seq1/framework/arm64
test -d /data/westlake-demo/u13/sources/seq1/framework/arm64
test "$(stat -c %a:%u:%g:%C /data/westlake-demo/u13/sources/seq1/framework/arm64)" = 750:0:0:u:object_r:system_file:s0
test "$(stat -c %d:%i /system/android/framework/arm64)" = "$(stat -c %d:%i /data/westlake-demo/u13/sources/seq1/framework/arm64)"
test ! -L /system/android/lib64
test -d /system/android/lib64
test "$(stat -c %a:%u:%g:%C /system/android/lib64)" = 750:0:0:u:object_r:system_lib_file:s0
test ! -L /data/westlake-demo/u13/sources/seq1/lib64
test -d /data/westlake-demo/u13/sources/seq1/lib64
test "$(stat -c %a:%u:%g:%C /data/westlake-demo/u13/sources/seq1/lib64)" = 750:0:0:u:object_r:system_lib_file:s0
test "$(stat -c %d:%i /system/android/lib64)" = "$(stat -c %d:%i /data/westlake-demo/u13/sources/seq1/lib64)"
test ! -L /system/android/lib64/westlake_flutter
test -d /system/android/lib64/westlake_flutter
test "$(stat -c %a:%u:%g:%C /system/android/lib64/westlake_flutter)" = 750:0:0:u:object_r:system_lib_file:s0
test ! -L /data/westlake-demo/u13/sources/seq1/lib64/westlake_flutter
test -d /data/westlake-demo/u13/sources/seq1/lib64/westlake_flutter
test "$(stat -c %a:%u:%g:%C /data/westlake-demo/u13/sources/seq1/lib64/westlake_flutter)" = 750:0:0:u:object_r:system_lib_file:s0
test "$(stat -c %d:%i /system/android/lib64/westlake_flutter)" = "$(stat -c %d:%i /data/westlake-demo/u13/sources/seq1/lib64/westlake_flutter)"
test ! -L /system/android/lib64/westlake_native
test -d /system/android/lib64/westlake_native
test "$(stat -c %a:%u:%g:%C /system/android/lib64/westlake_native)" = 750:0:0:u:object_r:system_lib_file:s0
test ! -L /data/westlake-demo/u13/sources/seq1/lib64/westlake_native
test -d /data/westlake-demo/u13/sources/seq1/lib64/westlake_native
test "$(stat -c %a:%u:%g:%C /data/westlake-demo/u13/sources/seq1/lib64/westlake_native)" = 750:0:0:u:object_r:system_lib_file:s0
test "$(stat -c %d:%i /system/android/lib64/westlake_native)" = "$(stat -c %d:%i /data/westlake-demo/u13/sources/seq1/lib64/westlake_native)"
chmod 755 /data/westlake-demo/u13/sources/seq1
test "$(stat -c %a:%u:%g:%C /system/android)" = 755:0:0:u:object_r:system_file:s0
chmod 755 /data/westlake-demo/u13/sources/seq1/etc
test "$(stat -c %a:%u:%g:%C /system/android/etc)" = 755:0:0:u:object_r:system_file:s0
chmod 755 /data/westlake-demo/u13/sources/seq1/etc/icu
test "$(stat -c %a:%u:%g:%C /system/android/etc/icu)" = 755:0:0:u:object_r:system_file:s0
chmod 755 /data/westlake-demo/u13/sources/seq1/etc/security
test "$(stat -c %a:%u:%g:%C /system/android/etc/security)" = 755:0:0:u:object_r:system_file:s0
chmod 755 /data/westlake-demo/u13/sources/seq1/etc/security/cacerts
test "$(stat -c %a:%u:%g:%C /system/android/etc/security/cacerts)" = 755:0:0:u:object_r:system_file:s0
chmod 755 /data/westlake-demo/u13/sources/seq1/framework
test "$(stat -c %a:%u:%g:%C /system/android/framework)" = 755:0:0:u:object_r:system_file:s0
chmod 755 /data/westlake-demo/u13/sources/seq1/framework/arm64
test "$(stat -c %a:%u:%g:%C /system/android/framework/arm64)" = 755:0:0:u:object_r:system_file:s0
chmod 755 /data/westlake-demo/u13/sources/seq1/lib64
test "$(stat -c %a:%u:%g:%C /system/android/lib64)" = 755:0:0:u:object_r:system_lib_file:s0
chmod 755 /data/westlake-demo/u13/sources/seq1/lib64/westlake_flutter
test "$(stat -c %a:%u:%g:%C /system/android/lib64/westlake_flutter)" = 755:0:0:u:object_r:system_lib_file:s0
chmod 755 /data/westlake-demo/u13/sources/seq1/lib64/westlake_native
test "$(stat -c %a:%u:%g:%C /system/android/lib64/westlake_native)" = 755:0:0:u:object_r:system_lib_file:s0
echo EXACT_10_DIRECTORY_METADATA_RESTORED
