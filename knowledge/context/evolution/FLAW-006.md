---
kind: context
id: FLAW-006
title: "改判与更正没用定式行首,进化采集哨一夜采到 0 张卡"
repo: A2OH/westlake-harness
layers: [Governance]
status: closed
severity: S3
recurrence: 4
fingerprint: governance/corrections-not-harvestable
issue:
cards: []
filed: 2026-09-30
---

## 症状

2026-09-30 凌晨至少四处更正落了板:cc-wiki「r16 未带 receiver guard 是错的」(真因是两层代理异常未解包)、外环把 auxio@5cd 从「回退」改判为板间差、外环派 cc-wiki「查 Westlake 完整 tagsoup」而 Westlake 其实只有同一空壳、cc-t3 就地覆盖已公示的 r17 JAR(4bbea1f6→8f4774e1)。01:30 的 `olp-evo-harvest.sh` 采到 0 张新卡。

## 责任步

更正写成散文(「更正:」「是错的」「改判」夹在句中),采集哨只认行首定式 `> 外环(<署名>)·改判(作废 #N):` 与 `> 外环(<署名>)·R2 记档(#N):`。

## 根因

定式只写在 octoloop skill 与协议文档里,车道上岗词和 RUNBOOK 没有;外环自己也没用。

## 修复

RUNBOOK 加一条:任何推翻已落板结论的更正,外环用定式行首另起一行记档(车道的更正由外环代记);本次四处已补记。

## 预防

外环每次读到「更正/误读/是错的/改判」类句子,当场补一行定式记档;retro 时若采集为 0 而板上有更正,即判定式漏记。
