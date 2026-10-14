spec: task
name: "Demo APK set and package inventory"
inherits: project
depends: []
---
## 意图
从签认S的109core、6limited、13excluded及独立Boat/头条记录生成唯一包清单，对比本轮bm dump原文。补装/保留/卸载/保护四类互斥，未知包只报unknown。

## 已定决策
- 原始证据与最终判断分别记录；raw rc、SHA、路径、来源与未知字段保持可追溯。
- 使用已验证脚本与实现；不推断未执行的设备行为或远端构建成功。

## 边界
### 允许修改
- benchmark/2026-10-14-demo-desktop-inventory/**
- tools/spec-checks/tests/demo_desktop_inventory.rs

### 禁止
- 不修改原V2签认、冻结文件或其他车道工作区。
- 不以进程存活、静态命中或历史成功替代本轮证据。

## 完成条件
场景: 清单与安装差异证据完整
  审核: human
  测试: demo_desktop_inventory
  Given signed keys and actual bundle records
  When deriving actions
  Then every signed key has exactly one package disposition

场景: 清单与安装差异缺项明确
  审核: human
  测试: demo_desktop_inventory
  Given an unknown or protected package
  When deriving removals
  Then no destructive action targets that package
