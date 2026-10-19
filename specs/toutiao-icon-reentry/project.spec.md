spec: project
name: "Toutiao manual icon recovery"
---
## 意图
在61b演示基线上允许头条退出后手点桌面图标再次启动，保留数据与已验证运行时。
## 约束
- 不诊断或修复随机SIG11，不改APK/native/JAR，不清应用数据，不自动同意隐私。
- 复用现行capture-feed-package，不覆盖历史证据。板操作由外环独占持锁执行。
- 一次明确桌面到宿主的前台事件最多启动一次；错误身份、停止标记和未知状态拒绝。
