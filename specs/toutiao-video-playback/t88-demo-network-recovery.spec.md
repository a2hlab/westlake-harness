spec: task
name: "T88 restore saved demo network and verify content"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t87-current-boot-manual-reopen]
---
## 意图
T87普通重开已显示信息流，但同刻WiFi not connected、wlan0无IPv4且路由为空，内容可能来自缓存。保留现有头条进程，通过正常设置恢复用户指定的已保存网络，再验证内容加载；不将网络恢复宣称白屏软件修复。
## 已定决策
- CC唯一操作61b0657200000000000000000324012c，先只读boot/holder/power、ps与头条状态、日期、ifconfig wlan0和/proc/net/route，明确child6291是否仍在。若已有IPv4和路由则不切网。若child已退出则记录，不重启或自动重开，仍可只做网络检查。
- 独占新锁后普通UI进入WiFi设置，复用T59已验证操作与新截图/layout。只连接用户既定且界面显示已保存的upstreamlabswifi，至多一次连接；无该已保存条目就报告实际可见名称并停止，不猜密码、不删配置、不反复开关WiFi、不切其他网。已连接则保留。密码/二维码截图仅私有且不得解码或发布。
- 等待最多120秒，记录Settings连接状态与IPv4/路由；基于绝对单调截止，每命令<=20秒且受剩余预算约束。新网络地址/接口只放私有原件，公开摘要删设备MAC和不必要网络标识。
- 原child仍活时通过普通返回键回到头条，不重新点击启动图标；若出现网络错误页可普通点一次重试，否则最多一次正常下拉刷新。动作前后截图+普通ps/state，观察60秒。新内容/进程存活/截图只能证明对应程度，不能单凭列表存在证明来自网络，不播放视频或滚动其他页面。
- 若原child退出或无已保存目标，停止内容动作并保留事实；不得启动第二child、清数据、重启/配置/运行时修改、trace、读取故障转储或源码。已有真实信息流保留，不按失败默认Home打断它。
- 全窗6分钟停止实验、8分钟内恢复power前像并释锁；网络正常恢复到用户既定已保存目标可保留，不以回滚名义断开成功网络。所有argv/时段/rc/stdout/stderr持久保存并检查正文错误。关键事实即时给外环，不等长报告或commit。
## 边界
### 允许修改
- benchmark/2026-10-23-demo-network-recovery/**
- 私有 $HOME/.local/share/westlake/demo-network-recovery-20261023/**
- 独占61b正常设置UI连接既定已保存网络和回到原头条进程一次刷新及power恢复
### 禁止
- 新增或删除网络配置、密码读取/公开、其他网络、重启/进程控制/清数据/新启动、代码或运行时改动、其他设备、故障/内存分析
## 验收标准
场景: 已保存网络恢复并回到原进程
  审核: human
  测试: demo_network_recovery_review
  假设无其他holder且目标已保存或当前已连通
  当正常UI连接且记录IPv4路由并返回原头条进程
  那么记录一次内容刷新及截图实际结果、区分缓存与在线证据，保留信息流并恢复power释锁，不签冷启动封板
场景: 条件不符或连接失败
  审核: human
  测试: demo_network_recovery_review
  假设目标未保存、原child退出、120秒未连接或命令失败
  当触发停止条件
  那么不猜密码或重复连接，不新启动头条，保留失败证据，8分钟内恢复power释锁
## 排除范围
WiFi驱动修复、白屏软件补丁、进程退出归属、断电验收与原神。
