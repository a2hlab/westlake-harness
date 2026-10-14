spec: task
name: "Demo installation reconciliation and real desktop launch"
inherits: project
depends: [t1-inventory, t2-icons]
---
## 意图
按外环审定清单补装缺失演示APK、卸载不支持测试APK、修复已证实错误的标签/图标。用真实桌面入口证据逐项证明可点开，保留已签有限功能限制及全部失败。

## 已定决策
- 原始证据与最终判断分别记录；raw rc、SHA、路径、来源与未知字段保持可追溯。
- 使用已验证脚本与实现；不推断未执行的设备行为或远端构建成功。

## 边界
### 允许修改
- benchmark/2026-10-14-demo-desktop-ready/**
- tools/spec-checks/tests/demo_desktop_ready.rs

### 禁止
- 不修改原V2签认、冻结文件或其他车道工作区。
- 不以进程存活、静态命中或历史成功替代本轮证据。

## 完成条件
场景: 桌面交付证据完整
  审核: human
  测试: demo_desktop_ready
  Given the approved action manifest and exclusive board lock
  When reconciling installed demo packages
  Then installed packages and real desktop click evidence match the final manifest

场景: 桌面交付缺项明确
  审核: human
  测试: demo_desktop_ready
  Given a package with failed launch or ambiguous icon
  When reviewing the final desktop
  Then the row is excluded or explicitly unresolved and never marked usable
