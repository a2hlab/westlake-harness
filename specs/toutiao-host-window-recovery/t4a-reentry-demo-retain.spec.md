spec: task
name: "Retain verified ordinary reentry for tomorrow's demo"
inherits: project
satisfies: [REQ-TTHOST]
depends: [t3-native-window-validation]
tags: [native, demo, partial-delivery, human-review]
---
## 意图
优先把已经实测可操作的头条重开修复留在61b演示机，满足用户明天演示的紧急要求。这个阶段交付与t4完整音视频封板分别记账，不修改t4验收条件，不把无法实听当作声音通过，也不因听音缺证恢复已证明白屏的旧件。
## 已定决策
- 前置为t3实际三阶段图审、触控和内容验证通过且精确回滚闭窗；外环固定执行计划和唯一写者后才能留板。仅61b0657200000000000000000324012c，candidate3291f76db0945f90b402ea61b14c3a912efbeecec9e0422af1a92fec95b8a819；baseline b0e5602a97133ebb1dca12972a8931a86528322685a211bb1a7a0a2185fefbd4。不重新编译、不修改运行时，只复用t3已核单库发布/恢复与身份检查。
- 写前只读准入、唯一锁、原像SHA及metadata、系统8ab非目标指纹和原电源值；fresh无child时只沿t3具名同boot同对象维护例外，固定最新实际恢复来源SHA，持锁后重核，不把历史maps称为当前映射。
- 同一候选至少两个不同普通软件boot，各自证实际child加载候选；每boot完成桌面单击首开、Home同host返回、Recent正常关闭自有卡片后单击新host旧child重开。每阶段一次图标点击，120秒内观察真实feed；三阶段合计须有实际滑动和点击内容后的真实画面变化。第二boot阶段不得因标签前缀漏掉samehost/recreated身份断言。
- 图审由专职外环实时审核员根据实际jpeg及对应SHA写独占回执；锁屏/Recent使用swipe字段、feed使用touch_kind及touch_coordinates，回执消费前校验字段，缺字段报告具体图审错误而不称应用失败。图审超时保留实际时间与遗漏，不修改原件补造当时通过。
- 尽量沿现有截图与只读日志采视频画面推进和音频提交证据；每项分别绑定候选SHA、boot及播放时段。无实际音频可观测通路时speaker_audio=pending，只有接口状态不记声音通过。未完成音视频验收时只记retained_reentry_validated_av_pending，t4完整封板及REQ-TTHOST最终完成仍pending；不得宣称sealed、全部行为保留或物理断电通过。
- 两boot三阶段通过且无已观察的功能回退，核最终候选实际maps/SHA、非目标件、原电源和最终图审后保留候选、保存精确可执行回滚依据并释放锁。观察到实质失败/身份漂移/未知写结果则停止新动作，按t3既有方法恢复精确baseline、核实际映射并闭窗；纯音频缺证不等于已观察音频失败。
- 每窗900秒停新实验、1200秒前开始恢复或成功闭窗核验、1800秒内释锁；允许分两个独立窗口，各自有准入/闭窗回执，未完成两boot不得记录上述留板资格。raw argv/start/end/rc/stdout/stderr与图片持久归档，公开材料脱敏。收据测试仅验证记录一致性，不代替真实设备图审。
## 边界
### 允许修改
- benchmark/2026-10-24-native-host-window-recovery/demo-seal/reentry/**
- tools/spec-checks/tests/host_window_reentry_retain.rs
### 禁止
- 修改t3/t4原始记录及验收、运行时实现、其他板、系统库、HAP/JAR/APK数据、网络、权限、冻结注册表、停止控制器或执行器；未经外环固定计划的设备写入；物理断电和推送。
## 验收标准
场景: 两boot可操作重开留板
  审核: human
  测试: host_window_reentry_retain_receipts
  假设t3已实际通过回滚闭窗且两boot各三阶段有正确身份及真实操作画面
  当核最终候选实际映射非目标电源回滚依据和释锁
  那么保留候选并记录retained_reentry_validated_av_pending且逐项列音视频实测程度而t4完整封板仍pending
场景: 前置或真实图审缺失
  测试: host_window_reentry_retain_receipts
  假设t3未实际通过或只有静态帧或图审超时或回执字段错误
  当核准入或阶段证据
  那么拒绝该阶段通过且不以fixture或迟到回执代替真实操作并保留具体原因
场景: 第二boot身份断言必须执行
  测试: host_window_reentry_retain_receipts
  假设第二boot阶段名带前缀而samehost换了host或recreated未换host或旧child改变
  当评审阶段绑定
  那么该阶段失败并恢复baseline而不因标签前缀绕过身份断言
场景: 音频缺证和失败分别记录
  审核: human
  测试: host_window_reentry_retain_receipts
  假设重开触控通过但当前候选声音未实听或仅有音频提交接口状态
  当记录演示留板结果
  那么speaker_audio为pending且不宣称完整封板或全部行为保留而不因该缺证自动回滚
场景: 实质失败或窗口超时
  测试: host_window_reentry_retain_receipts
  假设观察到功能回退或身份漂移或未知写结果或到900秒仍需新增试验
  当结束实验
  那么停止新增并按原像恢复及1200和1800秒边界闭窗且恢复失败明确recovery_required不假报释锁
## 排除范围
全量APK回归、新API冻结、随机退出根因、物理断电和完整音视频封板不在阶段交付中。t4及最终源码/API/远端交付任务仍继续，本任务不降低其通过判据。
