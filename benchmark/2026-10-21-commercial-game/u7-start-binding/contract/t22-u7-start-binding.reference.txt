spec: task
name: "G22 preserve label checks across U7 start and restoration"
inherits: project
depends: [t19-loader-deployment-admission]
---
## 意图
修复原 U7 DeviceIO 与当前 Deployment.start 的参数接线缺口，使已验证的启动和标签检查在应用、失败回滚、显式回滚及基线恢复中获得正确 manifest。先用真实原方法离线重现，再做最小修订，不以上板碰错检验。
## 已定决策
- 当前 DeviceIO.__init__ 没有初始化 self.a/self.m，继承 Deployment.start 首先访问 self.a.no_label_recipe 并对 self.m 调用 apply_recipe。必须以当前精确源码及无设备测试证明，不用模拟 start 的假成功掩盖缺口。
- 复用现有 Deployment.start、selinux_label_audit.apply_recipe 与 U7 journal；不复制新的部署器，不跳过标签配方，不改变任何门禁、父进程/child 身份或锁判据，不改变 APK。
- 应用启动绑定候选 manifest；所有恢复启动绑定已核验的基线 manifest。同一 host SHA 可能对应两套不同 manifest，不得以 host SHA 单独猜选。未绑定或漂移必须在启动命令前拒绝。
- 启动上下文仅来源于原 preflight/journal 已验包，构造/绑定应明确可追踪；兼容现有只读 DeviceIO 用法，不因缺启动参数阻止只读检查。
- 加真实继承方法的无设备回归，覆盖应用、失败回滚、显式回滚、baseline replay、候选与基线不同的标签目标、未绑定与漂移拒绝。保留初始 AttributeError 的失败回执。测试不能发送 hdc、orb、shell 设备命令。
- 运行原 u7_executor Rust target 与现有标签配方相关测试，区分既有红灯；不改老证据和历史包，只交最小源码差异、验证日志与 landing-paths。
## 边界
### 允许修改
- scripts/lab/u7_executor.py
- benchmark/2026-10-21-commercial-game/u7-start-binding/**
- tools/spec-checks/tests/u7_start_manifest_binding.rs
### 禁止
- 不修改 native gates、label recipe、Deployment.start 实现或权限；不设置 no_label_recipe=True，不运行设备，不改 G14/T38，不推送。
## 验收标准
场景: 应用与各恢复入口选择正确标签清单
  测试: u7_start_manifest_binding
  假设候选与基线 host SHA 相同但 manifest 标签目标不同
  当执行真实继承 start 的应用及三种恢复路径离线回放
  那么应用使用候选、失败回滚和显式回滚及baseline replay使用基线，先完成标签检查再发启动命令
场景: 未绑定启动拒绝且只读不受影响
  测试: u7_start_manifest_binding
  假设 DeviceIO 用于只读且尚未绑定启动上下文
  当调用只读接口或尝试启动
  那么只读接口正常且启动在发命令前明确拒绝，不出现缺属性 AttributeError
场景: 输入漂移或标签失败拒绝
  测试: u7_start_manifest_binding
  假设已绑定包被修改或标签配方拒绝
  当准备启动
  那么原检查拒绝且不发服务启动命令，日志保留具体失败，不降低检查标准
## 排除范围
上板、游戏首启、标签配方规则调整、原生运行时构建、通用部署器重构。
