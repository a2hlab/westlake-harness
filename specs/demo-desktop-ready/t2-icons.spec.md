spec: task
name: "Demo icon identity audit and bounded repair"
inherits: project
depends: [t1-inventory]
---
## 意图
先用原APK资源及已有安装器实现核对BMS与桌面图标/标签。交逐包证据与最小可回滚修复计划；未获外环精确派单不触板，不改冻结运行时。

## 已定决策
- 原始证据与最终判断分别记录；raw rc、SHA、路径、来源与未知字段保持可追溯。
- 使用已验证脚本与实现；不推断未执行的设备行为或远端构建成功。

## 边界
### 允许修改
- benchmark/2026-10-14-demo-desktop-icons/**
- tools/spec-checks/tests/demo_desktop_icons.rs

### 禁止
- 不修改原V2签认、冻结文件或其他车道工作区。
- 不以进程存活、静态命中或历史成功替代本轮证据。

## 完成条件
场景: 图标与标签证据完整
  审核: human
  测试: demo_desktop_icons
  Given exact APK identity and current icon bytes
  When comparing icons and labels
  Then each retained package has a pinned match or explicit repair entry

场景: 图标与标签缺项明确
  审核: human
  测试: demo_desktop_icons
  Given missing or undecodable source artwork
  When reviewing an icon
  Then the row records unknown or fallback and never claims original artwork
