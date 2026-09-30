spec: task
name: "Assemble and audit the v3c candidate offline"
inherits: project
---

## 意图

Produce a reviewable, hashed candidate with source provenance and three-board migration reports without board access.

## 已定决策

- Copy the B87 package and overlay pinned native artifacts; retain current GID host and Java namespace mainline.
- Keep ANL/provider route and Android aliases consistent in both payload bytes and declared live hashes.
- Reuse the existing package loader, replacement validator and dry-run CLI; report migration blockers rather than treating dry-run as deployment approval.
- Stage the requested external output under this worktree because the sandbox cannot write the requested sibling directory.

## 边界

### 允许修改
- benchmark/2026-09-30-v3c-candidate/**
- specs/bms-v3c-assembly/**
- tools/spec-checks/**
- README.md
- .octos/KNOWLEDGE-DIGEST.md

### 禁止
- No board operations, compilation, deployment-tool semantics changes or source artifact modifications.

## 验收标准

场景: 哈希与别名失败关闭
  测试: v3c_candidate_rules
  假设 A pinned artifact or a route alias is inconsistent
  当 The offline validation checks the package and aliases
  那么 It raises an error and does not claim a deployable candidate

场景: 三板干跑与溯源
  测试: v3c_candidate_inventory
  假设 The latest handoff and three recorded board states are supplied
  当 The candidate is assembled and all three dry-run commands execute
  那么 The report records hashes and source commits for selected artifacts and preserves runtime liblog host and loader decisions
  并且 Device I/O is false and migration limitations are explicit with unknown actual-board readiness
  并且 Output stays under this worktree and the requested external destination is recorded as not written

## 排除范围

- Board rollout, functional tests, JNI binding fixes, Java JAR implementation and screenshots.
