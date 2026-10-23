spec: task
name: "T106 current startup file identity across two boards"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t104-complete-desktop-launch, t105-launcher-identity-audit]
---
## 意图
T104的5cd单击约40秒信息流与T87的61b约90秒不是同一条件。先比较当前部署件，决定是否存在可复用的实现差异，禁止从不同板上屏时间直接归因。
## 已定决策
- Codex先离线整理T80已验证路径/哈希与T104当前进程回执，选宿主HAP、APK、ART、桥接与渲染库、BCP和boot文件组成最小清单。输出普通只读采集命令和来源，5分钟首交。不要打开T71/T74/T91停止对象，不分析随机退出。
- 外环审核清单后CC唯一设备执行者，61b/5cd仅held/boot/当前进程（可读对应PID的cmdline/maps以绑定正常已加载库的绝对路径；不读内存或environ、不做fault归因）及精确普通文件的存在、stat、SHA256读取，不改UI、电源、网络、权限、进程或部署。已有holder则停止该板；路径未知先报告，不猜目录/不批量遍历用户数据。
- 每板读采集最多90秒且全批4分钟停止，源文件不存在或超时保留unknown。Codex离线逐件比较，区分当前磁盘文件与实际映射身份，保留5cd长boot与61b失败/成功不同轮次，不能宣布单变量对照。
### 外环补充：HAP采集调用修正
- 初批保留原始失败：zsh未拆分serial/PID，使补采参数不合法，该rc0不能采认。批准一次独立T106B只读修正窗口（两板合计60秒），不覆盖初批16.8秒计时或任何旧回执。
- 用Python subprocess argv列表逐项传serial；serial必须全值白名单、PID必须fresh ps得到的纯数字且stat前后相同。宿主maps实际HAP路径经/proc/PID/root读取，stat/dev/inode夹持后SHA；不读内存，不改任何设备状态。参数验证失败即本地停止，原件写独立hap-corrected目录。
## 边界
### 允许修改
- benchmark/2026-10-23-cross-board-startup-inputs/**
- 私有 $HOME/.local/share/westlake/cross-board-startup-inputs-20261023/**
### 禁止
- 设备写入、运行时修改、源码冻结项、停止对象、应用数据、随机崩溃诊断
## 验收标准
场景: 当前部署件可比较
  审核: human
  测试: cross_board_startup_inputs_review
  假设来源和当前文件都有精确身份
  当CC只读采集后Codex比较
  那么逐件给同异和证据路径，明确是否有值得验证的实现差异且不直接归因时延
场景: 设备占用或输入不足
  审核: human
  测试: cross_board_startup_inputs_review
  假设holder冲突、路径缺失、超时或身份无法绑定
  当触发采集停止条件
  那么保留unknown和原始失败，不通过修改设备或猜测补齐
## 排除范围
改启动策略、部署、断电验收、重新统计既有时序。
