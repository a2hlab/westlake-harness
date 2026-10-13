#!/bin/bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
if [ "${1:-}" != --execute ]; then cat "$HERE/mapping.json"; exit 0; fi
: "${WORKSPACES:?}" "${HOLDER:?owner-only lock holder required}"
LOCK="$WORKSPACES/westlake-harness/scripts/lab/board_note.sh"
test "$(shasum -a 256 "$LOCK" | cut -d" " -f1)" = 311fefc23351902712ebf31b46302fd20a6d4230cfadc79ab81b8e73f5b2aca7
test "$(shasum -a 256 "$HERE/remote.sh" | cut -d" " -f1)" = 6041a6f282c5f4040609a70997ded73f391959be8159787758d86551431a1440
test "$(shasum -a 256 "$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r5-experiment-main-r4/run/plan.enabled.json" | cut -d" " -f1)" = 49ec0eec67ea374f78d127d7014ad4c4b64e476ae23dffb627f6255b26c8cfd3
test "$(shasum -a 256 "$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r5-experiment-main-r4/run/transaction/transaction.json" | cut -d" " -f1)" = 49d3ef9f28e3d45193a30a85c0c876024cc91e94f7412ddd4aa80a7100741db4
test "$(shasum -a 256 "$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r5-experiment-main-r4/run/transaction/rollback-1791886647068999000.json" | cut -d" " -f1)" = 5b080d575357fde5b76f4ee191afd64ed00f3f2098fff03054eeff50c3253242
test "$(shasum -a 256 "$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r5-experiment-main-r4/run/closed.json" | cut -d" " -f1)" = de30df6928df23d0cb90cbf8298b95f532babaebed2e89d3b2aab22617d273a8
test "$(shasum -a 256 "$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r5-experiment-main-r4/run/restored-r5.json" | cut -d" " -f1)" = b97376007ccc7abb8510282dad119b2ceb066304c1202654cb6890a909171a9d
test "$(shasum -a 256 "$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r5-experiment-main-r4/board-run/board-run-result.json" | cut -d" " -f1)" = 4e7c96aa12926d706a14d70bdf703aec841065f72c2a60e4a762465eb90f017d
test "$(shasum -a 256 "$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/final-v2-5cd-readonly/capture.json" | cut -d" " -f1)" = 5809dc04c8e9958ac50269d4ec6a783adeb9705e16dda174e56fac9e527160b2
test "$(shasum -a 256 "$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r5-experiment-main-r4/run/candidate-boot-result.json" | cut -d" " -f1)" = ea206db877c5d62b2aa600407ca59db9e9d9c42c106f5058c5448b0efa8bb3b8
test "$(shasum -a 256 "$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r5-experiment-main-r4/run/baseline-return-boot-result.json" | cut -d" " -f1)" = e149de0622b6ec7014e324ddfa3e5e4b59c11122e91c7bdb149e219b7f18345b
test "$(shasum -a 256 "$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r5-experiment-main-r4/run/candidate-boot-intent.json" | cut -d" " -f1)" = 5275f6f55ab57784b8fee77c57af25677f13265bf034e3771b067922b824cd81
test "$(shasum -a 256 "$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r5-experiment-main-r4/run/baseline-return-boot-intent.json" | cut -d" " -f1)" = a445f840d5e82f3dbf4ae304250d9b1f2f78d78d5b030038ff392ed09ea29689
test "$(shasum -a 256 "$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r5-experiment-main-r4/run/transaction/directory-created-000.json" | cut -d" " -f1)" = e88c604dfac3589a27516f7ada434b0b1767b04c7c9cf3dc48bd797748d8d435
test "$(shasum -a 256 "$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r5-experiment-main-r4/run/transaction/directory-created-001.json" | cut -d" " -f1)" = 075371f57b57cd0d52bccf1e0b2bacaf5a0654404eace3ef2bd8ed472eeb70f1
test "$(shasum -a 256 "$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/final-v2-5cd-owned-audit-readonly/receipt.json" | cut -d" " -f1)" = b5a205c11f4f38d9116dfa9bbb20363a24a1b62832ba87f4b7da620fd0d4934f
test "$(shasum -a 256 "$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/final-v2-5cd-owned-audit-readonly/stdout.txt" | cut -d" " -f1)" = 7d1773ddf56493e485d83d4e99023dab70610d5808dd369499395e1719f5185d
test "$(shasum -a 256 "$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/final-v2-5cd-owned-audit-readonly/stderr.txt" | cut -d" " -f1)" = e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
LOG=$(mktemp -d "$HERE/execution.XXXXXX")
date -u > "$LOG/started.txt"
check_held(){
 local text err; err=$(mktemp "$LOG/held.XXXXXX")
 text=$(bash "$LOCK" held 5cd1e3dd00000000000000000923012c 2>"$err") || return 1
 test ! -s "$err" || return 1
 local owner pid stamp extra; read -r owner pid stamp extra <<< "$text"
 test "$owner" = "$HOLDER"; [[ "$pid" =~ ^[0-9]+$ ]]; test -n "$stamp"; test -z "$extra"
 test "$(printf '%s\n' "$text" | wc -l | tr -d ' ')" = 1
 printf "%s" "$text"
}
held=$(check_held)
printf "%s\n" "$held" > "$LOG/held.txt"
test "$(check_held)" = "$held"
test "$(shasum -a 256 "$HERE/command.txt" | cut -d" " -f1)" = 15d6896ee2f89a0cc01df1cf86513f070ac314c5e86d4de45d974b719bfc94b4
if /Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc -t 5cd1e3dd00000000000000000923012c shell "$(cat "$HERE/command.txt")" > "$LOG/stdout" 2> "$LOG/stderr"; then trc=0; else trc=$?; fi
printf "%s\n" "$trc" > "$LOG/transport-rc.txt"
date -u > "$LOG/finished.txt"
cat "$LOG/stdout"; cat "$LOG/stderr" >&2
test "$trc" = 0
test ! -s "$LOG/stderr"
test "$(tail -n 1 "$LOG/stdout" | tr -d '\r')" = ARCHIVE_REMOTE_RC=0
grep -Fx '{"status":"ARCHIVED_VERIFIED","source":"/data/westlake-demo/u13/boat-v2-20261013-r4","destination":"/data/westlake-demo/u13/boat-audit-r5-return-bc6aaeb061fa4671a8733e5188570d4a","boot_id":"362f2212-1a42-4c1a-8487-0dddb091c74b","original_root_absent":true}' "$LOG/stdout"
test "$(check_held)" = "$held"
printf '%s\n' ARCHIVE_HOST_AND_REMOTE_VERIFIED > "$LOG/result.txt"
