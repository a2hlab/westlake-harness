spec: task
name: "T4 libandroid NDK 簇补口:SuperTuxKart"
inherits: project
depends: [t1-blocker-ranking]
tags: [ndk, libandroid, native]
---

## 意图

SuperTuxKart 补上 GLESv1_CM stub 后窗口已经起来,卡在 `AConfiguration_new: symbol not found`:libSDL2 还未定义引用 NDK libandroid 的 `AConfiguration_*`、`AAsset*`、`ALooper_*`、`ANativeWindow_*`,OH 的 libandroid shim 缺这些导出。本任务补齐 STK 实际引用的这一簇,并用 T1 的直方图查同簇缺口还卡着哪些 app。缺符号清单的计算是离线的,可与 T0 并行;上板部分等 T1 排序结果决定是否开工。

## 已定决策

- 缺符号清单:STK 全部 `.so` 的 `readelf --dyn-syms` 未定义符号集合,减去当前 OH libandroid shim 的导出集合
- 实现只重编 libandroid shim 这一个库:`tools/build_android_native.py --library libandroid.so`
- `AConfiguration_*` 返回与板子一致的固定配置(1200×1920 及板上实际密度);`AAsset*` 读 APK 内 assets
- GLESv1_CM stub 沿用 2026-09-27 那一版(sha256 `a1ae3950…b37bf`)

## 边界

### 允许修改
- benchmark/*-ndk-libandroid/**
- tools/spec-checks/**

### 禁止
- 不修改 APK
- 不改变 libandroid 已有导出符号的行为

## 验收标准

场景: 缺符号清单完整
  测试: t4_missing_symbol_set_computed
  假设 STK 的全部 `.so` 与当前 libandroid shim
  当 计算未定义符号减导出符号
  那么 `results.json` 的 `missing_symbols` 非空
  并且 每项标注所属簇

场景: STK 进入主菜单
  测试: t4_stk_reaches_main_menu
  审核: human
  假设 补齐后的 libandroid 与 GLESv1_CM stub 一起部署在一块白名单板上
  当 启动 fd-stk 并等待 60 s
  那么 stderr 无 `symbol not found`
  并且 截图显示 STK 自身菜单界面

场景: 补齐后撞到下一堵墙
  测试: t4_next_wall_recorded
  假设 `AConfiguration_new` 报错消失
  但是 截图仍不是 STK 菜单
  当 重新采集 `triage.json`
  那么 `results.json` 记录 `next_blocker` 与原文证据行

场景: 已有 libandroid 使用方不回退
  测试: t4_existing_libandroid_users_unchanged
  审核: human
  假设 13 个 LIT 对照组使用新 libandroid 重扫
  当 人读截图并在 wikipedia 打开一篇文章
  那么 13 个仍判为 LIT
  并且 wikipedia 文章页正常渲染

## 排除范围

- gl4es 或 GLESv1 fixed-function 实现(实测 STK 不调用)
- libmediandk(Unity 需要,另立任务)
