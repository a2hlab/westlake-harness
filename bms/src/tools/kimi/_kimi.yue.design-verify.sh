#!/bin/bash
# _kimi.yue.design-verify.sh
# Design-verify lane: L0/L1 spec validation + L3 oracle skeleton generation.
# Run this in its own terminal window for isolation (launched by _kimi.yue.sh).
set -euo pipefail

MAIN_REPO="/opt/Bridge"
WORKDIR="${MAIN_REPO}/worker2/design-verify"
LOG="${MAIN_REPO}/evidence/runs/_kimi.yue.design-verify.log"

mkdir -p "$(dirname "$LOG")"

cd "$WORKDIR"

exec > >(tee -a "$LOG") 2>&1

set +e
./run.sh
RC=$?
set -e

echo "===== 报告摘要 ====="
sed -n '1,60p' reports/Fn01-design-validation.md || true
echo "===== run.sh exit=${RC}（1=存在真实 ERROR，详见 reports/Fn01-design-validation.md）====="

exec bash
