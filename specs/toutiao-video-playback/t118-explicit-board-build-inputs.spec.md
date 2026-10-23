spec: task
name: "T118 explicit pinned board configuration inputs for package builder"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t117-existing-manual-entry-package-plan]
---
## 意图
修复现有包构建器只换serial仍隐含61b配置的问题，使目标板配置作为完整、显式、哈希固定的输入；交付代码及离线验证，不部署、不改变运行时实现。
## 已定决策
- Codex在自己的worktree修改既有generator包装器，保留原默认61b输入和行为；新配置参数必须与预期SHA成对提供，缺少或hash不符拒绝。不要通过删除旧模板校验来实现。
- 允许读取和修改builder及配置模板，不读watchdog及其改名副本实现，不重跑T71/T74/T91停止流程；运行时实现仅按既有批准manifest以SHA核验、不修改。
- 保存完整可复现argv，包含serial/root/owner-uid/service及显式模板身份。--owner-uid仅元数据须明确披露，不谎称能改运行时身份。
- T116当前配置用于列出目标绑定，STARTUP_START_PARENT_SHA必须与最终打包的实际父启动文件一致，不盲搬历史5cd值。JIT/request等外部依赖未绑定时标unknown并拒绝输出可部署状态。
- 使用隔离临时目录中的合成fixture验证输入处理，测试源码不得导入或提取停止实现；日志和实际结果保存在持久benchmark目录。先交最小代码修订及正反例，五分钟首片。
## 边界
### 允许修改
- benchmark/2026-10-19-toutiao-icon-reentry/generator/derive-candidate.sh
- benchmark/2026-10-23-explicit-board-build-inputs/**
### 禁止
- 设备操作、部署、改运行时实现、放宽冻结校验、读取停止实现或换模型重试停止动作
## 验收标准
场景: 默认输入兼容
  审核: human
  测试: explicit_board_build_inputs_review
  假设未指定新配置参数
  当离线检查原模板SHA与默认路径
  那么原校验及默认行为保持，真实运行时未执行
场景: 显式输入完整
  审核: human
  测试: explicit_board_build_inputs_review
  假设明确模板路径及匹配SHA
  当测试配置读取和argv记录
  那么所有目标配置来源可定位且完整argv被记录，不宣称板上通过
场景: 输入身份错误
  审核: human
  测试: explicit_board_build_inputs_review
  假设模板参数缺配对或SHA不符
  当运行输入校验
  那么退出非零且不产生可部署包
## 排除范围
随机崩溃修复、启动管理实现修改、实际上板验收。
