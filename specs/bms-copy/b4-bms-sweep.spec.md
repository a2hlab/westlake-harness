spec: task
name: "B4 BMS 路线横向点亮重跑"
inherits: project
depends: [b1-sandbox-prep, b2-label-resolve, b3-icon-resolve, b5-activity-alias]
tags: [bms, sweep, cx-t0]
---

## 意图

B1–B3 把安装与拉起的缺口补齐后,回到横向点亮:用 BMS 路线在三块板上重装并拉起 09-27 扫量的 66 个 app,得到逐 app 的点亮结果,并与 09-27 Westlake 结果对照,找出下一批要修的共性问题。

## 已定决策

- 使用 #20 批量脚本加 B1 的沙箱准备,installer 用 B2/B3 生效后的那一份,三板并行,`--keys` 分片
- 每 app 记:安装结果、`bm dump` 回读、桌面名、图标来源桶、沙箱准备结果、进程时间线、t+3 与 final 截图
- 未亮的 app 取首个 blocker:沙箱、spawn、ART 入口、首帧四类之一,并附原始日志行

## 边界

### 允许修改
- benchmark/2026-09-28-bms-route-deploy/**
- tools/spec-checks/**

### 禁止
- 不修改 APK
- 不改共享运行代

## 验收标准

场景: 66 个 app 各有一条完整记录
  测试: b4_every_key_recorded
  假设 三板分片跑完
  当 汇总 results.json
  那么 66 个 key 各恰好一条有效记录,含上述全部字段

场景: 点亮数由外环读图给出
  测试: b4_lit_count_from_outer_review
  审核: human
  假设 所有截图已收齐
  当 外环逐张读图
  那么 results.json 的 LIT 计数等于外环签认的数量

场景: 未亮 app 有具名首个 blocker
  测试: b4_unlit_have_first_blocker
  假设 某 app 未亮
  当 查看它的记录
  那么 `first_blocker` 属于四类之一并附原始日志行

场景: 某块板掉线时只停该分片
  测试: b4_board_detach_stops_shard_only
  假设 某分片进行中该板掉线
  当 批量脚本检测到阶段失败
  那么 该分片剩余 app 记 `interrupted` 或 `not-run`,其他板照常完成

## 排除范围

- 对单个 app 的专项修复
