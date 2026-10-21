spec: task
name: "Retire a strictly exited child without weakening reentry ownership"
inherits: project
satisfies: [REQ-TTVIDEO]
---
## 意图
仅修复guardian已确认旧child退出后仍反复校验该活动身份、可能因后续同数字PID复用而永久拒绝重开的状态缺口。保留r2原件与T31视频运行时；本任务先离线实现和验证，不授权设备部署。
## 已定决策
- 精确基线watchdog.sh SHA41f1bf653f4becf3bb40a1a754f8e0c35520ce9fa6a0eb3da84c01ef96e64a28及reentry-common.sh SHA43d7b073467708770c8c69724633666e410d45581f8c0099d5098c31215e78ab已与W04部署原件匹配；实现前再次核源SHA，不修改r2。
- fresh intake实际events在uptime95记录first_read_exited及AWAITING_REENTRY，在7024记录OWNER_REFUSED child_identity；后续只读guardian4074与旧child7172均不存在。生产函数host复验已证明退役缺口机制，7024的实际PID复用/其他身份值仍UNKNOWN，不把机制复验冒充历史根因取证。
- 在新r3副本的两个strict child_exit_verdict=exited分支登记退役键(boot,seq,PID,birth)，保留原instance与历史event原字节，只追加新的有界退役事件。不得以monitor_child返回0推退役，观察上限、stop、unknown及capture失败保持原语义。
- rc_child_state仅对当前精确匹配退役键返回gone，不再查后来同数字PID；未匹配或未退役的当前child继续完整原身份校验。退役状态在真实新spawn/adopt生命周期边界清除，下一实例重新绑定并受原守卫；spawn结果不明仍原sticky hold，不允许借退休状态重试。
- 原boot/parent/lock/currentchild身份门、STOP、WMS旧窗与其他owned窗口判据保持；不得简单清child字段使旧窗检测消失，不把复用PID的陌生窗口认成owned。错误窗口/unknown仍不spawn，每个真实desktop→host边最多一次spawn，无signal/删锁/清数据。
- CC离线实施，base独立peer；复用benchmark/2026-10-19-toutiao-icon-reentry/tests/run-all.sh及其实际shell函数/seam模式，测试实际r3函数和循环，不另造模拟状态机。新Rust选择器demo61b_child_retirement是待实现薄入口，调用本目录真实shell测试；当前未实现未执行不得报通过。
- 产物含r3源码、最小diff、源SHA、原始测试argv/stdout/stderr/rc、fresh证据脱敏索引和README。精确目标文件/元数据/前后SHA、备份及回滚卡完成并由外环独立采认前禁止上板；后继设备任务另准入，不在本轮自动重启或替换既有guardian。
## 边界
### 允许修改
- benchmark/2026-10-21-t34-demo61b-video/reentry-retirement-01/**
- tools/spec-checks/tests/demo61b_child_retirement.rs
- 私有原始证据$HOME/.local/share/westlake/t34-reentry-retirement-20261021/**。
### 禁止
- 不修改candidate-payload-r2、冻结owner/exit-verdict与历史证据；不修改T31候选native/JAR/HAP、API冻结、共享runtime或主树。
- 本任务无设备命令、部署、重启、信号、清锁、清数据、网络/权限变更或推送；不诊断SIG11，不重复要求用户听音。
## 完成条件
场景: 严格退出后PID复用不终止监护
  测试: demo61b_child_retirement
  审核: human
  假设 实际r3函数已在两个严格exited分支之一记录精确退役键
  当 同数字PID出现不同birth并发生正常desktop到host边
  那么 child_state返回gone且原boot parent lock守卫仍执行，只有窗口门明确no时允许一次spawn，历史instance保留
场景: 未退役或退役键不符仍拒绝身份漂移
  测试: demo61b_child_retirement
  假设 当前child未严格退出或退役键的boot seq PID birth任一不符
  当 child出现复用或原身份拒绝
  那么 原拒绝保留且无spawn无signal，父进程boot或锁漂移仍拒绝
场景: stop上限未知与capture失败不能制造退役
  测试: demo61b_child_retirement
  假设 monitor返回0来自观察上限或stop，或退出判断unknown或capture失败
  当 运行实际monitor与reentry函数
  那么 不登记虚假退休，stop优先且未知保持原failclosed语义
场景: 旧窗口与其他owned窗口继续阻止重复启动
  测试: demo61b_child_retirement
  假设 已退役child对应旧窗口或其他owned窗口仍在或窗口读取unknown
  当 真实desktop到host边被观察
  那么 不spawn且不通过清child字段或忽略旧窗来放行，不把陌生PID复用窗口冒充owned
场景: 新实例清除退休而不丢失活动身份守卫
  测试: demo61b_child_retirement
  假设 真实新spawn或adopt产生新实例或spawn结果不明
  当 生命周期边界处理完成
  那么 新实例重新受全部原身份检查且旧退休键不适用，结果不明保持sticky hold不重试，重复host边不重复spawn
场景: 源与原始回执完整但未升级为设备通过
  测试: demo61b_child_retirement
  审核: human
  假设 实际r3 shell反例与原行为回归已运行并保存完整rc和输出
  当 独立peer核源码diff与fresh原件索引
  那么 只签离线源码范围，当前guardian无进程与历史PID复用UNKNOWN分开，未部署不声明61b新spawn或feed或视频通过
## 排除范围
- T31运行时修复、冻结身份门放宽、重建guardian架构、SIG11根因、封板验收替代、自动设备部署和原神任务。
