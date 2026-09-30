spec: task
name: "T3 打补丁后在同一棵树里编 libart 与 host dex2oat"
inherits: project
depends: [t1-patch-series, t2-r1-tree]
tags: [dex2oat, build]
---

## 意图

在 T2 的 r1 树上按 T1 的 series 打补丁,`m build-art-host libart` 编出 host dex2oat64 与 arm64 libart,记录全部产物与所加载库的哈希及完整命令。

## 已定决策

- lunch 目标与 r16 实测一致:aosp_arm64-userdebug;构建日志与 `out/` 产物清单存档
- 产物哈希写入 `knowledge/toolchains/art-r155/BUILD.md`

## 边界

### 允许修改
- knowledge/toolchains/art-r155/**

### 禁止
- 不上板

## 验收标准

场景: 构建成功且产物有记录
  测试: d3_build_outputs_recorded
  假设 打完补丁的 r1 树
  当 执行 m build-art-host libart
  那么 构建以 build completed successfully 结束且 FAILED 行数为 0
  并且 dex2oat64、libart.so 与 dex2oat64 的全部 ldd 依赖都有 sha256 记录
