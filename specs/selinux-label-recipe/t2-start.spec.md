spec: task
name: "Fail-closed pre-start relabel integration"
inherits: project
depends: ["t1-audit.spec.md"]
---

## 意图

部署器在 start_service 前默认执行标签修复与完整读回审计。

## 已定决策

- 使用现有受守卫 shell，修复清单内 inode 标签，不改权限和安全配置。
- chcon 返回错误或读回仍错即拒绝启动，并保存前后审计与错误。
- --no-label-recipe 是显式关闭，Mac 到 VM 必须透传；既有部署测试仍需通过。
- JSON 是唯一事实源；部署器与自启 recover 共用由同一 JSON 生成的纯 sh，不能各持标签配方。

## 验收标准

场景: Repair is verified before daemon start
  测试: selinux_label_recipe
  假设 Mock labels reproduce the exec and library mapping walls
  当 Deployment start applies the recipe successfully
  那么 Readback passes before the first begetctl start and records both audits

场景: Failed relabel blocks daemon start
  测试: selinux_label_recipe
  假设 chcon fails or returns success without changing labels
  当 Deployment start audits the result
  那么 It refuses and preserves evidence without starting the daemon

场景: Opt-out remains explicit and dispatch preserves it
  测试: selinux_label_recipe
  假设 The caller selects --no-label-recipe
  当 Mac dispatch or mocked start runs
  那么 The same switch reaches the VM and only this label gate is skipped

场景: One recipe supplies both deployment and recover
  测试: selinux_label_recipe
  假设 Both callers use the same JSON and the same mocked inode labels
  当 Python audit and generated toybox shell audit run and source-before-bind repair runs
  那么 Both verdicts agree and the released shell exactly matches its JSON generator
