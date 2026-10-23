spec: task
name: "T59 61b saved WiFi then Toutiao feed continuation"
inherits: project
depends: [t58-61b-boot-first-use]
satisfies: [REQ-TTVIDEO]
---
## 意图
T58在新boot f8406e45上证明头条界面可见但推荐区"网络异常"，wlan0无地址、路由表空。用户收窄验收为开机→桌面图标→信息流→点入内容；本卡只用普通设置UI恢复已保存WiFi，再在仍活的头条进程上续验信息流与内容操作。这是联网后的续验，不是新boot首点。
## 已定决策
- 唯一板61b0657200000000000000000324012c；fresh只读核boot f8406e45、锁、宿主HAP b18978b8、cfg/ROOT、头条child 7432存活、wlan0/路由与实际power前像。漂移先停并交外环，不猜当前值。
- 先只读看网络：ifconfig、路由表、WiFi列表中可见与已保存网络。持board_note独占锁后用普通设置UI（设置→WLAN）连接已明确显示为已保存的网络；不输入或猜密码，不导出凭据，不改路由器或安全协议。若连接需要SSID或密码等未提供信息，立即报告准确缺项并停止联网动作。
- 联网成功（wlan0有地址且路由非空）后，经最近任务视图或普通桌面图标回到原活头条进程，不关闭、不重启、不部署；目读确认"网络异常/重试"后点一次重试。信息流出现才点一条可识别内容、返回、滚动一次，逐步截图读图验收。
- 不重启、不关闭头条进程、不force-stop、不清数据、不部署、不改权限、不运行T38/REA/debugger、不读environ/FD2、不研究随机崩溃。UITest副作用记录，power override每次恢复。
- 20分钟停止实验，留10分钟恢复实际power前像并读回、释锁后再报告。原始argv/start/end/stdout/stderr/rc、截图SHA持久保存；凭据不入日志。另只读取run.sh当前精确字节并配对原版供离线diff，不做全树hash。
- 本卡为人工读图现场观察，测试选择器为未实现的人工回执入口，不宣称lifecycle PASS、物理断电或真人触屏通过。
## 边界
### 允许修改
- benchmark/2026-10-23-61b-saved-wifi-feed/**
- 私有$HOME/.local/share/westlake/61b-saved-wifi-feed-20261023/**
- 持锁下61b普通设置UI连接已保存WiFi、头条普通UI、截图与power前像恢复
### 禁止
- 其他板、源码、构建、部署、重启、卸载、清数据、进程信号、权限、运行时、守护编排、T38、REA、environ/FD2、凭据导出、路由器或安全协议修改；不push。
## 验收标准
场景: 已保存WiFi恢复后头条信息流
  审核: human
  测试: existing_61b_saved_wifi_feed_receipts
  假设fresh身份一致、已持独占锁且设置中存在明确已保存网络
  当经普通设置UI连接后回到原活头条并点一次重试
  那么保存联网前后网络状态、重试前后截图；信息流出现才做点入返回滚动并逐步读图，注明联网后续验
场景: 缺凭据或网络不可连
  审核: human
  测试: existing_61b_saved_wifi_feed_receipts
  假设没有已保存网络、需要输入SSID或密码、或连接失败
  当到达联网步骤
  那么停止联网动作并报告准确缺项与原始回执，不猜密码不改协议，不对头条做后续操作
场景: 恢复或证据缺失
  审核: human
  测试: existing_61b_saved_wifi_feed_receipts
  假设截图、网络状态或power恢复有缺口
  当汇总
  那么标unknown与具体缺项，先恢复power并释锁再报告，不宣称封板或断电验收
## 排除范围
关闭进程重开、随机崩溃诊断、全量115复验、物理断电、2048深度验证、原神和部署修复。
