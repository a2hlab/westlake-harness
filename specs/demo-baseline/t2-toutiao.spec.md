spec: task
name: "Interactive Toutiao on the demo board"
inherits: project
---

## 意图

让演示板上的今日头条能打开、能刷首页、能点开文章,并通过 `scripts/lab/toutiao_accept.sh`。先离线判定走哪条路线,再上板。

## 已定决策

- 两条候选路线:A 是当前原包路线,需过 `libtttext_lite` 的 ICU 两堵墙(DIGEST 2026-10-03:应用命名空间缺 AOSP 公开库表,和 OH `/system/usr/icu` 版本号);B 是旧路线交付包 `~/a2hlab-provision/ttbundle`(MANIFEST 7/7,曾在 5cd 上可交互)与当前路线共存。
- 先静态判定:列出 B 在板上写的每个路径、起的每个进程、占用的包名和 ability,与当前路线部署件逐项比对冲突;再估 A 的两堵墙各需改什么文件。按「改动少、可回滚、不碰冻结项」选一条,写进 README 再上板。
- 上板在空闲板上先做,通过后才叠到演示板;叠加件单文件、带回滚脚本,并记进 runtime-fingerprint 的叠加清单。
- 残余冷启动崩溃如果仍有,用已有的看门狗自愈,并在验收里如实记崩溃率,不说成零崩。

## 边界

### 允许修改
- benchmark/2026-10-09-demo-toutiao/**
- specs/demo-baseline/**
- tools/spec-checks/tests/demo_baseline.rs

## 验收标准

场景: Route is chosen by an offline conflict and cost comparison
  测试: demo_baseline_toutiao_route
  假设 Deployed paths processes and abilities of both routes are listed from files
  当 The route decision is recorded
  那么 Every conflict is listed with its evidence and the chosen route cites why it changes fewer files and touches no frozen item

场景: Toutiao passes acceptance on the demo board three times
  测试: demo_baseline_toutiao_accept
  假设 The chosen route is overlaid on the demo board with a rollback script
  当 toutiao_accept.sh runs three cold starts
  那么 Each run reports feed headlines scroll article open and process alive and the screenshots of feed and opened article are attached

场景: Overlay does not regress other apps
  测试: demo_baseline_toutiao_accept
  假设 The overlay is installed
  当 Ten previously lit keys are relaunched on the same board
  那么 All ten stay lit by t20 screenshot or the overlay is rolled back

场景: Failed acceptance rolls the overlay back
  测试: demo_baseline_toutiao_accept
  假设 toutiao_accept.sh fails on the spare board
  当 The overlay step finishes
  那么 The rollback script restores the previous fingerprint and the failure and first fatal are recorded

## 排除范围

- 视频播放、登录、推送;修冻结项;改另两块实验板。
