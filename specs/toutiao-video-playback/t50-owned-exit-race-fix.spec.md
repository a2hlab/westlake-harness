spec: task
name: "T50 conservative owned watchdog exit-race and repeated audit fix"
inherits: project
depends: [t49-owned-exit-race-replay]
satisfies: [REQ-TTVIDEO]
---
## 意图
T49以原码复现了monitor两次读取间退出的终局拒绝，以及同seq诊断重名导致IO_FAILED。本任务只修本项目watchdog这两个离线可复现行为，保留身份校验、真实I/O失败和原始证据；不把合成结果当实板白屏根因。
## 已定决策
- 以T47 watchdog bcae2c69与owner fc63dae9为精确输入，在新目录发布新watchdog；owner保持字节不变，历史源/冻结表不改。
- 最小范围覆盖monitor首次birth读取失败及child_owned直接first_birth与last_birth读取失败：通过新的只读退出分类函数区分目录确实消失、同birth的Z、仍存活或未知。格式错误、PID复用、权限/读取未知不能成为恢复依据；先读父proc目录确认可读可遍历，不能把不可访问路径当消失。readable malformed stat也拒绝。已有值不匹配分支一律维持原拒绝。rb_owned内部失败保持原行为并明确未覆盖。
- 分类确认退出返回独立状态3；monitor沿原process_exit→RECOVERING路径；capture记录child_exited_during_capture并让下次monitor确认；首次attach或spawn的校验退出返回START_FAILED，不假称已接管或继续launch。其余调用者逐处审计，不能把3当成功。
- 首次诊断继续使用guardian-refusal-$seq.jsonl，已存在普通文件时保留字节并使用有限独占编号槽追加记录，最多16个附加槽。旧文件/槽若是symlink或非普通文件则IO_FAILED；真实写入/读回失败、槽耗尽仍IO_FAILED且保留锁。不采用设计稿中的吞掉I/O失败建议。状态/事件持久化门禁不变。
- 复用T49实际main与身份函数回放；不替换被验证分类函数或状态分支。仅进程文件读取与真实设备动作边界用合成夹具。禁止发真实signal、启动真实进程或访问设备。保留每次argv/start/end/stdout/stderr/rc与source SHA，全新持久输出，checker显式检查在python -O下有效。
- 复审补充：分类与rb_birth使用同一RB_PROC根，确认消失前同时核对已记录parent的birth作为可见性见证；见证未知则拒绝。同birth僵尸的state/birth必须来自同一次完整stat读。确认退出不得调用rb_deny或消耗诊断槽。首次校验退出不得增加attempt/sequence或写instance。覆盖上一已提交seq已有记录时的首次校验拒绝，以及dangling symlink/目录槽拒绝；编号名属于最后已提交seq，记录自带phase/pid/birth。
- 候选复审补充：monitor首次birth读取失败也必须调用同一退出分类器，避免不同birth僵尸绕过新校验；缺目录确认后再读取父proc列表，仍需正见证。分类子shell使用明确exit状态或提供目标shell证明。分类结果gone/zombie及发生阶段须留可检查证据，诊断slot0与原版同一拒绝的字节一致。
## 边界
### 允许修改
- benchmark/2026-10-22-toutiao-owned-exit-fix/**
- tools/spec-checks/tests/toutiao_owned_exit_fix.rs
### 禁止
- 设备或真实进程控制、第三方崩溃分析、REA/调试器、T38路径、部署、权限修改、历史/冻结源覆盖、commit/push。
## 验收标准
场景: 确认退出进入原恢复路径
  测试: toutiao_owned_exit_fix
  假设精确原版和新候选及合成进程文件
  当实跑正常对照、首次已消失、first_birth前消失、last_birth前消失及同birth僵尸
  那么新候选正常路径不变且确认退出进入原RECOVERING路径且诊断文件集不变，原版对照仍显示T49原结果，尝试预算与stop行为不变
场景: 未知或身份变化不能放行
  测试: toutiao_owned_exit_fix
  假设目录存在但stat不可读或畸形、父目录不可访问或parent birth见证失败、不同birth僵尸、活PID birth变化或ppid不匹配
  当执行实际分类与child_owned路径
  那么维持非零拒绝且没有signal或再次launch，不能把未知或复用当退出
场景: 诊断重名与真实写失败分离
  测试: toutiao_owned_exit_fix
  假设同seq已有旧诊断、已占附加槽、symlink目标或16槽耗尽
  当实际持久化拒绝记录
  那么正常重名选新槽且旧文件SHA不变并保留原身份拒绝码，危险路径或真实写失败或耗尽仍IO_FAILED并保留锁，绝不覆盖或跟随链接
场景: 所有直接调用者处理退出状态
  测试: toutiao_owned_exit_fix
  假设首次接管与capture分别遇到直接birth读取后确认退出
  当运行实际调用路径
  那么首次校验为START_FAILED且attempt与sequence与instance不变，不继续接管，capture为退出诊断而后monitor重新确认，不增加重试次数或改变父进程
场景: 错源旧输出与缺证据被实际入口拒绝
  测试: toutiao_owned_exit_fix
  假设源SHA漂移或输出已存在或实际trace缺少分类证据
  当普通Python与优化Python执行检查入口
  那么非零退出且历史输出不变，未运行的分支不记通过
## 排除范围
rb_owned内部所有read-error分类、第三方退出原因、设备根因证明、上板、白屏修复与封板签认；留待本候选独立复验后另立窗口。
