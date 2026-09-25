# #42：头条应用 AOT 已被 ART 接收，三臂性能验收被崩溃阻塞

**ACK(blocked)，R2=partially。** 同源 OAT247 两档部署/加载 verified；完成 baseline、verify、speed 各 3 次正式启动尝试，但有效固定时点条目点击分别只有 **3/0/2**。九轮最终均由父进程记录 signal 11；无法给出每臂 n≥3 的点击性能比较，也不能宣称解决首跑慢或文章页可用。详见 [DEVICE.md](DEVICE.md)、逐行数据 [device-results.json](device-results.json)。

独立分支 `feat/toutiao-aot-42`，worktree `westlake-harness-aot42`。VM `~/a2hlab/ws/out-aot42`；外环后续授权的板为 **5cd1e3dd00000000000000000923012c**，使用 Mac HDC。每轮前确认无 dalvikvm/linker64/头条/appspawn，结束清自己的 PID，最终再次核空。未动 bionic43、其他两块板、westlake 源码、共享 out 或系统分区。只运行应用 dex2oat，无 native 重编。

原 VM 阶段提交为 `f1133cd9a53dca9bbe9b2d9b20de6f7cd49ded23`。下面保留其输入与构建事实；“后续上板步骤”是当时计划，实际执行与偏差以 DEVICE.md 为准。

## 同源输入与产物

采用指定 `~/a2hlab/ws/out/host-tools/host/objects/bin/dex2oat`，冻结副本在 `out-aot42/tools/dex2oat`。SHA256 `8f9592174aa9d3f8b8f7e0d2879d15c6407e3c2f9f839346b8a8523c4434c7e3`，OAT 247。没有使用 OAT 230 的 AOSP14/hanbin 编译器。

参考 #38 `ability38/idle-a1/device-report.json` 和实际 `parent.log`，不是早先 #14 或 #38 trace-2 的不同 framework。参考报告的 `framework_report_sha256=3235d351b1a57cf758ca438b75eba2cf80dc7432794f5791cbd7d0b1230070c7`。按部署哈希匹配并冻结九个 BCP jar 与九组 boot art/oat/vdex，共 36 文件；逐项原路径、大小、哈希见 `evidence/input-files.json`。

|输入|SHA256|
|---|---|
|目标 libart.so|009a08fb8282b4ed8b857eaf014038adb93bb5cac0daa5d32ab89a13f29c8bbc|
|boot/boot.art|4be74675074455e905ee5f10c1f3aa2ccd6e4459e055feb1b6b4787447abd277|
|boot/boot.oat|7aafccfa3b5600b767cd06ee9eef9aaead1eb083dd89131bdb1cd58f5eb0d13f|
|fw/framework.jar|4a3d1688fe3753e7ac5164d2404cca3be1217c698ad7ce8383238713be44b0dd|
|fw/adapter-runtime-bcp.jar|5731db00562e3b814cfb4d4e32703c40c9e8726a022b28da155fd040fb59019a|
|toutiao.apk|a1112a0c941f865847c2fab9138cf815735268fbfcd41d697412fb80992c7395|
|map32 preload|cda75da6a331c7a6d2574b5235ffce1b3d063acb0351b5941a2e7e207396e69f|

APK 原件 138,641,340 字节、21 个 dex。逻辑路径必须是 `/data/local/tmp/asx/toutiao.apk`，并非名字为 base.apk 的文件。BCP 顺序为 core-oj、core-libart、core-icu4j、conscrypt、okhttp、bouncycastle、apache-xml、framework、adapter-runtime-bcp；逻辑 locations 均为 `/system/framework/*.jar`。参考实际 VM 选项见 `evidence/reference-parent.log` L30–51：image 为 `/data/local/tmp/asx/boot/boot.art`。

host 编译使用冻结目录内的物理 BCP 和 image，`inputs/boot/arm64 -> .`。两档构建日志均记录加载全部九段 boot image，未回退到重新解释 BCP 来编译。新产物的 BCP 校验串均为 `i;9/aa28fa9b`。**仅 OAT 版本相同不够**；下一次 #38 framework 有变化，需要重新冻结输入并编译。`check_framework.py REPORT` 会拒绝 36 项输入或 libart 哈希不一致。

## 编译结果

APK 自带 `assets/dexopt/baseline.prof`（11,399 字节、`pro\0 010\0`）及 baseline.profm（690 字节、002），不是完全没有 profile。当前 ART 接收 normal profile 015，直接传旧 profile 的 `speed-profile-1` 实测退出 1：`Error when reading profile: Profile version mismatch` / `Failed to process profile file`。未伪造、空造或强行跳过 profile 校验；按派单允许改测 verify/speed。

|最终候选|VM 耗时|odex 字节|vdex 字节|art 字节|ELF .text 字节|
|---|---:|---:|---:|---:|---:|
|verify-explicit|9.750s|1,725,056|197,777,992|24,688|0|
|speed-explicit|61.954s|599,929,624|197,777,992|24,688|483,412,476|

两者退出码 0，ELF machine=183 / ISA=2（ARM64），OAT 247、dex_count=21。`verify` 只预校验，不生成应用机器码；`speed` 有机器码，但不能因此声称所有方法都编译。完整产物哈希在 `results.json` 和各 `build.json`。

