#!/bin/zsh

# Generate a bounded Claude work queue every five minutes without touching devices.
set -u
export PATH="/Users/alexyang/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

ROOT="/opt/21.Game/02.unity.cardwords/adapter"
STATE="$ROOT/out/claude_task_radar"
TASKS="$ROOT/coordination/tasks"
QUEUE="$TASKS/CLAUDE_AUTO_QUEUE.md"
SEED="$TASKS/CLAUDE_AUTO_QUEUE.seed.md"
CANDIDATE="$STATE/candidate.md"
LAST_MESSAGE="$STATE/codex.last.md"
LOG="$STATE/heartbeat.log"
LOCK="$STATE/.generator.lock"
INTERVAL_SECONDS=300
MAX_GENERATION_SECONDS=180

mkdir -p "$STATE" "$TASKS"

log_event() {
  printf '[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$1" >> "$LOG"
}

recover_stale_lock() {
  [[ -d "$LOCK" ]] || return 0
  local owner=""
  owner="$(cat "$LOCK/pid" 2>/dev/null || true)"
  if [[ -z "$owner" ]] || ! kill -0 "$owner" 2>/dev/null; then
    rm -f "$LOCK/pid"
    rmdir "$LOCK" 2>/dev/null || true
  fi
}

validate_candidate() {
  [[ -s "$CANDIDATE" ]] || return 1
  grep -q '^# Claude 自动任务队列$' "$CANDIDATE" || return 1

  local task_count
  task_count="$(grep -c '^## TASK [1-3] ' "$CANDIDATE" 2>/dev/null || true)"
  (( task_count >= 1 && task_count <= 3 )) || return 1
  [[ "$(grep -c '^- 原子编号：' "$CANDIDATE" 2>/dev/null || true)" == "$task_count" ]] || return 1
  [[ "$(grep -c '^- 执行边界：' "$CANDIDATE" 2>/dev/null || true)" == "$task_count" ]] || return 1
  [[ "$(grep -c '^- 核心问题：' "$CANDIDATE" 2>/dev/null || true)" == "$task_count" ]] || return 1
  [[ "$(grep -c '^- 所需证据：' "$CANDIDATE" 2>/dev/null || true)" == "$task_count" ]] || return 1
  [[ "$(grep -c '^- 验收条件：' "$CANDIDATE" 2>/dev/null || true)" == "$task_count" ]] || return 1
  [[ "$(grep -c '^- 红线：' "$CANDIDATE" 2>/dev/null || true)" == "$task_count" ]] || return 1
  grep -Eq 'L(0[1-9]|1[0-4])\.A[0-9][0-9]' "$CANDIDATE" || return 1
  local unique_atom_count
  unique_atom_count="$(sed -n 's/^- 原子编号：\(L[0-9][0-9]\.A[0-9][0-9]\).*$/\1/p' "$CANDIDATE" | sort -u | wc -l | tr -d ' ')"
  [[ "$unique_atom_count" == "$task_count" ]] || return 1

  # D600 may appear only as a red-line statement; serials and D600 tooling are forbidden.
  grep -Eq '5bb5b1ae00000000000000000823012c|5eab586000000000000000001123012c|hdc (shell|install|file)' "$CANDIDATE" && return 1
  grep -Eq 'host-only|D200-A|D200-B|host/D200' "$CANDIDATE" || return 1
  return 0
}

ensure_seed_queue() {
  [[ -f "$QUEUE" ]] && return 0
  if [[ ! -s "$SEED" ]]; then
    log_event "seed_failed reason=missing_seed queue_present=false"
    return 1
  fi
  cp "$SEED" "$QUEUE.next"
  mv "$QUEUE.next" "$QUEUE"
  log_event "seed_published tasks=$(grep -c '^## TASK ' "$QUEUE") sha256=$(shasum -a 256 "$QUEUE" | awk '{print $1}')"
}

