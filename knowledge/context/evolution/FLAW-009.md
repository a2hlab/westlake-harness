---
kind: context
id: FLAW-009
title: "模块复验通过后才发现真实消费者接口不兼容"
repo: A2OH/westlake-harness
layers: [Design, Verification, Execution]
status: open
severity: S2
recurrence: 3
fingerprint: verification/producer-consumer-contract-not-replayed
issue:
cards: [EVO-0141]
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
