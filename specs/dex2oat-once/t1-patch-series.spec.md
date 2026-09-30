spec: task
name: "T1 定版 R155 的 ART 补丁序列"
inherits: project
tags: [dex2oat, patches, offline]
---

## 意图

把 R155 libart 相对 android-14.0.0_r1 的全部源码改动整理成一组可以按序打上去的补丁文件并入库,每个补丁标明来源;找不到源码、只能从 R155 反汇编推回的修复(如 DexCache::GetResolvedType 的 PRIMCLASS-GUARD)单列并写成源码补丁。离线完成,不碰板。

## 已定决策

- 以 B6 重建树 art-hanbin 相对 art-r1 的差异为起点,逐文件与寒冰两版补丁目录对账,记录哪一版命中
- 反汇编补回的修复以 `benchmark/2026-09-29-b6-static-diff/RESTORE-PLAN.md` 与 DIGEST E.7 为清单
- 产出 `knowledge/toolchains/art-r155/patches/*.patch`、`series`(顺序)与 `SOURCES.md`(每个补丁的来源与哈希)

## 边界

### 允许修改
- knowledge/toolchains/art-r155/**
- tools/spec-checks/**

### 禁止
- 不上板,不改运行时产物

## 验收标准

场景: 补丁序列干净地打在 r1 的 art 上
  测试: d1_patch_series_applies_to_r1
  假设 一份干净的 android-14.0.0_r1 art 源码
  当 按 series 顺序逐个 git apply
  那么 全部补丁无冲突打上
  并且 打完的 art 目录与 B6 重建树 art-hanbin 在 20 个差异文件上逐字节一致

场景: 每个补丁都有来源
  测试: d1_every_patch_has_source
  假设 series 列出的全部补丁
  当 读取 SOURCES.md
  那么 每个补丁都写明来源目录或反汇编依据与 sha256
  并且 没有来源的补丁数为 0
