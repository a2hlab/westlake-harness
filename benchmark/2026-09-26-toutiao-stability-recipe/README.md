# 头条稳定性集成配方（#46 → #27 / operator）

此配方固定今晚 **ability38 + wv46 + mc46 + npth + 四名 tt targets** 的组合，并加入启动前 `vm.max_map_count >= 1048576` 钩子。适用头条13.9.0的已有 ability38 **runtime 根目录**，其中含 `run.sh`、应用 `lib/arm64-v8a/` 和 `webview-t-lib/`。它不是只有 framework 的 stage，也不是只有 namespace launcher 的 `/data/local/tmp/a2hlab-app-*` 目录。

本次只做离线打包与验证，没有连接板子。二进制不复制进 Git；完整来源、原件/候选 SHA256 在 [fixes.json](fixes.json)。应用回执在 stage 的 `.stability46/receipt.json`；设备启动前可用的清单在 `stability46/SHA256SUMS`。

## 四项来源与覆盖位置

路径均相对于 runtime 根目录（应用内映射为 `/data/local/tmp/asx`）。源产物均位于 VM `~/a2hlab/ws/`。

| 项 | 来源提交 | 源产物 | 覆盖路径 / 行为 |
|---|---|---|---|
| wv46 | westlake `87fb17b6311e87a42b3671297595872d81f3f1b4` | `out-wv46/patched/libwebview_bionic_shim.so` | `webview-t-lib/libwebview_bionic_shim.so`；GLESv2→平台GLESv3重定向先于探测返回 |
| mc46 | westlake `ddb2f480e2b70af3e338304602ffe0f4b12c84bd` | `out-mc46/patched/liboh_adapter_bridge.so` | `liboh_adapter_bridge.so`；不支持的视频codec按可捕获异常返回，补getOwnCodecInfo注册 |
| npth | harness `12a617ed8e71749c6bd3eeb3d926ae46c0f5b3ab` 的 `patch_npth.py` | `out-npth46/libnpth.so` | `lib/arm64-v8a/libnpth.so`；固定APK版本的Bionic线程遍历在musl下自环，入口0x17930四字节改RET，不采集这份不兼容线程链 |
| tt四名 | harness helper `e878597043fee4f8bdaa5ae533e71127b84b7060`；四名实测部署记录 `e5e577b` | run.sh策略，无新二进制 | 保留原targets，追加去重：`libttcrypto.so`、`libttboringssl.so`、`libdelta.so`、`liblynxsecurity.so` |

候选完整 SHA256：

```text
ecc7b12c3591c979f3d9aece5bb1d414acc04d01d2c500a88364525082f9df9f  webview-t-lib/libwebview_bionic_shim.so
d4fae8e5802f3153a85175243edf665714900381d463ffc5ca1e64d0b308775b  liboh_adapter_bridge.so
8b8d559c50130a997b5fbf3383e8ebf6291ebe54ab2b5ed5fbc8e1ac73fe36af  lib/arm64-v8a/libnpth.so
```

tt helper SHA=`a1ea102c785c4eb6132350a93544f05bae38da693ba31f9078052f960a2f159b`。实测原run SHA=`65530f5cec5249c71ff03399a4fb78a5f3b9a264fd621be9bac6e5aace6e075c`，仅四名变换后=`e166b07cbad67122bccee331c38f581c655333b2cd319f4703c94e6c2735c0a9`；本配方加sysctl检查后，该参考run为 `1137344ea5308dd00067283351ada9753d390eeac3b73caae3611cdb9ead5832`。其他窗口ID/启动参数不同的run会有不同SHA，以回执为准。**不使用另一个新增15库闭包候选**。

## 应用配方

在 VM 准备**独立、未运行的本地打包目录**。本工具不下载、不编译、不调用hdc、不改本机sysctl。Python3负责哈希、校验和原子换文件；上板用的两个启动脚本仅需OH shell。

