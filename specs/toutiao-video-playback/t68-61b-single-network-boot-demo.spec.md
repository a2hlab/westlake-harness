spec: task
name: "T68 61b single preferred network boot and content acceptance"
inherits: project
depends: [t67-61b-wifi-preference-ui]
satisfies: [REQ-TTVIDEO]
---
## 意图
在T67明确自动重新连接偏好生效后，核重启自动连接同一个Compatibility网络，再验证桌面头条首点与内容返回。T66重启后换SSID且约59秒掉线，因此本次在启动头条前观察新boot网络90秒，不把网络和应用现象混为因果。
## 已定决策
- 仅61b0657200000000000000000324012c；T67结果与逐项截图必须表明Compatibility自动重连开启、其余三项关闭且锁释放。先只读核新鲜boot、锁、实际power、HAP b18978b8/cfg7b9f2c0e，无他人锁或现场操作再持独占新锁。
- 复用已验UI工具；若当前已连接Compatibility就不点网络，否则从普通设置单点已保存Compatibility一次，不输入/读取凭据。120秒未连停止；已连后30秒复核仍connected+IPv4/RUNNING才进入下一步。不得点其他SSID或改T67偏好；未知SSID不按正确网络通过。
- 一次普通软件重启，ready后普通唤醒解锁进桌面；120秒内自动连接必须通过Settings可见网络名或同boot关联日志绑定Compatibility，不进设置手工补连。关联成功后30秒与90秒采状态，若掉线立即停止。绝对deadline控制观察，不做全程抓包或改系统配置。
- 网络门通过后普通桌面头条图标首点一次，30秒与120秒截图。出现信息流后点一条普通内容、看到正文并应用内返回信息流，每步读图。白屏/退出/内容失败保存事实停止，不重开刷成功，不调查随机崩溃、不手工bootstrap/aa/guardian启动、不清数据。
- 20分钟停止实验，30分钟内恢复实际power读回并释锁。保留T67授权偏好，不将它冒充本卡变更。原始argv/start/end/stdout/stderr/rc与截图SHA持久保存；公开脱敏，实际数量据facts。只commit不push，人工回执选择器未实现不声明lifecycle PASS，不声明物理断电/真人手指通过。
## 边界
### 允许修改
- benchmark/2026-10-23-61b-single-network-boot-demo/**
- 私有$HOME/.local/share/westlake/61b-single-network-boot-demo-20261023/**
- 持锁下61b已保存Compatibility单次连接、普通重启/唤醒解锁、桌面头条与内容UI、power恢复
### 禁止
- 其他板、源码部署、构建、凭据/网络偏好/路由器/安全协议/MAC配置修改、删除网络、进程信号、T38、REA、debugger、environ/FD2、随机崩溃诊断；不push。
## 验收标准
场景: 同网络自动连接后桌面首启及内容返回
  审核: human
  测试: existing_61b_single_network_boot_demo_receipts
  假设T67偏好有逐项证据且fresh准入后本轮独占锁有效
  当一次普通重启唤醒解锁后自动连接Compatibility并保持至90秒，再桌面首点头条进入信息流、正文及返回
  那么分别保存SSID与boot、30/90秒网络证据及UI截图，恢复power释锁并报告本轮完整操作结果
场景: 网络或应用未通过
  审核: human
  测试: existing_61b_single_network_boot_demo_receipts
  假设目标网络120秒未连接、观察期掉线、SSID未知或不同、头条120秒空白或内容失败
  当到达相应停止条件
  那么保存失败且不重试、不改变配置或研究随机崩溃，恢复power释锁，不签交付
## 排除范围
关闭进程重开、随机崩溃修复、驱动/AP排障、全量APK与物理断电。
