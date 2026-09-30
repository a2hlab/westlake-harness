spec: task
name: "T4 新编 libart 与板上 R155 libart 的布局对照"
inherits: project
depends: [t3-build-art]
tags: [dex2oat, layout, gate]
---

## 意图

CheckSystemClass 比对的是 libart 编进去的系统类布局。在上板前用离线探针比较新编 libart 与板上 R155 libart(59e1bb45)的 mirror 类大小与字段偏移、Thread 偏移、ImageHeader/OatHeader 布局;对不上就回到 T1 补齐补丁,不上板。

## 已定决策

- 复用 cc-wiki 的 offsetof/sizeof 探针方法(DIGEST B.23)
- 比对清单覆盖 CheckSystemClass 检查的全部系统类

## 边界

### 允许修改
- knowledge/toolchains/art-r155/**
- tools/spec-checks/**

### 禁止
- 不上板

## 验收标准

场景: 系统类布局与板上 libart 一致
  测试: d4_mirror_layouts_match_board
  假设 新编 libart 与从板上拉回的 R155 libart
  当 对 CheckSystemClass 覆盖的系统类逐个比较对象大小与字段偏移
  那么 不一致项为 0
  并且 Thread 偏移与 ImageHeader/OatHeader 字段偏移不一致项为 0
