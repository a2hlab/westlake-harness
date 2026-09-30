---
kind: context
id: FLAW-005
title: "容忍守卫/桥接把代码放得更深,撞上新墙造成回退,上板前没有预判"
repo: A2OH/westlake-harness
layers: [Design, Verification]
status: open
severity: S2
recurrence: 3
fingerprint: design/guard-walks-deeper-regression
issue:
cards: []
filed: 2026-09-30
---

## 症状

三例同型:①r15 in-process bindService 桥让 droidify 的 SyncService 真跑起来 → `Service.startForeground` 打在空 `IActivityManager` 上;②r17a receiver guard 放行后 Noice(r16 亮)的播放服务走到 `nativePublishCommonEvent` 与 `PendingIntent.getActivity` 返回 null → 主线程 Kotlin NPE,两 key 回退;③r17a 让 etar/tasks/x/mcdonalds/immich 越过 provider/CommonEvent 后撞上更深的 create-application 墙。

## 责任步

守卫与桥接按「这堵墙过了没有」验收,没问「过了之后代码会碰到什么」;全量只看亮/不亮,没有逐 key 的首墙差分。

## 根因

容忍一个异常或接通一条系统通路,等于把后续路径交给了还没桩的系统面(发布、PendingIntent、前台服务)。

## 修复

oc-t4 每轮全量出「上一轮首墙 → 本轮首墙」逐 key 差分表(r17a-wall-diff.json);cc-t3 r17c 补 PendingIntent 族非 null 桩 + publish 与 subscribe 同容忍 + Service.attach 非 null IActivityManager 桩。DIGEST 记规则。

## 预防

加守卫/桥接的同一个 JAR 里,同时给该路径下一步会碰的系统面打类型正确的非 null 桩;每轮全量必出首墙差分,「走深」与「回退」分开记。待 r17c 全量确认 Noice 回来后关单。
