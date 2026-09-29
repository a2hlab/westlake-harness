---
kind: context
id: FLAW-008
title: "跨板/跨版本的差异被归到一个变量上,没有只改那一个变量的对照"
repo: A2OH/westlake-harness
layers: [Verification]
status: closed
severity: S2
recurrence: 5
fingerprint: verification/single-cause-without-control
issue:
cards: [EVO-0028, EVO-0029, EVO-0030]
filed: 2026-09-30
---

## 症状

2026-09-30 一夜五次,全部在上板对照出来之前就写成了原因:

- 05:20 外环判「r17p 让 ZigZag 回退」;cc-t3 在同板 r17m、r17q 各连跑 3 次都崩,ZigZag 本身不稳定(EVO-0028)。
- 05:39 cc-wiki 判「两个 Activity 的 session 全不同,复用假设不成立」;cx-t0 05:50 用 hilog 原文纠正(EVO-0029)。
- 06:35 外环把「Thunderbird/K-9/Tusky/AntennaPod 只在 5ea 亮」整体归到背景启动安装器;07:00 AntennaPod 在 61b 旧安装器下亮(EVO-0030)。
- 07:05 cc-wiki 判「32df 确定性杀 AntennaPod(唯一变量)」;外环 5cd 全量里 32df 下 AntennaPod 亮。
- 07:07 外环接着判「问题在 32df×r17p 组合」,让 cc-wiki 换 r17r;r17p/r17q/r17r 下 5ea 都 NPE,真正相关的是 5ea 这块板。

## 责任步

比较两次运行时,只数了自己关心的那一个变量。06:35 的「两板只差安装器」漏数了板子本身;07:05 的「唯一变量」只在 5ea 上成立,5cd 的结果一出来就不唯一了。

## 根因

运行时指纹(FLAW-004)只列文件差异,板子不在里面;单次运行里一个 app 翻转,既可能是变量造成,也可能是不稳定。没有工具把「差几个变量」算出来并写成判词,所以每次都靠人数。

## 修复

`scripts/lab/compare_runs.py <run-A> <run-B> [--keys …]`:板子也算一个变量,再加上指纹里每个 sha 不同或只在一边出现的路径;列出 t5/t20 存活翻转的 key 的两行 facts;最后一行给判词——恰好 1 个变量才叫单变量对照,多于 1 个一律是假设,0 个变量而 key 翻转则先重复 ≥3 次。单测 `scripts/lab/test_compare_runs.py`。用 r17p 全量两板实跑:`variables: 3`(板 + 安装器两件),06:35 的「只差安装器」按判词只能写成假设。

## 预防

写「X 造成 Y」之前先贴 `compare_runs.py` 的 `variables:` 行和判词;判词不是 single-variable 时,只写「假设 + 判别实验」。一个 app 在同条件下翻转,先同板同版本重复 3 次。
