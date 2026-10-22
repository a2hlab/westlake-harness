spec: task
name: "T49 replay owned watchdog exit-between-reads without devices"
inherits: project
depends: [t46-owned-guardian-diagnostics]
satisfies: [REQ-TTVIDEO]
---
## 意图
T48实际采到capture身份读取失败后进入RECOVERING，未采到终局OWNER_REFUSED。离线复现本项目watchdog的相邻读取时序，判断源码中的退出竞态及诊断文件重名能否触发不同退出路径；不推断第三方为何退出。
## 已定决策
- 精确使用已提交T46基线和T47候选的watchdog/owner字节，复用已有T46离线回放框架。只在外部进程读数/设备动作边界注入合成数据；实际main、monitor、child_owned、rb_deny、状态记录和诊断落盘路径执行原码，不改实现来制造预期结论。
- 分别安排首次birth读取已消失、首次成功而child_owned内第二次读取失败、第二种时序且同seq已有诊断文件。记录实际调用顺序、状态、退出码、诊断内容和旧文件SHA，比较基线与候选。
- 只读数值变化不能充当读取失败；无法通过现有接缝进入实际分支就报告未覆盖，不用独立伪算法替代。保留正常身份不变对照。
- 全部输出到全新持久目录；每次真实shell回放保留argv/start/end/stdout/stderr/rc和源SHA。原日志不覆盖，checker使用显式拒绝，优化Python不能绕过检查。
- 仅报告合成可重现的源码行为，T48历史实际记录保持capture→UI_UNVERIFIED→process_exit→RECOVERING，不把它改判终局拒绝。不修代码、不上板、不改变原身份门或恢复策略。
## 边界
### 允许修改
- benchmark/2026-10-22-toutiao-owned-exit-race/**
- tools/spec-checks/tests/toutiao_owned_exit_race.rs
### 禁止
- 设备、真实进程控制、第三方崩溃诊断、REA/调试器、T38流程、冻结源文件修改、权限修改、部署；不commit/push。
## 验收标准
场景: 相邻读取退出时序实跑
  测试: toutiao_owned_exit_race
  假设基线和候选SHA均符合
  当实际main和identity代码收到三种指定的合成读取序列及正常对照
  那么逐例记录原始argv stdout stderr rc与实际trace及state，区分退出分支、终局拒绝和诊断I/O拒绝，旧诊断文件不被覆盖
场景: 错源或旧输出拒绝
  测试: toutiao_owned_exit_race
  假设源SHA漂移或输出已存在
  当运行实际回放入口
  那么非零拒绝且不改历史输出，不执行任何设备命令
场景: 未命中真实路径不报通过
  测试: toutiao_owned_exit_race
  假设trace缺少规定相邻读取或未运行实际拒绝与状态路径
  当运行结果检查器
  那么非零退出并记录未覆盖，不用源码推断替代运行结果
## 排除范围
行为修复、实板根因断言、第三方退出原因、上板窗口、白屏或视频封板。
