spec: task
name: "T31 activate the already verified exact candidate"
satisfies: [REQ-TTVIDEO]
depends: [t1-offline-preparation, t3-durable-recovery]
---
## 意图
将已通过Replay两同片视觉周期、暂停续播、退出feed及正常图标返回的同SHA候选，进行一次最终5cd激活与可恢复留板。用户已确认手动打开视频有声并禁止逐片重复听验；按独立接受口径附录复用18帧和声音证据，不重跑两周期，不回写旧t2或补造旧签字。
## 已定决策
- 本任务独立引用共享安全范围而不继承旧project/t2逐片听验条款；最新用户口径在activation-verified/acceptance-addendum.json。旧t2、unknown、18帧实际时间和未签回执原字节保留；Replay因1200内未签而恢复，不判视频失败。两周期为同片，不扩大所有视频/公共API冻结或随机退出修复。
- 只接受5cd1e3dd00000000000000000923012c、UID20011300和原T30六态精确SHA，shim7f8d75bbf09e28e2b57a4621f1181ff944e79e462b78707c620dd67aef0b0bcb、bridgeb0e5602a97133ebb1dca12972a8931a86528322685a211bb1a7a0a2185fefbd4；新窗fresh WID29，否则拒绝。保留executor693448及T31_BASE/exec/helpers原字节，仅以全新T31_BASE隔离输出。
- 新holder/start、fresh boot/parent/host/child/birth/UID/exe/mnt由现场读数生成。原五备份及ABSENT marker必须来自本次activation真实apply-plan及scoped admission，不能用已恢复Replay计划。fresh before518八域+26supp、六态physical/private SHA/metadata/inode、同child五槽和一次真实feed/正常icon通道必须有新回执。
- quick无uniquechild只表示selector未选中，不等于功能失败。可从同次完整ps选唯一确切包名且PPID为已核parent、UID20011300的child；随后只读stat/status/exe/mnt前后核birth/非Z非X/Tracer0/parent一致。多候选、退出或漂移拒绝绑定，旧quick错误保留；不能只靠ps补写已验证birth。
- 已验证播放不重复做两轮。五槽如player尚未映射，可按真实画面正常进入视频一次以加载，再取五槽并返回feed，不推断未映射为故障。当前出现新的功能失败须保留并停止留板签认；不以历史PASS覆盖当前失败，不清数据不杀child。
- 窗口1200秒内完成真实retain-decision与原power10000/10000、debug缺失106核对，未齐则原apply-plan回滚，600秒恢复且1800硬限。签认人outer(codex)、真实时间、责任者、当前候选身份/六态/五槽/feed、origin备份来源及已验recovery源码pin齐全才留板；live-parent/WID29恢复范围明确，dead-parent/WID漂移未知需另审。
- 原始E→archive A→远端R→包外最终S单向固定。窗口内retain-decision须及时真实签署，归档可随后完成；不得为上传等待超时，不倒签已结束窗口，不生成自动签名。
## 边界
### 允许修改
- specs/toutiao-t31-demo-retain/t4-activate-verified-candidate.spec.md
- benchmark/2026-10-20-t31-demo-retain/activation-verified/**
### 禁止
- 不改t1/t2/t3/project、T30/T31冻结执行源和原证据、运行时源码或二进制、历史API等级。
- 内环不HDC、不构建、不部署、不推送；外环串行执行既有入口，不增加工具框架。
## 完成条件
场景: 同产物复用已接受周期证据
  测试: ttvideo_t31_preview
  审核: human
  假设 Replay18帧及两周期review与用户手动有声确认逐SHA可读
  当 审核最新用户口径附录和同候选六态
  那么 复用两同片视觉周期不再索要逐片声音，旧unknown与未签字段不改，不重复两轮播放
场景: 新窗激活与真实图标通道
  测试: ttvideo_t31_preview
  审核: human
  假设 fresh身份WID29和新holder/start有效且原态前像齐全
  当 原executor完成本次scoped apply及freshboot
  那么 新六态及同child五槽匹配、正常icon后真实feed成立，备份归本次origin且原power与debug恢复
场景: selector失败但同次进程证据可复核
  测试: ttvideo_t31_preview
  审核: human
  假设 quick未选uniquechild而同次完整ps有唯一包名PPID及UID匹配行
  当 只读核该child和parent前后stat/status/exe/mnt
  那么 birth稳定及身份门通过才能取五槽，保留quick失败；缺stat或多候选或漂移拒绝准入但不虚报视频故障
场景: 来源漂移或新功能失败拒绝留板
  测试: ttvideo_t31_preview
  审核: human
  假设 任一候选SHA漂移或WID非29或缺五槽或备份来源旧窗或当前UI失败
  当 审核activation证据
  那么 不签retain且按本次原plan回滚，历史视频PASS保持原范围不覆盖当前失败
场景: 及时可恢复签认与超时退路
  测试: ttvideo_t31_recovery
  审核: human
  假设 可恢复签认材料和原power回执已齐或仍缺项
  当 到达1200秒窗口决策点
  那么 仅已真实签署者留板并释放锁，其余开始回滚1800前收口；实际时间不倒填且包外S不回写归档
## 排除范围
宿主启动页优化、不同候选验证、跨板部署、通用API冻结、随机退出调查、重复逐片听验、本轮内环设备操作。
