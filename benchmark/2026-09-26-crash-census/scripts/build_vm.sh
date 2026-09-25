#!/usr/bin/env bash
set -euo pipefail
# Run in a2hlab via orb -m a2hlab bash -lc. No board operations.
src=$(cd -- "$(dirname -- "$0")/../native" && pwd)
output=${1:-"$HOME/a2hlab/ws/out-crash42/recorder"}
mkdir -p "$output"
cc -std=c11 -O2 -g -fno-omit-frame-pointer -Wall -Wextra -Werror \
  "$src/crash_snapshot.c" "$src/test_snapshot.c" -o "$output/test_snapshot"
testdir=$(mktemp -d "$output/host-test.XXXXXX")
"$output/test_snapshot" "$testdir" >"$testdir/stdout" 2>"$testdir/stderr"
python3 - "$testdir" <<'PY'
import pathlib, sys
p = pathlib.Path(sys.argv[1])
records = list(p.glob('*.txt'))
assert len(records) == 1, records
fields = {}
for line in records[0].read_text().splitlines():
    if line.startswith('[CRASH42] '):
        k, v = line[10:].split('=')
        fields[k] = int(v, 16)
assert fields['capture_end'] == 1
assert fields['stack_complete_to_vma_end'] == 1
assert records[0].with_suffix('.stack').stat().st_size == fields['stack_bytes'] > 0
assert records[0].with_suffix('.maps').stat().st_size > 0
assert records[0].with_suffix('.ucontext').stat().st_size > 0
print('PASS: raw context, maps and complete SP-to-VMA-end stack saved')
PY
sdk="$HOME/a2hlab/ws/toolchains/ohos-sdk/native"
"$sdk/llvm/bin/clang" --target=aarch64-linux-ohos --sysroot="$sdk/sysroot" \
  -std=c11 -O2 -g -fPIC -fno-omit-frame-pointer -Wall -Wextra -Werror \
  -shared "$src/crash_snapshot.c" -o "$output/libcrash42_snapshot.so" \
  -Wl,-z,defs,-z,relro,-z,now
"$sdk/llvm/bin/clang" --target=aarch64-linux-ohos --sysroot="$sdk/sysroot" \
  -std=c11 -O2 -g -fno-omit-frame-pointer -Wall -Wextra -Werror \
  "$src/crash_snapshot.c" "$src/test_snapshot.c" -o "$output/test_snapshot-ohos"
sha256sum "$output/libcrash42_snapshot.so" "$output/test_snapshot-ohos" >"$output/SHA256SUMS"
python3 "$(dirname -- "$0")/prepare_sigchain.py" \
  "$HOME/a2hlab/ws/art-build/stubs/sigchain_musl.cc" "$output/sigchain_musl_diag.cc"
c++ -O2 -Wall -Wextra -Werror -I"$src" "$output/sigchain_musl_diag.cc" \
  "$src/test_sigchain.cc" -pthread -o "$output/test_sigchain"
"$output/test_sigchain" >"$output/sigchain-test.stdout" 2>"$output/sigchain-test.stderr"
"$sdk/llvm/bin/clang" --target=aarch64-linux-ohos --sysroot="$sdk/sysroot" \
  -std=c11 -O2 -g -fPIC -Wall -Wextra -Werror -c "$src/crash_snapshot.c" \
  -o "$output/crash_snapshot.o"
"$sdk/llvm/bin/clang++" --target=aarch64-linux-ohos --sysroot="$sdk/sysroot" \
  -O2 -g -fPIC -Wall -Wextra -Werror -nostdlib++ -I"$src" -shared \
  "$output/sigchain_musl_diag.cc" "$output/crash_snapshot.o" \
  -Wl,-soname,libsigchain.so,-z,defs,-z,relro,-z,now -o "$output/libsigchain.so"
sha256sum "$output/libsigchain.so" >>"$output/SHA256SUMS"
printf 'VM_READY %s\n' "$output"
