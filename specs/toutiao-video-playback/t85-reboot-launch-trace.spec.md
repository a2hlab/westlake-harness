spec: task
name: "T85 one reboot and ordinary launch timing capture"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t84-launch-timeline-preparation]
---
## 意图
当前boot在启动拒绝后持续hold，普通点击及宿主重建均失败。以一次正常整机重启进入新的正常启动状态，同步记录一次桌面启动；优先恢复当前演示并取得新错误时间线，不声称物理断电验收或修复成功。
## 已定决策
- CC唯一执行61b0657200000000000000000324012c。先fresh锁/boot/状态/网络只读，若已有真实feed则保留不重启；否则独占新锁并记录原状态后仅允许一次标准hdc shell reboot。保存旧boot及新boot；不得清hold、清数据、改运行时或配置，不控制appspawn/guardian。
- 重启后重新读取power前像，普通解锁，自动网络最多等待180秒；设备时间只记录不修改。网络未就绪或身份不确定则停止。所有rc0须结合正文验证，Connect server failed/设备未找到/空boot视为失败不继续。准备使用已有实际验证的rec.py/UI工具，不把T84假命令包装器当设备执行器。
- 按T84本机help选择hitrace的ability/window两类别，有限30秒、4MB缓冲，输出唯一/data/local/tmp/t85-<run-id>.trace；不改trace_level、不启后台常驻。已存在别的trace会话则不覆盖，报告并停。trace启动成功后一次新鲜layout定位的桌面头条点击，记录实际argv与时段。trace若不支持则记录原文，不换模式强行继续。
- 同步只读普通WMS/ps/设备uptime/该新boot既有events与spawn输出：点击前一次、前10秒以不快于1秒间隔采样、之后30/60/120秒。每次采样都有start/end，禁止宣称就是谓词消费的瞬时输入。截图10/30/60/120；首次feed即报并保留，不追加正文或第二次点击。
- trace收尾拉回持久目录，确认本轮trace已结束，删除仅本轮生成的设备临时文件；始终在8分钟停止实验、10分钟内恢复新boot UI前power并释锁。失败返回桌面；所有原件保留，未修复则明确FAIL。若原生trace进程超时，使用help已确认的正常结束命令收尾，不盲kill。
- Codex仅离线消费新增原始回执，按T84判据区分宿主切换/新child/旧输出/新拒绝，出现明确证据立即回报。上屏须看图；本卡不做源码/内存/故障诊断，不绕任何工具拒绝。
## 边界
### 允许修改
- benchmark/2026-10-23-reboot-launch-trace/**
- 私有 $HOME/.local/share/westlake/reboot-launch-trace-20261023/**
- 独占61b一次标准重启、正常UI、有限trace及本轮临时文件和power恢复
### 禁止
- 清数据或hold、配置/运行时改动、直接服务或进程控制、其他板、网络偏好变更、源码/故障/内存/安全机制分析、重复重启/点击、永久trace参数修改
## 验收标准
场景: 新boot一次普通点击恢复信息流
  审核: human
  测试: reboot_launch_trace_receipts_review
  假设新boot身份与自动网络可核且trace支持
  当有限录制同时一次普通桌面点击
  那么绑定实际trace/状态/截图时段，真实feed供演示，结束trace恢复power释锁，不签物理断电封板
场景: 能力失败或仍无信息流
  审核: human
  测试: reboot_launch_trace_receipts_review
  假设网络不就绪、trace拒绝、命令正文失败或120秒无feed
  当触达停止条件
  那么保留失败和不确定性，不再点击或重启，完成trace与临时文件清理及power恢复释锁
## 排除范围
软件修复部署、跳过启动检查、物理供电操作、原神和全量APK。
