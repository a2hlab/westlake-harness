spec: task
name: "B12 显式窗口归属与 BLAST sync JNI 离线包"
inherits: project
depends: [b8-port-westlake-fixes]
tags: [graphics, native, offline]
---

## 意图

修复 Wikipedia 两个窗口的 SC 被全局 last-session 错绑到同一 producer,并把 Westlake 已有的 BLAST sync JNI 迁入 v3c runtime。此阶段交付单文件替换包和离线验证,板上点亮由外环另行排板验收。

## 已定决策

- 基线 runtime 为 `9e14bf20`,保留 CommonEvent、VelocityTracker 与 SQLite;不并入暂停的 next ANL/AudioSystem。
- SC 由 `OH_Surface_<sessionId>` 或父 SC 确定归属,copy/mirror 保持 sessionId;BBQ 不借用全局 last-session,未知 owner 返回未就绪。
- BLAST 照搬 VM Westlake `22b94532` 的 13 项表与保守实现:不收集 sync,返回 false,提供有效空 Transaction,异常保持 pending。
- 只生成 runtime 单文件包并 dry-run;不写任何板,不改 EGL destroy 行为。

## 边界

### 允许修改
- bms/src/adapter/framework/android-runtime/src/android_graphics_compat_shim.cpp
- bms/src/adapter/framework/android-runtime/src/android_view_SurfaceControl.cpp
- bms/src/adapter/framework/android-runtime/src/surface_session_identity.h
- benchmark/2026-09-30-graphics-session-sync/**
- tools/spec-checks/tests/graphics_session_sync.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

### 禁止
- 不修改 host、ANL、installer、JAR 或 APK
- 不写板、不宣称已点亮、不强制销毁其他 owner 的 EGLSurface

## 验收标准

场景: 两个 session 相互隔离
  测试: graphics_session_owners
  假设 SC 名字为 OH_Surface_297 与 OH_Surface_298
  当 宿主测试执行生产归属解析函数并测试父子继承
  那么 得到不同的 sessionId 且子 SC 保持父归属

场景: 未知或非法 owner 不借用全局值
  测试: graphics_session_invalid
  假设 名字为空、溢出、带尾随字符或没有父 SC
  当 执行归属解析和 BBQ 源码检查
  那么 不会选择其他窗口的 last-session

场景: BLAST 当前 DEX 签名与保守实现匹配
  测试: graphics_blast_signatures
  假设 冻结 framework.jar 含 13 个 BLAST native
  当 对照注册表与 Westlake 实现
  那么 13 项名称与签名全匹配且 sync 不声称已挂回调

场景: JNI 构造失败不吞异常
  测试: graphics_blast_exceptions
  假设 Transaction 查类或构造失败
  当 核对照搬实现的异常路径
  那么 保持 pending 异常而不把 null 宣称为成功的 Transaction

场景: 单文件包没有夹带暂停的候选
  测试: graphics_runtime_package
  假设 v3c 为替换基线
  当 检查包清单与 dry-run
  那么 仅 runtime 改变且 SHA 与产物一致,回滚 SHA 为 9e14bf20

## 排除范围

- 板上 HW/ZigZag/目标 app 截图验收,等待外环排板
- 实现完整 SurfaceFlinger 事务队列或改系统 RenderService
