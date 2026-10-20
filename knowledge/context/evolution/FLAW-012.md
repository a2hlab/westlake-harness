---
kind: context
id: FLAW-012
title: "留板签认准备挤占实际执行窗口"
repo: A2OH/westlake-harness
layers: [Execution, Verification]
status: open
severity: S2
recurrence: 2
fingerprint: execution/retention-closeout-misses-window-deadline
issue:
cards: [EVO-0160]
filed: 2026-10-20
---

## 复发证据

原 T31 与 replay02 均未在 1200 秒内完成实际 retain 签认。replay02 已取得两轮同片视觉验收证据，仍错过外环声明的 1100 秒停试验点和 1200 秒签认点，最终恢复并于 1724.974 秒收窗。这是外环收尾调度失败，不能改写为视频或声音失败。原未签记录、超时和未知字段均保留。

后继 t4 明确以 addendum 复用已验证事实，提前准备 unsigned 模板与独立复核，重新取得本窗部署身份、六态、五槽、备份恢复依据和真实截图，于 590.842 秒签认、608.565 秒解锁。此结果支持调整操作顺序，不是软件提速的单变量实验。

证据：`benchmark/2026-10-20-t31-evolution-review/`、`benchmark/2026-10-20-t31-replay-02-archive/`、`benchmark/2026-10-20-t31-runtime-peer/activation-01/` 与 `benchmark/2026-10-20-t31-video-seal-final/`。

## 处置

开窗前准备签认结构、不可变实证引用、复用范围和 peer 接线。窗口内补齐实际身份、状态、恢复绑定并及时签认；长报告和远端归档置于实际决定和 close 之后。错过截止就保留未签结果并恢复，禁止倒签或重置窗口起点。

恢复 Timeout/OverrideTimeout 为本板开窗前实测原值后，紧接截图与身份核验，避免短超时使最后截图变成锁屏。T31的5cd原值为10000/10000，T33的61b原值为30000/86400000，不能照搬。该调整不要求重复已通过的播放周期，也不补造逐片声音确认。

后继T32实际516.600秒收窗；T33在325.997秒签认、326.466秒收窗，均前置签认结构、保留恢复依据并把远端归档后置。这些不同任务支持操作顺序可复用，不构成单变量提速证据。见 `benchmark/2026-10-20-t32-host-page-accepted/`、`benchmark/2026-10-20-t33-demo61b-host/accepted/`。

派单后的连续跟进是相关调度问题，另见EVO-0152：两车道先后完成而外环未及时复验。不得把它虚算成本记录新的“迟签”复发次数。正ACK与负blocked/idle哨须维持到实际交件采认并发送回执；报告已写不等于窗口已签，车道idle也不等于交件已采认。

## 未完成

目前是经真实后继窗口支持的操作规则，尚未自动阻止所有迟签。保持 open，不能因一次成功就宣称已消除复发。
