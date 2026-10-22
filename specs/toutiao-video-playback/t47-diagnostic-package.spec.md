spec: task
name: "T47 build a disabled diagnostic-only control-file package"
inherits: project
depends: [t46-owned-guardian-diagnostics]
satisfies: [REQ-TTVIDEO]
---
## 意图
将已独验T46诊断补丁与T46-P采到的5cd真实控制文件绑定，生成可核对的6文件候选与逐件回滚原件。为下一轮定位身份拒绝子项准备；不重做T38编排，不改变恢复策略或宣称白屏修复。
## 已定决策
- 输入为T46主线候选watchdog/owner以及私有t46p-preimage-inputs-20261022的9件原件和输入清单。先逐件SHA/大小验证，只解析startup.env的固定赋值，不执行source、脚本或设备命令。
- 仅改变watchdog.sh、route-b-owner.sh、entry.sh两条精确SHA pin、members.tsv中这3个成员的SHA、startup.env中的成员SHA及STARTUP_ENABLED=0、startup.expected.sha256。输出路径保持实际既有root，boot-entry/config-common/init cfg字节不变。旧boot目录、stop、应用数据和权限不变。
- 将6件旧字节按原文件名复制到独立rollback目录，保留原SHA/stat引用。候选startup禁用，不生成授权签名、部署器、执行命令或设备编排；下一次启动必须由外环另行核验和启用。
- 原manifest另外10个成员（13减3）条目逐字保留，未采到原件的9个成员明示待部署前重新核SHA；不声称整包当前验证。输出机器可读清单，区分modified/unmodified/not_collected。
- builder使用显式输入/全新输出目录，拒绝旧输出及错SHA。原始构建argv/start/end/stdout/stderr/rc当场落持久位置；用本次真实输入构建并校验引用链。源码、补丁、输入索引与复现命令进repo，私有原始采集不公开。
## 边界
### 允许修改
- benchmark/2026-10-22-toutiao-diagnostic-package/**
- tools/spec-checks/tests/toutiao_diagnostic_package.rs
### 禁止
- 设备操作，部署/启动编排、T38内容和测试，冻结原文件、身份门、权限、进程控制、旧原件覆盖；不commit/push。
## 验收标准
场景: 精确输入生成禁用诊断包
  测试: toutiao_diagnostic_package
  假设9件真实输入与T46候选SHA吻合
  当运行实际builder并静态校验输出
  那么恰有6件候选和对应原字节rollback，entry与members与startup与expected哈希引用一致，STARTUP_ENABLED=0，未采成员保持原条目且明确待核
场景: 输入漂移拒绝
  测试: toutiao_diagnostic_package
  假设任一源SHA漂移或startup出现未知可执行语法
  当运行实际builder
  那么非零退出且不产出可部署结果，不执行输入或任何设备命令
场景: 输出冲突拒绝
  测试: toutiao_diagnostic_package
  假设输出目录已经存在
  当运行实际builder
  那么拒绝且历史输出字节不变
## 排除范围
诊断包启用/部署、回滚执行、宿主请求接线、第三方崩溃诊断、原神和白屏封板。
