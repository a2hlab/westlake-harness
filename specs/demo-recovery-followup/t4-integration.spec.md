spec: task
name: "Reviewed Route B recovery integration package"
inherits: project
depends: [t1-watchdog, t2-review]
---

## 意图

把已通过独立离线复验的恢复候选接入真实 Route B 启动链，交一个默认预览且未授权执行的完整集成包。提前闭合脚本别名、helper 路径、启动环境、JIT 与截图分类等已知缺口，使下一轮外环可以审核具体变更、回滚和新封板绑定，不在板上逐项试错。

## 已定决策

- 以 master 的 followup-1406 实采 owner/start-parent/spawn 和 wiki 的原始 79/91 为输入；精确 SHA 列清，禁止把 fixture 启动器当真实启动入口。
- 已有 stop 原件与用户数据必须保留；新 attempt 的控制状态采用独立目录，只有后续新授权可启用，不能默认绕过旧 stop。旧 overlay 不直接重跑。
- 不移除必要的原启动准备；JIT、namespace、窗口 ID、socket、UID、screen-gate 格式等逐项写对照与就绪判据。源码和本地既存产物可只读静态检查，不跑 VM/板。
- v1 范围与 Plan-2 的 61b 20-key + 5cd 128 对照不变；新变更不能套旧 plan_sha、旧 no_mac_repair 或旧截图签字。

## 边界

### 允许修改
- benchmark/2026-10-12-toutiao-recovery-integration/**
- tools/spec-checks/tests/toutiao_recovery_integration.rs

## 验收标准

场景: 候选别名与启动链完整绑定
  测试: toutiao_recovery_integration_bindings
  假设 t1 候选 SHA 已获 t2 离线 accept 且真实入口原件存在
  当 生成集成清单与新 attempt 草案
  那么 两份 watchdog 别名、helper、实际启动入口、依赖、placement 和新 plan 逐件绑定，缺件即 pending 且禁止执行

场景: 默认预览不触发设备或用户数据改动
  测试: toutiao_recovery_integration_preview
  假设 所有外部板命令由隔离录制器代替
  当 运行默认入口或传入未签、过期、错误 boot 或错误候选授权
  那么 默认只打印精确变更和回滚，错误授权非零且零设备调用，旧 stop、原 run 和数据哨兵字节不变

场景: 实际启动环境与依赖不被遗漏
  测试: toutiao_recovery_integration_launch
  假设 集成入口使用真实脚本字节但外部命令由隔离录制器代替
  当 模拟正常前置条件以及缺失 JIT 准备、helper、socket 就绪或截图格式不兼容
  那么 正常路径传入执行开关和当前 boot 并保留必要启动次序，缺前置条件保守拒绝而不报告 UI 或封板成功

## 排除范围

- 真实板访问、部署、重启、自动隐私操作、runtime 构建、修改冻结登记、实际签授权与执行新封板。
