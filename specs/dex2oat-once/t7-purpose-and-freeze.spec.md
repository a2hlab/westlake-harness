spec: task
name: "T7 用新工具链落一个 boot 类修复并冻结工具链"
inherits: project
depends: [t6-board-l2]
tags: [dex2oat, freeze, wikipedia]
---

## 意图

证明工具链解决了原问题:把 tagsoup(Parser.setProperty)的 boot 类修复放进输入 jar,重新生成镜像,Wikipedia 越过该墙;然后把配方、补丁序列、钉版清单、产物哈希登记进 knowledge/frozen,工具链从此不许漂移。

## 已定决策

- 修复进 boot jar 后按 T5 同一命令行重生成,短窗上板规则同 T6
- 冻结条目的 evidence 引用本任务与 T6 的 facts 与截图

## 边界

### 允许修改
- knowledge/frozen/**
- knowledge/toolchains/**
- benchmark/*-dex2oat-purpose/**

### 禁止
- 不删除或削弱已冻结条目

## 验收标准

场景: boot 类修复经新工具链生效
  测试: d7_bootclass_fix_reaches_board
  审核: human
  假设 含 tagsoup 修复的输入 jar 与 T3 的 dex2oat64
  当 重生成镜像并在持锁的板上短窗运行 Wikipedia
  那么 hilog 中 Parser.setProperty 的原失败消失,首个致命点移到别处或 Wikipedia 显示自身界面
  并且 工具链条目登记进 knowledge/frozen/frozen.json 且 check_frozen.py 退出码为 0
