spec: task
name: "B11 Wikipedia 专线:对照 Westlake 成功日志,按分叉点照抄,直到欢迎页上屏"
inherits: project
depends: [b8-port-westlake-fixes]
tags: [bms, wikipedia, westlake, cc-wiki]
---

## 意图

Wikipedia 在 09-27 的 Westlake 路线上亮到了 "All the world's knowledge" 欢迎页;在 route-A 上它越过了空指针墙(B6),r8b 又搬来了它需要的 B8 标 W 的几项,但还没有上屏。本任务由一条 Claude 车道独占 5ea 专做 Wikipedia:先在 5ea 用 Westlake 路线取一份完整的成功日志,再跑 route-A,逐段对照找第一个分叉点,按分叉点整段照抄 Westlake 的实现,直到外环读图签认 Wikipedia 欢迎页。

## 已定决策

- 独占 5ea34a4500000000000000001123012c,不与横扫混排;基线是 v3a 包 `/Users/zhaoyue/orca/workspaces/westlake-generation-v3a-74d1d6d4-r8b`
- Westlake 成功日志:5ea 上有 Westlake 宿主 `org.westlake.imehost` 与 a2hlab-source 运行时目录,按 09-27 的 probe 配方(VM `~/a2hlab/ws/out-appsweep-5ea34a45/wikipedia/run.sh`)在 hilog 16M、private off 下拉起 Wikipedia,保住 child stderr 与 hilog,截图到欢迎页;取不到时写明卡在哪,改用 Westlake smali(`~/a2hlab-provision/fxwork/out-smali.orig/`)与 route-A 源码做静态路径对照
- 对照顺序:Application → provider → Activity.attach → 主题 → 包查询(QueryAbilityInfos / getProviderInfo / resolveContentProvider)→ 首帧 → Surface;记第一个分叉点与两边原文
- 用户预先授权:单文件替换(Java 覆盖 JAR 或单个 native 库,经 `deploy_generation.sh` 单文件替换模式,带回滚)与照抄 Westlake 实现,不用请示
- 节奏:每轮只做一次单文件替换 + 一次从桌面拉起 + 截图,15–20 分钟在黑板报一次 PROGRESS,附截图路径,外环当场读图;截图数与存活只贴 `facts.txt`
- 批跑用 master 工作树的 `bms_batch.py`(自带预检)`--keys wikipedia --reinstall --hilog 20 --shots 5,20 --focus-check`

## 边界

### 允许修改
- benchmark/2026-09-29-wikipedia-line/**
- bms/src/adapter/framework/**
- tools/spec-checks/**

### 禁止
- 不修改 APK
- 不在 5ea 以外的板上部署
- 不改 installer

## 验收标准

场景: Wikipedia 欢迎页上屏
  测试: b11_wikipedia_welcome_lit
  审核: human
  假设 最后一次单文件替换已在 5ea 生效,板上 SHA 与 `results.json` 一致
  当 从桌面拉起 Wikipedia 并在 t+5 s、t+20 s 截图
  那么 外环读图签认截图是 Wikipedia 欢迎页

场景: Westlake 成功日志取到或写明取不到的原因
  测试: b11_westlake_reference_log
  假设 5ea 上 Westlake 宿主与运行时目录存在
  当 用 09-27 的 probe 配方拉起 Wikipedia
  那么 `results.json.westlake_log` 记录 hilog 与 child stderr 路径和欢迎页截图
  并且 取不到时记录卡住的步骤与原文,改用静态路径对照

场景: 每轮记下分叉点与照抄来源
  测试: b11_divergence_recorded
  假设 某一轮对照了 Westlake 与 route-A 的日志
  当 查看 `results.json.rounds`
  那么 每轮都有第一个分叉点、两边原文、照抄的 Westlake 类或 smali 路径、替换的文件与 SHA

场景: 替换后回归时回滚
  测试: b11_rollback_on_regression
  假设 某轮单文件替换后 HelloWorld 或 ZigZag 不再是各自界面
  当 执行该文件的单件回滚
  那么 板上 SHA 回到替换前,HelloWorld 与 ZigZag 截图恢复

## 排除范围

- 其他 app 的横扫(#74)
- 安装墙(#79)
