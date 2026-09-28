#!/bin/sh
# Invoked only in the immutable image recorded by the project-local lock.
set -eu

PM=/project/adapter/framework/package-manager
JNI="$PM/jni"
TEST="$PM/test"
OUT=/out
export HOME="$OUT/home"
export TMPDIR="$OUT/tmp"
mkdir -p "$HOME" "$TMPDIR" "$OUT/bin"

g++ -std=c++17 -Wall -Wextra -Werror \
    -I"$JNI" \
    "$JNI/apk_verify_result.cpp" "$TEST/test_apk_verify_result.cpp" \
    -Wl,-z,now -lcrypto \
    -o "$OUT/bin/test_apk_verify_result"
"$OUT/bin/test_apk_verify_result"

g++ -std=c++17 -D_GNU_SOURCE -Wall -Wextra -Werror \
    -I"$JNI" \
    -I/usr/include/minizip \
    "$JNI/apk_verify_result.cpp" \
    "$JNI/apk_signature_verifier.cpp" \
    "$JNI/apk_verifier_client.cpp" \
    "$TEST/test_apk_verifier_client_native.cpp" \
    -Wl,-z,now -lcrypto -lminizip -lz \
    -o "$OUT/bin/test_apk_verifier_client_native"
"$OUT/bin/test_apk_verifier_client_native" \
    /fixtures/signed-v2.apk

g++ -std=c++17 -Wall -Wextra -Werror \
    -I"$JNI" \
    "$JNI/game_install_plan_wire.cpp" \
    "$TEST/test_game_install_plan_wire.cpp" \
    -Wl,-z,now \
    -o "$OUT/bin/test_game_install_plan_wire"
"$OUT/bin/test_game_install_plan_wire"

rm -rf "$OUT/fn01-a01-run"
mkdir -p "$OUT/fn01-a01-run"
gcc -std=c11 -Wall -Wextra -Werror \
    -I"$PM/install_plan/include" \
    -c "$PM/install_plan/src/sha256.c" \
    -o "$OUT/bin/fn01_a01_sha256.o"
g++ -std=c++17 -DFN01_ENABLE_REFERENCE_FIXTURES \
    -Wall -Wextra -Werror \
    -I"$PM/package_transaction/include" \
    -I"$PM/install_plan/include" \
    "$PM/package_transaction/src/package_transaction.cpp" \
    "$PM/package_transaction/tests/package_transaction_host_test.cpp" \
    "$OUT/bin/fn01_a01_sha256.o" \
    -o "$OUT/bin/package_transaction_host_test"
"$OUT/bin/package_transaction_host_test" "$OUT/fn01-a01-run"

rm -rf "$OUT/fn01-a02-run"
mkdir -p "$OUT/fn01-a02-run"
g++ -std=c++17 -DFN01_ENABLE_REFERENCE_FIXTURES \
    -Wall -Wextra -Werror \
    -I"$PM/package_transaction/include" \
    -I"$PM/package_query/include" \
    -I"$PM/install_plan/include" \
    "$PM/package_transaction/src/package_transaction.cpp" \
    "$PM/package_query/src/package_query_v1.cpp" \
    "$PM/package_query/tests/package_query_host_test.cpp" \
    "$OUT/bin/fn01_a01_sha256.o" \
    -o "$OUT/bin/package_query_host_test"
"$OUT/bin/package_query_host_test" "$OUT/fn01-a02-run"

rm -rf "$OUT/fn01-a03-run"
mkdir -p "$OUT/fn01-a03-run"
g++ -std=c++17 -D_GNU_SOURCE -DFN01_PORTABLE_HOST \
    -Wall -Wextra -Werror \
    -fsanitize=address,undefined -fno-omit-frame-pointer -g \
    -I"$PM/manifest_facts/include" \
    -I"$PM/package_transaction/include" \
    -I"$PM/install_plan/include" \
    -I"$JNI" \
    "$PM/package_transaction/src/package_transaction.cpp" \
    "$PM/manifest_facts/src/manifest_facts_v1.cpp" \
    "$PM/manifest_facts/tests/manifest_facts_host_test.cpp" \
    "$JNI/axml_parser.cpp" \
    "$OUT/bin/fn01_a01_sha256.o" \
    -fsanitize=address,undefined \
    -lz \
    -o "$OUT/bin/manifest_facts_host_test"
"$OUT/bin/manifest_facts_host_test" \
    /fixtures/signed-v2.apk "$OUT/fn01-a03-run"

rm -rf "$OUT/fn01-a04-run"
mkdir -p "$OUT/fn01-a04-run"
g++ -std=c++17 -DFN01_ENABLE_REFERENCE_FIXTURES \
    -Wall -Wextra -Werror \
    -fsanitize=address,undefined -fno-omit-frame-pointer -g \
    -I"$PM/package_transaction/include" \
    -I"$PM/package_query/include" \
    -I"$PM/package_info/include" \
    -I"$PM/install_plan/include" \
    "$PM/package_transaction/src/package_transaction.cpp" \
    "$PM/package_info/src/package_info_v1.cpp" \
    "$PM/package_info/src/package_info_runtime_v1.cpp" \
    "$PM/package_info/tests/package_info_host_test.cpp" \
    "$OUT/bin/fn01_a01_sha256.o" \
    -fsanitize=address,undefined \
    -o "$OUT/bin/package_info_host_test"
