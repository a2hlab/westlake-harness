spec: project
name: "Read-only pre/post-boot state capture"
---

## 意图

按 RUNBOOK 63668b4db9 一次采全，避免上板逐层剥离；保留原始输出和不可比较状态。

## 约束

- 本轮只能用 transport 夹具，不连接 HDC/VM/SSH、不加锁、不改板。
- 不采环境变量值，不提交真实板子的完整参数或私密运行数据。
- 观察差异不等于证明根因；缺失或漂移证据不得算相等。

## 边界

### 允许修改
- scripts/lab/board_state_snapshot.py
- scripts/lab/board_state_diff.py
- scripts/lab/test_board_state.py
- knowledge/gates/board-state-collection.json
- tools/spec-checks/tests/board_state.rs
- benchmark/2026-10-10-board-state-tools/**
- specs/board-state-tools/**

## 排除范围

- 真板取证、标签修复、重启、推演器、自启改动、安全配置改动。
