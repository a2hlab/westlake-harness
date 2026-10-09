spec: task
name: "Demo manifest and board choice"
inherits: project
---

## 意图

产出演示清单 `benchmark/2026-10-09-demo-baseline/demo-manifest.json`:要装哪些 APK(SHA、包名、中文名、分类、是否游戏、演示顺序),以及选哪块 D600 做演示板。清单以已签认点亮的 key 为底,目标是装上后首屏有内容的包不少于 100 个。

## 已定决策

- 底表取 2026-10-08 领导画册的签认集合(129 key / 128 包),其中首屏有内容的 94 个直接入选;空列表、加载中的 32 个逐个看能否靠首次交互(同意弹窗、跳过引导)出内容,能的标 `needs_first_tap` 并写出点哪里。
- 游戏单列:12 个已签认的游戏和游戏工具必装;另列出语料里未点亮的游戏及其首个致命点,只记不修。
- 选板看三项证据:当前 runtime-fingerprint 是否就是最新统一态、剩余存储够不够装下全部 APK(按 APK 大小 ×3 估算)、该板过去签认的亮键数;只读检查,不写板。
- 头条不在本任务里处理,清单里留一行,状态取 t2 的结论。

## 边界

### 允许修改
- benchmark/2026-10-09-demo-baseline/**
- specs/demo-baseline/**
- tools/spec-checks/tests/demo_baseline.rs

## 验收标准

场景: Manifest covers at least 100 packages with verified identity
  测试: demo_baseline_manifest
  假设 The signed lit set and the local APK files are available
  当 The demo manifest is built
  那么 At least 100 distinct packages are listed with APK SHA and package matching the signed run records and any mismatch rejects

场景: Games are listed separately with their status
  测试: demo_baseline_manifest
  假设 The corpus contains lit and unlit game apps
  当 The manifest is validated
  那么 Every lit game is marked install and every unlit game carries its first fatal from a real run or unknown

场景: Board choice is backed by read-only evidence
  测试: demo_baseline_board_choice
  假设 Three boards report fingerprint storage and history read-only
  当 The demo board is chosen
  那么 The record cites the fingerprint match free storage against the estimate and past lit count for each board and no board write is logged

场景: Unreadable or mismatched APK rejects the manifest
  测试: demo_baseline_manifest
  假设 An APK file is missing or its SHA differs from the signed run record
  当 The manifest is built
  那么 The build exits nonzero naming the key and the manifest is not written

## 排除范围

- 安装、启动、截图、修任何墙、头条路线选择。
