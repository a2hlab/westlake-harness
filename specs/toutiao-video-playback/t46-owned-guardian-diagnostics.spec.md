spec: task
name: "T46 persist owned guardian refusal diagnostics without changing decisions"
inherits: project
depends: [t45-existing-bridge-evidence]
satisfies: [REQ-TTVIDEO]
---
## 意图
T45实证当前5cd guardian退出而详细拒绝原因无持久落点。先在独立候选中修复自有桥接诊断缺口，使下一正常生命周期验证能区分birth变化与具体owner检查失败；本卡不改变恢复策略，不宣称修复白屏。
## 已定决策
- 来源必须是实际部署watchdog SHA2b635ef1ea9e00546e1306b0fe6872a415a8c7d5653e19f9fb42fca04386db4a和route-b-owner SHA6bce7c3c8f84ad1047313c5dd76bcb084637d9095b9163dc710c88aaee12fe4c；从主线T45报告绑定的本地源码复制独立候选，写来源路径与git blob。
- 仅诊断差异：拆分原birth短路与child_owned失败的日志原因，保存自有审计输出至已有控制目录内受现有control_file规则约束的新文件；不覆盖历史证据，不跟随符号链接。诊断写入失败应显式失败，不允许把失败当授权。
- 保持身份检查、return值、退出与启动决策、进程操作、重试预算及调用顺序；不增加重启、接管、信号、权限、宿主请求消费或第三方检查。
- 只离线合成输入验证分支与拒绝语义，禁止读真实/proc或操作设备。不重试T38已停止的测试或编排，不使用REA/debugger，不复制其窗口代码。
- 最小交件候选源、精确补丁、README、results、SHA及有意义的分支验证。验证必须实际执行候选诊断路径，不能仅字符串断言。Rust选择器只转调本卡离线检查，不复制大套测试。
## 边界
### 允许修改
- benchmark/2026-10-22-toutiao-owned-guardian-diagnostics/**
- tools/spec-checks/tests/toutiao_owned_guardian_diagnostics.rs
### 禁止
- 设备、既有冻结源、部署文件、权限、T38代码和测试；不commit/push。
## 验收标准
场景: 两类拒绝可区分
  测试: toutiao_owned_guardian_diagnostics
  假设合成birth变化或合成owner检查失败
  当运行实际候选诊断分支
  那么原拒绝和退出值保留，持久记录分别标明birth和owner失败，不执行启动或信号
场景: 诊断路径不可写
  测试: toutiao_owned_guardian_diagnostics
  假设输出已存在或为符号链接或写入失败
  当记录拒绝
  那么显式失败，不覆盖证据、不启动、不把失败当授权
场景: 正常检查行为保留
  测试: toutiao_owned_guardian_diagnostics
  假设合成身份检查成功
  当经过候选路径
  那么继续原控制流且不产生拒绝，不新增恢复动作
## 排除范围
设备部署、白屏验收、生命周期恢复策略实现、第三方崩溃分析及原神。
