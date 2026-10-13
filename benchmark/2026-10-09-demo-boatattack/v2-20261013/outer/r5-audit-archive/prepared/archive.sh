#!/bin/bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
if [ "${1:-}" != --execute ]; then cat "$HERE/mapping.json"; exit 0; fi
: "${WORKSPACES:?}" ": ${HOLDER:?owner-only lock holder required}"
LOCK="$WORKSPACES/westlake-harness/scripts/lab/board_note.sh"
test "$(shasum -a 256 "$LOCK" | cut -d" " -f1)" = 311fefc23351902712ebf31b46302fd20a6d4230cfadc79ab81b8e73f5b2aca7
test "$(shasum -a 256 "$HERE/remote.sh" | cut -d" " -f1)" = 20b77263ac9aaa391b374c5d12cfad2b9870007e41e6d2bbf88fbb4612efd27f
test "$(shasum -a 256 "$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r5-experiment-main-r3/run/plan.enabled.json" | cut -d" " -f1)" = 49ec0eec67ea374f78d127d7014ad4c4b64e476ae23dffb627f6255b26c8cfd3
test "$(shasum -a 256 "$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r5-experiment-main-r3/run/transaction/transaction.json" | cut -d" " -f1)" = 49d3ef9f28e3d45193a30a85c0c876024cc91e94f7412ddd4aa80a7100741db4
test "$(shasum -a 256 "$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r5-experiment-main-r3/run/transaction/rollback-1791885140212660000.json" | cut -d" " -f1)" = 5912527d71eedc89267b3a1af6a6261d5f31bcfbc32e6af7c4f46b2c0cf7c9a6
test "$(shasum -a 256 "$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r5-experiment-main-r3/run/closed.json" | cut -d" " -f1)" = c507939ed0a716f092183a706c738754dc2239f37459eb6783cc3c90d499c11a
test "$(shasum -a 256 "$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r5-experiment-main-r3/run/restored-r5.json" | cut -d" " -f1)" = b4bb36c8db3272780428476be12568f37f281ae6bad21523aaed35579859d3e2
test "$(shasum -a 256 "$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r5-experiment-main-r3/board-run/board-run-result.json" | cut -d" " -f1)" = 3e01db8a9af54bd85b20efdb442ac5de6d5112d4ca28136b6b6fbbe1b1e81d47
test "$(shasum -a 256 "$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r5-experiment-main-r3/run/transaction/directory-created-000.json" | cut -d" " -f1)" = 78580fa587dca5d79bf28a22d3fe142667a8de341caa17d405ab3b0afddcd217
test "$(shasum -a 256 "$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r5-experiment-main-r3/run/transaction/directory-created-001.json" | cut -d" " -f1)" = 8fb3ad92400168e8de9f42dca908d5860f05522557aa7b2e81aac9bed8f352b0
check_held(){
 local text; text=$(bash "$LOCK" held 5cd1e3dd00000000000000000923012c 2>&1) || return 1
 local owner pid stamp extra; read -r owner pid stamp extra <<< "$text"
 test "$owner" = "$HOLDER"; [[ "$pid" =~ ^[0-9]+$ ]]; test -n "$stamp"; test -z "$extra"
 printf "%s" "$text"
}
held=$(check_held)
test "$(check_held)" = "$held"
/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc -t 5cd1e3dd00000000000000000923012c shell "$(cat "$HERE/remote.sh")"
test "$(check_held)" = "$held"
