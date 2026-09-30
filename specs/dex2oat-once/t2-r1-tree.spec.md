spec: task
name: "T2 在 hw248 同步 android-14.0.0_r1 完整源码树"
inherits: project
tags: [dex2oat, hw248, source]
---

## 意图

hw248 现有的 android-14.0.0_r1 只有 art/bionic/libcore 等源码目录,没有构建系统,不能编。按 r16 已验证的配方同步一棵完整的 r1 树并钉版,与 T1 并行。

## 已定决策

- 配方照 `knowledge/toolchains/dex2oat-a14.md` 的 Recipe,只把 `-b android-14.0.0_r16` 换成 `-b android-14.0.0_r1`,目录 `/home/alvin/aosp-14.0.0_r1-art`
- 同步完成后 `repo manifest -r` 钉版,清单入库为 `knowledge/toolchains/aosp-14.0.0_r1-pinned-manifest.xml`

## 边界

### 允许修改
- knowledge/toolchains/**

### 禁止
- 不改 hw248 上已有的任何源码树与他人目录

## 验收标准

场景: r1 树可构建且版本号与板上一致
  测试: d2_r1_tree_versions_match_board
  假设 同步完成的 /home/alvin/aosp-14.0.0_r1-art
  当 读取 art/runtime/image.cc 的 kImageVersion 与 art/runtime/oat.h 的 kOatVersion
  那么 分别为 108 与 230
  并且 build/envsetup.sh 存在且钉版清单已入库
