spec: task
name: "B6 Activity.attach 期间 getTheme 空指针崩溃"
inherits: project
depends: [b5-activity-alias]
tags: [bms, framework, context, cx-t0]
---

## 意图

B5 之后 Wikipedia 的 child 已实例化 `org.wikipedia.main.MainActivity`,但在 `Activity.attach+112` 里经解释执行的若干帧调到 `ContextImpl.getTheme+140 → ContextWrapper.getApplicationInfo+44`,读空指针 SIGSEGV(`SEGV_MAPERR@0`,tombstone 在 B5 的 `alias-entry/evidence/wikipedia/`)。同一运行代上 HelloWorld 正常上屏;两者都有 `nativeParseManifestJson` 的 `UnsatisfiedLinkError`,所以那条不是区分点。AppCompat 系 app 在 `attachBaseContext` 里包装 Context 很常见,这堵墙可能挡住一批 app。本任务找出是谁在外层 Context 尚未 attach 时调了 `getTheme`,把它修掉,让 Wikipedia 上屏。

## 已定决策

- 先照搬:在 `bms/src/adapter`(含 `aosp_patches/`、`framework/activity/`)、00.Workspace 主干与各 worktree、hanbin 里找 `ContextImpl.getTheme`、`getOuterContext`、`attachBaseContext`、`Activity.attach` 相关补丁;找到就照搬并在 README 写来源路径与 commit
- 先定位再修:把 `Activity.attach+112` 到 `getTheme` 之间的解释帧还原成具体 Java 方法(app 自己的 `attachBaseContext`、AppCompat delegate,或适配层代码),证据是日志行或 baksmali 出的 smali 片段,写进 `results.json.caller`
- 真机对照:同一个 Wikipedia APK 装到安卓参考机 `N100CU025C18D000128` 上从桌面启动,截图证明 APK 本身能用
- 顺带判定并记录:本运行时里编译代码的空指针解引用是抛 `NullPointerException` 还是直接 SIGSEGV(ART 隐式空检查的故障处理是否生效),写进 `results.json.null_check_mode` 并附证据;这决定 app 自己 catch 的 NPE 会不会变成崩溃
- 根因(#31 实证):OH musl 先派发 special 信号处理器,DFX 占 special 槽先收 SIGSEGV,ART 的 libsigchain 只登记为 user handler、晚 670 ms 才收到,隐式空检查转不成 NPE。修复照搬现成的 musl 桥:用 `bms/src/adapter/build/inner/compile_sigchain_muslcompat.sh` 把 `aosp_patches/art/sigchainlib/sigchain_muslcompat.cc` 编成 aarch64 `libsigchain.so`,替换 route-a 的 `libsigchain.so`(现为 ea7becd0,无 `add_special_signal_handler` 导入)。不重建 boot image,不改 framework
- 替换前核对:新库导出覆盖 route-a `libart.so` 从 `libsigchain.so` 导入的全部符号,缺一个就不部署
- 部署沿用 B5 的覆盖方式并带回滚;appspawn-x 若在父进程预载 ART,覆盖后要重启它才生效。板上实际加载的产物 SHA 写进 `results.json`

## 边界

### 允许修改
- benchmark/2026-09-28-bms-route-deploy/**
- bms/src/adapter/**
- tools/spec-checks/**

### 禁止
- 不修改 APK
- 不在 5ea 以外的板上部署
- 不改 installer(`libapk_installer.so` 归 B2/B3)

## 验收标准

场景: Wikipedia 从桌面启动后上屏
  测试: b6_wikipedia_lit
  审核: human
  假设 修复已在 5ea 生效,板上产物 SHA 与 `results.json` 一致
  当 从桌面点击 Wikipedia 图标并等待 15 s
  那么 其 BMS uid 下进程持续存活
  并且 外环读图签认截图是 Wikipedia 自身界面

场景: getTheme 的调用者被具名
  测试: b6_caller_identified
  假设 修复前的 Wikipedia 崩溃可复现
  当 还原 `Activity.attach` 与 `getTheme` 之间的解释帧
  那么 `results.json.caller` 写明调用 `getTheme` 的 Java 方法
  并且 附日志行或 smali 片段作为证据

场景: 修复后 HelloWorld 与 ZigZag 不回退
  测试: b6_no_regression_helloworld_zigzag
  审核: human
  假设 最终修复已在 5ea 生效
  当 用 `bms/` 复现器对 HelloWorld 与 ZigZag 各跑一次 `quick`
  那么 两者的截图仍是各自界面
  并且 任一回退即判本任务失败,`results.json.regressions` 列出该 app

场景: 越过 getTheme 但仍未上屏时记下一堵墙
  测试: b6_next_wall_recorded
  假设 修复后 Wikipedia 不再在 `getTheme` 崩溃,但截图仍不是它自身界面
  当 重新采集 hilog 与 faultlog
  那么 交付状态记 `advanced`,`next_blocker` 附原始日志行
  并且 点亮数不增加

场景: 板上产物不是本次构建时判失败
  测试: b6_fix_absent_detected
  假设 `/proc/<child pid>/root` 下实际加载的产物 SHA 与 `results.json` 记录值不一致
  当 执行验收
  那么 任务判失败且不计入点亮数

场景: 空指针处理方式有记录
  测试: b6_null_check_mode_recorded
  假设 已取得本运行时一次编译代码空指针解引用的现场
  当 查看 `results.json.null_check_mode`
  那么 值为 `npe` 或 `sigsegv` 之一并附 faultlog 或 hilog 原文
  并且 替换 libsigchain 后重新取证,修复生效时该值为 `npe`

场景: 新 libsigchain 缺符号时不部署
  测试: b6_sigchain_exports_cover_libart_imports
  假设 新编的 `libsigchain.so` 少导出 route-a `libart.so` 需要的某个符号
  当 执行部署前核对
  那么 部署中止,`results.json` 列出缺失符号,板上仍是原库

## 排除范围

- 名字与图标(B2、B3)
- 与 Context/Theme 无关的其他启动墙(交 B4 汇总)
