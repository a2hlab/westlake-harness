spec: task
name: "T63 current61b read-only WiFi failure boundary"
inherits: project
depends: [t62-61b-demo-homepage-handoff]
satisfies: [REQ-TTVIDEO]
---
## 意图
恢复演示验收所需网络，先查清T62自动联网超时后的当前状态与日志边界。只做有界只读取证，不再凭失败截图猜原因或重复重启；为一个可验证的下一步提供依据。
## 已定决策
- 仅61b0657200000000000000000324012c；先读当前锁、boot、power、ifconfig、完整路由、WifiDevice状态及系统版本。已有他人设备任务时仅记录冲突并停止；本卡无UI、不取写锁、不重启、不连接网络。
- 优先读T59至T62已保存raw，再按实际hilog帮助支持的单一模式取一次有界WiFi/DHCP/supplicant相关日志；最多10分钟、单次命令30秒超时。保留argv、时间、stdout、stderr、rc和日志首末时间；超时与缺覆盖不当无错误。
- 不读取保存网络配置/密码、凭据、用户数据；原始日志留私有持久目录，公开仅必要去标识证据和SHA。若接口拒绝就停止该入口，不换入口绕过。不要debugger、REA、environ/FD2、T38或随机崩溃诊断。
- 结果区分未关联、认证失败、DHCP失败、路由/外网未知；只有日志对应同boot和时间才支持具体原因。没证据写unknown，列单个最小后继动作，不进行修复。人工回执选择器尚未实现，不报lifecycle PASS。
## 边界
### 允许修改
- benchmark/2026-10-23-61b-wifi-readonly/**
- 私有$HOME/.local/share/westlake/61b-wifi-readonly-20261023/**
### 禁止
- 设备写入、UI、重启、切换SSID、读取凭据、权限修改、源码运行时部署、其他板、故障注入；不push。
## 验收标准
场景: 当前网络和既有日志可读取
  审核: human
  测试: existing_61b_wifi_readonly_receipts
  假设目标身份和无冲突已确认
  当读取当前网络与一次有界日志
  那么逐项记录原始回执与时间覆盖，按关联认证DHCP路由分层，提出一个有证据的最小后继动作
场景: 日志缺失或命令超时拒绝
  审核: human
  测试: existing_61b_wifi_readonly_receipts
  假设输出不足或读取被拒绝
  当结束有界采集
  那么保留失败且缺项标unknown，不改设备或凭据，不把空日志解释为不存在错误
## 排除范围
WiFi配置修改、随机崩溃、内容操作修复、原神、全量APK复验。