- 最终 verify odex：`adf3da4affa915cdca97c3b91b76a5fdecdc51b334f1bb17cd6e7b7a28ff6ed3`。
- 最终 speed odex：`f97d3191c2638feb8fa7d14d62b21f90d64df84d18fef97a7b6957036f5f5dbb`。
- 没有可用 profile，编译器明确提示 app image 无 classes；24,688 字节的小 .art 不是预装载大量应用类的证明。
- 两档仍有 `failed lock verification` 以及两个 Thread 相关方法的 verifier 错误；speed 另有 `X.RMX.<init>` 超 compiler instruction limit。原始日志完整保留；不通过修改 APK 或放宽验证消除这些警告。
- 首轮 verify-1/speed-1 未显式设置 OH 检查开关，**仅留档，不部署**。源 dex2oat 的既有 `WESTLAKE_EXPLICIT_NULL_CHECKS=1` 关闭隐式 null/suspend 检查；最终两档均设置并在日志中确认。该开关不改变 implicit stack-overflow 检查，不能声称所有隐式检查均关闭。源码依据见 source-excerpts.txt。

完整命令记录在各 `build.json`。复现新目录示例：

```sh
orb -m a2hlab bash -lc 'python3 /Users/zhaoyue/orca/workspaces/westlake-harness-aot42/benchmark/2026-09-25-toutiao-aot-42/build_aot.py --root ~/a2hlab/ws/out-aot42 --filter speed --name speed-repeat'
```

脚本校验冻结输入、编译器、APK 和 map32 哈希；拒绝覆盖已有输出。`inspect_oat.py` 按同源 OatHeader 247 布局读取 ELF .rodata/.text 与 metadata，不把字符串命中当作加载证明。最终工具整理只做输入校验和可读性改进，保留编译参数及环境开关。

## 后续上板步骤与判据

1. 外环明确分配板子后，检查只有本轮应用进程。复用 #38 最终一致的 native/framework/网络目标配置；先运行 `check_framework.py` 对照其 report，再核实际板上文件哈希。若 BCP/boot/libart 变化，重编两档；不跳过 ART checksum/context 检查。
2. 从已验 framework stage 建独立 stage，分别增加 `oat/arm64/toutiao.odex`、`.vdex`、`.art`；不得直接修改 #38 共享 stage。probe 的框架 stage 会复制进本轮 runtime，沙箱看到的路径为 `/data/local/tmp/asx/oat/arm64/toutiao.*`。权限/属主沿应用运行目录，实际部署后读回哈希。只写授权的临时目录与应用数据，不创建 `/data/misc/apexdata` 全局缓存。
3. class-loader-context 暂按正常 LoadedApk→ApplicationLoaders 的 `PCL[]` 编译：getPackageInfoNoCheck 传 null baseLoader，ApplicationLoaders 默认父为 boot loader。**尚未证明应用定制 ClassLoader/共享库不会改变实际 context**；板上出现 mismatch 必须按真实 context 重编，不使用跳过校验选项。
4. 三臂：无应用 odex 基线、verify、speed，各至少 3 轮。顺序交错（baseline/verify/speed；speed/baseline/verify；verify/speed/baseline），每轮新应用数据、相同网络/参数/同意流程；记录页缓存非冷启动这一限制，不清全机缓存影响其他人。无 odex 基线和 verify 不是同一臂。不得把保存同意状态的热启动与干净数据混比。
5. 每轮记录 APK/完整 stage 哈希、进程/TID、运行目录、有效 odex mappings、ART 加载或拒绝日志、活跃 compiler-filter。必须证明应用 odex 被接收并有可执行映射（speed）；仅文件存在、名字包含 oat 或 compiler 退出 0 不算。
6. 保存同意触摸 uptime、首次信息流正截图的采集起止 uptime（只能给区间）；固定同意后点击时点并核截图落在真实条目，不以宿主/弹窗画面作有效样本。uinput 前后读取同一板端 uptime，记录 queueMs、DOWN dispatch begin/end/handled、首次**行首** `[B47-SLA] ENTRY ...NewDetailActivity` 生命周期和后续 transaction 时间，配文章截图。settings JSON 中活动名子串一律不计；观察至少 40 秒，避免漏掉晚到的启动。若生命周期无精确 timestamp，给轮询区间，不能假称精确到毫秒。
7. 记录 UI 早退、work_thread SIGABRT、WebView 崩溃和无效点击；不剔除失败样本后称 n≥3。相同首跑时点是主要对照；等主线程空闲后的点击可单列，不能混入主要对照。

“Could not check odex”原始告警是全局 cache 的 **Permission denied**。它本身既不能证明没有 APK 邻接 odex，也不能单凭告警数断言全程解释执行。ART 的 `DexLocationToOdexFilename` 明确支持相邻 `oat/arm64/toutiao.odex`；全局 cache 探测仍可能打印权限错误。按原验收完整报告告警，若邻接 odex 确实加载但全局告警仍在，需外环判词，不通过隐藏日志或改全局权限达到表面“零告警”。

## 本次验证

`python3 benchmark/2026-09-25-toutiao-aot-42/verify.py` 校验原始证据哈希、构建返回值、两档元数据、九段 image 加载、汇总数字以及变更 framework 的拒绝行为。仓库已知答案测试按 loop.md 执行，结果见 evidence/tests.log。

二进制较大，不加入 Git；保留在 VM `out-aot42/{verify-explicit,speed-explicit}/toutiao.{odex,vdex,art}`，可按提交内哈希复核。原失败与首轮产物也留 VM。**当前设备轮数 0；queueMs/dispatch/详情页与首屏前后表暂未产生。** VM 部分完成，整体等待设备移交，ACK(blocked)，不是性能验收通过。
