spec: task
name: "B8 把 Westlake 已验证的框架修复并入 route-A 运行时,两条路线合为一份代码"
inherits: project
depends: [b1-sandbox-prep, b5-activity-alias]
tags: [bms, framework, westlake, port]
---

## 意图

09-27 在 Westlake 运行时上亮过 13 个 app(含 Wikipedia、头条、麦当劳),它们越过首帧、Surface、系统服务缺失等墙靠的是 Westlake 的框架修复——落在 `adapter-runtime-bcp.jar` 的补丁(如 telephony 等服务的 no-op 桩、`WindowSessionAdapter.relayout` 的宽度 clamp、Flutter 的 Impeller 回退开关)与 Westlake bridge 源码。route-A(BMS 路线)用的是另一份适配层运行时 `oh-adapter-runtime.jar`,这些修复大多没有。本任务先把 Westlake 的修复逐项盘点、与 route-A 对照,再把缺的搬进仓库里的 route-A 源码 `bms/src/adapter/`,让两条路线的修复合在同一份代码里;优先搬能解释「白色启动窗」13 个 app 与 B6 之后 Wikipedia 的那几项。

## 已定决策

- 盘点来源:本仓库 `benchmark/2026-09-27-framework-x-localsend-fix/`、`benchmark/2026-09-27-framework-x-localsend-smali/`、DIGEST 中 CLAMP48 / telephony 桩 / Impeller 的条目、Westlake bridge 源码(VM `/home/dspfac/bridge-build`,不可及时用 `~/orca/westlake/westlake-deploy-ohos/v3-hbc/` 与 Westlake 运行时 jar 的 smali)
- 盘点表逐项记:修复名、解决的现象、Westlake 中的类与方法、route-A 中对应的类与方法、状态(已有 / 缺 / 不适用)、移植方式
- 移植落点:route-A 适配层的 Java 源码 `bms/src/adapter/framework/**`,构建出新的 `oh-adapter-runtime.jar`;部署沿用 B5 的覆盖方式,带回滚;不改 route-A 的 28 个 provider 与封存清单
- 优先级:先搬与「系统未下发 ScheduleLaunchAbility / AbilityStage 超时」「bind 期间 ProviderInfo / FileProvider 异常」相关的,再搬首帧 / Surface / 服务桩类
- 2026-09-29 用户决定:同一个问题 Westlake 与原 BMS(00.Workspace、real-work)都做过时,比较两边谁做得多、做得好就抄谁,两边都可以抄;Westlake bridge 的 native 部分与 Impeller 回退也照此办,不以「依赖 Westlake 专有组件」为由直接判不适用——只有两边都没有可用实现时才判不适用
- 2026-09-29 用户决定:点亮首屏用不到的系统服务(notification、jobscheduler、connectivity、location、Google 推送等,国内本来也用不了 Google 推送)一律打空桩,只求不崩——返回类型正确的无害默认值(空列表、false/0、成功码、无操作),不返回 null(UserManager 为 null 正是 catima/fennec 的死因);沿用 r8b 的 LocalServiceBinders 一次成批加,剩下的长尾服务用一个按接口给默认值的通用桩兜底
- 运行代的哈希锁由 B9 拆除;需要改 native 库的移植项等 B9 的无锁代,之后单文件替换,不再整代重生成
- 验证统一用 master 的 `bms_batch.py`(`--reinstall --hilog --shots --focus-check`),移植在 5cd 上开发验证,61b 做回归与白窗 13 个、09-27 Westlake 亮过的 13 个的重跑

## 边界

### 允许修改
- benchmark/2026-09-29-westlake-port/**
- bms/src/adapter/framework/**
- tools/spec-checks/**

### 禁止
- 不修改 APK
- 不改 route-A 的 28 个 provider 与封存清单(B6 的范围)
- 不在 5cd、61b 以外的板上部署(5ea 留给 B6)

## 验收标准

场景: Westlake 修复盘点表完整
  测试: b8_inventory_complete
  假设 盘点来源已全部读过
  当 查看 `benchmark/2026-09-29-westlake-port/inventory.json`
  那么 每项修复都有 Westlake 位置、route-A 对应位置与状态,状态为「缺」的都有移植方式

场景: 搬过来的修复在 route-A 上生效
  测试: b8_ported_fix_effective
  假设 一批移植已构建进新的 `oh-adapter-runtime.jar` 并部署到 5cd 或 61b,板上 SHA 与记录一致
  当 用 `bms_batch.py` 拉起相关 app 并采 hilog
  那么 每项移植都有该修复生效的正证据(日志行或调用成功),原错误行不再出现

场景: 白色启动窗的 app 越过原卡点
  测试: b8_white_window_advanced
  假设 与白窗相关的移植已部署
  当 拉起白窗 13 个 app 并采 hilog
  那么 `results.json` 逐个记录是否收到 ScheduleLaunchAbility、是否画出首帧,越过的附原文

场景: 点亮数由外环读图给出
  测试: b8_lit_by_outer_review
  审核: human
  假设 截图已按焦点门采集
  当 外环读图
  那么 `results.json` 的点亮数等于外环签认的数量

场景: 移植不让已亮的 app 回退
  测试: b8_no_regression
  假设 最终的 `oh-adapter-runtime.jar` 已部署
  当 拉起 HelloWorld 与 ZigZag
  那么 两者截图仍是各自界面

场景: 不适用或搬不动的写明原因
  测试: b8_not_ported_reason_recorded
  假设 某项 Westlake 修复在 route-A 上不适用或依赖 route-A 没有的组件
  当 结束本任务
  那么 盘点表写明原因与证据
  并且 同时写明原 BMS(00.Workspace、real-work)对同一问题有无实现、为什么两边都不能抄

## 排除范围

- B6 的信号链与封存链
- 安装墙(fd-seal、x、toutiao)
