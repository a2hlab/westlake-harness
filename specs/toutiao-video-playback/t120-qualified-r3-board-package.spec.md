spec: task
name: "T120 qualify immutable r3 package with current 5cd configuration"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t118-explicit-board-build-inputs, t119-board-package-dependency-identities]
---
## 意图
用已批准且字节不变的r3输入、已复验builder和当前5cd配置生成一个离线禁用候选，补齐可复现构建与回滚对照，以便外环判断是否具备实际上板条件。
## 已定决策
- Codex在自己的worktree和持久工作目录执行；T118独立24例复验通过且builder SHA冻结后才构建。批准r3源来自T34原old-suite-r3目录，先逐个匹配CHAIN manifest；任何不符停止，不使用默认未知源码。
- 仅按manifest复制和hash不变运行时输入，不打开watchdog实现或改名副本，不执行实际控制器，不重跑T71/T74/T91停止流程。只执行普通包构建包装器。
- 精确目标5cd，ROOT=/data/westlake-demo/toutiao/recovery-attempts/icon-manual-20261023-5cd-r3；UID与service取T119/T116当前证据。startup模板显式输入且禁用，父启动SHA按候选实际文件，外部JIT/request/namespace/host-spawn SHA由T119实际回执，记录各自路径和来源。
- 默认61b模板不修改，冻结runtime字节不修改；新派生ROOT/config/member/startup/entry哈希逐件列出，watchdog及其他固定实现与原批准SHA一致。不能用生成payload/recovery.cfg覆盖live init。
- 保存从命令启动时开始的stdout/stderr/argv/rc与输入/输出manifest至持久目录；输出disable/deployable=false。生成当前5cd preimage与候选的精确变更表，按当前T116初始化配置仅提出新ROOT启动argv变更，不实际写板。
- 记录未知兼容性：owner-uid仅元数据，历史61b成功不自动证明5cd行为；不得把构建rc0当白屏修复或可封板。本卡不部署，不解除任何工具审批。
## 边界
### 允许修改
- benchmark/2026-10-23-qualified-r3-board-package/**
- 私有 $HOME/.local/share/westlake/qualified-r3-board-package-20261023/**
### 禁止
- 任何设备调用、运行时实现内容分析/修改/执行、部署、停止流程
## 验收标准
场景: 固定输入且配置完整
  审核: human
  测试: qualified_r3_board_package_review
  假设r3输入SHA匹配且T118冻结测试通过，T119依赖实物已核
  当在独立持久目录构建禁用候选
  那么rc0原始执行日志与输入输出逐件哈希齐全，固定实现未变，输出仍禁用
场景: 实物或输入身份不符
  审核: human
  测试: qualified_r3_board_package_review
  假设源pin不符或缺依赖回执
  当构建前核对
  那么非零退出并保留失败记录，不替换源或用历史声明填充
## 排除范围
上板、冷启动验收、修改冻结运行时行为。
