---
kind: context
id: FLAW-009
title: "模块复验通过后才发现真实消费者接口不兼容"
repo: A2OH/westlake-harness
layers: [Design, Verification, Execution]
status: open
severity: S2
recurrence: 4
fingerprint: verification/producer-consumer-contract-not-replayed
issue:
cards: [EVO-0141, EVO-0143]
filed: 2026-10-13
---

## 症状与证据

#91 三次不同接缝需要在执行前后补救：`board_note held` 返回整行而消费者按 owner 字符串判断；snapshot 把 owned source/control 路径当挂载 target；旧恢复入口的 argv/schema 不能消费新 current487 recipe。前两次证据分别在 `benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r5-preflight/held-protocol-review.json`、同目录 `snapshot-r4-review.json`。后一次见 `benchmark/2026-10-13-routeb-fresh-restore-review/entry-review.json`。

## 根因

复验对象是单模块或窄夹具，没有把生产者实际输出交给主树中的原消费者。动态参数尚待设备实测，不等于静态 argv、schema、路径归属也要等上板才验证。

## 已落实

current487 核心与后继入口分开发行：核心在 5cd 执行期间，后继完成独立 CLI 预演、完整回执检查和失败停止测试；主树落地 `069d943684`。入口只承认完整487历史，再运行原 live R5 与原 Boat provider，不替代设备证据。最终61b稳定源映射提前生成，真实 UID/boot/WMS 参数仍待采集。

## 后续判定

派单列出每个消费者的实际命令和输入；静态接缝在主树绑定后做 disabled 端到端预演，不能只验文档包含命令。新一轮执行无同类接口失败后再关闭本记录。此记录不新增封板验收门。

## 2026-10-14 收尾复发：前台集合对象未沿真实调用点核对

#91 收尾补充卡将 `foreground(wm, {current_host_pid})` 当成原门，拒绝同 UID 的合法头条焦点。原 BMS `bms_batch.py:767–772` 实际传目标 UID 的全部当前进程；`foreground:376–382` 只做集合归属。同 boot 086d 原 live954 已接受 host4583/WID33 与 focus6789/WID30；只读函数定义而未沿真实调用点追到集合来源，会把补充文案变成未授权新门。复审必须核对真实调用参数的对象与集合范围，并对已通过的原始输入做本地消费对照。

保留 singleton 原失败，新侧件纠正；不修改冻结 consumer 或 expected，宿主参数与 WL_PARENT_ID 仍为33。纠正后新824文件/130包采集、原 consume/compile/verify 与新proof live954均实际通过，实际签字另据最终 S。本记录保持 open，不因本次收尾成功关闭。原函数/调用点与9个来源pin见 `benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/final-foreground-object-review/results.json`；原失败与纠正见 `benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/final61b-finalization/host-attempt-result.json`、同目录 `root-foreground-review.json`，新终检见 `benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/final61b-v2-realization/final-live954.json`。
