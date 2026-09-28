#!/bin/bash
# 把 origin/main 同步进每条大类分支。
#
# ┌─ owner 2026-08-05 裁定:公共代码在分支上可以自由修改,不做自动同步。
# │  本脚本供 owner 手动使用。agent 不要运行,也不要设定期任务。
# │  裁决记录 var/state/decisions/20260805-app-category-branches.md
# └─
#
# 用法:
#   bash src/tools/app-categories/sync-categories.sh              # 同步全部分支
#   bash src/tools/app-categories/sync-categories.sh basic native # 只同步指定分支
#   DRY=1 bash src/tools/app-categories/sync-categories.sh        # 只报告落后多少,不改动
#
# 冲突的分支报告后跳过,不中断其余分支。
# 在临时 worktree 里操作,不碰当前工作目录。
set -uo pipefail

cd "$(git rev-parse --show-toplevel)"
CATS_YAML=docs/spec/apk-sample-set.yaml
WT_ROOT="${TMPDIR:-/tmp}/app-sync-$$"
DRY="${DRY:-0}"

if [ $# -gt 0 ]; then
  SLUGS="$*"
else
  SLUGS=$(grep -E '^\s+- slug:' "$CATS_YAML" | sed 's/.*slug:\s*//' | tr -d '\r')
fi

echo "== fetch origin =="
git fetch origin --prune --quiet || { echo "fetch 失败"; exit 1; }

rc=0
conflicted=""
synced=""
missing=""

for slug in $SLUGS; do
  br="app/$slug"
  if ! git rev-parse --verify --quiet "origin/$br" >/dev/null; then
    echo "-- $br : 远端不存在,跳过"
    missing="$missing $slug"
    continue
  fi

  behind=$(git rev-list --count "origin/$br..origin/main")
  ahead=$(git rev-list --count "origin/main..origin/$br")
  echo "-- $br : 落后 main $behind,自有 $ahead"

  [ "$behind" -eq 0 ] && { echo "   已是最新"; synced="$synced $slug"; continue; }
  [ "$DRY" = "1" ] && continue

  wt="$WT_ROOT/$slug"
  rm -rf "$wt"
  if ! git worktree add --quiet -B "$br" "$wt" "origin/$br" 2>/dev/null; then
    echo "   worktree 创建失败,跳过"
    rc=1; continue
  fi

  if git -C "$wt" merge --no-edit origin/main >/dev/null 2>&1; then
    if git -C "$wt" push origin "$br" >/dev/null 2>&1; then
      echo "   已同步并推送"
      synced="$synced $slug"
    else
      echo "   合并成功但推送失败"
      rc=1
    fi
  else
    files=$(git -C "$wt" diff --name-only --diff-filter=U | head -20)
    echo "   冲突,跳过。冲突文件:"
    echo "$files" | sed 's/^/     /'
    git -C "$wt" merge --abort 2>/dev/null
    conflicted="$conflicted $slug"
    rc=1
  fi

  git worktree remove --force "$wt" 2>/dev/null
done

git worktree prune
rm -rf "$WT_ROOT"

echo
echo "== 汇总 =="
[ -n "$synced" ]     && echo "  已同步:$synced"
[ -n "$conflicted" ] && echo "  有冲突(需人工处理):$conflicted"
[ -n "$missing" ]    && echo "  分支不存在:$missing"
exit $rc
