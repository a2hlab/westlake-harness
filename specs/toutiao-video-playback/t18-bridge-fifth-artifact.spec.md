spec: task
name: "5cd T18 bridge fifth-artifact guarded transaction"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t17-5cd-network-reuse]
tags: [5cd, bridge, rollback, human-review]
---
## 意图
从原T17执行器机械派生，在原R9四件事务中增加精确AudioTrack bridge第五件。预计移走首个致命点的key仅toutiao native_get_buffer_size_frames；只验JNI墙，不预告声音或动态播放通过。
## 已定决策
- 仅serial5cd，默认preview零设备；候选pin及production原件缺失拒执行。新outer admission须绑定执行器/候选/参数/源pins，真实boot/parent birth/mount/host/holder与bridge元数据不可用历史值替代。
- 复用原Board、fg、swap、CAS和原R9四件，机械派生脚本拒绝donor SHA漂移。bridge仅写runtime根liboh_adapter_bridge.so，原件d4fa与候选dca530逐哈希核；不写system全局路径。
- 保留1800秒窗口与600秒恢复余量。物理/private SHA和dev:inode一致、非符号链接、所有四份原件备份先验证再首次swap，原apply-plan先持久；stage和backup采用T18独立名字。
- rollback只接受本窗原apply-plan、同执行器/候选/前像/metadata；foreign拒绝，partial apply可恢复；no-parent仅物理恢复，随后freshboot与原同scope快照、真实feed仍需外环审核。
## 边界
### 允许修改
- benchmark/2026-10-20-t18-bridge-deployment/**
- specs/toutiao-video-playback/t18-bridge-fifth-artifact.spec.md
- tools/spec-checks/tests/toutiao_t18_bridge_transaction.rs
### 禁止
- 不改原T17/冻结源码，不设备操作、不推送、不操作61b、不扩播放验收。
## 完成条件
场景: 精确派生和默认预览
  测试: ttvideo_t18_bridge_transaction
  假设 原T17 donor与候选输入
  当 派生执行器并不传execute
  那么 保留原CAS函数且五件preview零设备命令
场景: 缺失候选与生产闭包拒绝
  测试: ttvideo_t18_bridge_transaction
  假设 候选pin为空或生产原件尚未冻结
  当 显式请求execute
  那么 Board创建前拒绝且无运行时写入
场景: 部分替换失败后恢复
  测试: ttvideo_t18_bridge_transaction
  假设 四份前像已备份并在bridge后人为中断
  当 使用原事务swap恢复
  那么 四原件字节恢复且foreign或符号链接拒绝
场景: 实际第五件窗口与恢复
  测试: ttvideo_t18_bridge_transaction
  审核: human
  假设 源码及生产闭包已独立审核且外环持锁
  当 实际五件部署后freshboot并读取头条JNI墙进展
  那么 只按原件认定JNI墙消失，声音播放保持独立；失败在600秒余量内原件恢复并freshboot核图
## 排除范围
- 新运行时构建、网络provider重编、随机退出归因、视频封板与API历史分级修改。
