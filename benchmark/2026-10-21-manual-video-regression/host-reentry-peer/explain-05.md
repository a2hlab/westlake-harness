# Contract Review: T37 independent reentry and manual video acceptance review

## Intent

独立审查T36宿主重建候选，并提前准备真正桌面手点重开和视频卡进入播放的验收路径，减少实现后的串行等待。没有候选时先从生产源码建立反例，不等待空转。

## Decisions

- t1输出精确预测与待修文件清单，t2只派发已绑定的最小修复；无可归属首致命点则t1交短窗观察方案，先补证不猜修复。
- t3成功记录至少两个完整播放周期，每周期不少于20秒动态播放、3秒暂停及10秒恢复，并记录退出和重新图标进入结果。
- API表新增本次版本映射，保留历史315条证据等级；冻结仍要求两个不同app过墙，头条单应用成功不自动冻结。
- 只读T34完整payload与T35真实白屏证据，区别活child暖返回、child退出、host重建三种事件；不以暖返回成功覆盖冷重入。
- 在独立目录回放生产函数，挑战活child、PID复用、枚举失败、socket陌生listener、停止失败、inode变更和两次点击。每个结论引用精确文件/SHA/回执，不只看作者PASS。
- 验收矩阵包含正常关闭后手点图标进feed、点视频卡后动态帧至少20秒、暂停3秒恢复10秒、退出重进；agent注入点击与真实human观察分别标记，不假称人工已测，不再重复要求声音确认。
- 仅离线，不设备、不REA、不重试已拒绝环境读取，不改作者源码；20分钟首片，候选后自适应复验。

## Boundaries

**Allowed:**
- benchmark/2026-10-21-manual-video-regression/host-reentry-peer/**
- tools/spec-checks/tests/toutiao_host_reentry_peer.rs

**Forbidden:**
- 不改T36文件、冻结项、历史签认、设备和主树，不push；缺实际证据写unknown。

## Verification Summary

| Total | Passed | Failed | Skipped | Uncertain | Pass Rate |
| --- | --- | --- | --- | --- | --- |
| 3 | 3 | 0 | 0 | 0 | 100.0% |

- ✅ 生产装配独立审阅
  - test: `toutiao_host_reentry_peer`
- ✅ 不同验收范围不得互替
  - test: `toutiao_host_reentry_peer`
- ✅ 不明对象拒绝
  - test: `toutiao_host_reentry_peer`

## Coverage Matrix

| Rule | Scenario | Test | Found | Verdict | Provenance |
|------|----------|------|-------|---------|------------|
| — | 生产装配独立审阅 | toutiao_host_reentry_peer | found | pass | computational |
| — | 不同验收范围不得互替 | toutiao_host_reentry_peer | found | pass | computational |
| — | 不明对象拒绝 | toutiao_host_reentry_peer | found | pass | computational |
