#!/bin/bash
set -euo pipefail

docker exec codex-pkg-cd-harness bash -lc '
set -euo pipefail
mkdir -p /tmp/oh_adapter_apk_verify_tests
g++ -std=c++17 -D_GNU_SOURCE -DOH_ADAPTER_APK_VERIFY_TESTING \
  -Wall -Wextra -Werror \
  -I/work/framework/package-manager/jni \
  /work/framework/package-manager/jni/apk_verify_result.cpp \
  /work/framework/package-manager/jni/apk_verifier_client.cpp \
  /work/framework/package-manager/test/test_apk_verifier_client_linux.cpp \
  -lcrypto -lpthread -o /tmp/oh_adapter_apk_verify_tests/test_apk_verifier_client_linux
/tmp/oh_adapter_apk_verify_tests/test_apk_verifier_client_linux
'
