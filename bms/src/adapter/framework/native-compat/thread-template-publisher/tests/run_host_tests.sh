#!/usr/bin/env bash

set -euo pipefail
IFS=$'\n\t'
umask 022

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/../../../../.." && pwd -P)
LOCK=$PROJECT_ROOT/adapter/framework/native-compat/thread-template-publisher/evidence/host_runtime.lock
OUT=${THREAD_TEMPLATE_HOST_OUT:-$PROJECT_ROOT/.work/thread-template-publisher-host}

case "$OUT" in
    "$PROJECT_ROOT"/*) ;;
    *) echo "ERROR output escaped project" >&2; exit 2 ;;
esac
[[ -f "$LOCK" ]] || { echo "ERROR missing local tool runtime lock" >&2; exit 2; }
IMAGE=$(awk -F= '$1 == "image_id" {print $2}' "$LOCK")
[[ -n "$IMAGE" ]] || { echo "ERROR empty image lock" >&2; exit 2; }

mkdir -p "$OUT"
ACTUAL=$(docker image inspect "$IMAGE" --format '{{.Id}}')
[[ "$ACTUAL" == "$IMAGE" ]] || { echo "ERROR image identity drift" >&2; exit 2; }

docker run --rm --read-only --network none \
    --cap-drop ALL --security-opt no-new-privileges \
    -v "$PROJECT_ROOT:/project:rw" -w /project "$IMAGE" \
    bash -c '
set -euo pipefail
src=/project/adapter/framework/native-compat/thread-template-publisher/tests/template_copy_host.c
publisher=/project/adapter/framework/native-compat/thread-template-publisher/src/thread_template_publisher.c
include=/project/adapter/framework/native-compat/thread-template-publisher/include
race=/project/adapter/framework/native-compat/thread-template-publisher/tests/publisher_race_host.c
out=/project/.work/thread-template-publisher-host
cc -std=c11 -O2 -Wall -Wextra -Werror -fno-stack-protector -no-pie \
   -Wl,-z,relro,-z,now -pthread -I"$include" "$src" "$publisher" -ldl \
   -o "$out/template-copy"
cc -std=c11 -O2 -Wall -Wextra -Werror -fno-stack-protector -no-pie \
   -Wl,-z,relro,-z,now -pthread -DWLTP_MUTANT_UNPATCHED \
   -I"$include" "$src" "$publisher" -ldl -o "$out/template-copy-mutant"
cc -std=c11 -O2 -Wall -Wextra -Werror -fno-stack-protector -no-pie \
   -Wl,-z,relro,-z,now -pthread -DWLTP_MUTANT_WRONG_OFFSET \
   -I"$include" "$src" "$publisher" -ldl \
   -o "$out/template-copy-wrong-offset-mutant"
cc -std=c11 -O2 -Wall -Wextra -Werror -fno-stack-protector -no-pie \
   -Wl,-z,relro,-z,now -pthread -DWLTP_MUTANT_COMPETING_WRITER \
   -I"$include" "$src" "$publisher" -ldl \
   -o "$out/template-copy-conflict-mutant"
cc -std=c11 -O2 -Wall -Wextra -Werror -fno-stack-protector -no-pie \
   -Wl,-z,relro,-z,now -pthread -I"$include" "$race" "$publisher" -ldl \
   -o "$out/publisher-race"
cc -std=c11 -O2 -Wall -Wextra -Werror -fno-stack-protector -no-pie \
   -Wl,-z,relro,-z,now -pthread -DWLTP_MUTANT_NO_EXACT_ONCE \
   -I"$include" "$race" "$publisher" -ldl \
   -o "$out/publisher-race-no-exact-once-mutant"
readelf -sW "$out/template-copy" | awk \
  "\$8 == \"g_main_tls_reservation\" && \$4 == \"TLS\" && \$3 == 48 {ok=1} END {exit !ok}"
readelf -lW "$out/template-copy" | awk \
  "\$1 == \"TLS\" && \$5 == \"0x000030\" && \$6 == \"0x000030\" {ok=1} END {exit !ok}"
"$out/template-copy"
"$out/publisher-race"
for mutant in \
    template-copy-mutant \
    template-copy-wrong-offset-mutant \
    template-copy-conflict-mutant
do
    set +e
    "$out/$mutant" >"$out/$mutant.log" 2>&1
    rc=$?
    set -e
    test "$rc" -eq 9
    grep -q "FAIL new-thread TLS template copy" "$out/$mutant.log"
done
set +e
"$out/publisher-race-no-exact-once-mutant" \
    >"$out/publisher-race-no-exact-once-mutant.log" 2>&1
rc=$?
set -e
test "$rc" -eq 4
grep -q "FAIL publisher race results=" \
    "$out/publisher-race-no-exact-once-mutant.log"
'

echo "PASS thread-template host exact_once=concurrent mutants_killed=4 product_activation=false"
