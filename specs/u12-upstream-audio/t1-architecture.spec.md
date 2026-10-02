spec: task
name: "Upstream architecture and route-A differences"
inherits: project
---

## 意图

Map four upstream revisions to their actual changed files and distinguish portable algorithms from loader and JNI-owner integration.

## 已定决策

- Pin git-show snapshots rather than assuming the current checkout contains the requested revisions.
- Compare actual05d8 PLAY profile and current facade5891 with the upstream wrapper paths.

## 边界

### 允许修改
- benchmark/2026-10-02-u12-upstream-audio/**
- specs/u12-upstream-audio/**
- tools/spec-checks/tests/u12_upstream_audio.rs

## 验收标准

场景: Upstream fixes are not route-A proof
  测试: u12_audio_architecture
  假设 Pinned upstream snapshots and factory05d8 unsupported PLAY profile
  当 Commit changes and wrapper dispatch are compared
  那么 The four revisions are recorded and unchanged PLAY forwarding and media-owner integration remain incomplete

## 排除范围

- No claimed equivalent framework68 deployment or corpus ledger reproduction.
