spec: task
name: "T119 current 5cd external package dependency identities"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t116-current-control-fingerprint]
---
## 意图
为T118显式目标配置补齐当前5cd外部依赖路径与真实SHA、宿主UID，不把startup.env里声明的SHA直接当实际文件证据。
## 已定决策
- CC唯一设备操作者，仅5cd只读，fresh held/boot/host身份，绝对时限90秒。无重启/UI/信号/写操作，61b不动。
- 先离线读取T116私有已采startup.env及既有批准部署metadata，提取JIT/namespace/host-spawn/request等字段的实际路径，不推测路径。对实际路径仅stat+sha256sum；脚本和二进制内容不读，不跟踪其他应用数据。
- 当前宿主由ps精确org.westlake.imehost确定，采/proc/PID/status的Uid/Gid及stat出生值，前后夹持；不得用历史PID直下命令。原始stdout/stderr/rc/argv持久保存；公开脱敏路径/SHA/UID和一致性表。
- 缺路径则unknown，不递归扫描。原始init及startup配置已由T116保留，不改。不得运行T71/T74/T91停止流程。
## 边界
### 允许修改
- benchmark/2026-10-23-board-package-dependency-identities/**
- 私有 $HOME/.local/share/westlake/board-package-dependency-identities-20261023/**
### 禁止
- 任何设备写、实现内容读取、部署、61b操作、未知路径扫描
## 验收标准
场景: 路径和宿主明确
  审核: human
  测试: board_package_dependency_identity_review
  假设fresh5cd可读且已采配置指定依赖路径
  当采实际stat和SHA及宿主UID
  那么输出声明SHA与实物SHA对照、前后boot和进程身份，未知项明确标记
场景: 输入不完整或超时
  审核: human
  测试: board_package_dependency_identity_review
  假设路径缺失、身份改变或90秒耗尽
  当终止采集
  那么保留原件和unknown，不写设备补齐
## 排除范围
部署、运行实现、随机崩溃归因。
