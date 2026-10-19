#!/bin/sh
# Derive candidate-r2 run.sh from a P1 candidate run.sh (template ea984942 at WID 33, or the live
# after(W) bytes): two single-line token appends, nothing else.
#   make_run_sh.sh <in run.sh> <out run.sh>
set -eu
sed -e 's#^\(export WESTLAKE_ANDROID_NATIVE_TARGETS=.*:libdelta\.so\)$#\1:libmffmpeg.so:libttmplayer.so#' \
    -e 's#^\(export WESTLAKE_ANDROID_NATIVE_INHERIT=libc\.so:libdl\.so:libm\.so:libz\.so:liblog\.so\)$#\1:libopensles_android_compat.so:libOpenSLES.so#' \
    "$1" > "$2"
test "$(diff "$1" "$2" | grep -c '^>')" = 2
