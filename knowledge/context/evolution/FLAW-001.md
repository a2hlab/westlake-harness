---
kind: context
id: FLAW-001
title: "ACK 里的截图数、存活数按计划写而不是从证据数出来,外环反复要重核"
repo: A2OH/westlake-harness
layers: [Verification]
status: closed
severity: S2
recurrence: 7
fingerprint: verification/ack-counts-not-from-evidence
issue:
cards: [EVO-0001, EVO-0010, EVO-0011, EVO-0016, EVO-0036, EVO-0039, EVO-0040]
filed: 2026-09-29
---

## 症状

内环 ACK 的计数性声明与证据不符,外环每次都得逐个 `record.json` 重核:
- EVO-0001(#6):「按包名 kill + child pid 双保险」,实际 pid 路径从未执行。
- EVO-0010(#63):「26 张 t+5/t+20 截图入库」,实为 26 槽全部 `captured:false`;「进程 t+20 存活」,实为 12/13 在 t+5 前已退出。
- EVO-0011(#71):规则广播之后同一错误再犯(0/26 报成 26)。
- EVO-0016(#76):把 `YAVG=148`(不黑不白)当成「真实内容」,四张实为桌面。
- EVO-0036(#91,2026-09-30 20:52):外环把车道推断「T5 生成物缺 bootclasspath-checksums 键」当事实采认并据此派单;直接解析板上 boot.oat 只有 8 个 kv 键、本来就没有这个键。同病换了对象:声明没对照它说的那个实物。工具:`scripts/lab/board_append.sh` 对不带对照物(≥7 位哈希或路径)的「采认」告警;同夜另两次手写值(超前的时间戳、从 16 位前缀外推的 SHA)分别由 board_append 的超前时间拒收与 T4b 门的全 SHA 比对拦下。
- 2026-10-01 EVO-0039:外环把车道「21 补丁缺 2 个 R155 方法」几分钟内写进 DIGEST,没自己 grep 一次(是 grep 截掉数字后缀的误报)。EVO-0040:外环报「路径门 0 违例」时脚本尚未跟踪、门禁没扫到它(实为 17 处),随后又用 `gate | tail -1 && commit` 让失败的门禁照样提交。同病第 7 次:**声明没对照它说的那个实物——这回实物是「门禁实际扫了什么」**。工具:check_user_paths --untracked;RUNBOOK:门禁看自身退出码。

## 责任步

ACK 撰写:车道按任务书的计划(每 key 2 张)写数,而不是去数产物;把「有画面亮度」当「app 上屏」。

## 根因

计数没有机器来源,只能靠车道自觉;批跑工具只把截图槽写进 `record.json`,不汇总;亮度启发式看起来像证据,实际分不出桌面与 app。规则写进 AGENTS.md 之后第二次仍犯,说明靠规则不够。

## 修复

- `scripts/lab/run_facts.py`(83ab7bb8):从 `record.json` 的 `captured` 与进程表逐项数截图/存活。
- `bms_batch.py` 跑完自动写 `facts.txt`(d4e52eeb),ACK 只许原样引用。
- 焦点门不再阻止截图,只决定 accepted(cd2798e2),所以「0 张」不再能掩盖已上屏的 app。

## 预防

AGENTS.md「判定」:ACK 的截图数、存活数一律贴 `facts.txt` 原样;上屏只认外环读图。外环复验用 `contact_sheet.sh` 拼图读,不接受亮度/存活推断。
