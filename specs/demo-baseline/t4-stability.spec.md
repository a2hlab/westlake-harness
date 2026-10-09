spec: task
name: "Stability rounds and reboot check for the demo set"
inherits: project
depends: [t2-toutiao, t2b-boatattack, t3-install-sweep]
---

## 意图

确认演示集合可以反复展示,用加速方案(用户 2026-10-09 采纳):t3 那一轮算第 1 轮,t4 只再跑 1 轮常规和 1 轮重启后;历史稳定的应用只复测 1 次,多轮复测集中在边缘应用。对外说法只能是「关键应用多轮验证、其余有历史多轮证据」。

## 已定决策

- 第 1 轮 = t3 的签认结果;第 2 轮 = 常规全量;第 3 轮 = 重启后全量,验证开机后不用人工补步骤。三轮之间不改板。
- 分两组:**历史稳定组** = 在 U13/U14 签认里至少 2 次运行、跨至少 2 块板都亮、且从未白屏的包,截图时间 10 秒;**边缘组** = 32 个空首屏点击类、游戏、头条、BoatAttack、历史上偶发白屏或只在一块板亮过的包,截图时间 20 秒。分组表由历史签认文件机械算出,不手挑。
- 历史稳定组在第 2 轮可跳过、只在第 3 轮(重启后)复测;边缘组第 2、3 轮都跑。最终演示清单 = 历史稳定组里第 1、3 轮都亮的 + 边缘组里三轮都亮的;其余标「不稳定」写 k/n。
- 签认用 contact_sheet.sh 拼图一次看几十张,外环逐格签认;拼图文件与签认结果一起入库。
- 每个游戏点一下开始或下一步,前后截图确认界面有变化;头条在第 3 轮再跑一次 toutiao_accept.sh。
- 发现回退不修,记首个致命点并移出最终清单。

## 边界

### 允许修改
- benchmark/2026-10-09-demo-baseline/**
- specs/demo-baseline/**
- tools/spec-checks/tests/demo_baseline.rs

## 验收标准

场景: Final demo list follows the stable and edge group rules
  测试: demo_baseline_stability
  假设 Round one from t3 a normal round two and a post-reboot round three are recorded
  当 The final list is computed from facts.txt of each round
  那么 Every stable-group package is lit in rounds one and three every edge-group package is lit in all three rounds and the others appear with k of n

场景: Group assignment is computed from signed history not chosen by hand
  测试: demo_baseline_stability
  假设 U13 and U14 signoff files are available
  当 The grouping table is generated twice
  那么 Both outputs are byte identical and every stable-group package cites at least two lit runs on at least two boards with no white screen

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
