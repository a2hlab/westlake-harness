spec: task
name: "T53 source-bound normal host service interface feasibility"
inherits: project
depends: [t52-owned-exit-fix-window]
satisfies: [REQ-TTVIDEO]
---
## 意图
查明自有宿主正常图标生命周期能否调用已有合法服务接口发起桥接启动。T52只证明自然退出分类，未修复关闭重开；已有lifecycle-entry-gap指出缺少可重复请求连接，本卡补齐接口与调用者权限的真实源码证据，决定能否进入实现。
## 已定决策
- 只读源码优先：以主树8bfba21cfb及已记录的OH版本源码为输入，先本地仓库/工作区索引；如缺文件只记录精确缺口，不遍历整盘。不调用设备或远程shell，不REA，不发起任何服务请求。
- 追踪宿主onCreate/onNewWant到已有自有服务入口的候选连接：客户端公开接口、服务端处理函数、调用者身份/权限检查、注册与构建归属逐项引用路径、行、SHA/blob；最多比较3个候选。不能将observer JSON、root shell命令或仅头文件声明视为可用接口。
- 只评估现有正常权限下的能力；无受支持端点则结论为实现前置缺口，不提出改权限、身份伪装或绕过。严禁重试T38 donor/reentry部署、测试或被拒读取；本卡不修第三方退出或保护机制。
- 输出README.md与results.json，列source_refs、caller_requirements、existing_implementation、missing_parts及下一步明确判据；公共API与harness恢复控制分开。引用源必须可重哈希，未验证运行时能力标unknown。
- 一个离线验证器校验引用SHA、范围、缺口状态，负例改源SHA/缺权限依据必须拒绝READY；Rust选择器转调验证器。结果属于静态可行性，不是关闭重开验收。
## 边界
### 允许修改
- benchmark/2026-10-23-toutiao-service-interface/**
- tools/spec-checks/tests/toutiao_service_interface.rs
### 禁止
- 修改实际宿主/运行时/权限/冻结项、设备命令、服务调用、T38路径及测试、REA、第三方诊断、修改主树、commit/push。
## 验收标准
场景: 接口结论绑定真实源码
  测试: toutiao_service_interface
  假设已有生命周期缺口与版本源码
  当生成至多3个候选的静态连接表
  那么每个已知结论引用实际源码SHA及行号，客户端和服务端权限依据分别列明，运行时未验证明确标unknown
场景: 证据漂移拒绝可实现结论
  测试: toutiao_service_interface
  假设源SHA漂移或服务端权限依据缺失
  当离线验证器校验该报告
  那么非零拒绝READY并指出缺项，不能用声明或root权限代替接口能力
场景: 无受支持接口保持缺口
  测试: toutiao_service_interface
  假设受限范围没有找到完整受支持接口
  当出具报告
  那么明确缺失的组件与实现前置条件，不调用设备不改权限不宣称关闭重开修复
## 排除范围
实现/部署/上板验收、第三方退出归因、T38 donor流程、原神、扩大重试次数。
