spec: task
name: "T31 final playback and explicit durable retention"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t1-offline-preparation, t3-durable-recovery]
---
## 意图
将5cd实测播放验收和可恢复持久部署签认分开。沿原六态事务完成精确新部署，不重建候选，不把T30一次声音扩大为两周期声音；本稿所有现场与签认场景等待外环human审核。
## 已定决策
- 5cd是本任务明确目标，旧t3的61b目标不套用；播放标准仍为两周期20秒播放、暂停3秒、恢复10秒、退出feed/图标再入。各周期记录t0/t5/t10/t20和暂停/恢复/退出截图、内容ROI、对应Surface及声音具名回执，facts只据record实数。
- fresh只读、MAIN锁、原前像518targets八域+26supplement、fresh admission、preflight、apply五备份+ABSENT marker、单次freshboot、真实候选physical/private SHA/metadata及同child五槽接线沿T30；run按实际WID完整SHA绑定，未知或漂移拒绝。
- 签认分两件：playback-review.json记录两周期逐项结果，retain-signoff.json由outer(codex)明确approved_by/时间/5cd/OH版本/APK/六态后像/当前boot与实际身份/production与源码commit/原apply-plan及五备份和ABSENT marker持久SHA/恢复入口及其离线known-pre-post与foreign拒绝回执/恢复负责人/原power与参数恢复回执/当前候选feed。缺项拒绝签认；本地preview不能生成签字。
- 签认记录本次freshboot候选实启动证据，不承诺长期稳定性；保留原cfg及图标生命周期，不清数据。最终关闭临时awake、恢复原power10000/10000和debug缺失106；保留候选时不执行baseline rollback，按新签认释放锁。旧原件可恢复且原回滚计划永不覆写。
- recovery-only继任实现和独立离线复核须在开最终窗前就绪；该入口使用新恢复锁/1800秒预算但保留原备份权属、origin plan哈希及目标known-state。未就绪时只能短窗验证后回滚，不允许“先留候选以后补退路”。
- 从已有dynamic原件核可复用项；仍缺的最终两段听验及对应周期不能代填。若1200秒前未齐签认，立即回滚六态、freshboot、518+26比较及真实最终UI，1800秒前解锁。失败、host-only、超时必须原样记录。
- 归档先固定动态证据E→archive A→远端回执R，再独立git固定签认S；S不反写归档避免哈希循环。更新scoped操作卡/API增量，不改历史315或宣布通用API冻结。
## 边界
### 允许修改
- specs/toutiao-t31-demo-retain/**
- benchmark/2026-10-20-t31-demo-retain/**
- tools/spec-checks/tests/toutiao_t31_preview.rs
### 禁止
- benchmark/2026-10-20-t30-request-recovery/**
- knowledge/frozen/**
- 不碰61b/5ea、不排查随机退出、不声称40601000根因普遍修复。
## 完成条件
场景: 两周期有声动态暂停恢复退出
  测试: ttvideo_t31_preview
  审核: human
  假设 新5cd窗口实际身份与候选生效已核
  当 两周期分别20秒动态暂停3秒恢复10秒并退出feed图标再入
  那么 视频内容变化及暂停停止恢复推进逐图成立，两份声音确认分别指向该周期内容，facts和原件SHA完整
场景: 声音未知或UI失败拒绝留候选
  测试: ttvideo_t31_preview
  审核: human
  假设 任一周期声音unknown或仅封面控件变化或未返回feed
  当 审核最终播放结果
  那么 不能签playback通过或永久留候选，到1200秒执行原回滚且保留失败
场景: 可恢复签认后持久留候选
  测试: ttvideo_t31_preview
  审核: human
  假设 两周期通过且跨窗恢复入口已独立审核并绑定备份与原plan
  当 外环在1200秒前签署独立retain-signoff并关闭临时power和参数设置
  那么 精确六态候选成为仅5cd演示基线，记录当前真实feed和释放锁，归档R与包外S单向绑定
场景: 缺退路或超时拒绝签认
  测试: ttvideo_t31_preview
  审核: human
  假设 只有旧同窗rollback或origin备份不全或签认未在1200秒前完成
  当 窗口结束处理
  那么 不伪造旧holder/start、不延长1800秒门，按原plan恢复并如实记录超时和最终UI，不称已封板
## 排除范围
跨窗恢复继任仅在独立t3实现与离线复核；本任务不运行设备，不生成任何真人签名；不重做候选旧测试和既有REA。
