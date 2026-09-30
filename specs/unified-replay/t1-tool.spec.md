spec: task
name: Restore verified J2 and J3 overlays and prepare four shards
inherits: project
---
## 意图
Prepare an offline-tested command to replay U3 after board reconnection, and four balanced 66-key lists for the new Mac.
## 已定决策
- Reuse N2 package live hashes and FZ-001 installer identity, the archived two-layer bind sequence, bms_batch transport status and lock/boot guards.
- Verify both local JAR hashes before device access, native/installer hashes in shell and daemon root before mutation; never repair mismatched native state.
- Replay only missing J2 then J3 layers, check shell/appspawn-x root at each step, be idempotent, unwind only this invocation's mounts on failure.
- Unknown or divergent mount stacks, service PID/boot changes, transport failures and wrong locks stop with an explicit reason. No service restart or application launch.
- Reuse historical-cost LPT for 17/17/16/16 keys; fourth OH board stays unassigned until present in the whitelist. Android reference is not an OH execution target.
## 边界
### 允许修改
- scripts/lab/replay_unified_state.*
- scripts/lab/lab_paths.py
- scripts/lab/check_frozen.py
- benchmark/2026-09-30-unified-replay/**
- benchmark/2026-09-30-round1-plan/shard/make_four_shards.py
- benchmark/2026-09-30-round1-plan/four-board-v1/**
- specs/unified-replay/**
- tools/spec-checks/src/lib.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md
- .octos/OPS-RUNBOOK.md
### 禁止
- No hdc execution against real hardware, native replacement, installer replacement or changes to earlier receipts.
## 验收标准
场景: 双层恢复及重复执行
  测试: unified_replay_success
  假设 FakeBoard has matching N2 and FZ-001 with the base or J2 JAR
  当 replay_unified_state.sh workflow replays missing layers then repeats
  那么 J2 precedes J3 and both roots reach the full J3 SHA without duplicate mounts
场景: 错件或状态漂移拒绝
  测试: unified_replay_rejection
  假设 An input is missing, hash differs, root diverges, or lock/boot/process changes
  当 Preflight or replay checks run
  那么 The command fails with a reason and restores only its own mounts when the original session remains valid
场景: 四分片离线交付
  测试: unified_replay_shards
  假设 66 pinned app keys and archived per-key durations
  当 Four lists are generated without a fourth OH serial
  那么 Lists are disjoint and cover 66 keys with capacities 17/17/16/16 and the fourth serial is unknown
## 排除范围
- N2 package deployment, USB recovery, application smoke tests, screenshot signoff, automatic board locking, and declaring a fourth device provisioned.
