#!/bin/sh
# Build data fixtures only. Never execute the generated ELF objects.
set -eu
source_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
output_dir=${1:?usage: rebuild.sh OUTPUT_DIRECTORY}
mkdir -p "$output_dir"
output_dir=$(CDPATH='' cd -- "$output_dir" && pwd)
compiler=${CC:-gcc}
for bits in 32 64; do
    "$compiler" -m"$bits" -fPIC -shared -nostdlib -g0 \
        -Wl,--hash-style=both,--build-id=none,-soname,libfixturedep.so \
        "$source_dir/dependency.c" -o "$output_dir/dependency$bits.elf"
    "$compiler" -m"$bits" -fPIC -shared -nostdlib -g0 \
        -Wl,--hash-style=both,--build-id=none,-soname,libfixture.so \
        "$source_dir/consumer.c" -Wl,--no-as-needed "$output_dir/dependency$bits.elf" \
        -o "$output_dir/consumer$bits.elf"
    "$compiler" -m"$bits" -fPIC -shared -nostdlib -g0 \
        -Wl,--hash-style=both,--build-id=none,-soname,libmiddle.so \
        "$source_dir/middle.c" -Wl,--no-as-needed "$output_dir/dependency$bits.elf" \
        -o "$output_dir/middle$bits.elf"
    "$compiler" -m"$bits" -fPIC -shared -nostdlib -g0 \
        -Wl,--hash-style=both,--build-id=none,-soname,libroot.so \
        "$source_dir/root.c" -Wl,--no-as-needed "$output_dir/middle$bits.elf" \
        -o "$output_dir/root$bits.elf"
    readelf -h -l -d -s "$output_dir/consumer$bits.elf" > "$output_dir/consumer$bits.readelf.txt"
done
"$compiler" --version
