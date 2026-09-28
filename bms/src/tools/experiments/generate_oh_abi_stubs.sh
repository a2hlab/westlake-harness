#!/bin/bash
#
# Generate link-only AArch64 ABI providers from exact OpenHarmony ELF inputs.
# The outputs preserve defined dynamic FUNC/OBJECT names, types, sizes and
# GLOBAL/WEAK binding, but deliberately contain no DT_NEEDED dependencies.
# They are build inputs only and must never be deployed.
#
# Usage:
#   generate_oh_abi_stubs.sh <real-provider-dir> <stub-output-dir>
#
set -euo pipefail

if [ "$#" -ne 2 ]; then
    echo "usage: $0 <real-provider-dir> <stub-output-dir>" >&2
    exit 2
fi

source_dir="$(cd "$1" && pwd -P)"
mkdir -p "$2"
output_dir="$(cd "$2" && pwd -P)"
toolchain="${OH_SDK:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native}"
clang="$toolchain/llvm/bin/clang"
readelf="$toolchain/llvm/bin/llvm-readelf"
work_dir="$output_dir/.gen"
mkdir -p "$work_dir"

for tool in "$clang" "$readelf"; do
    [ -x "$tool" ] || {
        echo "missing executable: $tool" >&2
        exit 2
    }
done

count=0
for real in "$source_dir"/*.so; do
    [ -f "$real" ] || continue
    name="$(basename "$real")"
    syms="$work_dir/$name.syms"
    assembly="$work_dir/$name.s"
    object="$work_dir/$name.o"
    stub="$output_dir/$name"

    "$readelf" --dyn-syms --wide "$real" |
        awk '
          $7 != "UND" && $6 == "DEFAULT" &&
          ($5 == "GLOBAL" || $5 == "WEAK") &&
          ($4 == "FUNC" || $4 == "OBJECT") {
              full = $8
              name = full
              sub(/@.*/, "", name)
              if (index(full, "@") != 0) {
                  print "versioned defined symbol is unsupported: " full > "/dev/stderr"
                  exit 3
              }
              if (!seen[name]++) {
                  print $5 "\t" $4 "\t" $3 "\t" name
              }
          }' >"$syms"

    [ -s "$syms" ] || {
        echo "no eligible symbols in $real" >&2
        exit 1
    }

    awk -v out="$assembly" '
      BEGIN {
          print "// generated link-only ABI provider; never deploy" > out
          print "  .text" >> out
      }
      {
          binding = $1
          type = $2
          size = $3
          name = $4
          if (type == "FUNC") {
              if (binding == "WEAK") print "  .weak " name >> out
              else print "  .globl " name >> out
              print "  .type " name ",%function" >> out
              print name ":" >> out
              print "  ret" >> out
          } else {
              objects[++n] = binding "\t" size "\t" name
          }
      }
      END {
          print "  .bss" >> out
          for (i = 1; i <= n; i++) {
              split(objects[i], fields, "\t")
              binding = fields[1]
              size = fields[2]
              name = fields[3]
              if (binding == "WEAK") print "  .weak " name >> out
              else print "  .globl " name >> out
              print "  .type " name ",%object" >> out
              print "  .size " name "," size >> out
              print name ":" >> out
              if (size + 0 > 0) print "  .zero " size >> out
          }
      }' "$syms"

    "$clang" --target=aarch64-linux-ohos -c "$assembly" -o "$object"
    "$clang" --target=aarch64-linux-ohos -nostdlib -shared \
        -Wl,-soname,"$name" -o "$stub" "$object"

    real_count="$("$readelf" --dyn-syms --wide "$real" |
        awk '$7 != "UND" && $6 == "DEFAULT" &&
             ($5 == "GLOBAL" || $5 == "WEAK") &&
             ($4 == "FUNC" || $4 == "OBJECT") {
                 name = $8; sub(/@.*/, "", name); if (!seen[name]++) n++
             } END { print n + 0 }')"
    stub_count="$("$readelf" --dyn-syms --wide "$stub" |
        awk '$7 != "UND" && $6 == "DEFAULT" &&
             ($5 == "GLOBAL" || $5 == "WEAK") &&
             ($4 == "FUNC" || $4 == "OBJECT") {
                 name = $8; sub(/@.*/, "", name); if (!seen[name]++) n++
             } END { print n + 0 }')"
    [ "$real_count" -eq "$stub_count" ] || {
        echo "$name parity failed: real=$real_count stub=$stub_count" >&2
        exit 1
    }

    echo "$name: parity=$stub_count"
    count=$((count + 1))
done

[ "$count" -gt 0 ] || {
    echo "no .so inputs found in $source_dir" >&2
    exit 1
}
echo "generated $count ABI-only providers in $output_dir"
