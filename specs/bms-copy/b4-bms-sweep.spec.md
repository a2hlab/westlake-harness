spec: task
name: "B4 BMS 路线横向点亮重跑"
inherits: project
depends: [b1-sandbox-prep, b5-activity-alias, b6-attach-theme-context]
tags: [bms, sweep, oc-t4]
---

## 意图

B1 与 B5 把沙箱与 alias 两堵墙补上后,回到横向点亮:用 BMS 路线重装并拉起 09-27 扫量的 66 个 app,得到逐 app 的点亮结果,并与 09-27 Westlake 结果对照,找出下一批要修的共性问题。

## 已定决策

- 使用 #20 批量脚本加 B1 的沙箱准备与 B5 的 alias 修复;先在 61b 单板跑,其他板空出后按 `--keys` 分片加入;名字与图标(B2/B3)只影响桌面显示,不阻塞本任务,生效后再补一轮
- 每 app 记:安装结果(按 `bm install` 输出文本判,返回码 0 不算;已装旧版先 `bm uninstall`)、`bm dump` 回读、桌面名、图标来源桶、沙箱准备结果、进程时间线、t+3 与 final 截图、拉起前清缓冲后 15 s 的 hilog 与新增 faultlog
- 每次点击前核 boot_id 未变且前台是桌面,任一不满足即停
- 未亮的 app 取首个 blocker:沙箱、spawn、alias/入口、Activity.attach、ART 入口、首帧之一,并附原始日志行;按 blocker 汇总直方图,决定下一批修哪堵墙

## 边界

### 允许修改
- benchmark/2026-09-28-bms-route-deploy/**
- tools/spec-checks/**

### 禁止
- 不修改 APK
- 除按 B5 README 部署 B5 已交付的 alias JAR(带回滚)外,不改共享运行代

## 验收标准

场景: 66 个 app 各有一条完整记录
  测试: b4_every_key_recorded
  假设 各分片跑完
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
  那么 `first_blocker` 属于上述类别之一并附原始日志行

场景: 某块板掉线时只停该分片
  测试: b4_board_detach_stops_shard_only
  假设 某分片进行中该板掉线
  当 批量脚本检测到阶段失败
  那么 该分片剩余 app 记 `interrupted` 或 `not-run`,其他板照常完成

## 排除范围

- 对单个 app 的专项修复(`Activity.attach`/`getTheme` 墙归 B6;B6 生效后对首个 blocker 为它的 app 补跑)
