# 头条视频剩余工作估算

已读取 agent-spec-estimate 1.3.1；输入为同目录 t1/t2/t3-contract.txt，非仅按代码行数。
关键路径 t1 → t2 → t3，图标重开可并行，增加第二CC不能压缩此依赖链；来源/播放器调用链/音频Surface静态调查可以分工。

### Estimate: t1 current-route static evidence

#### Contract Summary
- **Scenarios**: 3 (1 happy + 2 exception)
- **Decisions**: 4 fixed choices
- **Boundaries**: 2 allowed paths, 1 grouped forbidden rule
- **Inherited constraints**: 6（另继承3条共享决策）

#### Module Breakdown

| # | Module | Scenarios | Base Rounds | Risk | Effective | Notes |
|---|--------|-----------|-------------|------|-----------|-------|
| 1 | 路径/来源/真实provider | S1 | 6–8 | 1.56 | 10–13 | 当前部署与namespace需匹配 |
| 2 | 缺证/网络/歧义拒绝 | S2/S3 | 2–4 | 1.56 | 3–7 | 相同证据检查模块复用 |

#### Summary
- **Base rounds**: 8–12
- **Integration**: +2 rounds
- **Verification**: +1 rounds (lifecycle retries)
- **Risk-adjusted total**: 16–22 rounds（保守取整）
- **Estimated wallclock**: 32–66 分钟（2–3 分钟/轮）

#### Risk Factors
1. 当前身份可能未采；历史stub计数不等于当前首致命点。
2. 本估算从已生成的contract计算，未以parse/lint通过当实现完成。

#### Confidence
- 中。治理、视觉与声音验收仍待完成；无本任务历史轮次可校准。

### Estimate: t2 first-blocker minimal repair

#### Contract Summary
- **Scenarios**: 3 (1 happy + 2 exception)
- **Decisions**: 4 fixed choices
- **Boundaries**: 2 allowed paths, 1 grouped forbidden rule
- **Inherited constraints**: 6（另继承3条共享决策）

#### Module Breakdown

| # | Module | Scenarios | Base Rounds | Risk | Effective | Notes |
|---|--------|-----------|-------------|------|-----------|-------|
| 1 | 复用实现和精确输入构建 | S1 | 10–16 | 1.56 | 16–25 | 前提已有可复用生产实现 |
| 2 | 漂移/假成功与API正反例 | S2/S3 | 2–4 | 1.56 | 3–7 | 源码边界绑定后再实现 |

#### Summary
- **Base rounds**: 12–20
- **Integration**: +2–3 rounds
- **Verification**: +1 rounds (lifecycle retries)
- **Risk-adjusted total**: 22–36 rounds（保守取整）
- **Estimated wallclock**: 66–108 分钟（3 分钟/轮）

#### Risk Factors
1. 解码/Surface生产链未证存在；若需从零搭建，当前估算失效，必须重新拆spec。
2. 本估算从已生成的contract计算，未以parse/lint通过当实现完成。

#### Confidence
- 低。治理、视觉与声音验收仍待完成；无本任务历史轮次可校准。

### Estimate: t3 dynamic playback and API delivery

#### Contract Summary
- **Scenarios**: 4 (2 happy + 2 exception)
- **Decisions**: 5 fixed choices
- **Boundaries**: 3 allowed paths, 1 grouped forbidden rule
- **Inherited constraints**: 6（另继承3条共享决策）

#### Module Breakdown

| # | Module | Scenarios | Base Rounds | Risk | Effective | Notes |
|---|--------|-----------|-------------|------|-----------|-------|
| 1 | 两轮硬件生命周期与回归 | S1/S2/S3 | 6–9 | 1.2 | 8–11 | 人工听验/视觉核查、单板窗口 |
| 2 | API源码构建实测映射 | S4 | 2–3 | 1.2 | 3–4 | 独立delta由外环批量出版 |

#### Summary
- **Base rounds**: 8–12
- **Integration**: +1–2 rounds
- **Verification**: +2 rounds (lifecycle retries)
- **Risk-adjusted total**: 13–19 rounds（保守取整）
- **Estimated wallclock**: 65–95 分钟（5 分钟/轮）

#### Risk Factors
1. 网络内容必须可播且非静音；板锁和61b合流排队；超过一次主要返工需重新估算。
2. 本估算从已生成的contract计算，未以parse/lint通过当实现完成。

#### Confidence
- 低至中。治理、视觉与声音验收仍待完成；无本任务历史轮次可校准。

#### Dependency Analysis
- **Critical path**: t1 → t2 → t3，共约51–77轮，163–269分钟；再加30–60分钟合流/等待/一次小返工缓冲，约3.2–5.5小时，适合向用户报“视频3–6小时，条件性估计”。
- **Parallel branches**: 图标重开主任务；视频t1下的APK调用链、源实现与部署指纹可并行，但合并结论后才放行t2。
- **Minimum serial time**: 即使3位实现者也不能把确认首阻断→构建→真板播放验收变为同时完成；板窗口仍串行持锁。
- **With 2 agents**: 图标和视频两条链重叠，总工期应取两链较长者再加61b合流，不将两者简单相加；全部任务4–7小时的外环估计只有在图标约60–100分钟、媒体已有生产实现且最多1–2个候选窗时成立。
- **Re-estimation trigger**: t1发现缺少真实解码/Surface生产或音频链实现时，不承诺上述小时范围。此时“1–2工作日”也只是风险提示，需另写实现子契约后重新估算；网络/服务拒绝不纳入代码修复倒计时。
