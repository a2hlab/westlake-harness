#!/bin/bash
# _kimi.yue.fn05.sh — Fn05（输入）交互式 lane（host 契约升级，零设备）
exec /Users/alexyang/.agents/skills/lane-launch/scripts/ilane.sh \
  --agent kimi \
  --prompt /opt/Bridge/worker2/prompts/fn05-lane.md \
  --title "Fn05" \
  --bounds "0 450 860 1110"
