#!/usr/bin/env bash

# Consume independent Game-Claude presearch cards without blocking Codex work.
set -u
export PATH="/Users/alexyang/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

ROOT="/opt/21.Game/02.unity.cardwords/adapter"
TASK_DIR="$ROOT/coordination/tasks/claude_presearch"
STATE="$ROOT/out/claude_presearch_dispatch"
CLAIMS="$STATE/claims"
RESULTS="$STATE/results"
RUNS="$STATE/runs"
PROGRESS="$STATE/progress"
STATUS="$STATE/status.tsv"
HEARTBEAT="$STATE/heartbeat.log"
DISPATCH_LOCK="$STATE/.dispatcher.lock"
INTERVAL_SECONDS=300
MAX_PARALLEL=2
MAX_TASK_SECONDS=2700

mkdir -p "$CLAIMS" "$RESULTS" "$RUNS" "$PROGRESS"

log_event() {
  printf '[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$1" >> "$HEARTBEAT"
}

task_key() {
  local task="$1"
  local id sha
  id="$(basename "$task" .md)"
  sha="$(shasum -a 256 "$task" | awk '{print $1}')"
  printf '%s_%s\n' "$id" "${sha:0:12}"
}

ordered_tasks() {
  local task
  for task in "$TASK_DIR"/P*R*.md; do
    [ -f "$task" ] && printf '%s\n' "$task"
  done
  for task in "$TASK_DIR"/P*.md; do
    [ -f "$task" ] || continue
    [[ "$(basename "$task")" == *R*.md ]] && continue
    printf '%s\n' "$task"
  done
}

delivery_dir() {
  local task="$1"
  local relative
  relative="$(grep -Eo 'scratchpad/claude_presearch/P[0-9]{2}_[A-Za-z0-9_.-]+' \
    "$task" | head -1 || true)"
  [ -n "$relative" ] || return 1
  printf '%s/%s\n' "$ROOT" "$relative"
}

delivery_is_ready() {
  local task="$1"
  local id dir ready
  id="$(basename "$task" .md)"
  [[ "$id" == *R* ]] && return 1
  dir="$(delivery_dir "$task" 2>/dev/null || true)"
  [ -n "$dir" ] && [ -d "$dir" ] || return 1
  ready="$(find "$dir" -maxdepth 1 -type f -name 'READY_FOR_REVIEW*' -print -quit)"
  [ -s "$ready" ] && [ -s "$dir/MANIFEST.sha256" ] || return 1
  (cd "$dir" && shasum -a 256 -c MANIFEST.sha256 >/dev/null 2>&1)
}

reconcile_external_deliveries() {
  local task key
  while IFS= read -r task; do
    [ -f "$task" ] || continue
    key="$(task_key "$task")"
    [ ! -f "$RESULTS/$key.done" ] || continue
    [ ! -d "$CLAIMS/$key.claim" ] || continue
    if delivery_is_ready "$task"; then
      printf 'ready from externally delivered, manifest-verified scratch output\n' \
        > "$RESULTS/$key.done"
      rm -f "$RESULTS/$key.failed"
      log_event "task_ready_external key=$key"
    fi
  done < <(ordered_tasks)
}

recover_stale_dispatcher() {
  if [ -d "$DISPATCH_LOCK" ]; then
    local owner=""
    owner="$(cat "$DISPATCH_LOCK/pid" 2>/dev/null || true)"
    if [ -z "$owner" ] || ! kill -0 "$owner" 2>/dev/null; then
      rm -f "$DISPATCH_LOCK/pid"
      rmdir "$DISPATCH_LOCK" 2>/dev/null || true
    fi
  fi
}

