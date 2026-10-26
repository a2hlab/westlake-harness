spec: task
name: Demo payload and build-input collection
satisfies: [REQ-ARTIFACT-RECOVERY]
---
## 意图
收齐最近61b演示运行组合及回滚的可用二进制与构建输入，形成可导入制品库的来源映射。原始文件保持只读，缺口必须按组件给出。
## 已定决策
- 以61b-reentry-delivery的3291候选、b0e回滚及实际runtime/HAP/JAR/boot依赖为锚，结合既有seal和runtime指纹确定完整恢复范围；不可把单库备份称整板恢复。
- 先本地持久目录及worktree，再Orb，再hw248找原件；hash逐件核实。仅普通只读板文件查询/接收用于核物理路径，不启动/停止/部署app，不读取应用个人数据。
- 输出benchmark/2026-10-26-demo-artifact-recovery/intake/README.md、results.json、source-map私有文件和构建状态表；大文件放独立持久目录。公开manifest不得带凭据或个人绝对路径。
- manifest schema westlake-artifact-release/v1，release_id安全标识，files包含path/sha256/size/mode整数/role；路径是恢复目录相对路径。stage根由私有映射定位，tool只读其下普通文件，symlink应物化为经验证字节并保留部署link关系元数据。
- 保存五个编译单元及103复用链接输入（46个.o、56个.so、1个.a）、必要SDK/工具链/链接库、原构建stdout/stderr/rc；区分archived/recoverable/rebuildable与missing，源码重建缺口不能由文件存在代替。
## 边界
### 允许修改
- benchmark/2026-10-26-demo-artifact-recovery/intake/**
### 禁止
- 修改设备、清理worktree、覆盖原证据、擅自更改冻结注册、推送、公开APK和私密日志
## 验收标准
场景: 收集与历史身份匹配
  测试: artifact_recovery_intake
  假设候选回滚及运行组合已按权威清单定位
  当从源读取并计算完整SHA256
  那么manifest文件逐件与历史锚点一致且每个声明的恢复组件有来源
场景: 缺口不冒充通过
  测试: artifact_recovery_intake
  假设某构建依赖或运行成员未找到或只有历史hash
  当输出结果
  那么该成员列missing并阻止完整恢复声明且不以另一个同名版本替换
场景: 独立存储与公开边界
  测试: artifact_recovery_intake
  假设私有原件含商业APK或个人路径
  当生成公开清单
  那么清单只含内容hash和脱敏定位且二进制留独立私有存储
## 排除范围
完整重编缺失历史源码、上板实验、物理另一台Mac验收。
