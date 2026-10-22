spec: task
name: "T45 correlate existing owned bridge records with T44 clicks"
inherits: project
depends: [t44-verified-desktop-observation]
satisfies: [REQ-TTVIDEO]
---
## 意图
T44已证明onCreate→onNewWant新回调，但两图仍白，第二次WMS出现头条PID22549后截图晚33秒又是宿主布局。只读既存自有桥接记录，确定实际运行代、事件链和下一修复对象，不再重复点击或重部署观察包。
## 已定决策
- 仅5cd1e3dd00000000000000000923012c，只读。先读连接、boot、板锁；若有其他写窗则停止不并发。T44 boot为8b64b087-b46f-4704-922f-d1ef36832472，已15:02:25恢复b189。新boot不混同历史。
- 不UI、不开写窗、不安装/重启/改电源、不启动停止guardian或任何进程、不执行读取的脚本。不REA/debugger/attach/内存读取，不重试T38或任何已拒操作；不分析第三方安全机制或随机崩溃根因。
- 从T44原始ps/WMS和自有源码给出的路径出发：只读/data/westlake-demo/toutiao及/data/local/tmp/operator45的浅层配置/目录名，按当前boot和实际自有进程cmdline/cwd确定真实状态目录。不得source配置、全盘find或猜一个donor就声称部署同源。/proc只读已识别自有wrapper/parent的stat、cmdline、exe和cwd链接以及系统ps/uptime；不读environ、mem或第三方私有数据。
- 在实际自有目录中读取既存events.log、spawn.txt、instance.txt、state、sequence和源码明确引用的stdout/stderr日志；缺失明确missing。保存完整小文件或有明确范围的尾部，单文件上限8MiB、总32MiB、采集限5分钟。不运行脚本产生新事件；原始本地持久保存，必要文件stat及读取前后SHA记录，动态变化标注，私有日志不公开。
- 以T44点击14:58:49/15:00:03、宿主20722/birth7773571、观察到parent20851/child22549以及恢复27648为索引，按日志自身boot/uptime/seq对齐；绑定实际脚本SHA到仓库源或标unknown。c2 WMS15:00:12和截图15:00:45不能视为同一瞬间。只称现有记录支持的启动/等待/退出/焦点阶段，不能从现存PID倒推完整历史。
- 原始每命令argv/start/end/stdout/stderr/rc持久保存。命令正文失败停止该读取、不猜工具或换权限；已获记录仍可离线分析，缺证不补造。交最小timeline.json、README、results与SHA索引，指出可验证的下一步，不写修复/运行时编排。
## 边界
### 允许修改
- benchmark/2026-10-22-toutiao-existing-bridge-evidence/**
- tools/spec-checks/tests/toutiao_existing_bridge_evidence.rs
### 禁止
- 设备零写操作；不改部署件、控制态、应用数据或权限；不commit/push。
## 验收标准
场景: 既存桥接链可对齐
  测试: toutiao_existing_bridge_evidence
  假设同boot且自有状态目录由原件绑定
  当限量只读已有事件和脚本身份并对齐T44点击
  那么时间线每项带原件路径SHA及PID/seq，不把被动JSON存在等同桥接请求，不混同采样时刻
场景: 缺失或变动
  测试: toutiao_existing_bridge_evidence
  假设目录不明、日志缺失变化、boot不一致或正文错误
  当读取与分析
  那么记录unknown和缺证范围，不扩大扫描、不运行脚本、不推断白屏根因
场景: 原始记录不全
  测试: toutiao_existing_bridge_evidence
  假设命令记录或时间无法核对
  当汇总
  那么不声明完整因果或修复成功，保留真实失败和未执行步骤
## 排除范围
修改桥接、设备部署、第三方崩溃诊断、视频声音复验、原神及封板。
