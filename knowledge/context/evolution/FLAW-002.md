---
kind: context
id: FLAW-002
title: "测量缺口被当成结论:日志被冲、截图被拒,读出了假的根因"
repo: A2OH/westlake-harness
layers: [Verification, Execution]
status: closed
severity: S2
recurrence: 2
fingerprint: verification/measurement-gap-as-finding
issue:
cards: [EVO-0011]
filed: 2026-09-29
---

## 症状

- #71(EVO-0011):12 个 app 子进程 hilog 0 行,车道据此推断「r8b JAR 在 6cb 栈上不发 B43/B8-R8B 标记」。实为 61b 重启后 hilog 缓冲回到 256K、`hilog.private.on=true`,子进程几万行日志在采集前被冲掉。
- #78:fd-AppManager、fd-droidify 在 t5/t20 都活着,却 0/26 截图——焦点门(focused PID 不是目标 / 焦点行缺失)把真上屏的画面拒掉,这两个 app 其实已经亮了。

## 责任步

批跑采集:开跑前没有核对测量条件(缓冲大小、隐私遮蔽);截图前的焦点检查失败时直接放弃拍照。

## 根因

板子重启会把 hilog 设置恢复默认,工具默认当前设置是对的;焦点检查依赖 WMS 窗口表解析,route-A 窗口在表里形态不同,把把关工具的假阴性当成了事实。

## 修复

- `bms_batch.py` 预检(d4e52eeb):设 `hilog -G 16M`、`hilog -p off`、熄屏超时、板钟,逐项回读写进每个 `record.json`,不达标拒跑。
- 焦点门只决定 accepted、不挡截图(cd2798e2)。

## 预防

DIGEST「hilog 缓冲重启即回 256K」「焦点门漏拍」两条;规则:没有日志 ≠ 没有发生,先确认测量手段完好再下结论。
