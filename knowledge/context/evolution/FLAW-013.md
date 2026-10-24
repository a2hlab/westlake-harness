---
kind: context
id: FLAW-013
title: "异步页面的一张早期截图被当成最终内容响应"
repo: A2OH/westlake-harness
layers: [Verification, Measurement]
status: open
severity: S2
recurrence: 2
fingerprint: verification/early-frame-premature-content-failure
issue:
cards: [EVO-0169]
filed: 2026-10-25
---

## 复发证据

T141 的 b8eafe 与 e42601 两个不同软件boot，在关闭自有宿主后重开、单次点击文章时，第一张响应帧均不足以证明正文可用；第二张新截图才有实际正文和配图。两次没有重复点击，且boot/host/root/main身份检查保持。若按旧入口“第一帧非usable立即回滚”的条件，这两个实际可用响应都会被误拒。两篇不同文章不构成受控时延对照。

更早的 ffd0d4 只取得一张未变帧，不能追改通过。完整日志仅证明触摸到达应用并handled、新Activity RESUMED；Show无自身时戳，邻近时戳和条件估算截图区间重叠，不能倒推确切绘制时刻。

证据：`benchmark/2026-10-25-61b-reentry-delivery/` 的两组content-after/after-2原图、独立review、final-signoff；`benchmark/2026-10-24-native-host-window-recovery/demo-seal/reentry/boot1-02-click-review/` 的完整日志哈希及原始时间锚。

## 处置

当前T141入口只发送一次触摸，在原60秒观察期和900秒总操作预算内至多采8张新图。每帧有独立标签、SHA与图审，unknown或明确未变化的feed仅表示该帧未响应；只有实际changed+usable才通过。每帧之后核core身份；身份漂移、明确拒绝、观察耗尽或图审超时仍失败。不能重复点、重置期限、复用旧图或日志代上屏。

实现落于31b8a9e00b；生产方法由`ContentMultiFrame`测试覆盖迟到变化、单次触摸、时限、拒绝和身份漂移；全入口81个离线检查通过。两个真实boot完成三阶段并在332.331/299.404秒留板释锁，说明当前入口已避免这个误判，不证明所有异步页面或其他入口已覆盖。

## 未完成

保持open：规则和当前入口已修，历史工具仍保留原样，不声称全仓自动消除此类问题。完整音视频/物理断电和随机退出另记，不由这个验证工具修订代替。
