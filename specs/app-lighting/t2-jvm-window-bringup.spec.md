spec: task
name: "T2 纯 Java app 窗口起栈:markor 试点"
inherits: project
depends: [t1-blocker-ranking]
tags: [framework, smali, jvm]
---

## 意图

7 个纯 Java 未亮 app 进程活着却从不创建渲染节点,静态缺口图里找不到把它们和已亮 app 区分开的缺口。以 markor 为试点:用 T0 抓到的主线程栈或异常定位窗口起栈断在哪一步,在 `adapter-runtime-bcp.jar` 里做最小修复,再用同一构建重扫同族 app 与 13 个 LIT 对照组,量出一个修复覆盖几个 app。

## 已定决策

- 开工条件:markor 所在族在 T1 排序表前两名;否则换成 T1 第一名族里的纯 Java app 当试点
- 修复落点只在 `adapter-runtime-bcp.jar`:baksmali 反编译、smali 外科补丁、westlake host dex2oat(oat 247,Rosetta 下 `LD_PRELOAD=libmap32bit.so`)重建 boot image、部署到一块白名单板
- 根因是某个 system service 返回 null 时,按 telephony 先例在 `OHServiceManager.lookupAdapter` 把该服务名路由到 `LocalServiceBinders` 的 no-op proxy
- 补丁 diff 与重建出的 jar、boot image 的 sha256 记入 `results.json`

## 边界

### 允许修改
- benchmark/*-jvm-window-bringup/**
- tools/spec-checks/**

### 禁止
- 不修改 APK
- 不修改 native 库
- 不把补丁后的 boot image 部署到白名单外的板子

## 验收标准

场景: markor 点亮
  测试: t2_markor_lit
  审核: human
  假设 补丁后的 boot image 部署在一块白名单板上
  当 用扫量脚本启动 markor 并等待 30 s
  那么 截图显示 markor 自身界面
  并且 `render_node` 为 true

场景: 同族 app 用同一构建重扫
  测试: t2_same_family_resweep_recorded
  假设 T1 把另外若干 app 归入与 markor 相同的族
  当 用同一 boot image 重扫这些 app
  那么 `results.json` 为每个 app 记录 `before`、`after` 两个判定与截图路径

场景: 修复引入回退时判失败
  测试: t2_regression_fails_task
  审核: human
  假设 13 个 LIT 对照组用补丁后的 boot image 重扫
  当 任一 app 的截图不再是它自身界面
  那么 任务判失败
  并且 `results.json` 的 `regressions` 列出该 app

场景: 补丁未生效时判失败
  测试: t2_patch_absent_detected
  假设 板上 boot image 的 sha256 与 `results.json` 记录值不一致
  当 执行验收
  那么 任务判失败且不计入点亮数

场景: markor 越过本 blocker 撞到下一堵墙
  测试: t2_next_wall_recorded
  假设 T0 记录的 blocker 证据行在补丁后消失
  但是 markor 截图仍不是它自身界面
  当 重新采集 `triage.json`
  那么 `results.json` 记录 `next_blocker` 与原文证据行,本任务以推进一层结项

## 排除范围

- jvm+native 类 app 的专属修复
- 修改 Westlake 源码树或 bridge-build 构建
