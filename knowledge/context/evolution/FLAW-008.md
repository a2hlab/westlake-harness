---
kind: context
id: FLAW-008
title: "跨板/跨版本的差异被归到一个变量上,没有只改那一个变量的对照"
repo: A2OH/westlake-harness
layers: [Verification]
status: closed
severity: S2
recurrence: 8
fingerprint: verification/single-cause-without-control
issue:
cards: [EVO-0028, EVO-0029, EVO-0030, EVO-0031, EVO-0037, EVO-0038]
filed: 2026-09-30
---

## 症状

2026-09-30 一夜五次,全部在上板对照出来之前就写成了原因:

- 05:20 外环判「r17p 让 ZigZag 回退」;cc-t3 在同板 r17m、r17q 各连跑 3 次都崩,ZigZag 本身不稳定(EVO-0028)。
- 05:39 cc-wiki 判「两个 Activity 的 session 全不同,复用假设不成立」;cx-t0 05:50 用 hilog 原文纠正(EVO-0029)。
- 06:35 外环把「Thunderbird/K-9/Tusky/AntennaPod 只在 5ea 亮」整体归到背景启动安装器;07:00 AntennaPod 在 61b 旧安装器下亮(EVO-0030)。
- 07:05 cc-wiki 判「32df 确定性杀 AntennaPod(唯一变量)」;外环 5cd 全量里 32df 下 AntennaPod 亮。
- 07:07 外环接着判「问题在 32df×r17p 组合」,让 cc-wiki 换 r17r;r17p/r17q/r17r 下 5ea 都 NPE,真正相关的是 5ea 这块板。

- 07:25 外环以「32df 在 5ea 的独有损失是 AntennaPod」回滚 32df;cc-wiki 07:41 清装矩阵表明是 r17r 与 app 数据损坏(一次崩溃写坏 WorkManager 库,不重装就一直崩),32df 未经受控验证(EVO-0031)。第 6 次,并暴露第三类变量:app 数据状态。
- 22:19 外环采认「读屏障是 T6 的根因(功能性坐实)」:T6 判别换的是整套 27 个 boot 镜像文件,读屏障只是 T5 与 v3c 之间众多差异之一,runtime-fingerprint.txt 却「不变」(它不含 boot 镜像);当作症状的「子进程集体 SIGILL」是常规 sigchain 行。正式 T6 用读屏障关的 T5b 仍不亮(EVO-0037)。第 7 次,并暴露第四类变量:指纹没覆盖的 boot 镜像。
- 2026-10-01 00:10 外环据「逐件换回」二分(每步只跑 1 次)采认「fd-noice 回退 = N3b 的 ANL」并写进 DIGEST 与 N4 定版;双板单变量 A/B 各 3 次:两版 ANL 都是 2/6 亮(EVO-0038)。第 8 次,新形态:**不稳定 app 的单次观测**;且白屏时进程仍活,存活表不翻转,compare_runs 原先看不见它。工具:knowledge/gates/flaky-keys.json + compare_runs 对登记的 key 降级判词为「每边 ≥3 次」,重放该二分现在给出 flaky 判词。

## 责任步

比较两次运行时,只数了自己关心的那一个变量。06:35 的「两板只差安装器」漏数了板子本身;07:05 的「唯一变量」只在 5ea 上成立,5cd 的结果一出来就不唯一了。

## 根因

运行时指纹(FLAW-004)只列文件差异,板子不在里面;单次运行里一个 app 翻转,既可能是变量造成,也可能是不稳定。没有工具把「差几个变量」算出来并写成判词,所以每次都靠人数。

## 修复

`scripts/lab/compare_runs.py <run-A> <run-B> [--keys …]`:板子也算一个变量,再加上指纹里每个 sha 不同或只在一边出现的路径;列出 t5/t20 存活翻转的 key 的两行 facts;最后一行给判词——恰好 1 个变量才叫单变量对照,多于 1 个一律是假设,0 个变量而 key 翻转则先重复 ≥3 次。单测 `scripts/lab/test_compare_runs.py`。之后又补两类变量:同板重启(baseline.json 的 boot_id)与未 `--reinstall` 的运行(app 数据延续)。2026-09-30 夜又补第四类:boot 镜像与 9 个 BCP jar 另记 `boot-image-fingerprint.txt`(facts.txt 的 BOOTIMAGE 行,不改 RUNTIME 指纹),compare_runs 把它的变化算 1 个变量,缺记录的一侧只给 note。用 r17p 全量两板实跑:`variables: 3`(板 + 安装器两件),06:35 的「只差安装器」按判词只能写成假设。

## 预防

写「X 造成 Y」之前先贴 `compare_runs.py` 的 `variables:` 行和判词;判词不是 single-variable 时,只写「假设 + 判别实验」。一个 app 在同条件下翻转,先同板同版本重复 3 次。
