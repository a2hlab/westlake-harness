spec: task
name: "Native host recovery evidence and mainline delivery"
inherits: project
satisfies: [REQ-TTHOST]
depends: [t4-native-demo-seal]
tags: [native, evidence, delivery, human-review]
---
## 意图
把t4实际留板结果与源码、真实构建、部署身份、截图和收据完整绑定到master，完成REQ-TTHOST的可复现交付。只在实测达到对应程度后推进API候选状态；仓内材料齐备、远端一致与设备封板是分别核验的事实。
## 已定决策
- 前置是t4两个独立软件boot与最终候选保留的真实验收；若t4失败、仅t3临时成功并回滚或仍执行阻断，本任务可整理已有材料但最终发布保持pending，不写白屏已修复。
- 固定源码/依赖/工具链/原构建argv、输入SHA和实时stdout/stderr/rc，逐项追到最终候选与设备实际映射SHA。原对象重链接不能写成全源码重编，旧build01/失败日志保留，snapshot02及后继有依据的实际版本明确区分。
- 交付t3临时窗回滚与t4最终保留的独立收据、boot及PID/birth/UID、maps dev/inode/process-root SHA、锁/时间/电源/metadata、两boot逐阶段截图与触控视频图审、候选音频输出证据及观测方式和限制、facts及精确基线恢复材料。视频画面推进与音频分别判定；音频证据绑定候选SHA/boot/播放阶段，不引用旧版本用户实听确认冒充新候选实听。优先沿已有采证通路核验，无法观测保持pending，不默认反复询问用户声音且不称全部行为保留。原件大日志/二进制使用持久归档及大小/SHA，公开仓不放凭据、用户邮箱、完整邮件头或私人工单ID。
- API进度仅对本候选追加实测证据与限制，不把lint/fixture标成实测。两条历史derive-candidate.sh引用预期c2855d54而当前0862a334的红灯单列保留，不盲替SHA，不导出恢复该历史停止对象。当前renderer因旧引用拒绝时只更新候选JSON并明确HTML/CSV待更新，不能宣称全表全绿；该已知红灯不否定有实际证据的新候选状态。
- 冻结规则仍需至少两个不同app过墙且其中至少一个t20截图亮；只有头条的两个boot不等于两个app。未满足规则不改frozen registry，不宣称公共API已冻结。
- 源码、配方、收据索引、截图和API候选记录落实际master后，由有权外环按用户明示推送；核本地master和远端master同一交付commit及清单对象SHA。仅worktree文件、内环ACK或旧远端提交不算完成。此规划任务不自行推送或远程访问。
- 原CC停止与支持链保留；最新product_bug_report_acknowledged仅为自动确认收到，execution_not_restored。只有后继真实受支持恢复证据可改变执行状态，不因交付文档修改就解除停止。
## 边界
### 允许修改
- benchmark/2026-10-24-native-host-window-recovery/evidence-delivery/**
- benchmark/2026-10-19-api-progress-update/observations.json
- tools/spec-checks/tests/host_window_native_evidence_delivery.rs
### 禁止
- 修改既有观察对象历史SHA或事实、冻结registry、renderer、停止对象或历史正文、运行时和设备、原t1/t2/t3及冻结执行计划、权限、未经明示推送。
## 验收标准
场景: 实测发布链完整
  审核: human
  测试: host_window_native_evidence_delivery_receipts
  假设t4留板已通过且源码构建部署图审与恢复原件齐全
  当核公开清单持久归档与master远端交付commit
  那么候选完整SHA与实际运行件一致且截图和输入视频画面推进及音频输出结论逐项绑定本候选证据与人工审核并且本地远端master清单一致
场景: 缺实际收据或构建错绑
  测试: host_window_native_evidence_delivery_receipts
  假设只有fixture或只重链原对象却标全源码重编或实际候选与源码构建SHA不符
  当核交付来源
  那么最终发布为pending或failed并列精确缺项且不宣布白屏修复
场景: 历史API红灯不偷换
  测试: host_window_native_evidence_delivery_receipts
  假设历史两引用仍预期c2855d54且当前0862a334导致渲染拒绝
  当追加本候选的真实观测
  那么原观察对象不变且红灯单列并允许候选JSON已更新而HTML和CSV保持pending而不冒称全表通过
场景: 未达两个app冻结条件
  测试: host_window_native_evidence_delivery_receipts
  假设仅头条两个boot通过
  当核公共API交付状态
  那么记录单app实测和未冻结且frozen registry保持不变
场景: 留板或远端发布未完成
  测试: host_window_native_evidence_delivery_receipts
  假设最终设备已回滚基线或仅有本地commit或远端master对象不一致
  当核完成状态
  那么分别报告留板未完成或发布未完成且不以文档收件代替最终交付
场景: 视觉与支持状态不升级
  审核: human
  测试: host_window_native_evidence_delivery_receipts
  假设图审缺失或候选音频无法观测或只引用旧版本实听或仅支持自动确认收到而无执行恢复证据
  当核对交付结论与公开隐私字段
  那么对应视觉或音频项保持pending_review或pending或执行保持blocked且不称全部行为保留并且公开材料不含邮箱邮件头或私人标识
## 排除范围
本轮仅规划；选择器尚未实现为pending，不实现新checker，不重做设备实验或支持邮件。parse/lint、合成用例和归档SHA均不证明实机图像内容；不从软件boot推断物理断电可靠性。
