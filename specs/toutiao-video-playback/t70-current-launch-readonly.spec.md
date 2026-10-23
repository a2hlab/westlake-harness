spec: task
name: "T70 current deployed launch inputs and ordinary startup errors"
inherits: project
depends: [t69-first-launch-path-comparison]
satisfies: [REQ-TTVIDEO]
---
## 意图
补齐T69当前boot部署身份缺口，并读现成的普通启动输出，区分明确的配置/库加载/Java启动错误与原因未知的child退出。仅做已授权首启故障的普通运维核查，不重启试错或研究随机崩溃。
## 已定决策
- 限10分钟，仅61b0657200000000000000000324012c只读，先核boot与板锁，无并行写入。原始argv、stdout/stderr、rc和时间保存到私有持久目录。若已有锁则停止，不抢锁。
- 沿T68已知精确路径核HAP、两cfg、r3根watchdog与当前boot副本；最多13个明确常规文件，逐件SHA及大小，不递归散列，不读app数据树。对照已提交源码或T34/T58证据；缺少来源写unknown。不得重试此前被拒路径或变换权限上下文。
- 从我们自己的启动脚本重定向定位现有普通stdout/stderr路径，最多读取各末200行与我们自己的guardian事件。路径必须先由已有源码或已有日志证明，拒绝全盘猜测。仅归类显式缺类、缺库、权限或入口错误；不得读debugger/tombstone、内存、environ、FD2、REA或研究第三方反虚拟化/随机崩溃机制。
- 若常规日志仅显示child退出且无受控错误，明确无法归因，不以推测修复、不再上板重试；保留全部失败。远端超时后先核准确进程身份，不重复启动散列。只commit不push。
- 原始文件留私有持久目录，公开提取不含账号、凭据、个人数据的小证据；截图数量不适用。本卡人工选择器未实现，不报lifecycle PASS。
## 边界
### 允许修改
- benchmark/2026-10-23-current-launch-readonly/**
- 私有$HOME/.local/share/westlake/current-launch-readonly-20261023/**
### 禁止
- 板上写入、重启或应用重开、进程信号、应用数据、构建部署、权限工具配置、随机崩溃诊断。
## 验收标准
场景: 当前部署身份与明确普通启动错误可核对
  审核: human
  测试: existing_current_launch_readonly_receipts
  假设61b可读且没有写入任务占锁
  当核限定文件SHA并只读已知启动输出
  那么输出当前boot指纹与源码对照、原始回执哈希及明确错误证据，不改设备
场景: 来源未知或没有可归属错误
  审核: human
  测试: existing_current_launch_readonly_receipts
  假设路径未绑定、读失败、锁被占、只有child退出或达到10分钟
  当停止相应核查
  那么记录unknown和边界，不猜路径、不改变权限、不重新启动应用
## 排除范围
随机崩溃根因、第三方二进制、网络排障、关闭后重开、其他板。
