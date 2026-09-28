#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
OUT_DIR=${FN01_HOST_TEST_OUT:-"$SCRIPT_DIR/out-host"}
CXX=${CXX:-c++}
TEST_BINARY=$OUT_DIR/test_fn01_topology

mkdir -p "$OUT_DIR"

if [[ ${FN01_HOST_TEST_CAPTURE:-0} != 1 ]]; then
  set +e
  FN01_HOST_TEST_CAPTURE=1 "$0" >"$OUT_DIR/host-tests.log" 2>&1
  test_status=$?
  set -e
  cat "$OUT_DIR/host-tests.log"
  exit "$test_status"
fi

"$CXX" \
  -std=c++17 \
  -Wall \
  -Wextra \
  -Werror \
  -I"$SCRIPT_DIR" \
  "$SCRIPT_DIR/fn01_secure_store.cpp" \
  "$SCRIPT_DIR/test_fn01_topology.cpp" \
  -o "$TEST_BINARY"
"$TEST_BINARY"

grep -q 'O_NOFOLLOW' "$SCRIPT_DIR/fn01_secure_store.cpp"
grep -q 'openat' "$SCRIPT_DIR/fn01_secure_store.cpp"
grep -q 'fstatat' "$SCRIPT_DIR/fn01_secure_store.cpp"
grep -q 'lstat' "$SCRIPT_DIR/fn01_secure_store.cpp"
grep -q 'S_ISDIR(value.st_mode)' "$SCRIPT_DIR/fn01_secure_store.cpp"
grep -q 'S_ISREG(value.st_mode)' "$SCRIPT_DIR/fn01_secure_store.cpp"
grep -q 'value.st_uid == owner' "$SCRIPT_DIR/fn01_secure_store.cpp"
grep -q 'CLIENT_CLAIM_REJECTED' "$SCRIPT_DIR/fn01_topology_probe.cpp"
grep -q 'ClaimVerdict::kUnsupportedUser' "$SCRIPT_DIR/fn01_topology_policy.h"
grep -q 'client_identity' "$SCRIPT_DIR/run_device_e1_e3.sh"
grep -q '"id -u"' "$SCRIPT_DIR/run_device_e1_e3.sh"
grep -Fq "client '\$client_uid' 0" "$SCRIPT_DIR/run_device_e1_e3.sh"
grep -q 'libsamgr_common.z.so' "$SCRIPT_DIR/audit_device_readonly.sh"
grep -q 'bundle_permission_mgr.cpp' "$SCRIPT_DIR/audit_on_alexpc.sh"
grep -q 'bundle_framework_core_ipc_interface_code.h' \
  "$SCRIPT_DIR/audit_on_alexpc.sh"

set +e
"$SCRIPT_DIR/run_device_e1_e3.sh" \
  5EAB586000000000000000001123012C \
  /does/not/exist \
  /tmp/fn01-runner-must-not-create >/dev/null 2>&1
refuse_5eab_rc=$?
"$SCRIPT_DIR/audit_device_readonly.sh" \
  5EAB586000000000000000001123012C >/dev/null 2>&1
audit_refuse_5eab_rc=$?
"$SCRIPT_DIR/run_device_e1_e3.sh" \
  NOT-ALLOWLISTED \
  /does/not/exist \
  /tmp/fn01-runner-random-must-not-create >/dev/null 2>&1
refuse_random_rc=$?
"$SCRIPT_DIR/audit_device_readonly.sh" \
  NOT-ALLOWLISTED >/dev/null 2>&1
audit_refuse_random_rc=$?
"$SCRIPT_DIR/run_device_e1_e3.sh" \
  61B0657200000000000000000324012C \
  /does/not/exist \
  /tmp/fn01-runner-61b0-must-not-create >/dev/null 2>&1
allow_upper_61b0_rc=$?
"$SCRIPT_DIR/run_device_e1_e3.sh" \
  654B3A6B00000000000000000824012C \
  /does/not/exist \
  /tmp/fn01-runner-654b-must-not-create >/dev/null 2>&1
allow_upper_654b_rc=$?
set -e
test "$refuse_5eab_rc" -eq 65
test "$audit_refuse_5eab_rc" -eq 64
test "$refuse_random_rc" -eq 66
test "$audit_refuse_random_rc" -eq 65
test "$allow_upper_61b0_rc" -eq 68
test "$allow_upper_654b_rc" -eq 68
test ! -e /tmp/fn01-runner-must-not-create
test ! -e /tmp/fn01-runner-random-must-not-create
test ! -e /tmp/fn01-runner-61b0-must-not-create
test ! -e /tmp/fn01-runner-654b-must-not-create

bash -n \
  "$SCRIPT_DIR/build_on_alexpc.sh" \
  "$SCRIPT_DIR/audit_on_alexpc.sh" \
  "$SCRIPT_DIR/audit_device_readonly.sh" \
  "$SCRIPT_DIR/run_device_e1_e3.sh"

printf 'PASS fn01_topology_static_gates\n'
printf 'HOST_TEST_BINARY_SHA256=%s\n' \
  "$(shasum -a 256 "$TEST_BINARY" | awk '{print $1}')"
