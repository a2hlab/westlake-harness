---
kind: context
id: FLAW-010
title: "采集哨存活不能证明进化记录持续更新"
repo: A2OH/westlake-harness
layers: [Lifecycle, Measurement]
status: open
severity: S2
recurrence: 2
fingerprint: lifecycle/collector-process-without-output-health
issue:
cards: [EVO-0140]
filed: 2026-10-13
---

## 症状与证据

RUNBOOK 已记录 GNU stat 和全角 EVO 编号的问题；10月13日系统 Bash 3.2 再次复现编号解析错误。旧两哨进程活着，stdout/stderr 都指向 `/dev/null`，最新卡仍为10月10日。旧进程环境无法从本机 ps 确认，不能把环境未知写成缺失。没有新定式 R2 行也会没有新卡，不能仅凭卡日期认定漏采。

## 根因与实证修复

`$'\uff08'` 在 Bash 3.2 不展开，原脚本在 EVO-0139 后误算下一编号0001。隔离副本改为取连续数字前缀，显式 GNU 工具 PATH 与真实 review board；139卡实写回放只加0140，第二次新增0，原139卡字节保持。证据 `benchmark/2026-10-13-evolution-health/results.json`。不修改全局发行脚本。

## 运维闭环

新双哨使用独立 runtime 并保留 stdout/stderr，切换见同目录 `live-switch.json`。必须取得真实 R2→新 EVO 卡的回执，再跑 harvest/retro 确认无重复；进程存活只是其中一项。记录保持 open，待实际采集与随后一次正常节拍验证再关闭。
