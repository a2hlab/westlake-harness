---
kind: context
id: FLAW-004
title: "板间运行库漂移不进运行记录,同一 key 两板结果不同被当成 JAR 回退"
repo: A2OH/westlake-harness
layers: [Measurement, Lifecycle]
status: closed
severity: S2
recurrence: 3
fingerprint: measurement/board-runtime-drift-unrecorded
issue:
cards: []
filed: 2026-09-30
---

## 症状

2026-09-30 凌晨 r16 全量里 fd-auxio@5cd 死在 `VelocityTracker.nativeInitialize`,前一天它在 61b 签过亮,第一眼像 r16 JAR 回退;实为 #87 只在 61b 单换了 runtime c835a93e(注册 VelocityTracker)+ liblog 8c81a937,5cd 没换。同夜外环在 61b 换 ANL 被部署器拒(与当前活动包差三件),也是 61b 的 #87 单换造成。r15c@5cd 早已同死,当时没人把它和 61b 对照。

## 责任步

全量跑之前没有记录各板运行时加载路径的实际 SHA;`baseline.json` 只读 appspawn-x 与 JAR 两件。跨板比较时只能靠记忆知道哪块板换过什么。

## 根因

单文件替换(B9)是按板做的,每次只在一块板验证;替换记录分散在各车道 receipt 里,运行记录不带这些信息。

## 修复

`bms_batch.py` 每次运行把 appspawn-x、runtime JAR、`/system/android/lib64/*.so`、`route-a/*/*.so` 的 sha256 写进 `runtime-fingerprint.txt`,`facts.txt` 首行给 12 位指纹(`RUNTIME fingerprint=… files=N`);单测 `test_runtime_fingerprint.py`。外环用 61b 单跑 auxio 验证了板间假设(r16 JAR 下 61b 亮)。

## 预防

两板同 key 结果不同,先比 facts.txt 首行指纹与 runtime-fingerprint.txt,再疑 JAR;单板单换的 native 修复进 v3c 合代清单,合代前不计入「修好」。
