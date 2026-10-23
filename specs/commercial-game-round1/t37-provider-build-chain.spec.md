spec: task
name: "G37 exact provider build-chain source follow-through"
inherits: project
satisfies: [REQ-COMMERCIAL-GAME]
---
## 意图
补齐G34实际映射运行库的构建来源，优先将已命中provider-v12的unwindstack从manifest声明推进到可复核源码/配方链。此任务服务于已验证实现进入主线的要求，不代表原神首帧进展。
## 已定决策
- 输入是已入库route-provider-source-lookup结果：unwindstack d2c1cbc7仅manifest命中，sigchain6d5d5538未命中。先读已有receipt与明确producer文件引用，不重复宽泛SHA搜索；追踪至多2层生产脚本/构建记录引用。
- 仅本地已记录源树与manifest/recipe文本读取；若必需hw248文件只列精确路径与读取理由交外环，不自行SSH/Orb/ADB/HDC/REA/调试、构建或运行目标。不得重试G34调试和G36本地ADB拒绝路径。
- 将源快照SHA、实际编译命令、工具链、链接输入、原始rc0日志与最终对象SHA分列。Android.bp或provider清单不能替代实际命令与日志；对sigchain不得以ea7becd0代替6d5d5538。
- 有确定存在的可公开小源码/配方才收进card，保留来源与许可证；大对象仅持久路径+哈希。结果README/results包含完整绑定、未证步骤及下一个精确文件请求，不能生成虚构构建记录。
- 离线验证器检查引用完整性及不同sigchain SHA误绑定负例；Rust选择器转调验证器。运行结果、游戏画面仍unknown，不将来源核对宣称启动修复。
## 边界
### 允许修改
- benchmark/2026-10-23-provider-build-chain/**
- tools/spec-checks/tests/provider_build_chain.rs
### 禁止
- 设备/远程命令、构建/运行目标、调试/REA、第三方保护诊断、旧记录修改、主树修改、commit/push。
## 验收标准
场景: 生产链按实际引用推进
  测试: provider_build_chain
  假设已有provider-v12清单与明确来源引用
  当追踪最多2层本地生产文件
  那么报告逐项绑定源码配方日志对象SHA或明确unknown，不把manifest声明升级为重哈希或全源重编
场景: 不同对象不得替代
  测试: provider_build_chain
  假设sigchain记录仅有ea7becd0而目标为6d5d5538
  当验证构建绑定
  那么非零拒绝将其当成目标来源，保留实际缺口与精确下一步读取请求
场景: 源码或日志不可得
  测试: provider_build_chain
  假设本地不存在确切生产脚本或原始日志
  当输出本轮结果
  那么声明有界缺失及路径依据，不重复原搜索不运行远程命令不宣称原神启动成功
## 排除范围
原神故障诊断、Android对照重试、上板、重编部署、权限调整。
