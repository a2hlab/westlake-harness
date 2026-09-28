#!/bin/bash
# Build libwl_sqlite_jni.so for the D600 board (aarch64 / OHOS) on mac-server.
set -e
cd "$HOME/wl"
NDK=/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native
CC=$NDK/llvm/bin/aarch64-unknown-linux-ohos-clang
CXX=$NDK/llvm/bin/aarch64-unknown-linux-ohos-clang++
SYSROOT=--sysroot=$NDK/sysroot

SQLITE_FLAGS="
 -DSQLITE_THREADSAFE=1
 -DSQLITE_TEMP_STORE=3
 -DSQLITE_POWERSAFE_OVERWRITE=1
 -DSQLITE_DEFAULT_FILE_PERMISSIONS=0600
 -DSQLITE_DEFAULT_AUTOVACUUM=1
 -DSQLITE_DEFAULT_JOURNAL_SIZE_LIMIT=1048576
 -DSQLITE_DEFAULT_WAL_SYNCHRONOUS=1
 -DSQLITE_ENABLE_MEMORY_MANAGEMENT=1
 -DSQLITE_ENABLE_FTS3
 -DSQLITE_ENABLE_FTS3_PARENTHESIS
 -DSQLITE_ENABLE_FTS4
 -DSQLITE_OMIT_LOAD_EXTENSION
 -DSQLITE_OMIT_BUILTIN_TEST
 -DSQLITE_HAVE_ISNAN=1
 -DHAVE_USLEEP=1
"

echo "=== compiling sqlite3.c (this takes a minute) ==="
time $CC $SYSROOT -c sqlite3.c -o sqlite3.o -O2 -fPIC -fvisibility=hidden -w $SQLITE_FLAGS

echo "=== compiling wl_sqlite_jni.cpp ==="
$CXX $SYSROOT -c wl_sqlite_jni.cpp -o wl_sqlite_jni.o \
  -O2 -fPIC -fvisibility=hidden -fvisibility-inlines-hidden \
  -std=c++17 -Wall -I"$HOME/wl"

# Export only the four registrars, pthread_create, the thread-guard entry point and the
# two ScopedJniAttachment ctor/dtor interposers.  This library is LD_PRELOADed into
# appspawn-x, so every symbol it exports interposes on the whole process; keeping
# sqlite3_* private means we can only ever displace what we mean to displace.
# The two C++-mangled names MUST be listed here -- the shim compiles with
# -fvisibility=hidden, so without an entry they stay local and silently do nothing.
cat > wl_sqlite_jni.map <<'EOF'
{
  global:
    pthread_create;
    WLTG_VerifyCurrentThreadReady;
    _ZN8westlake3jni19ScopedJniAttachmentC1EP7_JavaVMPKcNS0_10AttachModeE;
    _ZN8westlake3jni19ScopedJniAttachmentD1Ev;
    _ZN7android42register_android_database_SQLiteConnectionEP7_JNIEnv;
    _ZN7android38register_android_database_SQLiteGlobalEP7_JNIEnv;
    _ZN7android37register_android_database_SQLiteDebugEP7_JNIEnv;
    _ZN7android38register_android_database_CursorWindowEP7_JNIEnv;
  local: *;
};
EOF

echo "=== linking ==="
$CXX $SYSROOT -shared -o libwl_sqlite_jni.so wl_sqlite_jni.o sqlite3.o \
  -static-libstdc++ \
  -Wl,--version-script="$HOME/wl/wl_sqlite_jni.map" \
  -Wl,--exclude-libs,ALL \
  -ldl -lm

echo "=== result ==="
ls -la libwl_sqlite_jni.so
$NDK/llvm/bin/llvm-nm -D --defined-only libwl_sqlite_jni.so
echo "--- undefined deps ---"
$NDK/llvm/bin/llvm-readelf -d libwl_sqlite_jni.so | grep -i needed
shasum -a 256 libwl_sqlite_jni.so
