# 61b 头条演示操作说明（草稿，2026-10-25）

> 草稿。板上候选是否留下、以什么状态交付，**一律以 T141 最终 result/receipt 为准**，用本目录 `check_delivery.py` 核对哈希后再由外环图审签认。本文不宣称封板。

## 已验证的三种打开（T136 v9，外环独立图审）
证据：peer 树 `device-validation/t136/.private/execute-20261025-041851-b503ee/result.json`（SHA `21a9c90d…`），`runtime_result=three_stages_outer_reviewed_usable_pending_independent_review`，验完已按设计回滚到 baseline、释锁、电源恢复。

1. **重启后首次打开**：桌面点头条图标 → 实际信息流 → 一次滑动，内容随之移动（本阶段只验证了滑动）。
2. **同宿主重进**：按 Home 回桌面，再点图标（宿主未变）→ 信息流 → 一次滑动，内容随之移动（本阶段只验证了滑动）。
3. **新宿主、旧 child 重进**：在最近任务里上划关掉头条卡片，再点桌面图标（宿主重建、应用进程沿用）→ 信息流 → 点击一篇文章，打开了正文（三阶段中只有这一阶段验证了点进文章）。

时延（**本轮观测，不是保证**）：首次打开先白屏，约 60 秒后出现信息流；重进约 5 秒。

## 演示步骤
1. 亮屏、上滑解锁（不要输入任何密码）。
2. 点一次桌面头条图标。本轮首次打开是先白屏、约 60 秒后才出信息流；等待期间**不要连点、不要重启**。若 **120 秒仍未出现信息流，记为本次未通过**并停止操作；不承诺白屏一定会恢复。
3. 上下滑动信息流，点一篇文章看正文。（应用内返回列表本轮未验证，不作承诺。）
4. 演示重进：按 Home → 再点图标；或打开最近任务、上划关闭头条卡片 → 再点图标。

## 正在验 / 待定（不要对外宣称）
- **软件重启两轮**：T141 boot1/boot2 正在由唯一写板者执行，结果未出前不宣称“重启后可用已保持”。
- **音视频**：扬声器声音与视频音画验收待定（`speaker_audio`/`video_audio_acceptance` 仍为 pending）。
- **物理断电**冷启动未验。
- **随机退出**未修：应用可能自行退出；历史上退出后再点图标曾两次重新拉起到信息流（T72 约 63 秒、T123 约 60 秒），属观测、不是保证。

## 交付核对（演示前外环执行）
`python3 check_delivery.py --manifest <manifest.json>`（模板见 `manifest.template.json`）：只核清单内 result/handoff/receipt/图片的 SHA 与 handoff 哈希链，并按原件字段报告状态，例如 `candidate_retained_av_pending`、`boot1_only_boot2_pending`、`candidate_not_retained_baseline_restored`。
它**不看图、不代替图审，永不输出 sealed**；脚本退出 0 只表示证据一致。
