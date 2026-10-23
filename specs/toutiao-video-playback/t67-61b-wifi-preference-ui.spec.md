spec: task
name: "T67 61b ordinary WiFi auto-connect preference inspection"
inherits: project
depends: [t66-61b-awake-boot-demo]
satisfies: [REQ-TTVIDEO]
---
## 意图
T66重启前Compatibility稳定180秒，重启后自动选Test_2.4GHz并在59秒后断开。先查标准设置是否能保留所有密码而限定自动连接首选网络，不修改驱动、不盲目重启。
## 已定决策
- 唯一设备61b0657200000000000000000324012c。先只读核boot预期29d88b39、锁与实际power；漂移报告，不复用T66锁。无其他持锁和现场操作才取board_note独占锁。
- 复用普通设置UI和截图工具，只打开WLAN与已保存网络详情页，检查是否存在明确标注自动连接/自动加入开关。读取当前UI状态，不读任何配置文件、密码、二维码或分享页。若没有清晰开关则报告unsupported并停止，不点击忘记网络。
- 可修改的唯一设置：若UI明确提供开关，保存原始截图及值，把Compatibility自动连接设开，其他三项已保存UpstreamLabs、Test_2.4GHz、Guest自动连接设关；每项改后读回。先查全所需开关，任一不存在不改任何项。不得改安全协议、MAC策略、代理、IP、密码或路由器。所有开关可按前像恢复，异常立即恢复已经改过的项并逐项读回。
- 本卡不主动连接、不重启、不启动头条。已连接网络不切走。只为后继同网络重启验收准备可审查设置；不声称联网修复、退出根因或完整交付。
- 10分钟停止操作、20分钟内恢复power前像读回并释锁；截图和原始argv/start/end/stdout/stderr/rc留持久私有目录，公开脱敏。只commit不push。人工回执选择器未实现，不能称lifecycle PASS。
### 外环追加：已保存网络入口（原失败保留）
- Phase A于11:54:02闭窗，Test_2.4GHz从可用扫描列表消失，所有设置未改；这不证明已保存网络详情不存在。
- Phase B只从普通WLAN更多菜单查找明确的已保存网络/网络管理入口，不扫描系统文件。若有列表，按网络标题找四项详情，不以扫描是否可见代替保存状态；任一仍不可验证则停止。
- 这是新窗，fresh读检、新holder/start及power前像；10分钟停操作20分钟闭窗，phase A证据不能覆盖。四开关查全后才按原卡更改偏好，每项读回，失败按前像恢复。
- 所有UI坐标须先检查x/y均为有效非空数值再调用；布局可能重排，打开后核页面标题，不匹配即返回并重新取当前布局，最多一次。若菜单不存在或无法解析，保存unknown并停止，不点删除/分享/二维码。

### 外环追加：Phase C逐网络独立调整（保留A/B失败）
- Phase B菜单只有安装证书，没有已保存网络入口，窗口已关闭；但其12:00原图重新显示Test_2.4GHz。下一窗从实际可见已保存行详情逐项操作，不再重复菜单搜索。
- 本追加替代“必须四项同时查全才改”的外环限制：每个网络是独立可逆设置，读取精确标题与开关前像后即可改该项并立即读回；无行的项保留pending、不猜坐标。最多一轮四项，缺项停止，不等待扫描反复尝试。只允许Compatibility开、UpstreamLabs/Test_2.4GHz/Guest关，密码及其他配置不动。
- Phase C新锁及power前像，10分钟停20分钟闭窗。已成功调整项可保留作为演示偏好，明确逐项状态和原值，失败动作涉及该项才回滚该项；四项最终状态未全部证实则T68不能启动。原phase A/B results不可覆盖，输出新phase-c。

## 边界
### 允许修改
- benchmark/2026-10-23-61b-wifi-preference-ui/**
- 私有$HOME/.local/share/westlake/61b-wifi-preference-ui-20261023/**
- 持锁下61b标准WLAN详情UI与明确自动连接开关、power恢复
### 禁止
- 其他板、删除网络/密码、凭据/二维码读取、源码部署、构建、驱动/系统配置文件/安全协议/MAC修改、重启、头条、进程信号、REA、debugger、随机崩溃诊断；不push。
## 验收标准
场景: 四个保存网络均有明确自动连接开关
  审核: human
  测试: existing_61b_wifi_preference_ui_receipts
  假设fresh准入成功且四项普通详情UI均有可读明确开关
  当保留前像后仅开启Compatibility并关闭其余三项自动连接
  那么逐项截图读回，保留恢复路径，恢复power释锁，报告配置变更但联网未验收
场景: 无开关或操作异常
  审核: human
  测试: existing_61b_wifi_preference_ui_receipts
  假设任一开关缺失或动作返回异常
  当停止
  那么不删除网络，不改凭据，已改项按前像恢复读回，报告unsupported或failure并恢复power释锁
## 排除范围
WiFi底层修复、AP配置、启动验收、随机崩溃、全量APK、物理断电。
