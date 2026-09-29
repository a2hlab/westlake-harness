# Contract Review: B6 Activity.attach 期间 getTheme 空指针崩溃

## Intent

B5 之后 Wikipedia 的 child 已实例化 `org.wikipedia.main.MainActivity`,但在 `Activity.attach+112` 里经解释执行的若干帧调到 `ContextImpl.getTheme+140 → ContextWrapper.getApplicationInfo+44`,读空指针 SIGSEGV(`SEGV_MAPERR@0`,tombstone 在 B5 的 `alias-entry/evidence/wikipedia/`)。同一运行代上 HelloWorld 正常上屏;两者都有 `nativeParseManifestJson` 的 `UnsatisfiedLinkError`,所以那条不是区分点。AppCompat 系 app 在 `attachBaseContext` 里包装 Context 很常见,这堵墙可能挡住一批 app。本任务找出是谁在外层 Context 尚未 attach 时调了 `getTheme`,把它修掉,让 Wikipedia 上屏。

## Decisions

- 名字与图标都在 `bms/src/adapter/framework/package-manager/jni/apk_installer.cpp` 合成资源 HAP 的流程里修;两项由同一车道先后做,避免同文件冲突
- native 库用 `westlake-inputs/tools/dockbuild.sh` 按锁定工具链为 OH 6.1 编;换 installer 的步骤必须带回滚
- 沙箱准备照搬 HelloWorld restore 与 ZigZag `prepare_sandbox` 的逻辑,参数化为包名与 uid
- 先照搬:在 `bms/src/adapter`(含 `aosp_patches/`、`framework/activity/`)、00.Workspace 主干与各 worktree、hanbin 里找 `ContextImpl.getTheme`、`getOuterContext`、`attachBaseContext`、`Activity.attach` 相关补丁;找到就照搬并在 README 写来源路径与 commit
- 先定位再修:把 `Activity.attach+112` 到 `getTheme` 之间的解释帧还原成具体 Java 方法(app 自己的 `attachBaseContext`、AppCompat delegate,或适配层代码),证据是日志行或 baksmali 出的 smali 片段,写进 `results.json.caller`
- 真机对照:同一个 Wikipedia APK 装到安卓参考机 `N100CU025C18D000128` 上从桌面启动,截图证明 APK 本身能用
- 顺带判定并记录:本运行时里编译代码的空指针解引用是抛 `NullPointerException` 还是直接 SIGSEGV(ART 隐式空检查的故障处理是否生效),写进 `results.json.null_check_mode` 并附证据;这决定 app 自己 catch 的 NPE 会不会变成崩溃
- 根因(#31 实证):OH musl 先派发 special 信号处理器,DFX 占 special 槽先收 SIGSEGV,ART 的 libsigchain 只登记为 user handler、晚 670 ms 才收到,隐式空检查转不成 NPE。修复照搬现成的 musl 桥:用 `bms/src/adapter/build/inner/compile_sigchain_muslcompat.sh` 把 `aosp_patches/art/sigchainlib/sigchain_muslcompat.cc` 编成 aarch64 `libsigchain.so`,替换 route-a 的 `libsigchain.so`(现为 ea7becd0,无 `add_special_signal_handler` 导入)。不重建 boot image,不改 framework
- 替换前核对:新库导出覆盖 route-a `libart.so` 从 `libsigchain.so` 导入的全部符号,缺一个就不部署
- route-a 的 child 插件把每个 provider 的 SHA/build-id 封进 sealed manifest,loader 映射前校验;只换 `libsigchain.so` 会被拒(#33:`WLCGATE:LSP:LOAD_ERROR:8`,`WLSCPL_ERROR_ARTIFACT_IDENTITY`)。所以按 `stock_child_plugin/build_target_in_container.sh` 既有构建流重生成一代:新 `libsigchain.so` 进 provider 清单 → 重生成 `sealed_provider_manifest.c` 并重编 child 插件 → 把新插件 SHA 钉进 appspawn-x。不绕过、不关闭身份校验
- 2026-09-28 用户决定:板上 R155 这一代(child 0976dee8、appspawn-x 1f6cf53b)找不到同版源码,改用 00.Workspace 最新源码整代重建——libart 与全部 provider、native roots、child 插件、appspawn-x 同源同配置一起构建;若新 libart 与板上 boot image 不兼容,同源重建 boot image。不混用板上旧件与新源码产物
- 部署走 `bms/` 复现器的候选代机制(`var/state/<skill>/candidates/`)或 B5 的覆盖方式,整代一起换、一起回滚;板上实际加载的 libsigchain、child 插件、appspawn-x 的 SHA 写进 `results.json`

## Boundaries

**Allowed:**
- benchmark/2026-09-28-bms-route-deploy/**
- bms/src/adapter/**
- tools/spec-checks/**

**Forbidden:**
- 不修改 APK
- 不在 5ea 以外的板上部署
- 不改 installer(`libapk_installer.so` 归 B2/B3)

**Out of Scope:**
- 名字与图标(B2、B3)
- 与 Context/Theme 无关的其他启动墙(交 B4 汇总)

## Verification Summary

| Total | Passed | Failed | Skipped | Uncertain | Pass Rate |
| --- | --- | --- | --- | --- | --- |
| 8 | 3 | 5 | 0 | 0 | 37.5% |

- ❌ Wikipedia 从桌面启动后上屏
  - test: `b6_wikipedia_lit`
- ✅ getTheme 的调用者被具名
  - test: `b6_caller_identified`
- ❌ 修复后 HelloWorld 与 ZigZag 不回退
  - test: `b6_no_regression_helloworld_zigzag`
- ❌ 越过 getTheme 但仍未上屏时记下一堵墙
  - test: `b6_next_wall_recorded`
- ✅ 板上产物不是本次构建时判失败
  - test: `b6_fix_absent_detected`
- ❌ 空指针处理方式有记录
  - test: `b6_null_check_mode_recorded`
- ❌ 重生成的一代通过 loader 身份校验
  - test: `b6_generation_passes_identity_gate`
- ✅ 新 libsigchain 缺符号时不部署
  - test: `b6_sigchain_exports_cover_libart_imports`

## Coverage Matrix

| Rule | Scenario | Test | Found | Verdict | Provenance |
|------|----------|------|-------|---------|------------|
| — | Wikipedia 从桌面启动后上屏 | b6_wikipedia_lit | found | fail | computational |
| — | getTheme 的调用者被具名 | b6_caller_identified | found | pass | computational |
| — | 修复后 HelloWorld 与 ZigZag 不回退 | b6_no_regression_helloworld_zigzag | found | fail | computational |
| — | 越过 getTheme 但仍未上屏时记下一堵墙 | b6_next_wall_recorded | found | fail | computational |
| — | 板上产物不是本次构建时判失败 | b6_fix_absent_detected | found | pass | computational |
| — | 空指针处理方式有记录 | b6_null_check_mode_recorded | found | fail | computational |
| — | 重生成的一代通过 loader 身份校验 | b6_generation_passes_identity_gate | found | fail | computational |
| — | 新 libsigchain 缺符号时不部署 | b6_sigchain_exports_cover_libart_imports | found | pass | computational |
