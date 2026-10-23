spec: task
name: "T66 61b preserve connected network and verify awake boot demo"
inherits: project
depends: [t65-61b-saved-network-demo]
satisfies: [REQ-TTVIDEO]
---
## 意图
T65在点击切网前已自动连上Compatibility，点击UpstreamLabs后原连接断开，故不能把这次断开记自然掉线。本卡保留已经连通的网络；未连接才恢复用户建议且刚刚实证连通的Compatibility。重启后走普通唤醒解锁再点图标，避免用睡眠锁屏等待替代真实使用。
## 已定决策
- 唯一设备61b0657200000000000000000324012c。先只读核锁、boot、HAP b18978b8、cfg及实际power前像，无他人锁、无现场操作才持board_note独占锁。当前预期boot db7ebf7b，漂移则报告新状态交外环。
- 复用既有UI/截图/原始回执工具，不造新框架。每次网络写入前立即重读Settings与接口：若已有IPv4/RUNNING且Settings已连接则保持，不切网；只有未连接时普通设置WLAN页点已保存UpstreamLabs_Compatibility一次。若无该行或需密码立即停止，不读取/输入凭据、不遗忘网络、不改MAC策略、不切其他SSID。记录操作前后wlan0状态及短hilog单模式；MAC仅私有保存，公开仅same/different。
- 连接等待最多120秒，区分pending与已连接后掉线。连接成功后以首次成功为锚观察30/90/180秒，绝对monotonic deadline防累计超时；Settings截图与IPv4/RUNNING/路由交叉核对，无main默认路由不独自判互联网失败。
- 稳定后一次标准软件重启；就绪后普通唤醒、解锁进入桌面（不进入WiFi设置、不补连网络），此时开始自动联网等待120秒。分别记录boot-ready、wake/unlock、connected时刻，不能把唤醒相关性升级成睡眠根因。无自动联网立即留失败证据停止，不手动补连接刷通过；成功才普通桌面图标首点头条，30/120秒截图，出现信息流后点一条普通内容并应用内返回，逐步读图。
- 头条已退出、白屏或内容失败立即保存事实并停止；不诊断随机崩溃，不杀进程、不手工bootstrap、不执行aa/guardian启动，不改runtime或数据。正常重启不声明物理断电测试，UI自动操作不声明真人手指验收。
- 20分钟停止实验、30分钟内恢复实际power前像并读回、释锁；失败同样闭窗。原始argv/start/end/stdout/stderr/rc、截图SHA落持久私有目录，公开小证据脱敏；截图数量按facts实际计数。只commit不push。人工回执选择器未实现，不宣称lifecycle PASS。
## 边界
### 允许修改
- benchmark/2026-10-23-61b-awake-boot-demo/**
- 私有$HOME/.local/share/westlake/61b-awake-boot-demo-20261023/**
- 持锁下61b普通设置连接已保存UpstreamLabs_Compatibility、成功后一次标准重启与普通桌面/头条UI、power恢复
### 禁止
- 其他板、源码部署、构建、权限/凭据/路由器/安全协议修改、MAC策略修改、清数据、进程信号、T38、REA、debugger、environ/FD2、随机崩溃诊断；不push。
## 验收标准
场景: 稳定联网后重启首点与内容交互
  审核: human
  测试: existing_61b_awake_boot_demo_receipts
  假设fresh身份一致、本轮持独占锁且连接后180秒观察稳定
  当一次重启后普通唤醒解锁且自动联网，再普通桌面首点头条并打开一条内容再返回
  那么留同boot网络时间线及逐步截图，分别报告feed、content、return结果，恢复power并释锁
场景: 关联失败或重启后联网失败
  审核: human
  测试: existing_61b_awake_boot_demo_receipts
  假设当前未连接且目标保存网络不在列表、120秒未连接、稳定阶段掉线或重启后120秒无网络
  当到达停止条件
  那么不补密码或切网重试，留关联日志和失败截图，恢复power释锁并报告根因unknown
场景: 头条操作失败或预算到期
  审核: human
  测试: existing_61b_awake_boot_demo_receipts
  假设头条白屏退出、内容失败或到20分钟
  当保存事实
  那么停止操作、不研究随机崩溃，30分钟内恢复power释锁且不签完整交付
## 排除范围
关闭进程重开、随机崩溃修复、WiFi底层修复、全量APK、音频复验、物理断电。