generate_once() {
  ensure_seed_queue || return 1
  recover_stale_lock
  if ! mkdir "$LOCK" 2>/dev/null; then
    log_event "skip reason=generator_already_running"
    return 0
  fi
  print -r -- $$ > "$LOCK/pid"
  trap 'rm -f "$LOCK/pid"; rmdir "$LOCK" 2>/dev/null || true' EXIT INT TERM

  log_event "generation_start interval=${INTERVAL_SECONDS}s scope=host_or_claude_d200_only"
  rm -f "$CANDIDATE" "$LAST_MESSAGE"

  cd "$ROOT" || return 1
  codex exec --ephemeral --skip-git-repo-check --sandbox read-only --color never \
    -C "$ROOT" -o "$CANDIDATE" \
    '你是 Unity-on-OpenHarmony 的 Claude 任务雷达，只负责出题，不执行任务、不修改文件、不访问任何设备。先完整 cat COORDINATION.md，再只读检查 coordination/tasks、scratchpad 下最近报告、out 下最近证据与现有 coordination/tasks/CLAUDE_AUTO_QUEUE.md。基于当前真实楼层、Proven/Not-proven/Failed 与反证账本，生成 1-3 张互相正交、Claude 可独立完成的 host-only 或 Claude D200-A/D200-B 任务卡。绝不把 Codex D600-A/D600-B、D600 serial、D600 hdc 操作或 D600 device_verified 分给 Claude；D200 结论不得冒充 D600/ARM64 结论。避免重复已经解决、已反证、已交 READY_FOR_REVIEW 或上一队列仍有效的题；优先产生能解除当前队首阻塞或低成本预证下一门的原子问题。每张任务必须有唯一 L01-L14 的 Lxx.Axx 编号，边界、一个可证伪问题、所需 exact evidence、明确验收条件、红线，并要求产物落 canonical scratchpad、附 manifest/hash/Proven/Not-proven/Failed。任务需有界且可由 Claude 无需等待 Codex 互动独立完成。不要包含生成时间、动态 revision、寒暄、解释或代码围栏，以便内容不变时字节稳定。只输出以下严格 Markdown 结构，TASK 标题可在破折号后加短名称：
# Claude 自动任务队列

## TASK 1 — 名称
- 原子编号：Lxx.Axx
- 执行边界：host-only、D200-A、D200-B 或 host/D200；说明可读写范围
- 核心问题：一个可证伪问题
- 所需证据：exact artifact/command/report 要求
- 验收条件：PASS/FAIL/NOT_PROVEN 的判定门
- 红线：必须含不访问 D600、不改 APK/SO、不冒充 device_verified

后续 TASK 2/3 使用同一六字段；最多三张。' > "$LAST_MESSAGE" 2>&1 &
  local codex_pid=$!
  local elapsed=0
  while kill -0 "$codex_pid" 2>/dev/null && (( elapsed < MAX_GENERATION_SECONDS )); do
    sleep 2
    (( elapsed += 2 ))
  done

  local rc=0
  if kill -0 "$codex_pid" 2>/dev/null; then
    kill -TERM "$codex_pid" 2>/dev/null || true
    sleep 2
    kill -KILL "$codex_pid" 2>/dev/null || true
    wait "$codex_pid" 2>/dev/null || true
    rc=124
  else
    set +e
    wait "$codex_pid"
    rc=$?
  fi

  if (( rc != 0 )); then
    log_event "generation_failed codex_exit=$rc max_seconds=$MAX_GENERATION_SECONDS queue_preserved=true"
  elif ! validate_candidate; then
    log_event "generation_rejected reason=schema_or_scope_validation queue_preserved=true"
  elif [[ -f "$QUEUE" ]] && cmp -s "$CANDIDATE" "$QUEUE"; then
    log_event "generation_unchanged queue_overwrite=false tasks=$(grep -c '^## TASK ' "$CANDIDATE")"
  else
    cp "$CANDIDATE" "$QUEUE.next"
    mv "$QUEUE.next" "$QUEUE"
    log_event "generation_published queue_overwrite=true tasks=$(grep -c '^## TASK ' "$QUEUE") sha256=$(shasum -a 256 "$QUEUE" | awk '{print $1}')"
  fi

  rm -f "$LOCK/pid"
  rmdir "$LOCK" 2>/dev/null || true
  trap - EXIT INT TERM
  return 0
}

if [[ "${CLAUDE_RADAR_ONCE:-0}" == "1" ]]; then
  generate_once
  exit $?
fi

while true; do
  cycle_started="$(date '+%s')"
  generate_once || log_event "cycle_failed queue_preserved=$([[ -s "$QUEUE" ]] && print true || print false)"
  cycle_elapsed=$(( $(date '+%s') - cycle_started ))
  cycle_sleep=$(( INTERVAL_SECONDS - cycle_elapsed ))
  (( cycle_sleep > 0 )) || cycle_sleep=1
  sleep "$cycle_sleep"
done
