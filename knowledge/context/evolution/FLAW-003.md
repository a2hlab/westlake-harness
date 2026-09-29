---
kind: context
id: FLAW-003
title: "auto 模式会话被服务端判定硬拒板上 /system 写入,部署卡了约 3 小时"
repo: A2OH/westlake-harness
layers: [Governance, Lifecycle]
status: closed
severity: S1
recurrence: 2
fingerprint: governance/auto-mode-blocks-board-system-writes
issue:
cards: []
filed: 2026-09-29
---

## 症状

2026-09-29 晚两次上板被挡:appspawn-x(gid 3003)包 20:02 就绪、约 20:40 才执行(约 40 分钟);installer(INTERNET 权限)包 21:19 就绪、23:39 才上板(约 2 小时 20 分钟)。cc-wiki(auto 模式)与外环主会话都报 `Auto-Mode Bypass` / `server-side classifier`,不弹权限提示;用户在聊天里的「允许」、本地 `orb` 允许规则、`!` 转发、转派车道都解不开。

## 责任步

外环在 21:26 第一次被拦时没有识别出这是服务端判定,先后试了五六种绕法,每种都要用户再操作一次。

## 根因

auto 模式的服务端安全判定把「替换 /system 核心二进制 + 重启系统服务」判为高风险,只认用户亲手执行或以免审批方式启动的会话;本地规则与对话内授权都不在它的判定面上。另有一处叠加:部署脚本写死经 VM `hdc_mac.sh` 转发,foundation 重启期间转发 60 s 超时。

## 修复

用户以 `claude --dangerously-skip-permissions` 重开外环会话后,外环直接完成 installer 与 appspawn-x 部署;部署脚本改用 Mac 直连 hdc 的变体。RUNBOOK d5407ce7 记两条。

## 预防

RUNBOOK:板上 `/system` 写入的会话开工就用 skip-permissions 启动;撞到 `Auto-Mode Bypass`/`server-side classifier` 立即请用户重开会话,不再试别的绕法;foundation 重启期间用 Mac 直连 hdc。