```sh
# Mac发起；将路径换为自己的runtime打包目录。
orb -m a2hlab bash -lc '
  bash /Users/zhaoyue/orca/workspaces/westlake-harness-recipe46/benchmark/2026-09-26-toutiao-stability-recipe/apply_all_fixes.sh \
    "$HOME/a2hlab/ws/out-my-integration/toutiao-runtime" --workspace "$HOME/a2hlab/ws" --dry-run
'
# 核对输出后，同一命令去掉 --dry-run 即应用；重跑不会重复追加targets或hook。
```

应用时先核全部源文件SHA、目标基线SHA和run格式，再写任何文件。二进制只接受 [fixes.json](fixes.json) 中的旧SHA或候选SHA；未知版本报错，不会强制覆盖。原件按内容SHA备份到 `.stability46/backups/`，每个文件原子替换后重算SHA，最后生成回执与启动校验清单。原有模式保留；root运行时保留目标owner。整个目录不是多文件事务，异常中断后保留已核验单文件和原件备份，可修正故障后重跑。拒绝指向目录外的符号链接。

**#27已有其他bridge改动时**：不能用这份老mc46 bridge覆盖。脚本会拒绝未知SHA；应先在#27源码集成wv46/mc46提交并按最小单元重编，经复验后另出新配方版本及新哈希，不扩充白名单来掩盖回退。npth补丁同样只对应锁定APK版本。不要对运行中实例做原地覆盖。

打包器需要把整个runtime（含 `stability46/`）保留下来；若重新生成run.sh、重新解压APK lib或重建webview-t-lib，**在这些步骤之后再应用一次配方**，避免打包器覆盖已修内容。部署后、启动前核 `sha256sum -c stability46/SHA256SUMS`；启动包装也执行同样校验。

## 启动前 map_count 钩子

`stability46/run-with-fixes.sh` 接收原始启动命令及其argv：先核六个关键文件的SHA，再调用 `prelaunch_map_count.sh` 设置并读回 `/proc/sys/vm/max_map_count`，成功后 `exec` 原命令。值低于1048576时设为1048576，已有更高值不降低；失败则停止启动。此设置是**设备全局且重启失效**，不写持久配置。钩子输出原值/新值供归档。

必须在仍有权限的外层启动、`source_app_namespace` 降权之前运行。以下为**移交给部署方的设备shell命令模板，本任务未执行**，变量取自该实例device-report：

```sh
runtime=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-INSTANCE
launcher_stage=/data/local/tmp/a2hlab-app-INSTANCE
launch_uid=20010053
nohup /system/bin/sh "$runtime/stability46/run-with-fixes.sh" \
  "$launcher_stage/source_app_namespace" "$runtime" "$launch_uid" \
  /system/bin/sh /data/local/tmp/asx/run.sh \
  >"$launcher_stage/parent.log" 2>&1 </dev/null &
```

保留原socket等待、host_spawn、前台化/触摸流程；只给原 `source_app_namespace ...` 命令加外层包装。operator常驻重启循环每次都走同一包装，避免板重启后遗漏设置。**不要在应用UID里直接调用写sysctl的包装**；配方插入run.sh的仅是 `--check`，低值立即退出并提示外层包装缺失。`prelaunch_map_count.sh --file <普通文件>`只用于离线夹具，正式部署不用此参数。

## 上板验证清单

每次记录配方回执、设备六文件SHA、parent日志的 `STABILITY46_MAP_COUNT_PASS`、child PID/starttime、完整child.stderr、真实输入时间、截图与maps/RSS曲线。至少按今晚流程同一进程打开5篇不同的带视频文章，每篇正文停留≥120s，另看信息流与非视频文章。视频封面可见不等于视频解码播放通过。

针对**同一child完整生命周期日志**执行以下grep断言（grep零命中本身返回1，手工统计时注意）：

