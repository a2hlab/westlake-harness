spec: task
name: "B5 启动入口是 activity-alias 时解析到目标 Activity"
inherits: project
depends: [b1-sandbox-prep]
tags: [bms, alias, cx-t0]
---

## 意图

B1 补上沙箱准备后,Wikipedia 的 child 已进入 `ActivityThread.main`,随后把桌面入口 `org.wikipedia.DefaultIcon` 当类实例化,抛 `ClassNotFoundException` 退出。`DefaultIcon` 是 manifest 里的 `<activity-alias>`,真正的类是它的 `android:targetActivity`;BMS 登记的该 ability `targetAbility` 为空,`apk_manifest_parser.cpp:368/536` 把 activity 与 activity-alias 按同一种元素解析。很多 app 用 alias 做启动入口,本任务让入口是 alias 时启动其目标 Activity。

## 已定决策

- 先在 `bms/src/adapter`、00.Workspace 各 worktree 与 hanbin 中找现成的 alias 处理照搬;没有再新写
- 修复点二选一,以改动少者为准:① 安装时解析 alias 的 `targetActivity` 并登记进 BMS;② 运行时按 app 自己的 manifest 把 alias 映射到目标类;选定后在 README 写明理由
- 统计 66 个 key 中启动入口是 alias 的 app 数,写进 results.json

## 边界

### 允许修改
- benchmark/2026-09-28-bms-route-deploy/**
- bms/src/adapter/framework/**
- tools/spec-checks/**

### 禁止
- 不修改 APK
- 不在 5ea、61b 以外的板上部署

## 验收标准

场景: Wikipedia 从桌面启动后越过 alias 墙
  测试: b5_wikipedia_passes_alias_wall
  假设 修复已在 5ea 生效,Wikipedia 已安装且做过沙箱准备
  当 从桌面点击它的图标并采集 hilog
  那么 实例化的类是 `org.wikipedia.main.MainActivity`,不再出现 `ClassNotFoundException`
  并且 进程走到 `Activity.attach`(上屏由 B4 汇总的下一批墙负责)

场景: alias 被解析到目标类
  测试: b5_alias_resolved_to_target
  假设 某 app 的启动入口是 `<activity-alias>`,其 `targetActivity` 为 X
  当 该 app 被拉起
  那么 hilog 显示实例化的类是 X,不是 alias 名

场景: 入口不是 alias 的 app 行为不变
  测试: b5_non_alias_entry_unchanged
  假设 HelloWorld 的启动入口是普通 activity
  当 从桌面启动 HelloWorld
  那么 它照常上屏

场景: alias 的目标类不存在时明确报错
  测试: b5_missing_target_reported
  假设 某 alias 的 `targetActivity` 在 dex 里找不到
  当 该 app 被拉起
  那么 hilog 记录 alias 名、目标名与失败原因,进程退出而不是挂住

## 排除范围

- 名字与图标(B2、B3)
- alias 之后的其他启动墙(交 B4 汇总)
