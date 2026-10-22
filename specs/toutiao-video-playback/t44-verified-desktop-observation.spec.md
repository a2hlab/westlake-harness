spec: task
name: "T44 observe host callbacks from a verified live desktop"
inherits: project
depends: [t41-host-observer-package]
satisfies: [REQ-TTVIDEO]
---
## 意图
完成 T43 未做到的真实桌面图标定位和自有宿主回调观察。T43 的六份翻页结果实际为相同锁屏；T32 健康记录第0页也只有照片和设置、目标在第8页，故先在原b189核准桌面和目标，再临时安装已验签观察包。
## 已定决策
- 仅5cd1e3dd00000000000000000923012c。重新只读确认boot、独占锁、b18978b875098bc66f1ee78e471ef64c7899978bf46052502c41801f168e9ff0及bundle身份。写操作前持本轮板锁；先保存电源Timeout/OverrideTimeout实际值、完整runtime/boot-image逐件SHA、宿主目录dev/inode/mode/UID/GID。复用T43已证的命令，必需文件缺失或正文报错即停止，不能用证书fingerprint替代运行时。
- UI操作也计写操作。持锁后正常wakeup，临时power-shell timeout -o 600000并核实际值，正常Home；每条uitest操作后重新设置并核实临时override，不假设uitest保留先前超时值。以当前layout和snapshot_display截图共同确认窗口/display与界面。只有无凭据的普通锁屏可采用既有bms_batch.desktop_launch中的按当前屏幕bounds推导的标准上滑；最多2次。若有PIN/password/身份验证或权限对话框即停止，不输入、不绕过。
- 真实桌面须有SwiperPage_Grid_WorkSpace节点和普通应用图标，且当前布局无ScreenLockRootComponent。SceneBoard进程名、图标数2、shell rc0均不能独立判桌面或目标缺失。先在b189定位精确AppIconCommonView_org.westlake.imehost.EntryAbility，只定位不点击；保存layout、截图及当前节点bounds。不依赖历史坐标/第8页推测。
- 允许正常桌面水平翻页：每步按当前屏幕bounds执行，之后立即采当前layout，重新核桌面/锁屏及活动页。全卡安装前后共用每方向9次、总18次额度，不随阶段重置；相同活动页标识与图标布局连续2次则停止该方向（不以全layout字节比较判同页）。锁屏/非桌面立即中止翻页，按上面的最多2次正常唤醒恢复额度重验；不能把锁屏或无效页面计入遍历。目标未定位则不安装候选，恢复电源并释锁，结论只能是本轮未定位。
- 原包目标已定位后方可正规同签名bm install -r安装T41 release-02（02f56d181fa883f96505e196570eab6ea75911fa2f1e5edab15f5180c9f19485，59008B），再核设备HAP及bundle身份。更新后重新采有效桌面和精确节点，只接受当前活动页内唯一、可见、enabled且bounds位于当前display的目标，不复用安装前坐标。
- 最多2次普通桌面图标点击：首次点击前保存已有observation/window-state或明确不存在，逐次对比实例/序号/前值，旧文件未变单列不能作新回调；首次点击后采宿主PID/birth、launch-observation.json、window-state.json、窗口与截图；然后正常Home，重新定位同一图标并第二次点击，再采同样证据。标automated_desktop_click，不冒称人工触屏；回调只说明已观察到的生命周期，不给manual_origin/eligible_for_reentry授权。
- 不使用aa start、REA、debugger，不修改权限/exported、guardian、第三方app、运行时或其他板；不重试T38或其他已被工具安全拒绝的操作。既有桥接自然反应只观察，不编排。截图/layout原件私有持久保存；公开只放必要无隐私证据和SHA。
- 从LOCK起最多20分钟实验、另10分钟恢复。若安装候选则正规恢复b189并核设备SHA、当前宿主候选实例是否仍在运行及完整前后清单/目录/身份；恢复原实际电源值并核验。安装或恢复超时/结果未知先只读核实际HAP与进程，不盲重装。恢复与释锁先于报告。每条命令在执行时保存argv/start/end/stdout/stderr/rc，锁释锁也留原始回执；采样PID只称采样时状态，未知不能报全程从未运行。
## 边界
### 允许修改
- benchmark/2026-10-22-toutiao-verified-desktop-observation/**
- tools/spec-checks/tests/toutiao_verified_desktop_observation.rs
### 禁止
- 不改历史原件、冻结实现、其他代码；不新增运行时编排器。内环不commit/push，交路径/SHA由外环复验。
## 验收标准
场景: 有效桌面点击和回调观察
  审核: human
  测试: toutiao_verified_desktop_observation
  假设本轮完整前像和锁有效且原b189当前截图与布局证实真实桌面和精确目标
  当临时更新观察包后两次重新定位并点击且逐次采证再恢复
  那么输出两次真实点击回执、回调内容或缺失分类、截图和完整恢复证据，不以工具返回码或宿主PID代替上屏验收
场景: 锁屏或目标未定位
  测试: toutiao_verified_desktop_observation
  假设当前布局含锁屏、PIN或不是有效桌面或有界翻页后未找到精确目标
  当执行桌面准入
  那么锁屏不计有效翻页、PIN不操作、无目标不安装候选，记录实际状态和task_pass=false并恢复电源释锁
场景: 运行或恢复证据不完整
  测试: toutiao_verified_desktop_observation
  假设必需前像缺失、命令正文失败、时间或原始记录缺失或恢复任一项未知
  当执行或汇总
  那么停止后续实验并按已核依据恢复，输出明确失败和unknown，不虚构连续PID证明或白屏修复成功
## 排除范围
白屏策略修复、图标注册修改、自动拉起、第三方崩溃诊断、原神、其他板与视频声音复验。
