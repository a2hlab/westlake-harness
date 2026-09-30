spec: task
name: "T5 用新 dex2oat 生成 9 段 boot image 并与板上逐字节比对"
inherits: project
depends: [t4-layout-gate]
tags: [dex2oat, boot-image]
---

## 意图

用 T3 的 dex2oat64、板上 boot.oat 键值里的 dex2oat 命令行与完整键集(含 bootclasspath-checksums、compilation-reason),对 9 个输入 jar 生成 27 个镜像文件,与参考哈希逐字节比对,记录无法逐字节一致的字段及原因。

## 已定决策

- 输入与参考:`knowledge/toolchains/boot-image-inputs.sha256`;dex-location 用板上路径 /system/android/framework
- 命令行与键值集对照 `knowledge/toolchains/dex2oat-a14.md` 的 OatHeader key-value 节

## 边界

### 允许修改
- knowledge/toolchains/**

### 禁止
- 不上板

## 验收标准

场景: 生成的镜像版本与校验和字段符合板上 libart 的要求
  测试: d5_image_headers_match
  假设 T3 的 dex2oat64 与 9 个参考输入 jar
  当 按记录的命令行生成 27 个文件
  那么 9 个 vdex 与参考逐字节一致
  并且 boot.oat 的 oat 版本为 230、boot.art 的 image 版本为 108,键值集与板上一致
