spec: task
name: "B7 不依赖 B6 的两类墙:UnsatisfiedLinkError 与 ART 入口崩溃(5cd)"
inherits: project
depends: [b1-sandbox-prep, b5-activity-alias]
tags: [bms, native, namespace, cc-t3]
---

## 意图

B4 v3 直方图里,除了 B6 空指针族,还有 7 个 app 死在另外两类墙上,与 B6 无关,可以在 5cd 上先修:UnsatisfiedLinkError 5 个——opencamera(无法为 classloader 创建 namespace)、fd-android 与 fd-k9(JNI 方法无实现,如 `SQLiteConnection.nativeOpen`)、fd-libre 与 fd-saber(Flutter,`path is outside app domain`);ART 入口 2 个——fd-catima、fd-fennec_fdroid(崩在 libart 的 nterp 解释器)。本任务逐个查清首因,能在适配层修的就修,修完从桌面拉起验证。

## 已定决策

- 独占板 5cd;每次点击前核 boot_id 未变且前台是桌面;已装旧版先 `bm uninstall` 再装,安装按输出文本判成败
- 每个 app 拉起前 `hilog -r`,拉起后 15 s 落 hilog 与新增 faultlog,首因写进 `results.json`(原文行 + 文件路径)
- 同类的一起修:JNI 注册缺失查 `liboh_adapter_bridge` / 运行时 JNI 表;namespace 与 app 域路径查 native loader 的 permitted path 与 `nativeLibraryDir`;修复落点优先适配层 Java(`oh-adapter-runtime.jar`,沿用 B5 的覆盖方式)或 native loader 配置
- 修复不改 APK,不改 route-A 运行代的 28 个 provider(B6 在 5ea 上做),部署带回滚

## 边界

### 允许修改
- benchmark/2026-09-29-bms-link-entry-walls/**
- bms/src/adapter/framework/**
- tools/spec-checks/**

### 禁止
- 不修改 APK
- 不改 route-A provider 与 sealed manifest
- 不在 5cd 以外的板上部署

## 验收标准

场景: 七个 app 的首因都有原文证据
  测试: b7_first_cause_recorded
  假设 七个 app 已在 5cd 上各拉起一次并采集 hilog 与 faultlog
  当 查看 `results.json`
  那么 每个 app 的 `first_cause` 附原文行与文件路径

场景: 修复后至少一类墙被越过
  测试: b7_wall_crossed
  假设 某类墙的修复已在 5cd 生效
  当 从桌面拉起该类的 app
  那么 hilog 里原错误行不再出现,且有该调用成功或进程走到下一阶段的正证据

场景: 越过墙的 app 上屏由外环读图
  测试: b7_lit_by_outer_review
  审核: human
  假设 某 app 越过原墙后进程持续存活
  当 截取 t+5 s 与 t+20 s 截图(焦点窗口属于该 app)
  那么 外环读图签认是否为该 app 自身界面

场景: 修复不让 HelloWorld 与 ZigZag 回退
  测试: b7_no_regression
  假设 修复已在 5cd 生效
  当 从桌面拉起 HelloWorld 与 ZigZag
  那么 两者截图仍是各自界面

场景: 修不了的写明原因
  测试: b7_blocked_reason_recorded
  假设 某个 app 的首因在适配层之外
  当 结束本任务
  那么 `results.json` 写明该 app 的 `blocked_reason` 与证据,不计点亮

## 排除范围

- B6 空指针族(在 5ea 上由 B6 处理)
- 安装墙(fd-seal 原生库校验、x/toutiao manifest -2005)
