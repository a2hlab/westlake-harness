spec: task
name: "G13 repaired installer real install and first launch"
inherits: project
depends: [t9-extractor-build, t12-installer-window-prep]
satisfies: [REQ-COMMERCIAL-GAME]
---
## 意图
在5ea实际验证G09修复是否移走原神ZIP注释首个致命点，并取得安装或下一首个失败证据。优先复用按需安装服务，避免无关foundation重启；安装成功且当前运行时前提齐备时继续首启截图。
## 已定决策
- 唯一设备5ea34a4500000000000000001123012c；候选7c24bd11190b0728b81ecd958519f01c688efb2533ef26c9b7ae4eefc82151db，原件51e1b52538b3198d2a8a3236a9479bf8512f51acc74c0d68e34acca358f39be5，精确官方APK abd3c4d59217d78745a65aaa952367872354298bff5bc1ba2faae00b8f37a9cc不改。
- G09原始编译日志与源码已落主树，基线逐字及13阶段rc0；用G12 fresh-next-01、真实installs.cfg/profile和完整maps作准入输入，锁下再核身份/消费者。已观察新boot a1d869b4-69a2-40a4-937e-4860f5b54239；不得用G06旧boot/PID签认。
- 只改/system/lib64/libinstalls.z.so及platformsdk同名两个独立常规文件；持久备份原件与标签权限、恢复设置，先复核冻结门禁。无消费者且现有声明ondemand=true/run-on-create=false时不停止foundation，由真实安装按需启动SA511。
- 复用swap_installer.py apply/rollback单库manifest及G06安装、记录、恢复接口；新入口补外层boot/完整holder/预算守卫和实际loader映射inode/process-root SHA验证。不得使用原工具foundation-only verify冒充安装器加载证明；未知不算空，写前差异拒绝。
- 原始执行argv/stdout/stderr/rc/时间必须运行时记录。先交disabled精确计划和离线拒绝用例，外环审定pins/恢复链后执行；用户部署授权已存在，approved_by写outer(codex)。单窗口30分钟，20分钟停止新增试验。
- 安装返回体非零即失败，不只看hdc rc0。成功读回bundle、APK/库身份及实际loader；保留install hilog首个致命点。当前runtime有精确可恢复指纹且对照app实际上屏才首启并取5/20/60秒截图；无前提明确记启动未测，不凭存活判上屏。
- 使用现有installs按需空闲退出（profile为180秒）并观测实际退出；候选仍被加载时，仅精确服务绑定后停止installs，不kill未知PID、不停foundation、不自动重启整板。恢复两个原件、root只读及设置，loader存在时核原件加载，按需未加载则明确unobserved。保留本窗口新装应用，不删除用户数据。
## 边界
### 允许修改
- benchmark/2026-10-21-commercial-game/apk-extractor/device-window/**
- tools/spec-checks/tests/commercial_game_installer_device_window.rs
- 私有$HOME/.local/share/westlake/commercial-game-20261021/apk-extractor/device-window/**
- 外环采认后仅5ea精确计划枚举的安装器、测试应用与设置
### 禁止
- 不动61b和5cd、不改APK不清用户数据、不改旧件/冻结源码、不重编、不绕未知身份门、不未经审定写板、不push。
## 验收标准
场景: 安装墙实测和启动记录
  审核: human
  测试: commercial_game_installer_device_window
  假设源与候选pins匹配且fresh空消费者/按需声明与恢复前像齐全并持锁
  当单库替换后实际安装精确APK并读取返回体和loader
  那么记录是否越过EOCD错误及真实下一失败，安装成功才按已核runtime对照首启；stdout/stderr/rc原件齐全，截图与facts不按计划造数
场景: 准入漂移与覆盖缺失拒绝
  测试: commercial_game_installer_device_window
  假设boot或holder或alias身份漂移或maps读取失败或原始备份不符
  当执行离线负例或真实准入
  那么不改板、不把unknown当无消费者，准确输出拒绝对象
场景: 部分部署和安装失败恢复
  测试: commercial_game_installer_device_window
  假设只改了一个alias或安装失败或到达预算
  当执行恢复
  那么从独立原件恢复两个alias及设置，保留真实加载是否observed结论和失败日志，禁止把恢复成功当游戏成功
## 排除范围
完整下载资源和可玩承诺、反虚拟化、安全机制绕过、其他设备和整代运行时升级不在本次窗口。
