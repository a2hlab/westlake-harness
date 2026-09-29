spec: task
name: "B9 拆掉运行代的哈希锁,并把 manifest 解析 JNI 编回桥接库"
inherits: project
depends: [b6-attach-theme-context]
tags: [bms, native, generation, unlock, cx-t0]
---

## 意图

route-A 运行代有三层哈希锁:appspawn-x 钉 child 插件 SHA、child 的 sealed loader 逐个核 28 个 provider 的 SHA/build-id(`WLSCPL_ERROR_ARTIFACT_IDENTITY`)、appspawn-x/provider 编译期钉运行时库与桥接库 SHA(`exact adapter bridge admission failed`,单换桥接库退出码 123)。它让任何 native 改动都要整代重生成,B6、B7、#67 都被它拖慢;用户 2026-09-29 批准拆锁。同时 B8 #65 查明 14 个 app 统一死在 `onCreate` 的第一类墙:当前桥接库 84695d62 不导出 `Java_adapter_activity_AppSchedulerBridge_nativeParseManifestJson`(也没有 `nativeGetSysProp`),`[B43-BIND] providers populated:0`,`<application android:name>` 不生效,Koin 等自定义 Application 从不初始化。实现已在库里(`bms/src/adapter/framework/package-manager/jni/apk_manifest_jni.cpp`,00.Workspace 验证过),只是本代桥接库没编进去。本任务一次重生成「无锁代」,之后 native 库可以单文件替换。

## 已定决策

- 拆锁方式(2026-09-29 用户定):运行时加载器不再做封存——appspawn-x 不钉 child 插件 SHA、child 的 sealed loader 不核 provider 的 SHA/build-id、bridge/runtime admission 不比 SHA;按路径正常加载。正常的桥接层(含 Westlake)都不在运行时加载器里做这种封存
- 「库配错当场报错」的保护挪到部署工具:`tools/deploy_generation.sh` 部署前核包内清单 SHA,部署后核板上关键件 SHA、单份 ART、桥接库版本与子进程 `/proc/<pid>/maps`,任一不符即回滚
- `deploy_generation.sh` 增加单文件替换模式:换一个库时更新包内清单、bind-mount 该文件、跑同一组部署后检查,不符即只回滚这一个文件
- appspawn-x、child 插件、provider 三者本次一起重建,这是最后一次整代重建;之后 native 改动都走单文件替换
- 桥接库按 `bms/src/adapter/build/inner/compile_oh_adapter_bridge.sh` 的 P2-B 段编入 `apk_manifest_jni.cpp`、`apk_manifest_parser.cpp`、`axml_parser.cpp` 与 minizip+zlib;脚本对缺失源文件是静默 `continue`、对缺 minizip 只打 WARN,本任务把这两处改成缺了就构建失败
- 基于 #67 的 v2(`15728be5`,含 SQLite JNI 与 Flutter app-domain 修复)生成 v3;打包与部署沿用 `tools/deploy_generation.sh`,带回滚;源码快照、补丁、工具链哈希按 AGENTS.md 入库或存 hw248 `/home/alvin/`
- 在 5ea 上开发验证;验收过后交 5cd、61b 换代

## 边界

### 允许修改
- bms/src/adapter/framework/appspawn-x/**
- bms/src/adapter/build/**
- bms/src/adapter/framework/package-manager/jni/**
- benchmark/2026-09-29-unlocked-generation/**
- tools/spec-checks/**
- tools/deploy_generation.sh
- scripts/lab/deploy_generation.sh

### 禁止
- 不修改 APK
- 不改 installer(`libapk_installer.so`)
- 不在 5ea 以外的板上部署,直到外环签认 v3

## 验收标准

场景: 无锁代上单换桥接库被接受
  测试: b9_single_bridge_swap_accepted
  假设 v3 已部署到 5ea,HelloWorld 正常
  当 只把 `liboh_adapter_bridge.so` 换成另一份 SHA 不同的构建并从桌面拉起 HelloWorld
  那么 hilog 不出现 `exact adapter bridge admission failed`、`LOAD_ERROR` 与 `WLSCPL_ERROR_ARTIFACT_IDENTITY`
  并且 子进程 maps 映射的是换上去的桥接库

场景: 桥接库导出 manifest 解析 JNI
  测试: b9_bridge_exports_manifest_jni
  假设 v3 的桥接库已构建
  当 对它跑 `llvm-nm -D --defined-only`
  那么 输出含 `Java_adapter_activity_AppSchedulerBridge_nativeParseManifestJson` 与 `Java_adapter_activity_AppSchedulerBridge_nativeGetSysProp`

场景: 自定义 Application 被实例化
  测试: b9_custom_application_created
  假设 v3 已部署到 5ea
  当 从桌面拉起 fd-k9 与 ooniprobe 并采 hilog
  那么 `[B43-BIND] providers populated` 的数字大于 0
  并且 不再出现 `KoinApplication has not been started` 与 Application 强转失败,越过的附原文

场景: 缺源文件时构建失败
  测试: b9_bridge_build_fails_on_missing_source
  假设 构建目录里去掉 `apk_manifest_jni.cpp` 或 minizip 目标文件
  当 运行桥接库构建
  那么 构建以非零退出码结束并打印缺失的路径,不产出桥接库

场景: 无锁代不让已亮的 app 回退
  测试: b9_no_regression
  审核: human
  假设 v3 已部署到 5ea
  当 拉起 HelloWorld 与 ZigZag
  那么 外环读图签认两者截图仍是各自界面

场景: 部署工具拦下配错的库
  测试: b9_deploy_tool_rejects_mismatch
  假设 v3 已部署到 5ea
  当 用单文件替换模式换上一个与包内清单 SHA 不符的库,或换后子进程 maps 出现两份 libart
  那么 `deploy_generation.sh` 以非零退出码结束并打印不符的组件
  并且 该文件被回滚,板上 SHA 回到替换前

场景: 部署失败时回滚到 6cb40cd6
  测试: b9_rollback_on_failed_deploy
  假设 v3 部署后 HelloWorld 不能上屏或出现双份 libart
  当 执行 `deploy_generation.sh --rollback`
  那么 5ea 回到 6cb40cd6,板上关键件 SHA 与 6cb40cd6 清单一致

## 排除范围

- installer 与安装墙(fd-seal、x、toutiao)
- Java 侧的 manifest 回退(B8 r8b 在 5cd 并行做)
