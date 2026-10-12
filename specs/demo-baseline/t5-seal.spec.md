spec: task
name: "Seal the demo board"
inherits: project
depends: [t4-stability]
---

## 意图

把演示板封存成以后固定拿来展示的机器:记下完整指纹,写一份照着就能演示的手册和一键恢复脚本,并在仓库规则里把它登记为演示板。

## 已定决策

- 指纹包含 runtime-fingerprint、叠加清单、已装包列表(包名+版本+APK SHA)、系统版本,存进 benchmark 目录。
- 演示手册写:开机后怎么确认就绪、演示顺序、头条怎么操作、某个应用失败时跳过哪个;一键只读自检脚本对比当前指纹与封存指纹。
- 恢复脚本从封存的部署件把板恢复到封存态,先在空闲板上演练一次。
- AGENTS.md 板子纪律加一行:该序列号为演示板,零改动,只读巡检,解封只有用户能批。
- 分两步封存(用户 2026-10-10 定):先封 v1 = 统一态 128 个 app + 头条 Route B + 开机自启(拔电重开即可演示),不带 BoatAttack;Boat 作为叠加层做好后再补进去重封 v2。演示版不被 Boat 卡住。
- 61b 最终重启前严格执行「先拍快照(board_state_snapshot.py),再跑 sepolicy 门(t2d,配方每条有策略证明)」,有推演器(t2e)就附预测表;任何一项不过不重启(用户 2026-10-10 定)。
- 每次封存只重启一次:该版的所有层(自启、头条、以及 v2 的 Boat)一次叠齐,重启前按 RUNBOOK 拍完整状态快照,重启后不碰 Mac 自起,再跑全量 128 回归(t4/regress_vs_signoff.py)。
- 用户 2026-10-12 明示「同意精确参数派生，继续封板」：同板重启及备机恢复允许白名单中的宿主 UID/GID、序列号、独立控制目录和宿主窗口 ID 按实测参数精确派生；固定模板 SHA、生成器 SHA、输入参数、逐项差异和完整生成文件 SHA，其他字节必须相等，未知差异拒绝。原 seal 保留不覆盖，派生证明单独绑定它；不以任意文件排除或空白例外满足验收。

## 边界

### 允许修改
- benchmark/2026-10-09-demo-baseline/**
- scripts/lab/demo_selfcheck.sh
- scripts/lab/demo_restore.sh
- AGENTS.md
- specs/demo-baseline/**
- tools/spec-checks/tests/demo_baseline.rs

## 验收标准

场景: Self check matches the sealed fingerprint
  测试: demo_baseline_seal
  假设 The board is sealed and the fingerprint is stored
  当 demo_selfcheck.sh runs read-only
  那么 It reports every component equal to the sealed fingerprint or its user-approved exact parameter realization and exits zero and any unapproved difference exits nonzero naming the component

场景: Restore is rehearsed on a spare board
  测试: demo_baseline_seal
  假设 A spare board starts from the unified state
  当 demo_restore.sh runs
  那么 The spare board self check matches the original fingerprint through the user-approved exact parameter realization with template and generator hashes parameters complete rendered file hashes and retained raw execution logs

场景: Self check detects drift
  测试: demo_baseline_seal
  假设 One deployed file differs from the sealed fingerprint
  当 demo_selfcheck.sh runs
  那么 It exits nonzero and prints the path with expected and actual SHA

场景: Demo runbook lists order fallback and Toutiao steps
  测试: demo_baseline_seal
  假设 The runbook is written
  当 It is checked against the final demo list
  那么 Every demo app appears in order each has a skip fallback and the Toutiao and BoatAttack steps are present

## 排除范围

- 修墙、加新应用;封存后对演示板的任何写操作。
