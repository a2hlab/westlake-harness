#!/bin/zsh

# Three-minute autonomous radar heartbeat. All work stays in this adapter.
# Four orthogonal Codex lanes run in parallel; the cycle lock prevents overlap.
# Codex owns both D600 boards. Claude owns both D200 boards outside this loop.
set -u
export PATH="/Users/alexyang/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

ROOT="/opt/21.Game/02.unity.cardwords/adapter"
STATE="$ROOT/out/auto_drive"
LOCK="$STATE/.codex.lock"
LOG="$STATE/heartbeat.log"
INTERVAL_SECONDS=180
LOOP_MESSAGE="自驱动，自循环，直到实现 Unity 安卓游戏上屏幕"
mkdir -p "$STATE"

recover_stale_lock() {
  [[ -d "$LOCK" ]] || return 0
  local owner=""
  owner="$(cat "$LOCK/pid" 2>/dev/null || true)"
  if [[ -z "$owner" ]] || ! kill -0 "$owner" 2>/dev/null; then
    rm -f "$LOCK/pid"
    rmdir "$LOCK" 2>/dev/null || true
  fi
}

run_lane() {
  local lane="$1"
  local task="$2"
  local lane_log="$STATE/lane_${lane}.log"
  local sandbox="read-only"
  local scope="只读 canonical adapter 与外部 OH/AOSP/artifacts；不得改外部树。"
  if [[ "$lane" == d600_a || "$lane" == d600_b ]]; then
    sandbox="danger-full-access"
    scope="可仅按任务指定的设备/工具执行取证、启动、自动化 UI 或视频测试，并将新证据写入 canonical adapter/out；不得改外部 OH/AOSP 源树。"
  fi
  {
    printf '[%s] lane=%s start\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$lane"
    cd "$ROOT" || exit 1
    codex exec --ephemeral --skip-git-repo-check --sandbox "$sandbox" --color never \
      -C "$ROOT" -o "$STATE/lane_${lane}.last.md" \
      "你是独立雷达角度 ${lane}，使用当前 Codex 高能力模型，不切换 fast 模型。先完整读取 COORDINATION.md。${scope}${task} 只做一个有界子任务，输出 JSON 风格结论：claim、Proven、Not-proven、Failed、Exact evidence、下一步。不得改 APK/SO、不得使用 title/package allowlist、LD_PRELOAD、raw rt_sigaction 或全局 signal override；不得把 host/static 结果标成 build_pass/device_verified。若发现其它 lane 正在改动，只做只读审查。遇到权限、安全或资源阻塞时，不等待人工确认，不绕过红线；记录阻塞证据后立即切换到下一个安全子任务并结束本轮。" 2>&1
    printf '[%s] lane=%s end\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$lane"
  } >> "$lane_log" 2>&1
}

while true; do
  recover_stale_lock
  if mkdir "$LOCK" 2>/dev/null; then
    printf '[%s] heartbeat start lanes=4 interval=%ss message=%s\n' \
      "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$INTERVAL_SECONDS" "$LOOP_MESSAGE" >> "$LOG"
    print -r -- $$ > "$LOCK/pid"
    run_lane "abi" "从 L03.A13.A01/A02 角度审计 Bionic32/Musl152 转换、claimed signal chain、redzone 与 public musl provider 语义；尽力证伪当前 broker 候选。" &
    run_lane "loader" "从 L03.A13 loader 角度审计 ELF64 PT_DYNAMIC/RELA、RELRO 恢复、provider identity、递归 dlopen 与 constructor 时序；尽力证伪 post-load/GOT 候选。" &
    run_lane "d600_a" "你独占 D600-A '5bb5b1ae00000000000000000823012c'。可用 hdc 做有界 provider/readback、启动、hilog、截图、录屏与 UI 自动化；先取 boot_id 和当前 APK/adapter identity。不得改写 APK/SO，未有已审查候选时不得部署系统库。" &
    run_lane "d600_b" "你独占 D600-B '5eab586000000000000000001123012c'。可用 hdc 做独立的原始 APK 安装/启动前置、crash/输入/录屏基线或复现实验；先取 boot_id 和当前 APK/adapter identity。不得改写 APK/SO，未有已审查候选时不得部署系统库。" &
    wait
    printf '[%s] heartbeat end lanes=4 message=%s\n' \
      "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$LOOP_MESSAGE" >> "$LOG"
    rm -f "$LOCK/pid"
    rmdir "$LOCK" 2>/dev/null || true
  fi
  sleep "$INTERVAL_SECONDS"
done
