spec: task
name: "B2 桌面名用 APK 自己的标签"
inherits: project
tags: [bms, label, oc-t0]
---

## 意图

条目 23 装进 BMS 的 62 个 app 桌面名全是 "Hello World":已装 `entry.hap` 的 `resources.index` 是同一份模板(SHA 3e970218…),合成资源 HAP 时只换了图标、没换标签。`apk_installer.cpp` 已有 `ResolveLabelResId()` 调 `ResolveApkLabel()` 解析 `@string` 标签,但结果没有进入资源 HAP。本任务让解析出的标签写进资源 HAP,并在板上生效。

## 已定决策

- 优先找已编好且含标签写入的 `libapk_installer.so`(`.bridge-payload/`、00.Workspace 各 worktree),找不到才用 `dockbuild.sh` 为 OH 6.1 重编
- 标签来源顺序:launcher activity 的 label,其次 application 的 label;都解析不到时用包名,不用 "Hello World"
- 换 installer 的步骤写回滚方式,并按 project 判据核实 foundation 里实际加载的是新库

## 边界

### 允许修改
- benchmark/2026-09-28-bms-label-resolve/**
- bms/src/adapter/framework/package-manager/jni/**
- tools/spec-checks/**

### 禁止
- 不修改 APK
- 不在 5cd 以外的板上换 installer

## 验收标准

场景: 四个 app 的桌面名是各自真名
  测试: b2_labels_are_real_names
  假设 新 installer 已在 5cd 生效
  当 重装 wikipedia、termux、aegis、markor
  那么 `bm dump -n` 的 label 分别是各自 APK 的应用名
  并且 外环读图签认桌面上显示的名字一致

场景: 新 installer 确实被 foundation 加载
  测试: b2_new_installer_loaded_in_foundation
  假设 已替换 `libapk_installer.so`
  当 读取 `/proc/<foundation pid>/root` 下该库与 maps
  那么 哈希等于本任务记录的新库哈希

场景: 标签解析失败时退到包名
  测试: b2_unresolvable_label_falls_back_to_package
  假设 某 APK 的 label 引用解析失败
  当 安装它
  那么 桌面名是包名,不是 "Hello World"
  并且 hilog 有带资源 id 的 `ResolveLabelResId` 告警

场景: 回滚后恢复原 installer
  测试: b2_rollback_restores_original
  假设 执行本任务写出的回滚步骤
  当 读取 foundation 里加载的 installer 哈希
  那么 等于替换前记录的原哈希

## 排除范围

- 图标(见 B3)
- 多语言标签选择
