spec: task
name: "T105 launcher identity and discoverability audit"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t103-spare-board-icon-observation]
---
## 意图
给CC桌面定位提供准确入口，避免安装存在被误认为图标存在。离线对照现有HAP桌面声明与T103布局，不重复已完成的启动时间分析。
## 已定决策
- Codex只读已有T103私有raw和T89已绑定HAP源，提取bundle、ability、launcher skill、label、图标资源和已检查页范围。引用实际文件与SHA；目标动态bounds只能由CC新布局确认。
- 五分钟首交，可先把入口结论直接通知外环；如静态不足则明确缺口，不虚构图标缺失根因。不运行REA、不上板，不读取T71/T74/T91停止对象。
- 有确定manifest缺陷才提出独立候选及构建入口；本任务不构建部署。已有代码满足时明确无修改建议。
## 边界
### 允许修改
- benchmark/2026-10-23-launcher-identity-audit/**
### 禁止
- 设备操作、应用数据、运行时修改、已停止对象、权限配置
## 验收标准
场景: 现有入口可绑定
  审核: human
  测试: launcher_identity_audit_review
  假设现有HAP和布局都有完整来源
  当对照桌面skill和目标标识
  那么给出可供新布局定位的精确bundle与ability和引用证据，不复用旧坐标
场景: 数据缺失或身份不符
  审核: human
  测试: launcher_identity_audit_review
  假设文件缺失或仅前三页没有图标
  当形成结论
  那么标明有限覆盖，不判定应用没有桌面入口或白屏已修复
## 排除范围
随机崩溃、启动时延重新统计、部署及封板。
