#!/bin/bash
# One offline relink of the already pinned r8 inputs. Not executed by this lane.
# Keep the failed outer build intact; OUT must be a fresh persistent directory.
set -euo pipefail
: "${BUILD_SOURCE:?existing r8-build-outer-2324/build with verified inputs}"
: "${SOURCE_REPO:?repository supplying existing dockbuild.sh}"
: "${OH_NATIVE:?container-visible exact pinned OH SDK native root}"
: "${OUT:?fresh persistent absolute directory}"
case "$OUT" in /tmp/*|/private/tmp/*) exit 2;; /*) ;; *) exit 2;; esac
DB="$SOURCE_REPO/scripts/lab/dockbuild.sh"
mkdir "$OUT"
cp -R "$BUILD_SOURCE/src" "$BUILD_SOURCE/inputs" "$BUILD_SOURCE/link-only.NOT-FOR-DEPLOY" "$OUT/"
cp "$BUILD_SOURCE/inputs.sha256" "$BUILD_SOURCE/compare-abi.py" "$OUT/"
mkdir "$OUT/raw" "$OUT/unstripped" "$OUT/artifacts"
cp "$BUILD_SOURCE/raw/30-old-abi.stdout" "$BUILD_SOURCE/raw/05-liblog-abi.stdout" "$OUT/raw/"
cd "$OUT"
step() {
  local name=$1 rc; shift
  printf '%q ' "$@" > "raw/$name.command"; printf '\n' >> "raw/$name.command"
  if "$@" > "raw/$name.stdout" 2> "raw/$name.stderr"; then rc=0; else rc=$?; fi
  printf '%s\n' "$rc" > "raw/$name.rc"
  printf '%s rc=%s\n' "$name" "$rc"
  [ "$rc" -eq 0 ] || exit "$rc"
}
step 00-inputs shasum -a 256 -c inputs.sha256
cat > relink.sh <<'INNER'
#!/bin/bash
set -euo pipefail
OH=$1; action=$2
flags=(--target=aarch64-linux-ohos --sysroot="$OH/sysroot" -fPIC -O2 -g
  -Wall -Wextra -Werror -shared -fuse-ld=lld -Wl,-z,relro,-z,now,-z,defs
  -Wl,-soname,libopensles_android_compat.so src/opensles_android_compat.c src/ttplayer_log_mirror.c
  -ldl -Llink-only.NOT-FOR-DEPLOY -Linputs -Wl,--no-as-needed -lOpenSLES -l:liblog.so
  -Wl,--as-needed -o unstripped/libopensles_android_compat.so)
case "$action" in
  driver-default) "$OH/llvm/bin/clang-15" -### "${flags[@]}" ;;
  driver-none) "$OH/llvm/bin/clang-15" -### --unwindlib=none "${flags[@]}" ;;
  link) "$OH/llvm/bin/clang-15" --unwindlib=none "${flags[@]}" \
    -Wl,--why-extract=raw/unwind-none.why-extract.txt -Wl,-Map,raw/unwind-none.map ;;
  strip) cp unstripped/libopensles_android_compat.so artifacts/libopensles_android_compat.so
    "$OH/llvm/bin/llvm-strip" --strip-unneeded artifacts/libopensles_android_compat.so ;;
  abi) "$OH/llvm/bin/llvm-readelf" -h -dW --dyn-syms artifacts/libopensles_android_compat.so ;;
  relocs) "$OH/llvm/bin/llvm-readelf" -rW artifacts/libopensles_android_compat.so ;;
  *) exit 2 ;;
esac
INNER
invoke() {
  local command
  printf -v command 'bash %q %q %q' "$OUT/relink.sh" "$OH_NATIVE" "$2"
  step "$1" "$DB" run -- "$command"
}
invoke 10-driver-default driver-default
invoke 11-driver-none driver-none
invoke 20-link link
invoke 21-strip strip
invoke 31-new-abi abi
invoke 32-relocations relocs
step 33-abi-compare python3 compare-abi.py
step 34-inputs-after shasum -a 256 -c inputs.sha256
step 40-output-sha shasum -a 256 unstripped/libopensles_android_compat.so artifacts/libopensles_android_compat.so
printf 'Offline relink only. Production provider binding remains pending.\n'
