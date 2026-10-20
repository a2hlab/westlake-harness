spec: task
name: "T30 resource-free request failure recovery"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: []
---
## 意图
使本次无资源Request失败保留原错误返回，同时不把后续合法lock永久锁死。预计移走toutiao切换后连续-16这一已实测持续阻断，不宣称解释或修复首次40601000。
## 已定决策
- 最小恢复谓词为request_called且request_rc非零、buffer/native均NULL、mapped为0、fd为-1，H/N/M/U/F/B均未调用；不根据错误码名称单独推断所有权。
- fd非-1、已返回buffer、已Map或任何cleanup失败均沿旧保守保留路径；即使Abort成功也不在本轮扩大恢复范围。若后续需要放宽fd条件，先补准确provider资源契约与用例并修订本规格。
- 无资源分支返回原规范化错误并保留raw rc；R15本次Request reservation、R14 reservation释放、R26 token恢复到原可用状态、pair额外owner ref恰好释放一次。R26既有geometry/cache常驻ref不误删；正常后续调用可重新Request，当前调用只Request一次。
- 原T29诊断预算/regular-file sink及errno纪律保留。引用释放失败不冒报恢复成功，也不强制清空未知ownership；用真实owner返回值覆盖这一边界。
- 必须另派生真实provider_adapter.c：在lower Request返回并重获a->mu后、尚未自行设置uncertain/failed之前核本次idx仍RESERVED且window相等，既有failed/uncertain及其他调用、suppressed、adapter_error均无污染；只有lower rc非零、bNULL、fd为-1才可清本次record。不得按窗口重新挑record，不清并发污染记录，不改变返回原lower rc。
## 边界
### 允许修改
- benchmark/2026-10-20-t30-request-recovery/**
- benchmark/2026-10-20-t30-contract-peer/**
- specs/toutiao-t30-request-recovery/**
- tools/spec-checks/tests/toutiao_t30_recovery.rs
### 禁止
- benchmark/2026-10-20-t29-window-observation/**
- benchmark/2026-10-20-t26-yv12/**
- knowledge/frozen/**
## 完成条件
场景: 无资源失败后同一对象下一次成功
  测试: ttvideo_t30_request_recovery
  层级: integration
  替身: 外部OH Request故障注入和有效owner，真实派生pair/R14/R26
  假设 同一wrapper和OH的第一次Request返回40601000且bufNULL与fd为-1，第二次提供合法buffer
  当 通过真实lock入口顺序调用两次再unlock
  那么 第一次返回原错误且raw40601000不变，H/N/M/U/F/B调用数0、retained0，第二次可Request并成功Map与Flush，不因旧FAILED返回-16
  并且 第一次额外owner ref释放一次，第二次按原成功路径配平，不删除原cache引用
场景: 重复无资源失败与并发reservation
  测试: ttvideo_t30_request_recovery
  假设 注入至少两次无资源失败及两个线程竞争同一OH的wrapper别名
  当 运行真实实现并用受控barrier交错Request和slot释放
  那么 每个进入provider的lock仅调用一次Request，未拥有reservation的线程不得清除别人的slot，失败后可用而非耗尽8槽或增加引用
场景: 有资源和未知cleanup保持保守保护
  测试: ttvideo_t30_retained
  层级: integration
  替身: 外部provider分别返回buffer或fd并注入close/Unmap/Abort/Flush错误
  假设 Request失败带非NULLbuffer、fd非-1、或后续已持有资源、或cleanup失败
  当 真实lock或unlock走失败路径
  那么 原首错与cleanup raw rc保留，retained1及原FAILED保护不清除，不重复Abort或释放不明owner，也不自动再次Request
场景: R15本次失败与并发污染明确区分
  测试: ttvideo_t30_retained
  层级: integration
  替身: 阻塞真实adapter lower Request的外部provider与pthread barrier
  假设 lower Request在途时同一record可能被并发非法Flush或Abort经deny标记failed
  当 lower返回非零且bufNULL与fd为-1并重获adapter mutex
  那么 未污染的本次RESERVED记录可清且下一次调用到达lower；被并发污染的记录保持保护且后续不得被当作新空槽使用，首lower raw错误不被改写
  并且 无关窗口记录不变，不能将本次55行自设uncertain与调用返回前已有uncertain混为一谈
场景: owner释放失败不可伪报完整恢复
  测试: ttvideo_t30_retained
  假设 无资源失败的额外owner release返回非成功
  当 执行实际pair收尾
  那么 记录真实release结果并返回错误，不伪报引用配平或通过强制清零掩盖未释放资源
场景: 原格式成功路径保持
  测试: ttvideo_t30_success_regression
  假设 原RGBX2与偶数YV12合法输入及未知格式拒绝输入
  当 用真实派生实现运行原输出与cleanup用例
  那么 输出字节/stride/格式/alpha和provider调用顺序次数、errno及原拒绝行为不变，除指定无资源失败外不放宽retained
场景: 真机切换前后均有真实动态画面
  测试: ttvideo_t30_runtime_evidence
  审核: human
  假设 外环部署准确候选并绑定实际provider、fresh身份与恢复依据
  当 在同一受控窗口记录切换前播放和切换后播放的带时序原始截图
  那么 两侧视频ROI均呈真实内容变化且各自绑定clip与child，不能仅用进度条或日志rc0替代；失败或缺图保留FAIL或UNKNOWN，声音单独按用户实际回执判定
  并且 如果真机未出现目标Q失败，只能证明该窗切换结果，不能声称实际验证Q失败恢复；关闭后保留原六态与power恢复证据
## 排除范围
不调查随机退出，不修首次Request错误来源，不扩到所有失败可重试，不新增设备调用、部署器、永久配置、视频封板结论或API冻结升级。