"$OUT/bin/package_info_host_test" "$OUT/fn01-a04-run"

rm -rf "$OUT/fn01-a05-run"
mkdir -p "$OUT/fn01-a05-run"
g++ -std=c++17 -DFN01_ENABLE_REFERENCE_FIXTURES \
    -Wall -Wextra -Werror \
    -fsanitize=address,undefined -fno-omit-frame-pointer -g \
    -I"$PM/package_transaction/include" \
    -I"$PM/package_query/include" \
    -I"$PM/package_info/include" \
    -I"$PM/application_info/include" \
    -I"$PM/install_plan/include" \
    "$PM/package_transaction/src/package_transaction.cpp" \
    "$PM/package_query/src/package_query_v1.cpp" \
    "$PM/application_info/src/application_info_v1.cpp" \
    "$PM/application_info/src/application_info_public_entry_v1.cpp" \
    "$PM/application_info/src/application_info_runtime_v1.cpp" \
    "$PM/application_info/src/application_info_runtime_owner_v1.cpp" \
    "$PM/application_info/tests/application_info_host_test.cpp" \
    "$OUT/bin/fn01_a01_sha256.o" \
    -fsanitize=address,undefined \
    -pthread \
    -o "$OUT/bin/application_info_host_test"
"$OUT/bin/application_info_host_test" "$OUT/fn01-a05-run"

sha256sum \
    "$JNI/apk_verify_result.cpp" \
    "$JNI/apk_signature_verifier.cpp" \
    "$JNI/apk_verifier_client.cpp" \
    "$JNI/game_install_plan_wire.cpp" \
    "$TEST/test_apk_verify_result.cpp" \
    "$TEST/test_apk_verifier_client_native.cpp" \
    "$TEST/test_game_install_plan_wire.cpp" \
    "$PM/package_transaction/include/package_transaction.h" \
    "$PM/package_transaction/src/package_transaction.cpp" \
    "$PM/package_transaction/tests/package_transaction_host_test.cpp" \
    "$PM/package_query/include/package_query_v1.h" \
    "$PM/package_query/src/package_query_v1.cpp" \
    "$PM/package_query/tests/package_query_host_test.cpp" \
    "$PM/manifest_facts/include/manifest_facts_v1.h" \
    "$PM/manifest_facts/src/manifest_facts_v1.cpp" \
    "$PM/manifest_facts/tests/manifest_facts_host_test.cpp" \
    "$PM/package_info/include/package_info_v1.h" \
    "$PM/package_info/include/package_info_runtime_v1.h" \
    "$PM/package_info/src/package_info_v1.cpp" \
    "$PM/package_info/src/package_info_runtime_v1.cpp" \
    "$PM/package_info/tests/package_info_host_test.cpp" \
    "$PM/application_info/include/application_info_v1.h" \
    "$PM/application_info/include/application_info_public_entry_v1.h" \
    "$PM/application_info/include/application_info_runtime_v1.h" \
    "$PM/application_info/include/application_info_runtime_owner_v1.h" \
    "$PM/application_info/src/application_info_v1.cpp" \
    "$PM/application_info/src/application_info_public_entry_v1.cpp" \
    "$PM/application_info/src/application_info_runtime_v1.cpp" \
    "$PM/application_info/src/application_info_runtime_owner_v1.cpp" \
    "$PM/application_info/tests/application_info_host_test.cpp" \
    "$PM/application_info/tests/application_info_entry_audit.py" \
    "$PM/java/PackageManagerAdapter.java" \
    "$PM/java/PackageInfoBuilder.java" \
    "$PM/jni/package_info_jni.cpp" \
    "$PM/jni/application_info_jni.cpp" \
    "$JNI/axml_parser.h" \
    "$JNI/axml_parser.cpp" \
    "$OUT/bin/test_apk_verify_result" \
    "$OUT/bin/test_apk_verifier_client_native" \
    "$OUT/bin/test_game_install_plan_wire" \
    "$OUT/bin/package_transaction_host_test" \
    "$OUT/bin/package_query_host_test" \
    "$OUT/bin/manifest_facts_host_test" \
    "$OUT/bin/package_info_host_test" \
    "$OUT/bin/application_info_host_test" \
    >"$OUT/artifacts.sha256"

echo "PASS package_manager_locked_host result_model=true sealed_transport=true native_v2=true typed_plan=true fn01_a01_developer_test=true fn01_a02_developer_test=true fn01_a03_developer_test=true fn01_a04_developer_test=true fn01_a05_developer_test=true device_verified=false"
