spec: task
name: "G36 Android reference first screen for the exact Genshin APK"
inherits: project
depends: [t34-locale-runtime-window]
satisfies: [REQ-COMMERCIAL-GAME]
---
## 意图
在已授权的安卓参考机上观察与G34相同官方APK的首次启动，建立画面和标准系统日志对照。对照只缩小输入及平台差异，不替代OH游戏验收或断言signal11根因。
## 已定决策
- 唯一设备为安卓N100CU025C18D000128；先只读核设备、ABI、SDK、boot、包是否存在和可用空间，再持原board_note锁；单次窗口不超过20分钟。三块OH板零写入。
- APK必须为513290344字节、SHA256 abd3c4d59217d78745a65aaa952367872354298bff5bc1ba2faae00b8f37a9cc，包com.miHoYo.Yuanshen。先从既有official输入索引定位并复核SHA，不下载替代包。若包已存在，停止安装而保留现场；不得覆盖或清数据。
- 普通adb install安装，安装失败不强制降级或改变签名。安装成功核实际package路径与版本，再一次显式启动com.miHoYo.GetMobileInfo.MainActivity；该入口为安卓Activity对照，不能声称桌面点击验收。首屏观察至多120秒，记录t5/t20及结束截图、同时间标准logcat和包进程状态。
- 不执行旧capture-genshin-golden.sh整体流程。无root、su、strace、ptrace、调试器附加、权限策略修改或REA；不清全局日志、不改系统设置、不触头条或用户数据。不登录、不购买、不点击资源下载、协议同意或授权弹层；遇弹层即记录停止。
- 运行器在启动前先落持久argv/时间记录，每条收rc/stdout/stderr，超时和失败原件保留。标准日志私有持久保存，公开仅目标包相关脱敏片段及截图；APK、账号、完整设备日志不入git。
- 结束以普通am force-stop仅停本次新安装包，核正文及进程状态并回桌面；保留已安装测试包供后续对照，不卸载用户应用。清理失败仍记录并释放本lane锁，不虚报恢复。任意拒绝不改写重试，不经其他agent绕过。
- 先交可读的命令序列、输入核验和收尾方式供外环复核，复核后执行。结果表区分安装成功、首屏、弹层、退出、超时与unknown；Android成功不等于OH成功。
## 边界
### 允许修改
- benchmark/2026-10-22-genshin-android-reference/**
- tools/spec-checks/tests/commercial_game_android_reference.rs
- .octos/boards/app-lighting.md
### 禁止
- 不改桥接运行时、冻结表、API历史、OH设备、权限设置、现有安装包或用户数据。
## 验收标准
场景: 同包普通首启形成实际画面对照
  测试: commercial_game_android_reference
  审核: human
  假设精确APK哈希与独占安卓设备已核对且该包不存在
  当完成一次安装和至多120秒普通Activity启动观察
  那么原始命令与实际截图逐一对应，报告可见首屏或明确失败，不将进程存活或安卓画面当OH成功
场景: 输入或设备不符合时拒绝写入
  测试: commercial_game_android_reference
  假设序列号错误、APK哈希漂移、包已存在或锁被占用
  当运行前置检查
  那么停止安装启动并保留原因，不覆盖旧包或修改设备策略
场景: 安装启动采图或清理失败如实保留
  测试: commercial_game_android_reference
  假设命令超时、正文错误、截图缺失或清理失败
  当结束窗口并生成结果
  那么失败原件和实际截图数保留，不输出成功验收并核对锁已释放
## 排除范围
游戏登录、资源下载、可玩验收、OH部署、动态插桩、保护绕过、T38或G14被拒操作的替代执行。
