spec: task
name: "Stability rounds and reboot check for the demo set"
inherits: project
depends: [t2-toutiao, t2b-boatattack, t3-install-sweep]
---

## 意图

确认演示集合可以反复展示:在演示板上再跑三轮全量首屏和一次重启后全量,只把每轮都亮的应用留在最终演示清单;游戏额外做一次触摸交互。

## 已定决策

- 三轮之间不改板;第四轮在重启后跑,验证开机后不用人工补步骤。
- 最终演示清单 = 四轮都亮的包;只亮了部分轮次的标为「不稳定」,写 k/n。
- 每个游戏点一下开始或下一步,截图前后对比确认界面有变化;头条再跑一次 toutiao_accept.sh。
- 发现回退不修,记首个致命点并移出最终清单。

## 边界

### 允许修改
- benchmark/2026-10-09-demo-baseline/**
- specs/demo-baseline/**
- tools/spec-checks/tests/demo_baseline.rs

## 验收标准

场景: Final demo list keeps only apps lit in all four rounds
  测试: demo_baseline_stability
  假设 Three normal rounds and one post-reboot round are recorded
  当 The final list is computed from facts.txt of each round
  那么 Every listed package is lit in four of four rounds and the others appear with k of n

场景: Games respond to a tap and Toutiao still passes after reboot
  审核: human
  测试: demo_baseline_stability
  假设 The post-reboot round is complete
  当 Each game is tapped once and Toutiao acceptance runs
  那么 Before and after screenshots differ for every listed game and Toutiao acceptance passes

场景: Board that does not come back after reboot stops the round
  测试: demo_baseline_stability
  假设 The demo board is not listed by hdc within ten minutes after reboot
  当 The post-reboot round starts
  那么 The round is marked aborted with the timestamp and the outer loop is notified instead of retrying silently

## 排除范围

- 修墙;重烤运行时;动另两块板。
