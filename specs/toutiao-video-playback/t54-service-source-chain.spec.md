spec: task
name: "T54 normal host service source chain"
inherits: project
depends: [t53-owned-service-interface]
satisfies: [REQ-TTVIDEO]
---
## 意图
利用新取到的真实ability_runtime源码，解决T53缺失服务端实现的问题。给出普通UIAbility调用公开服务连接接口的实际调用链、准入条件，以及对当前自有宿主方案的可实现结论。
## 已定决策
- 输入仅为outer提供的持久源码快照、exact manifest、HEAD及本地补丁记录，T53主干0a52f405ec报告及签包元数据。源码树标签不等于板上版本绑定，必须分别列明revision、修改和版本证据。
- 跟踪公开connectServiceExtensionAbility从JS入口到服务端的实际分支、权限检查和返回值，引用文件行号及SHA；最多追两种连接路径。不依据SDK声明猜权限。
- 针对现有normal、非system的宿主，分别判断普通连接调用者、目标ServiceExtension的注册资格、目标服务自身能否承担桥接；缺一个仍是GAP。若明确被框架拒绝，写精确条件和返回值，停止该路线，不改权限不伪装身份。
- 输出最小实现前置清单。若公开现有接口不能满足，不设计绕过，不转换成T38被拒流程；区别应用内重开UI与重建桥接运行时。
- 本地只读静态分析，无设备、远程、REA或服务请求。先用rg定位真实调用者与被调者，缺文件向outer列实际include/引用，不猜路径。不得修改T53证据。
- 报告README.md/results.json及离线校验器，Rust转调。校验引用漂移、版本缺口被冒充已绑定、权限缺口被冒充READY，负例非零拒绝。
## 边界
### 允许修改
- benchmark/2026-10-23-service-source-chain/**
- tools/spec-checks/tests/service_source_chain.rs
### 禁止
- 修改运行时、宿主、权限、冻结登记、已有报告、主树、commit/push，设备及远程命令，T38路径/测试，第三方保护诊断。
## 验收标准
场景: 调用链绑定实际分支
  测试: service_source_chain
  假设outer提供带manifest和修改记录的源码快照
  当分析正常公开连接路径
  那么客户端与服务端分支引用实际源码并分列调用者准入和目标注册资格，未闭合能力标unknown
场景: 错误版本或源码漂移拒绝就绪
  测试: service_source_chain
  假设引用SHA变化或板上版本绑定缺失
  当检查器校验READY声明
  那么非零拒绝并输出具体缺口，不把目录名当版本证明
场景: 权限缺口拒绝可部署结论
  测试: service_source_chain
  假设普通调用者或目标服务不满足实际准入条件
  当出具实现判据
  那么结论保留GAP且列源码返回条件，不修改权限也不调用设备
## 排除范围
实现、构建运行时、部署、真机验收、T38重试、原神和第三方退出归因。
