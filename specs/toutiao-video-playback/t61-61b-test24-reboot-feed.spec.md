spec: task
name: "T61 61b saved Test_2.4GHz stability gate then reboot first tap"
inherits: project
depends: [t60-61b-reboot-autonet-feed]
satisfies: [REQ-TTVIDEO]
---
## 意图
T60阶段A中已保存UpstreamLabs_Compatibility在连接后30到90秒间掉线并从扫描列表消失，未进入重启。用户只建议过compatibility、未禁止其他已保存网络；外环按全权调度默认改用已保存UpstreamLabs_Test_2.4GHz复用T60两阶段门：先做最小网络稳定观察，稳定才做一次标准重启与桌面首点短验，用户后续回复可纠偏。
## 已定决策
- 唯一板61b0657200000000000000000324012c；fresh只读核boot f8406e45、锁、宿主HAP b18978b8、cfg/ROOT、guardian、无遗留采集任务、实际power前像及当前WiFi状态；漂移先停交外环。
- 阶段A（网络稳定门）：持board_note独占锁，经普通设置WLAN页点一次已保存UpstreamLabs_Test_2.4GHz，只连这一个SSID，不输入或读取密码、不改路由器或安全协议、不连其他SSID。连接后同一时刻保存设置页截图、完整ifconfig、/proc/net/route与WifiDevice状态；在连接后30秒、90秒、180秒各做一次只读复核并留末图。
- 阶段A判定：三次复核wlan0均有IPv4且RUNNING、路由非空才算180秒稳定；任一次掉线即记录掉线时刻、设置页显示的原因和三类状态口径，停止本卡后续动作，不重启，向用户报告准确网络阻塞。
- 阶段B（仅阶段A稳定时）：一次标准hdc target boot，记录新旧boot；就绪判断对param值去尾部空白后比较true；就绪后自动联网等待上限120秒，只读轮询wlan0/路由/WifiDevice，超时即记录缺口停止，不运行手工bootstrap、aa、guardian或启动命令。网络自动可用才从当前layout识别的桌面图标首点头条一次，30秒/120秒截图；信息流出现才点一条普通内容并用应用内返回，每步读图。重启后未自动联网则记录需手工连网络这一演示步骤并停止，不再手工连接。
- 信息流可能来自缓存，不据此宣称持续在线；文章正文成功与网络失败并列报告。不部署、不回滚、不改权限、不清数据、不杀进程、不运行T38/REA/debugger、不读environ/FD2、不研究随机崩溃；比对一律用/usr/bin/diff。
- 两阶段合计20分钟停止实验，留10分钟恢复实际power前像并读回、释锁后报告。原始argv/start/end/stdout/stderr/rc与截图SHA持久保存；人工读图回执入口未实现，不宣称lifecycle PASS、物理断电或真人触屏通过。
- 外环addendum（原30秒准入失败保留为initial_connection_pending）：首轮锁实为11:03:08–11:04:31。闭窗后只读观察到延迟连接成功；以首次connected采样11:05:10为锚，+108秒（迟于+90）与+180秒均有IPv4、RUNNING、wlan0路由，视为稳定后进入阶段B。阶段B须新开board_note锁并重取实际power前像，两阶段窗口各自20分钟停止、30分钟闭窗，不复用已关闭的锁；/proc/net/route无默认路由只记事实，不据此判断互联网不可达。
## 边界
### 允许修改
- benchmark/2026-10-23-61b-test24-reboot-feed/**
- 私有$HOME/.local/share/westlake/61b-test24-reboot-feed-20261023/**
- 持锁下61b普通设置UI连接已保存UpstreamLabs_Test_2.4GHz、阶段A稳定后一次标准软件重启、头条普通UI、截图与power前像恢复
### 禁止
- 其他板、源码、构建、部署、回滚、卸载、清数据、进程信号、权限、运行时、守护编排、T38、REA、environ/FD2、凭据读取或导出、路由器与安全协议修改、自动切换SSID；不push。
## 验收标准
场景: 网络180秒稳定后重启首点进入信息流
  审核: human
  测试: existing_61b_test24_reboot_feed_receipts
  假设fresh身份一致、本轮持独占锁且阶段A三次复核均有IPv4、RUNNING和非空路由
  当执行一次标准重启并在网络自动可用后从桌面图标首点头条
  那么保存阶段A时间线、新旧boot、重启后联网时间线、30秒与120秒截图；信息流出现才点一条内容并返回，逐步读图验收
场景: 阶段A网络掉线
  审核: human
  测试: existing_61b_test24_reboot_feed_receipts
  假设连接后30、90或180秒任一复核无IPv4、非RUNNING或路由为空
  当到达该复核点
  那么记录掉线时刻、设置页原因与三类状态口径，停止重启与头条动作，报告准确网络阻塞
场景: 重启后未自动联网或证据缺失
  审核: human
  测试: existing_61b_test24_reboot_feed_receipts
  假设重启后等待期内无地址或路由，或首点白屏、截图与power恢复有缺口
  当汇总
  那么记录需手工连网络或具体失败与unknown缺项，先恢复power释锁再报告，不重开刷成功
## 排除范围
音频视频复验、关闭进程重开、随机崩溃诊断、2048等其他APK、全量115复验、物理断电、路由器排障和部署修复。
