spec: task
name: "G14 installed Genshin first launch on restored baseline"
inherits: project
depends: [t13-installer-device-window]
satisfies: [REQ-COMMERCIAL-GAME]
---
## 意图
G13已在5ea安装原神并恢复原安装器，游戏尚未启动。对保留的精确应用做一次独立首启，取得真实截图和首个失败，避免重复安装或要求按需安装服务在游戏启动时一直存活。
## 已定决策
- 只用5ea34a4500000000000000001123012c；原神com.miHoYo.Yuanshen、APK abd3c4d59217d78745a65aaa952367872354298bff5bc1ba2faae00b8f37a9cc、UID20011077；G13安装/加载/恢复/闭窗原件在持久device-window/outer-plan-01与outer-window-01，必须校验实际回执，不以本契约文字当证据。
- G13于18:06:45恢复并解锁。新窗口先只读核boot、完整holder、当前bundle及安装文件身份、160项基线指纹、power和focus，捕获新前像后才写；安装器必须保持原51e1b52538b3198d2a8a3236a9479bf8512f51acc74c0d68e34acca358f39be5两份，不再部署候选。
- 安装时候选实际加载证据与启动时状态分开：保存G13 PID7798/b303100/maps inode5547/process-root SHA7c24的原件与独立审查；当前installs按需空闲退出不阻止启动已安装app，不伪造当前loader观测。APK/bundle或runtime漂移则拒绝。
- 复用现有bms_batch.collect_app(...launch_only=True,reinstall=False)与已验截图/日志入口，优先现成CLI，不复制新执行框架。不调用bm install/uninstall、不修改数据、不拉起安装服务、不改运行时。先交disabled精确argv、原件pins及恢复路径，外环采认才执行。
- 只做一次桌面图标首启，采5/20/60秒截图及按实际child PID的有界hilog；读取实际图才能判上屏。登录、资源下载或同意页只记录，不代登录、不下载完整资源。失败保留首fatal和原始日志，无证据写unknown，不称可玩。
- 复用G13已验完整身份守卫与设置恢复方法，按新窗口前像恢复power/hilog等本次改动；不卸载原神。需要停止本次目标时以原安装来源、当前精确bundle/UID及实际进程身份为依据。≤30分钟，20分钟停止新增测试，源码/计划在锁外准备。
## 边界
### 允许修改
- benchmark/2026-10-21-commercial-game/installed-first-launch/**
- tools/spec-checks/tests/commercial_game_installed_first_launch.rs
- 私有$HOME/.local/share/westlake/commercial-game-20261021/installed-first-launch/**
- 外环采认后仅5ea精确计划列出的UI/日志/设置和测试目标生命周期
### 禁止
- 不动61b/5cd，不改APK/安装器/运行时/冻结项，不重装、不清用户数据、不处理安全机制绕过、不运行T38已被拒绝的操作，不push。
## 验收标准
场景: 已安装应用独立首启
  审核: human
  测试: commercial_game_installed_first_launch
  假设G13安装来源与新鲜bundle及基线指纹一致且恢复方案与新锁齐全
  当以launch_only启动并采实际截图和日志
  那么记录是否亮屏与真实首fatal，按facts原样报计数，安装服务空闲不被误判为游戏启动前提，未出现可玩证据不称可玩
场景: 对象漂移或身份缺证
  测试: commercial_game_installed_first_launch
  假设APK或bundle或UID或boot或holder或runtime与准入记录不符
  当检查计划或执行前置核对
  那么拒绝设备写入并保留具体原因，不以旧加载证据代替当前应用身份
场景: 失败和预算结束恢复
  测试: commercial_game_installed_first_launch
  假设首启失败或到达停止试验预算
  当按新窗口前像恢复并核对
  那么保留原神安装及数据，恢复本轮设置，记录原件与解锁回执，恢复成功不升级为游戏成功
## 排除范围
安装器再次实验、完整资源下载、账号登录、可玩承诺、其他板、头条被拒操作。
