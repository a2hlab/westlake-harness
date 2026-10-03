#!/bin/bash
# (src/genstub/ = hand stand-ins for IDL-generated headers, searched last; lite/simulator/C-kit/mock/test trees excluded)
# Runs ON hw248. Finds the OH 6.1 include directories a0probe.cpp needs: compile, take the first missing header,
# locate it in the OH tree (interfaces / inner_api / innerkits / include dirs preferred, tests excluded), add its dir,
# repeat. Seeds with src/include-seed.txt (directories checked by hand: same-named headers exist in lite/simulator/C-kit
# trees, and picking those would compile but break the ABI). Writes the ordered list to $B/out/include-dirs.txt (used verbatim by build_a0_hw248.sh).
set -uo pipefail
B=${A0_BUILD:?hw248 build dir}; OH=${OH610:?OH 6.1.0.31 source tree}
LLVM=$OH/prebuilts/clang/ohos/linux-x86_64/llvm; SYSROOT=${OH_SYSROOT:?OH NDK sysroot}
sed "s|^|$OH/|" $B/src/include-seed.txt > $B/out/include-dirs.txt   # the known-correct dirs first
for i in $(seq 1 120); do
  inc="$(sed 's/^/-I/' $B/out/include-dirs.txt | tr '\n' ' ') -I$B/src/genstub"
  err=$($LLVM/bin/clang++ --target=aarch64-linux-ohos --sysroot=$SYSROOT -nostdinc++ -isystem $LLVM/include/libcxx-ohos/include/c++/v1 \
        -std=c++17 -fsyntax-only -D__MUSL__ $inc $B/src/native/a0probe.cpp 2>&1 | grep -m1 "fatal error: '.*' file not found")
  [ -z "$err" ] && { echo "resolved after $i passes"; exit 0; }
  h=$(echo "$err" | sed "s/.*fatal error: '\(.*\)' file not found.*/\1/")
  cand=$(cd $OH && find base foundation commonlibrary third_party/json utils interface/sdk_c \( -path "*/test*" -o -path "*simulator*" -o -path "*_lite*" -o -path "*/kits/c/*" -o -path "*/mock*" \) -prune -o -path "*/$h" -print 2>/dev/null \
         | awk '{s=0; if ($0 ~ /inner_api|innerkits|interfaces\/kits|\/include\//) s-=10; print s, length($0), $0}' | sort -n -k1 -k2 | head -1 | cut -d" " -f3)
  if [ -z "$cand" ]; then
    # IDL-generated header: forward-declare the interface (namespace from the .idl), never define it
    idl=$(cd $OH && find foundation base -name "*.idl" 2>/dev/null | while read f; do
            n=$(basename $f .idl); s=$(echo "$n" | sed 's/\([a-z0-9]\)\([A-Z]\)/\1_\2/g; s/^I\([A-Z]\)/i\1/' | tr 'A-Z' 'a-z');
            [ "$s.h" = "$(basename $h)" ] && echo $f; done | head -1)
    [ -z "$idl" ] && { echo "UNRESOLVED $h"; exit 1; }
    q=$(grep -m1 -o "interface [A-Za-z0-9_.]*" $OH/$idl | cut -d" " -f2); ns=${q%.*}; cls=${q##*.}
    g=$B/src/genstub/$h; mkdir -p $(dirname $g)
    { echo "// AUTO stand-in for IDL-generated $h from $idl: empty RefBase-derived class, only ever a null sptr"; echo "#pragma once"; echo "#include \"refbase.h\"";
      for part in $(echo $ns | tr . ' '); do echo "namespace $part {"; done; echo "class $cls : public virtual OHOS::RefBase {};";
      for part in $(echo $ns | tr . ' '); do echo "}"; done; } > $g
    echo "+ $h -> AUTO STUB ($q from $idl)"; continue
  fi
  d=$OH/${cand%/$h}; echo "$d" >> $B/out/include-dirs.txt; echo "+ $h -> ${cand%/$h}"
done
echo "gave up"; exit 1
