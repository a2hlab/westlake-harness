spec: task
name: "T4 libandroid NDK 簇补口:SuperTuxKart"
inherits: project
depends: [t1-blocker-ranking]
tags: [ndk, libandroid, native]
---

## 意图

SuperTuxKart 补上 GLESv1_CM stub 后窗口已经起来,卡在 `AConfiguration_new: symbol not found`:libSDL2 还未定义引用 NDK libandroid 的 `AConfiguration_*`、`AAsset*`、`ALooper_*`、`ANativeWindow_*`,app 命名空间里实际解析到的 libandroid 缺这些导出。本任务分两段:离线段(T1 开工门的批准例外)按实际命名空间算出真正应由 libandroid 提供的缺口、在独立源码目录补齐并做主机侧与功能测试准备;上板段等 T1 排序结果决定是否开工。交付状态按 project 约定分 `lit` / `advanced` / `no-change`。

## 已定决策

- 缺口口径:按 STK 各 `.so` 在 app 命名空间里的实际加载顺序、`DT_NEEDED` 与符号版本解析,只保留应由 libandroid 提供的**强**未定义 NDK 符号;由 libc、GLES、app 自带库负责的符号与弱未定义项不算缺口;结果用 STK 当前原始报错核验
- 源码补丁在独立的源码副本与独立构建目录里改和编,不覆盖任何共享的 libandroid 产物;补丁 diff、`dockbuild.sh run` 构建命令、产物 sha256 放进 `benchmark/2026-09-28-ndk-libandroid/`
- `AConfiguration_*` 返回与板子一致的固定配置(1200×1920 及板上实际密度,单位与 NDK 头文件一致);`AAsset*` 读 APK 内 assets
- 功能测试程序(aarch64 OH)在离线段编好:覆盖 AConfiguration 尺寸与密度、AAsset 读 / seek / EOF / 缺失项、旧导出符号的关键行为;上板段在持锁板上运行
- GLESv1_CM stub 沿用 2026-09-27 那一版(sha256 `a1ae3950…b37bf`,`dockbuild.sh cc` 可逐字节复现)
- 上板时板上实际加载的 libandroid 哈希必须等于本任务构建出的哈希

## 边界

### 允许修改
- benchmark/*-ndk-libandroid/**
- tools/spec-checks/**

### 禁止
- 不修改 APK
- 不改变 libandroid 已有导出符号的名字、版本与行为
- 不覆盖其他车道正在引用的 libandroid 产物或 framework report

## 验收标准

场景: 缺口只含应由 libandroid 提供的强未定义符号
  测试: t4_missing_symbol_set_computed
  假设 STK 的全部 `.so`、它们的 `DT_NEEDED` 与 app 命名空间里实际解析到的 libandroid
  当 按加载顺序与符号版本解析
  那么 `results.json` 的 `missing_symbols` 非空且每项标注所属簇与需要它的库
  并且 libc、GLES、app 自带库提供的符号与弱未定义项不在其中

场景: 缺口与原始报错一致
  测试: t4_missing_set_matches_reported_error
  假设 STK 在当前运行时的原始报错为 `AConfiguration_new: symbol not found`
  当 比对 `missing_symbols`
  那么 报错里的符号出现在缺口中

场景: 新库导出覆盖缺口且旧导出不变
  测试: t4_new_library_exports_superset
  假设 在独立构建目录编出的新 libandroid 与当前 libandroid
  当 比对两者的导出名字与符号版本
  那么 新库导出包含全部 `missing_symbols`
  并且 当前库的每个导出在新库里名字与版本都不变

场景: 功能测试程序已编好且断言真实行为
  测试: t4_functional_tests_built
  假设 离线段编出的 aarch64 OH 功能测试程序
  当 检查它的用例清单
  那么 清单包含 AConfiguration 尺寸与密度、AAsset 读 / seek / EOF / 缺失项、至少 3 个旧导出的行为断言
  并且 把新库里任一 AAsset 实现改成恒返回失败时,对应用例在上板运行中失败

场景: STK 进入主菜单
  测试: t4_stk_reaches_main_menu
  审核: human
  假设 T1 放行上板段,新 libandroid 与 GLESv1_CM stub 部署在一块持锁的白名单板上,板上哈希与构建一致
  当 启动 fd-stk 并等待 60 s
  那么 stderr 无 `symbol not found`
  并且 外环读图签认截图显示 STK 自身菜单界面,交付状态记 `lit`

场景: 补齐后撞到下一堵墙时按正证据记 advanced
  测试: t4_next_wall_recorded
  假设 `AConfiguration_new` 调用现在成功,但截图仍不是 STK 菜单
  当 重新采集 `triage.json`
  那么 交付状态记 `advanced`,`results.json` 记录 `next_blocker` 与原文证据行
  并且 点亮数不增加

场景: 已有 libandroid 使用方不回退
  测试: t4_existing_libandroid_users_unchanged
  审核: human
  假设 13 个 LIT 对照组在装有新 libandroid 的同一基座上重扫
  当 外环读图并在 wikipedia 打开一篇文章
  那么 13 个仍判为 LIT
  并且 wikipedia 文章页正常渲染

## 排除范围

- gl4es 或 GLESv1 fixed-function 实现(实测 STK 不调用)
- libmediandk(Unity 需要,另立任务)
