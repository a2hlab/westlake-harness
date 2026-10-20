spec: project
name: "Toutiao one-click host-page transition"
---
## 意图
使5cd一次正常头条图标操作沿现有宿主和guardian自动到feed，同时移除Westlake开发控件；保留已接受视频候选及所有对象身份门。
## 约束
- 仅本地准备、源码闭合、构建和复验；HDC/安装/重启/留板操作仅root另行持锁执行，内环零设备调用、不推送。
- 不改T31留板来源、t1原诊断、旧HAP/旧日志或旧冻结源码；root只读intake是本任务输入，不伪造fresh身份。
- 不绕过OH宿主窗口，不改变正常图标、EntryAbility生命周期、guardian/spawn策略、运行时库、app数据或签名权限；黑/空背景不等于提速。
- 公开源码与配方可复现，原始新stdout/stderr/rc持久保存；只有公开上游开发签名材料可用，私有凭据不得入库。
## 边界
### 允许修改
- specs/toutiao-launcher-transition/project.spec.md
- specs/toutiao-launcher-transition/t2-host-page-candidate.spec.md
- benchmark/2026-10-20-toutiao-launcher-page/**
- tools/spec-checks/tests/toutiao_launcher_page.rs
### 禁止
- 改其他app、设备访问、改已留板运行时、部署或推送。