```sh
grep -c 'GLES library translated libGLESv2.so -> /system/lib64/platformsdk/libGLESv3.so' child.stderr  # 1
grep -c 'GrGLInterface creation failed' child.stderr        # 0
grep -c 'InitializeGL failure' child.stderr                # 0
grep -c 'UnsatisfiedLinkError' child.stderr                # 0；有残留就明确失败
grep -Ec 'SIGTRAP|Fatal signal 5\b' child.stderr           # 0
grep -E 'No implementation found.*getOwnCodecInfo' child.stderr  # 无
```

每10s保存同一PID的uptime、`wc -l /proc/<pid>/maps`、VmRSS、当时max_map_count，CSV列为 `uptime,maps,rss_kib,swap_kib,mem_available_kib,limit`。检查曲线覆盖整次会话、每行 `0 < maps < limit`，limit≥1048576；记峰值和末段趋势，不能用一个低值采样宣称没撞顶。最后核parent退出状态，避免未输出Fatal横幅的退出被漏掉。

```sh
python3 verify_logs.py child.stderr maps-curve.csv
```

该工具拒绝空日志（必须恰有一次GLES翻译）、空/非递增曲线、撞顶、ULE或SIGTRAP；退出0仅表示列出的日志/曲线断言通过。仍须人工核PID/时间范围、真实页面、输入/生命周期对应、存活和信号退出。若为文章窗口另切日志，必须明确标窗口，不替代全生命周期统计。

## 已知边界与本次验证

今晚依据 `feat/ability-focus-38` 的 `bab3fc0d202e2feb4f09ffd80ae3f1b3f4dc0a74`：五篇正文持续可读、各窗口>120s、SIGTRAP=0；maps峰21792，低于新上限也低于旧65530，所以不能证明提高上限是存活原因。完整child仍有metasec加载ULE及work_thread SIGABRT横幅，五篇窗口ULE=0，**全局ULE=0尚未达成**。ttcrypto/ttboringssl仍各两份映像，四名targets没有根治TicketGuard。视频播放、评论网络、<2s性能SLA和长期稳定性均不在本配方的已通过声明中。

本次离线验证：真实三产物SHA全部匹配；源/目标原件备份核验；首次应用、二次应用字节完全一致；targets-only输出与今晚实测run一致；启动哈希清单自检通过；普通文件模拟sysctl设置/读回与低值拒绝；6项失败路径/幂等测试通过。真实fixture记录见 [smoke.json](evidence/smoke.json)。**未上板，不声称本次新增的启动包装或设备验收已实测通过。**

## v2:#47 AAssetManager 族并入(aasset47,2026-09-26)

`fixes.json` 升 `toutiao-stability-46-v2`:新增第 4 个 binary 条目 `aasset47`——
- source:`out-aasset47/webview-candidate/webview-t-lib/libandroid.so`(commit `eaa814b`,westlake 分支 `fix/webview-ndk-assets-47`)
- destination:`webview-t-lib/libandroid.so`;original=sp20 候选的 52 导出/0 AAsset 变体;patched=70 导出/18 AAsset\*(含 `T AAssetManager_fromJava`)
- 动机:c40 三 app(burgerking/co-candycrushsaga/co-discord)的首阻塞 `Error relocating … AAssetManager_fromJava: symbol not found`,修复把 20 个 AAsset 入口(AOSP14 语义)植入该 libandroid 边界并懒转发到每次 stage 已部署的 `libwestlake_asset_bridge.so`(14 个 `wl_AAsset*`)。

验证:配方单测 6/6;合成 stage(真实基线字节,四 destination 齐)`apply_all_fixes.py --dry-run` 通过——plan 接受 v2 全部四条目并输出 8 项更新(四 binary+run.sh 改写+两 hook+SHA256SUMS)。板上生效断言(等外环分配板):三 app `AAssetManager_fromJava: symbol not found` 计数=0、首阻塞前移。
