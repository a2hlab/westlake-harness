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
- 产物哈希写入 `knowledge/toolchains/art-r155/BUILD.md`,并附 `t4b-build-json` 结构化回执(完整 SHA256、构建环境逐项)
- 构建环境(T3b,2026-09-30):`ART_USE_READ_BARRIER=false ART_DEFAULT_GC_TYPE=CMS ART_USE_GENERATIONAL_CC=false ART_HEAP_POISONING=false ART_TEST_DEBUG_GC=false ALLOW_MISSING_DEPENDENCIES=true`
- 板上 R155 的 device libart 不是 Soong 编的,是配方 `knowledge/toolchains/art-r155/recipe/adapter/build/inner/cross_compile_arm64.sh` 用 OH clang 手写 ART_DEFS 编的;Soong 的 target libart 只作对照件,不部署
- **host dex2oat 必须与它要配合的 device libart 同一份 ART 源码**(T5b 教训:编译宏全一致、读屏障已关,r1+21 补丁的 dex2oat 出的镜像在 R155 libart 上仍在 boot 编译码的 const-string 处 abort)。两条路:① 找到 R155 libart 59e1bb45 的原始 ART 源,用它编 host dex2oat;② 找不到就三件套从同一棵树重编并一起部署——device libart 用 recipe 的 cross_compile_arm64.sh、host dex2oat 用 Soong、boot image 用 gen_boot_image.sh(原作者规则 [B-5])

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

场景: host dex2oat 与部署的 device libart 同源
  测试: d3_same_source_as_deployed_libart
  审核: human
  假设 回执里记录的 host dex2oat 的 ART 源码树与部署到板上的 libart 的 ART 源码树
  当 逐文件比对两棵树的 art/runtime、art/compiler、art/dex2oat、art/libartbase
  那么 差异文件数为 0,或者 device libart 与 boot image 由同一棵树重编并一起部署
  并且 只换镜像、保留来历不明的旧 libart 的方案被拒
