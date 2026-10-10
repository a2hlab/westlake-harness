spec: task
name: "Minimal reboot simulator"
inherits: project
depends: [t2d-sepolicy-gate]
---

## 意图

重启前先算出「重启后会剩什么」,在推演状态上跑三类检查,出一张预测表;不过就不重启。先做最小版,不阻塞封存:封存窗照常走快照+实测,推演表作为附加输入。实测与推演不一致的地方,就是推演器要补的规则(AGENTS「漏掉的墙补进扫描器」)。

## 已定决策

- 输入:部署计划(56 层 target 与 source)、`board_state_snapshot.py` 快照(cc-t3 在做)、sepolicy 门的查询接口、自启配置(是否启用、recover 何时运行)。
- 推演规则最小集:bind mount 不跨重启;物理 /system 文件与标签跨重启保留;自启启用时按 recover 配方重放 bind 并打标签,未启用时只剩物理件。
- 三类检查:① 入口点:每个 init service 的 path 在推演状态下的标签是否为其 secon 的 entrypoint;② 依赖闭包:host 与关键库的 DT_NEEDED 闭包在推演状态下是否都存在且 appspawn 域可 map;③ seccomp/cfg 层:GetCfgFiles 默认层(/system:/chipset:/sys_prod:/chip_prod)下 `lib64/seccomp/lib<name>_filter.z.so` 恰好一份且子进程域可见。
- 用今天 61b 的四堵墙做已知答案:INVALID 粘死、EACCES 入口点、exit 127 data_local_tmp、seccomp 层 0 份;推演器至少报出后三条。

## 边界

### 允许修改
- scripts/lab/reboot_sim.py
- scripts/lab/test_reboot_sim.py
- benchmark/2026-10-10-reboot-sim/**
- tools/spec-checks/tests/demo_baseline.rs
- specs/demo-baseline/**

### 禁止
- 上板写操作;让推演结果成为封存的硬前置(最小版只出表)。

## 验收标准

场景: Prediction table lists the walls of the 61b reboot
  测试: demo_baseline_reboot_sim
  假设 The 61b deployment plan and the pre-fix snapshots from 2026-10-10
  当 reboot_sim.py runs
  那么 The table flags the appspawn-x entrypoint label the data_local_tmp libraries and the seccomp layer count with the evidence for each

场景: Clean predicted state passes
  测试: demo_baseline_reboot_sim
  假设 A snapshot whose recipe labels and autostart replay are complete
  当 reboot_sim.py runs
  那么 All three checks pass and the table says safe to reboot

场景: Missing input refuses to predict
  测试: demo_baseline_reboot_sim
  假设 The snapshot or the deployment plan is missing or its SHA does not match
  当 reboot_sim.py runs
  那么 It exits nonzero naming the missing input and prints no prediction

## 排除范围

- 完整 init 时序模拟;替代实测快照对照。
