#!/usr/bin/env bash
set -euo pipefail
if [ "${U16_OUTER_REPLAY:-}" != outer-approved ]; then
  echo 'DISABLED: outer only; no remote or device operation'
  exit 78
fi
: "${LAB_HOME:?explicit frozen lab directory required}"
[ "$(uname -s)" = Linux ] && [ "$(uname -m)" = x86_64 ] && [ "$(hostname -s)" = ecs-9f6c ] || exit 3
[ "$(printf %s "$LAB_HOME" | sha256sum | cut -d ' ' -f 1)" = 4e5277d9907dc562d2135c48e53fa1ed5764ab628dae1e8e397499e708a1c102 ] || exit 3
ROOT="$LAB_HOME/u16-stubs-8593-runtime-f6f5-v3-20261003T162410-42707"
OATDUMP="$LAB_HOME/aosp-14.0.0_r1-art/out/host/linux-x86/bin/oatdump"
export LD_LIBRARY_PATH="$LAB_HOME/aosp-14.0.0_r1-art/out/host/linux-x86/lib64"
printf '%s  %s\n' cd3babf9b1db4066c3e38414aeb74a0c251305a9d167a3a547a615ec4519d8f5 "$OATDUMP" | sha256sum -c -
(cd "$ROOT" && sha256sum -c SHA256SUMS)
OUT="$ROOT/oatdump-u16-$(date +%Y%m%dT%H%M%S)-$$"
[ ! -e "$OUT" ] || exit 4
mkdir -p "$OUT"
BCP=; LOCATIONS=
for JAR in core-oj core-libart core-icu4j okhttp bouncycastle apache-xml adapter-mainline-stubs framework oh-adapter-framework; do
  BCP="$BCP${BCP:+:}$ROOT/jars9/$JAR.jar"
  LOCATIONS="$LOCATIONS${LOCATIONS:+:}/system/android/framework/$JAR.jar"
done
for RUN in 1 2; do
  mkdir -p "$OUT/img-run$RUN"
  ln -s "$ROOT/run$RUN" "$OUT/img-run$RUN/arm64"
  COMMAND=("$OATDUMP" "--image=$OUT/img-run$RUN/boot.art" --instruction-set=arm64 --header-only --runtime-arg "-Xbootclasspath:$BCP" --runtime-arg "-Xbootclasspath-locations:$LOCATIONS")
  printf '%s\n' "${COMMAND[@]}" > "$OUT/run$RUN.argv.txt"
  set +e
  "${COMMAND[@]}" 2>&1 | tee "$OUT/run$RUN.log" >/dev/null
  STATUS=("${PIPESTATUS[@]}")
  set -e
  printf '{"oatdump_exit_code":%s,"tee_exit_code":%s}\n' "${STATUS[0]}" "${STATUS[1]}" > "$OUT/run$RUN.status.json"
  sha256sum "$OUT/run$RUN.log" "$OUT/run$RUN.argv.txt" "$OUT/run$RUN.status.json"
  [ "${STATUS[0]}" -eq 0 ] && [ "${STATUS[1]}" -eq 0 ] || exit 8
  grep -n -A14 -B3 -E '0x7003e360:|0x7003e380:|0x7003e3a8:|CANCELLED:' "$OUT/run$RUN.log" > "$OUT/run$RUN.excerpt.txt"
done
printf '%s\n' "$OUT"
find "$OUT" -maxdepth 1 -type f ! -name SHA256SUMS -print0 | LC_ALL=C sort -z | xargs -0 sha256sum > "$OUT/SHA256SUMS"
echo "PERSISTENT_OBJECT_DUMP=$OUT (return excerpts/status/argv/SHA256SUMS; keep full logs here)"
