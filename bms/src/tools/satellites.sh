#!/usr/bin/env bash
# 卫星仓库拉取与状态查询。真源：docs/spec/satellites.yaml
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

# name|url|mount
SATS=(
  "00.Workspace-var|git@github.com:a2hlab/00.Workspace-var.git|var"
  "00.Workspace-vendor|git@github.com:a2hlab/00.Workspace-vendor.git|src/vendor"
)

usage() { echo "用法: $0 {pull|status}"; exit 2; }
[ $# -ge 1 ] || usage

case "$1" in
  pull)
    for s in "${SATS[@]}"; do
      IFS='|' read -r name url mount <<<"$s"
      if [ -d "$mount/.git" ]; then
        echo "== $name 已存在，更新 $mount"
        git -C "$mount" pull --ff-only
      else
        echo "== $name 克隆到 $mount"
        mkdir -p "$(dirname "$mount")"
        rm -rf "${mount:?}"
        git clone "$url" "$mount"
      fi
    done
    ;;
  status)
    for s in "${SATS[@]}"; do
      IFS='|' read -r name url mount <<<"$s"
      if [ -d "$mount/.git" ]; then
        printf "%-22s %s  HEAD=%s  文件=%s\n" "$name" "$mount" \
          "$(git -C "$mount" rev-parse --short HEAD)" \
          "$(git -C "$mount" ls-files | wc -l | tr -d ' ')"
      else
        printf "%-22s %s  未拉取（运行 %s pull）\n" "$name" "$mount" "$0"
      fi
    done
    ;;
  *) usage ;;
esac
