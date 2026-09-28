#!/bin/bash
# P13.2.c: compile rs_surface_helper.cpp using OH ninja flags verbatim.
set -e
OH=/home/HanBingChen/oh
ADAPTER=/home/HanBingChen/adapter
OUT_OBJ=$ADAPTER/out/aosp_lib/obj
OUT_LIB=$ADAPTER/out/aosp_lib
mkdir -p $OUT_OBJ

CXX=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang++
NINJA_FILE=$OH/out/rk3568/obj/foundation/graphic/graphic_2d/rosen/modules/render_service_client/render_service_client_src.ninja

# Extract ninja variables. `\$ ` in ninja is an escaped space inside a value.
# Python unescapes cleanly and strips FFRT_* multi-word defines that bash can't handle.
python3 - << 'PYEOF' > /tmp/rs_helper_flags.txt
import re
with open("$NINJA_FILE".replace("$NINJA_FILE", "/home/HanBingChen/oh/out/rk3568/obj/foundation/graphic/graphic_2d/rosen/modules/render_service_client/render_service_client_src.ninja")) as f:
    content = f.read()

def grab(name):
    m = re.search(r'^' + name + r' = (.*)$', content, re.M)
    return m.group(1) if m else ""

defines = grab("defines")
includes = grab("include_dirs")
cflags = grab("cflags")
cflags_cc = grab("cflags_cc")

# Unescape ninja: \$  -> a single space that is part of a value.
# Trick: replace "\\$ " (literal backslash-dollar-space) with "\x00" so subsequent
# split on real spaces works, then rejoin with "=" -like quoting. Simpler:
# drop any define containing "\$" (these are FFRT multi-word values we don't need).
def clean_defines(s):
    # Drop all FFRT_* defines — they are multi-word via ninja escaping and
    # we don't need them to compile rs_surface_node.cpp anyway.
    s = re.sub(r'-DFFRT_\S+(?:\\\$ \S*)*', '', s)
    # Also drop any residual backslash-escape tokens.
    out = []
    for tok in s.split(" "):
        if not tok:
            continue
        if "\\" in tok:
            continue
        if tok.isdigit():
            continue
        out.append(tok)
    return " ".join(out)

# Clean cflags: drop sanitize-blacklist (relative paths) and LTO
def clean_cflags(s):
    out = []
    skip = False
    for tok in s.split(" "):
        if skip:
            skip = False
            continue
        if tok.startswith("-fsanitize-blacklist="):
            continue
        if tok in ("-flto=thin", "-fsplit-lto-unit", "-fwhole-program-vtables"):
            continue
        if tok == "-Werror" or tok.startswith("-Werror="):
            continue
        out.append(tok)
    return " ".join(out)

import shlex
print("DEFINES=" + shlex.quote(clean_defines(defines)))
print("INCLUDES=" + shlex.quote(includes))
print("CFLAGS=" + shlex.quote(clean_cflags(cflags)))
print("CFLAGS_CC=" + shlex.quote(cflags_cc))
PYEOF

source /tmp/rs_helper_flags.txt

cd $OH/out/rk3568

echo '[compile] rs_surface_helper.cpp...'
$CXX -MMD -MF $OUT_OBJ/rs_surface_helper.o.d \
    $DEFINES $INCLUDES $CFLAGS $CFLAGS_CC \
    -I/home/HanBingChen/aosp/system/logging/liblog/include \
    -Wno-everything \
    -c $ADAPTER/framework/surface/jni/rs_surface_helper.cpp \
    -o $OUT_OBJ/rs_surface_helper.o 2>&1 | tail -30

if [ -f $OUT_OBJ/rs_surface_helper.o ]; then
    SIZE=$(stat -c%s $OUT_OBJ/rs_surface_helper.o)
    echo "OK rs_surface_helper.o = $SIZE bytes"
    NM=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/llvm-nm
    $NM -C $OUT_OBJ/rs_surface_helper.o 2>&1 | grep -E 'rs_surface_helper|RSSurfaceNode' | head -10
else
    echo 'FAIL: rs_surface_helper.o not produced'
    exit 1
fi
