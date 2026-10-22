spec: task
name: "T48 normal-boot window for owned recovery diagnostics"
inherits: project
depends: [t47-diagnostic-package]
satisfies: [REQ-TTVIDEO]
---
## 意图
仅把已验证的T46日志补丁放入5cd正常开机链，记录本项目守护进程拒绝恢复的具体原因，然后恢复原六控制文件。该窗口不改变身份判据或恢复策略，不处理第三方随机崩溃，不作为白屏修复或封板验收。
## 已定决策
- 使用T47精确六文件及T46-P/P2原件；候选启用、候选禁用、基线禁用和基线恢复的startup.env与expected文件分别绑定完整SHA。expected的文件SHA和其中的env SHA分列。外环在具体计划上另签本窗，历史approved_by不是本窗签认。
- 写前核5cd实际serial/boot、无他人锁、九控制及十三成员、正常ready设置链的实际cfg/script、宿主HAP/UID、runtime124/boot36、目录身份、电源值和六件权限/所有者/SELinux标签。原始日志持久保留argv/start/end/stdout/stderr/rc；正文错误不由传输rc0覆盖。
- reader隔离采用正常禁用配置后正常重启的维护态；先核新boot、disabled配置及expected的完整SHA、该boot目录未生成；由已核源码证明无法进入entry，并核无本ROOT当前boot的guardian，再切换正文文件，完整引用链最后启用，再正常重启。恢复也先进入正常禁用维护态，再恢复六原件并正常重启。不能证明隔离则不开写窗，不替换为手工服务启动、信号或清锁。
- 所有stage、backup和临时替换名全新且拒绝既存对象/符号链接，核父目录身份；逐件保留原权限、所有者、SELinux标签并读回。保留全部旧boot目录、stop、锁、审计与用户数据。rename后的inode记录新值，不假称恢复旧inode。
- 单板独占窗口最多1800秒，1200秒开始恢复，每次正常重启等待最多180秒。诊断只执行正常桌面目标图标一次，核实际候选boot拷贝和入口，再观察最多120秒；无refusal记未观察到。预算不足、未知状态、stop存在或丢回执时停止推进，先读回判明阶段，不盲重发、不清stop、不自动重试。
- 复用已有记录器、board_note、正常HDC文件传输/target boot和已验桌面入口，不新建通用部署框架。实施前交固定方案、所有SHA、回滚依据给外环复核；批准后才执行。恢复后核六原件与其metadata、十三成员、runtime/boot/宿主/目录/电源及实际启动现象，符合计划才释放锁。
## 边界
### 允许修改
- benchmark/2026-10-22-toutiao-diagnostic-maintenance-plan/**
- benchmark/2026-10-22-toutiao-normal-boot-diagnostics/**
- tools/spec-checks/tests/toutiao_normal_boot_diagnostics.rs
### 禁止
- 未经外环具体计划采认的设备写，其他板写入，T38流程或测试，已拒绝调试路径，修改init/ready参数或身份门、手工启动guardian、终止第三方进程、删除历史对象或放宽门禁；不commit/push。
## 验收标准
场景: 原始诊断与恢复证据闭合
  审核: human
  测试: toutiao_normal_boot_diagnostics
  假设外环已采认完整计划且新鲜准入全部符合
  当执行正常维护与诊断及恢复窗口
  那么完整回执绑定实际boot与各阶段SHA和原始日志，诊断结果区分已观察与未观察，恢复实际核对通过且按时解锁
场景: 准入拒绝不写入
  测试: toutiao_normal_boot_diagnostics
  假设任一输入漂移、stop存在或reader隔离不能证明
  当审核准入结果
  那么记录具体拒绝且不开始后续文件替换，不能生成成功窗口回执
场景: 不完整证据拒绝完成
  测试: toutiao_normal_boot_diagnostics
  假设回执缺实际恢复证据或原始命令记录
  当执行回执检查器
  那么非零退出，不能以离线测试或计划文本代替设备执行成功
## 排除范围
白屏修复、自动重启策略、宿主新服务、第三方崩溃诊断、原神、视频封板、其他板部署。
