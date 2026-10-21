spec: task
name: "T38 host reentry r4c device window"
inherits: project
depends: [t36-host-reentry, t37-reentry-peer]
satisfies: [REQ-TTVIDEO]
---
## 意图
将独立复验通过的r4c接入真实61b关闭再开路径，修复手点图标后白屏。复用T34真实部署和恢复链，先交可审的精确装配计划并做只读fresh，外环采认计划后执行单板短窗，不把离线通过当成设备通过。
## 已定决策
- 唯一设备61b0657200000000000000000324012c；r4c watchdog c73dadb3c0d6ba082c030d7c1096810129b5afec7e3aced4d896dce86e59f0e5、T37的18例函数及165项装配审查为输入。保留旧r3和失败r4，不覆盖旧证据目录。
- 首阶段只读核boot、锁、运行时/宿主/guardian与精确恢复前像，网络期待upstreamlabswifi但shell ping不代表app联网。不得重试已被安全拒绝的parent环境读取；不使用REA。不能用历史PID/birth作为fresh。
- 派生独立新ROOT，重新生成entry/members/startup/manifest/deploy-cfg/CHAIN和generation，禁止沿用r3 ROOT并覆盖原件。先保留disabled/unapproved，外环独立核绑定和回滚后才按既有授权转执行；缺证保持拒绝。
- 复用T34 W05既有持锁、单次部署、设置恢复、日志和截图工具，最多30分钟；保留视频库和用户数据，真实重开失败即记录首个拒绝/致命点并恢复原件和设置，不循环强杀未知进程。
- 验收按T37两轮正常关闭→桌面图标→feed→普通视频卡进入→20秒内容帧→暂停3秒/恢复10秒→退出再入；截图为真，不以存活/字幕/进度条当完整视频验收。区分注入点击与用户手动观察；历史音频确认沿用，不重复追问用户。
- 原始argv/stdout/stderr/rc/时间、部署前后SHA、facts与截图持久保留。执行前复核冻结门禁和锁；回滚按实际加载对象和前像复核。外环签认不冒充用户签名。
## 边界
### 允许修改
- benchmark/2026-10-21-manual-video-regression/host-reentry-window/**
- tools/spec-checks/tests/toutiao_host_reentry_window.rs
- 私有$HOME/.local/share/westlake/manual-video-regression-20261021/host-reentry-window/**
- 采认精确计划后仅对61b计划枚举对象执行部署与回滚
### 禁止
- 不访问其他板、不改APK和用户数据、不改既有冻结项和旧证据、不REA、不重试被拒读取、不push、不在缺少审定计划时写板。
## 验收标准
场景: 精确部署和重开
  审核: human
  测试: toutiao_host_reentry_window
  假设新ROOT所有pins和fresh恢复前像由外环采认且单板锁已持有
  当部署并按两轮正常关闭再开及视频步骤验证
  那么实际加载为审定版本且两轮feed和视频帧有截图与facts佐证，未验证项明确保留
场景: 不完整准入拒绝
  测试: toutiao_host_reentry_window
  假设旧ROOT或manifest漂移或身份未知或锁被占用或回滚未绑定
  当执行计划检查
  那么不写板并明确缺项，历史PID不替代fresh
场景: 实测失败恢复
  测试: toutiao_host_reentry_window
  假设新parent未启动或拒绝reason或白屏或新运行时回退
  当窗口失败或预算到期
  那么记录真实故障并按审定路径恢复旧件及设置，回读实际加载SHA和截图，不把恢复与修复混为成功
## 排除范围
随机崩溃归因、反虚拟化、原神与新音频能力不在本卡。
