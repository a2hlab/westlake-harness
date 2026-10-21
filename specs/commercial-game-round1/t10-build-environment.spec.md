spec: task
name: "G10 isolated build environment readiness"
inherits: project
depends: [t8-apk-extractor]
satisfies: [REQ-COMMERCIAL-GAME]
---
## 意图
独立定位G09编译环境阻塞并给出可执行入口，使源码车道继续完善构建配方。当前cx报告orb true超时、status为Stopped，不可称为整机卡死。
## 已定决策
- 先核当前正确orb status和run命令及已有只读记录，短调用有界15秒，不全盘find，不重复长等；遵循RUNBOOK49/50/184的Stopped和自愈区分。
- 可检查既有a2hlab或hw248输入可用性及精确归档/工具链哈希；不变更权限、不绕过沙箱拒绝、不强杀/重启共享服务、不自己启动编译。需启动已停止VM则把精确命令和影响回报外环处理。
- 归档61ff2def和编译器b107ce03不换；hw248 Python3.10与旧build.py不兼容不代表原tar解包与clang不能运行，给可复用配方要求但不复制大资产。
- 仅本卡报告目录写入，10分钟首片，环境查完即向cx交接，不另跑相同构建。
## 边界
### 允许修改
- benchmark/2026-10-21-commercial-game/apk-extractor/environment-readiness/**
- tools/spec-checks/tests/commercial_game_environment_readiness.rs
### 禁止
- 不设备、不部署、不改G09文件或共享kit、不push、不重启VM、不变更权限。
## 验收标准
场景: 环境状态有真实回执
  测试: commercial_game_environment_readiness
  假设cx报告orb超时
  当执行有界最小只读检查
  那么区分Stopped与Running和未知，保留实际argv双流rc及时间，不以超时证明卡死
场景: 替代入口有精确输入
  测试: commercial_game_environment_readiness
  假设原通道不能运行
  当核已有替代环境及原归档工具链
  那么可用性依据实际结果，缺输入明确列出，不虚报已编译不启动第二构建
场景: 工具拒绝不绕过
  测试: commercial_game_environment_readiness
  假设探查被拒绝或返回未知
  当整理交接
  那么保留拒绝并停止该操作，只读其他已授权独立资料，缺字段不改判为可用
## 排除范围
构建、VM启动恢复、任何设备动作由后继执行处理。
