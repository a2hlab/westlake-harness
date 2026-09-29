---
kind: context
id: FLAW-007
title: "只凭 t5 或转述就报「点亮」,t20 已回桌面"
repo: A2OH/westlake-harness
layers: [Verification]
status: closed
severity: S2
recurrence: 3
fingerprint: verification/lit-claim-from-first-frame-or-relay
issue:
cards: [EVO-0027]
filed: 2026-09-30
---

## 症状

2026-09-30 凌晨三次同型:Wikipedia 首页 feed、NewPipe「直播」页在 t5 上屏、t20 回桌面,车道报告里写成「亮/全亮」;05:18 cc-wiki 转述 cc-t3 的 61b r17p 结果为「wikipedia/newpipe/AppManager 全亮」,外环读原图:前两者 t20 进程已不在。

## 责任步

车道汇报点亮时只看了首帧或只转述别的车道的结论,没有给 t20(最后一张)截图路径与 facts 行;外环若不逐图读就会记错累计数。

## 根因

「上屏」与「稳定点亮」两个口径在车道里没有分开;facts.txt 已有 alive t20 列,但汇报时没引用。

## 修复

外环逐图读 t5/t20,首屏未稳定单列不计入;本次在黑板用定式 R2 记档更正。

## 预防

点亮声明必须附最后一张截图路径 + 该 key 的 facts 原样行(alive t20=yes);只在 t5 在屏的记「首屏未稳定」;转述别的车道结论时注明「未读原图」。外环签认只按自己读的最后一张图。