recover_stale_claims() {
  local claim pid runner key output
  for claim in "$CLAIMS"/*.claim; do
    [ -d "$claim" ] || continue
    key="$(basename "$claim" .claim)"
    pid="$(cat "$claim/claude.pid" 2>/dev/null || true)"
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      continue
    fi
    if [ -f "$claim/starting" ] && [ ! -f "$claim/claude.pid" ]; then
      runner="$(cat "$claim/runner.pid" 2>/dev/null || true)"
      if [ -n "$runner" ] && kill -0 "$runner" 2>/dev/null; then
        continue
      fi
      rm -f "$claim/starting" "$claim/runner.pid"
      rmdir "$claim" 2>/dev/null || true
      log_event "claim_recovered key=$key state=queued reason=claude_not_started"
      continue
    fi
    output="$RUNS/$key/claude.output.log"
    runner="$(cat "$claim/runner.pid" 2>/dev/null || true)"
    if [ -n "$runner" ] && kill -0 "$runner" 2>/dev/null; then
      continue
    fi
    if [ ! -s "$output" ]; then
      rm -f "$claim/starting" "$claim/claude.pid" "$claim/runner.pid"
      rmdir "$claim" 2>/dev/null || true
      log_event "claim_recovered key=$key state=queued reason=empty_launch"
      continue
    fi
    printf 'stale claim recovered\n' > "$RESULTS/$key.failed"
    rm -f "$claim/starting" "$claim/claude.pid" "$claim/runner.pid"
    rmdir "$claim" 2>/dev/null || true
    log_event "claim_recovered key=$key state=failed"
  done
}

active_count() {
  local count=0 claim
  for claim in "$CLAIMS"/*.claim; do
    [ -d "$claim" ] || continue
    count=$((count + 1))
  done
  printf '%s\n' "$count"
}

refresh_status() {
  local tmp="$STATUS.next.$$.$RANDOM"
  local task key id atom state pid progress
  printf 'card\tatom\tstate\tpid\tprogress_file\ttask_file\n' > "$tmp"
  while IFS= read -r task; do
    [ -f "$task" ] || continue
    key="$(task_key "$task")"
    id="$(basename "$task" .md)"
    atom="$(grep -Eo 'L[0-9]{2}\.A[0-9]{2}' "$task" | head -1)"
    state="queued"
    pid=""
    progress="$PROGRESS/$key.md"
    if [ -f "$RESULTS/$key.done" ]; then
      state="ready_for_review"
    elif [ -f "$RESULTS/$key.failed" ]; then
      state="failed"
    elif [ -d "$CLAIMS/$key.claim" ]; then
      state="running"
      pid="$(cat "$CLAIMS/$key.claim/claude.pid" 2>/dev/null || true)"
    fi
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
      "$id" "$atom" "$state" "$pid" "$progress" "$task" >> "$tmp"
  done < <(ordered_tasks)
  mv "$tmp" "$STATUS"
}

terminate_task_tree() {
  local pid="$1"
  pkill -TERM -P "$pid" 2>/dev/null || true
  kill -TERM "$pid" 2>/dev/null || true
  sleep 2
  pkill -KILL -P "$pid" 2>/dev/null || true
  kill -KILL "$pid" 2>/dev/null || true
}

dispatch_task() {
  local task="$1"
  local key claim run_dir progress
  key="$(task_key "$task")"
  claim="$CLAIMS/$key.claim"
  run_dir="$RUNS/$key"
  progress="$PROGRESS/$key.md"

  mkdir "$claim" 2>/dev/null || return 1
  : > "$claim/starting"
  mkdir -p "$run_dir"

  (
    local claude_pid elapsed rc
    local output="$run_dir/claude.output.log"
    local prompt
    prompt="先完整读取 ${ROOT}/COORDINATION.md，再执行任务卡 ${task}。只写任务卡指定的专属 scratchpad，并在完成时 append COORDINATION.md；禁止访问 D600、修改产品源码/APK/SO、写外部树或启动远端构建。中间进展必须由你原子覆写 ${progress}：开始证据盘点后、候选方案形成后、测试/反证完成后至少各更新一次；固定字段为 stage、current_claim、Proven、Not_proven、Failed、exact_evidence_paths、blockers、next_action，内容必须反映当时真实状态，不能预写最终成功。先验证已有 Proven/Not-proven/Failed，遇到安全或权限阻塞时记录证据并结束，不等待人工确认。最终 READY_FOR_REVIEW 前必须确认该进展文件存在且已到 test_or_adversarial_review 阶段。完成只输出 READY_FOR_REVIEW。"

    cd "$ROOT" || exit 1
    claude -p --effort high --permission-mode acceptEdits \
      --allowedTools Read,Grep,Glob,Bash,Write,Edit \
      --output-format text "$prompt" > "$output" 2>&1 &
    claude_pid=$!
    printf '%s\n' "$claude_pid" > "$claim/claude.pid"
    rm -f "$claim/starting"
    log_event "task_start key=$key pid=$claude_pid card=$task"

    elapsed=0
    while kill -0 "$claude_pid" 2>/dev/null && [ "$elapsed" -lt "$MAX_TASK_SECONDS" ]; do
      sleep 5
      elapsed=$((elapsed + 5))
    done

    if kill -0 "$claude_pid" 2>/dev/null; then
      terminate_task_tree "$claude_pid"
      wait "$claude_pid" 2>/dev/null || true
      printf 'timeout after %ss; output=%s\n' "$MAX_TASK_SECONDS" "$output" \
        > "$RESULTS/$key.failed"
      log_event "task_timeout key=$key seconds=$MAX_TASK_SECONDS"
    else
      set +e
      wait "$claude_pid"
      rc=$?
      set -e
      if [ "$rc" -eq 0 ] && grep -q 'READY_FOR_REVIEW' "$output" && \
         [ -s "$progress" ] && \
         grep -Eiq '^[[:space:]#*-]*stage:[[:space:]]*(test|adversarial)' "$progress"; then
        printf 'ready; output=%s\n' "$output" > "$RESULTS/$key.done"
        log_event "task_ready key=$key rc=0"
      else
        printf 'failed rc=%s; output=%s\n' "$rc" "$output" \
          > "$RESULTS/$key.failed"
        log_event "task_failed key=$key rc=$rc"
      fi
    fi

    rm -f "$claim/claude.pid" "$claim/runner.pid" "$claim/starting"
    rmdir "$claim" 2>/dev/null || true
    refresh_status
  ) &
  printf '%s\n' "$!" > "$claim/runner.pid"
  return 0
}

dispatch_cycle() {
  local task key active
  recover_stale_claims
  reconcile_external_deliveries
  active="$(active_count)"
  while IFS= read -r task; do
    [ -f "$task" ] || continue
    [ "$active" -lt "$MAX_PARALLEL" ] || break
    key="$(task_key "$task")"
    [ ! -f "$RESULTS/$key.done" ] || continue
    [ ! -f "$RESULTS/$key.failed" ] || continue
    [ ! -d "$CLAIMS/$key.claim" ] || continue
    if dispatch_task "$task"; then
      active=$((active + 1))
    fi
  done < <(ordered_tasks)
  refresh_status
  log_event "cycle active=$active max=$MAX_PARALLEL pending_status=$STATUS"
}

recover_stale_dispatcher
if ! mkdir "$DISPATCH_LOCK" 2>/dev/null; then
  echo "claude presearch dispatcher is already running" >&2
  exit 2
fi
printf '%s\n' "$$" > "$DISPATCH_LOCK/pid"
trap 'rm -f "$DISPATCH_LOCK/pid"; rmdir "$DISPATCH_LOCK" 2>/dev/null || true' EXIT INT TERM

if [ "${CLAUDE_PRESEARCH_ONCE:-0}" = "1" ]; then
  dispatch_cycle
  exit 0
fi

while true; do
  cycle_start="$(date '+%s')"
  dispatch_cycle
  cycle_elapsed=$(( $(date '+%s') - cycle_start ))
  cycle_sleep=$(( INTERVAL_SECONDS - cycle_elapsed ))
  [ "$cycle_sleep" -gt 0 ] || cycle_sleep=1
  sleep "$cycle_sleep"
done
