spec: task
name: "B3 桌面图标取最高分辨率并支持自适应图标"
inherits: project
depends: [b2-label-resolve]
tags: [bms, icon, oc-t0]
---

## 意图

安装器按写死的路径表找 `ic_launcher.png`,资源名被混淆的 APK 找不到;按 manifest 解析到自适应图标 XML 时直接放弃回退,结果桌面图标是低分辨率位图,fd-seal、toutiao、x 更因找不到图标报 `9568260` 装不进去。本任务让图标按 manifest 的图标资源 id 在 arsc 里取**最高密度**的位图;是自适应图标时取前景与背景层合成;并让这三个 app 能装进去。

## 已定决策

- 选图顺序:manifest 图标 id 在各密度桶中的最高密度位图(xxxhdpi 优先);自适应图标 XML 取 foreground 与 background 引用的最高密度位图按层合成;写死路径表只作最后回退
- 输出图标尺寸不低于 OH 桌面图标所需尺寸,缩放用高质量重采样
- 与 B2 在同一车道先后做,同一文件 `apk_installer.cpp`,B2 合入后再改

## 边界

### 允许修改
- benchmark/2026-09-28-bms-icon-resolve/**
- bms/src/adapter/framework/package-manager/jni/**
- tools/spec-checks/**

### 禁止
- 不修改 APK
- 不在 5cd 以外的板上换 installer

## 验收标准

场景: 图标来自最高密度桶
  测试: b3_icon_from_highest_density
  假设 wikipedia、termux、aegis、markor 四个 APK
  当 安装后读取合成资源 HAP 里的图标
  那么 每个图标都来自该 APK 图标资源的最高密度桶,记录桶名与像素尺寸

场景: 自适应图标合成前景与背景
  测试: b3_adaptive_icon_composed
  假设 某 APK 的图标是 `<adaptive-icon>` XML
  当 安装它
  那么 合成资源 HAP 里的图标由 foreground 与 background 两层合成
  并且 外环读图签认桌面图标不是占位图

场景: 此前因无图标失败的 app 能装进去
  测试: b3_missing_icon_apps_install
  假设 fd-seal、toutiao、x 此前 `bm install` 报 9568260
  当 用新 installer 安装
  那么 三个都安装成功且 `bm dump -n` 可查,或逐个写明仍失败的新原因

场景: 取不到任何位图时用占位并告警
  测试: b3_no_bitmap_uses_placeholder_with_warning
  假设 某 APK 图标资源在所有密度桶都不是位图
  当 安装它
  那么 安装成功且用占位图标
  并且 hilog 记录图标资源 id 与原因

## 排除范围

- 动态图标与主题图标
- 名字(见 B2)
