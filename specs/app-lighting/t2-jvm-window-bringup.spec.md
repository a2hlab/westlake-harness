spec: task
name: "T2 纯 Java app 窗口起栈:试点修复"
inherits: project
depends: [t1-blocker-ranking]
tags: [framework, smali, jvm, critical-path]
---

## 意图

7 个纯 Java 未亮 app 进程活着却从不创建渲染节点,静态缺口图里找不到把它们和已亮 app 区分开的缺口。选一个试点 app(默认 markor):用 T0 取回的主线程栈或异常定位窗口起栈断在哪一步,在 `adapter-runtime-bcp.jar` 里做最小修复,再用同一构建重扫同族 app 与 13 个 LIT 对照组,量出一个修复覆盖几个 app。交付状态按 project 约定分 `lit` / `advanced` / `no-change`,只有外环签认的 `lit` 计入点亮数。

## 已定决策

- 开工条件:T1 排序表前两名里存在含纯 Java app 的族;试点取该族里 T1 证据最完整的纯 Java app,默认 markor。前两名里没有合格的纯 Java 候选时本任务暂停,落 `ACK blocked`,不用别的 app 顶替
- 试点 app 的 key、package、apk_sha256 在开工时写进 `results.json.pilot`,全部场景都针对这个试点,不以其他 app 的结果满足试点场景
- 修复落点只在 `adapter-runtime-bcp.jar`:baksmali 反编译、smali 外科补丁、westlake host dex2oat(oat 247,在 `dockbuild.sh run` 里带 `LD_PRELOAD=libmap32bit.so`)重建 boot image、部署到当前车道持锁的一块白名单板
- 根因是某个 system service 返回 null 时,按 telephony 先例在 `OHServiceManager.lookupAdapter` 把该服务名路由到 `LocalServiceBinders` 的 no-op proxy
- `advanced` 须有正证据:T0 记录的那次失败调用现在返回成功(日志或栈里可见),而不只是原错误行消失
- 补丁 diff、重建出的 jar 与 boot image 的 sha256、板上实际加载的 boot image 哈希都记入 `results.json`

## 边界

### 允许修改
- benchmark/*-jvm-window-bringup/**
- tools/spec-checks/**

### 禁止
- 不修改 APK
- 不修改 native 库
- 不把补丁后的 boot image 部署到白名单外的板子

## 验收标准

场景: 试点 app 点亮
  测试: t2_pilot_lit
  审核: human
  假设 补丁后的 boot image 部署在一块持锁的白名单板上,且板上哈希与 `results.json` 一致
  当 用 T0 的采集脚本启动 `results.json.pilot` 指定的 app 并等待 30 s
  那么 外环读图签认截图显示该 app 自身的首个可用界面
  并且 `results.json` 的交付状态为 `lit`

场景: 试点越过原 blocker 但未点亮时记为 advanced
  测试: t2_pilot_advanced_with_positive_evidence
  假设 试点截图仍不是它自身界面
  当 重新采集 `triage.json`
  那么 只有 T0 记录的失败调用现在成功的原文证据存在时,交付状态才记 `advanced`,并写明 `next_blocker`
  并且 这种情况下点亮数不增加

场景: 原错误行消失但没有正证据时不算推进
  测试: t2_no_advance_without_positive_evidence
  假设 补丁后原错误行不再出现,但也没有该调用成功的证据
  当 判定交付状态
  那么 交付状态记 `no-change`,`results.json` 的 `note` 写明「原错误行消失、原因待查(含采集失效)」

场景: 同族 app 用同一构建重扫
  测试: t2_same_family_resweep_recorded
  假设 T1 把另外若干 app 归入与试点相同的族
  当 用同一 boot image 重扫这些 app
  那么 `results.json` 为每个 app 记录 `before`、`after` 两个判定与截图路径,新增 `lit` 均有外环签认

场景: 最终构建上的回归失败时判任务失败
  测试: t2_regression_fails_task
  审核: human
  假设 13 个 LIT 对照组用最终补丁构建重扫
  当 任一 app 的截图不再是它自身界面
  那么 任务判失败
  并且 `results.json` 的 `regressions` 列出该 app

场景: 补丁未生效时判失败
  测试: t2_patch_absent_detected
  假设 板上 boot image 的 sha256 与 `results.json` 记录值不一致
  当 执行验收
  那么 任务判失败且不计入点亮数

场景: 没有合格试点时暂停
  测试: t2_pauses_without_pure_jvm_candidate
  假设 T1 排序表前两名的族里都没有纯 Java app
  当 本任务开工检查
  那么 车道落 `ACK blocked` 并写明 T1 前两名的族键
  并且 不修改任何文件

## 排除范围

- jvm+native 类 app 的专属修复
- 修改 Westlake 源码树或 bridge-build 构建
