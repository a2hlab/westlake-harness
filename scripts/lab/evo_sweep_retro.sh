#!/bin/bash
# Light retro after every full sweep (user rule 2026-10-01): harvest this round's R2 records into cards and count
# them by family, then post one summary line on the board. Only the cards since the sweep started are looked at.
#
#   evo_sweep_retro.sh <sweep start, ISO UTC e.g. 2026-10-01T03:50:00Z> [board.md]
#
# The full every-two-hours retro (olp-evo-retro.sh + at most 3 DIGEST/RUNBOOK/tool items) is unchanged.
set -euo pipefail
SINCE=${1:?usage: evo_sweep_retro.sh <ISO UTC start> [board.md]}
REPO=$(cd "$(dirname "$0")/../.." && pwd)
BOARD=${2:-$REPO/.octos/boards/app-lighting.md}
HARVEST=${OLP_EVO_HARVEST:-$HOME/workspace/octoscode/scripts/olp-evo-harvest.sh}
export OLP_EVO_REVIEW_BOARD=$BOARD
[ -d /opt/homebrew/opt/coreutils/libexec/gnubin ] && export PATH=/opt/homebrew/opt/coreutils/libexec/gnubin:$PATH
"$HARVEST" "$REPO" 2>&1 | tail -1
SUMMARY=$(python3 "$REPO/scripts/lab/evo_family.py" --since "$SINCE")
echo "$SUMMARY"
FAM=$(printf '%s\n' "$SUMMARY" | sed -n '2,$p' | sed -E 's/^ +//; s/ +/ /g' | cut -d' ' -f1,2 | tr '\n' ';')
"$REPO/scripts/lab/board_append.sh" "$BOARD" "ACK(95): $(date +%Y-%m-%dT%H:%M:%S%z) 外环(claude) 全量后轻量 retro(只看 $SINCE 之后的卡):$(printf '%s' "$SUMMARY" | head -1);按家族:${FAM:-无}。同家族本轮 ≥2 张就在下一次完整 retro 优先处理。"
