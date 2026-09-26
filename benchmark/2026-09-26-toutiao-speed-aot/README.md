# Operator speed-AOT 增量配方（#42 复用，VM 完成）

**可复用原 `out-aot42/speed-explicit` 三件套，无需重编。** 当前保存的 operator framework/BCP 与 #42 的36项输入一致；当前 A1 libart 的差异已单独核查。VM产物哈希、离线安装/幂等验证完成，未占板、未启动应用。**当前稳定基线 + speed 的设备接收、崩溃率及提速均待验收**；待外环稳定性结论后一起部署，不能把#42旧数据当本轮结果。

## 同源性与当前基线

权威输入：

- `westlake-harness-triage46/benchmark/2026-09-26-toutiao-crash-triage/BASELINE.md`：当前shim为85c789f4（含#46 GLES与#49堆兼容处理），mc46 bridge为d4fae8e5，npth为8b8d559c，保留现场tt targets/LD_PRELOAD和启动前map_count。AOT模块不写这些文件或设置。
- VM `~/a2hlab/board/61b0657200000000000000000324012c/operator45/framework/device-report.json`，stage与报告SHA见 [verification.json](evidence/verification.json)。九个BCP jar、九组boot art/oat/vdex，共36文件逐项匹配 #42 的冻结副本。
- 较新的 `stub48/stub-r3/parent.log` 记录的 BCP顺序/locations/image仍相同：core-oj、core-libart、core-icu4j、conscrypt、okhttp、bouncycastle、apache-xml、framework、adapter-runtime-bcp。逻辑locations=`/system/framework/*.jar`；image=`/data/local/tmp/asx/boot/boot.art`。摘录见 [parent-bcp.txt](evidence/parent-bcp.txt)。这是已存证据，本任务没有实时读板。
- **不能只查旧framework report的libart**：现场A1为 `ae2cb1829ffa9eca08e1a0fe816edfc33bbe0e1ca3e2f43aaa99e522924a8937`，不是#42的009a08fb。`out-operator48/result.json` + art-build-operator48 `94f8195685b73c5254a719c78a06110f24f577fc` 证明：原454对象先重链复现009a08fb，只换 `stubs/link_stubs_arm64.weak.o`，其余453不动；源码差异只涉及应用native加载器兼容辅助函数及测试，没有改OatHeader、DexFile、编译器、ArtMethod布局或quick entrypoint。见 [lineage.json](evidence/lineage.json)。因此这项native加载改动不要求重编应用dex。此为源码/构建层兼容性结论，实际ART接收仍需设备证明。
- 指定同源工具 `out-aot42/tools/dex2oat` SHA=`8f9592174aa9d3f8b8f7e0d2879d15c6407e3c2f9f839346b8a8523c4434c7e3`；OAT247、ARM64、21 dex、filter=speed、context=`PCL[]`、BCP checksum=`i;9/aa28fa9b`。没有使用OAT230工具，没有跳过任何checksum/context校验。

Installer不仅核报告：还重新读取待打包runtime的36文件、当前A1 libart、原APK实际SHA。若外环最终换了ART/BCP/boot/APK，**此版本立即拒绝**，需重新评估/编译，不扩白名单放行。

## 产物与 SHA256

VM来源：`~/a2hlab/ws/out-aot42/speed-explicit/`。产物不加入Git。

| 文件 | 字节 | SHA256 |
|---|---:|---|
| toutiao.odex | 599929624 | `f97d3191c2638feb8fa7d14d62b21f90d64df84d18fef97a7b6957036f5f5dbb` |
| toutiao.vdex | 197777992 | `e6f5c1aaf69bdec6975fc08c238f6090f7ef1a0e784e098c9ee35d476748106d` |
| toutiao.art | 24688 | `5fc5662dd2f72cffa7157ebc62059a65fed83317f6c08e826d15671e3b7093c9` |

APK SHA=`a1112a0c941f865847c2fab9138cf815735268fbfcd41d697412fb80992c7395`，逻辑路径必须是 `/data/local/tmp/asx/toutiao.apk`。安装到其相邻 `oat/arm64/toutiao.{odex,vdex,art}`。`.text` 为483412476字节，#42实测r-xp映射483414016字节（页对齐）。24KB `.art` 不代表预装大量应用类；原构建保留verifier警告及个别超大方法未编译，不声称全方法AOT。

## 幂等安装与稳定配方衔接

当前native基线准备完之后，通过稳定配方目录的增量入口调用：

```sh
orb -m a2hlab bash -lc '
  bash /Users/zhaoyue/orca/workspaces/westlake-harness-speed50/benchmark/2026-09-26-toutiao-stability-recipe/apply_speed_aot.sh \
    "$HOME/a2hlab/ws/out-final-operator/toutiao-runtime" \
    --framework-report "$HOME/a2hlab/board/61b0657200000000000000000324012c/operator45/framework/device-report.json" \
    --bundle "$HOME/a2hlab/ws/out-aot42/speed-explicit" --dry-run
'
# 同一命令去掉 --dry-run 执行；两次执行字节一致。
```

参数是**未运行、已解包的本地runtime打包树**，含fw/boot/libart/toutiao.apk/run.sh，不是仅namespace launcher目录。脚本不调用hdc，不写板子；预检全部输入后只追加三件套与 `.speed-aot/{receipt.json,SHA256SUMS,apply.lock}`。不改run.sh、原生库、应用数据、targets、LD_PRELOAD或sysctl；遇已有不同AOT拒绝，避免混入verify/其他版本。复制逐文件原子替换并读回SHA；文件0644、目录0755，root运行时跟随APK uid/gid。打包/部署工具仍须保持应用属主、SELinux上下文和可读性，设备上读回核验。

当前shim85c789f4已超出早期稳定配方v1的ecc7b12c范围，**不要为启用AOT重新运行旧 `apply_all_fixes.sh`**。用新增 `apply_speed_aot.sh` 即可。本分支在原稳定配方提交fa18bdd上追加AOT模块，不重新定义native基线，也不选择任何尚在验证的稳定性候选。

部署方最后复制三文件到对应operator runtime的 `oat/arm64/`，启动前从runtime根执行：

```sh
sha256sum -c .speed-aot/SHA256SUMS
```

继续沿用当前已授权的native基线启动包装与map_count钩子。必须新启动ART进程才能观察新AOT，不能用已打开旧APK/oat的常驻进程证明生效。若复制被打包器覆盖或未被接收，按日志修正输入/路径，不禁用ART校验。回退对照用另一份没有这三文件的runtime，避免边跑边移走映射文件。

## 设备接收与速度断言

保存实际runtime三件套/38输入SHA、完整child.stderr、同PID maps、PID/starttime及原生基线回执。

1. ART必须出现行首 `[IMG] Loaded /data/local/tmp/asx/oat/arm64/toutiao.art at ...`，并在同PID maps出现 `r-xp .../oat/arm64/toutiao.odex`，大小至少覆盖483412476字节。同时检查oat_file/assistant的checksum/context拒绝信息。仅文件存在、编译成功、或全局“Could not check odex”权限告警都不是接收结论。
2. `python3 verify_acceptance.py child.stderr maps.txt` 联合检查两份接收证据。此工具已用#42历史speed轮验证：app image=1，执行映射483414016；**那是历史回归夹具，不是当前基线已验证**。工具只判接收见证，不判稳定性/提速；完整日志仍须查看其他加载失败。
3. 当前相同native/Java基线，无AOT与speed两臂交错，各≥3个有效条目点击；建议B/S、S/B、B/S。新旧数据策略、网络、同意后点击时点、文章类型和page cache条件匹配。不能把warm第二篇与cold首篇混算提速。记录所有退出/无效输入，另报尝试数及成功数。
4. 同一板端uptime记录uinput起止；从真正的 `[B47-SLA] ENTRY ...NewDetailActivity` 与RESUMED/transaction行提取时间，同时记录该条目DOWN queueMs、dispatch耗时、正文截图。若RESUMED只由轮询发现，报告区间/误差，不能拿宿主或任意日志里的活动名充数。
5. 输出表：臂/轮次、进程、AOT接收、uinput uptime、RESUMED uptime或区间、差值、queueMs、dispatch、正文可见/存活、退出信号。要求speed条目时间相对同批baseline约减半，且正文/稳定性无回退。继续把原生崩溃分开分类，AOT性能成功不能抵销退出。

## 预期收益与验证状态

#42有效点击：baseline=12.379/22.169/12.782s（n=3），speed=7.240/5.833s（n=2），都是uinput→RESUMED。中位数12.782→6.5365s，约49%下降，**仅用作本轮约6–7s、约减半的预期**。旧组合崩溃截断样本，不能从中证明统计稳定收益；更不能承诺当前文章/热启动也固定减半。#49处理了相关原生故障方向，speed叠加后的稳定性仍需实测。

本次VM：36项BCP/boot核对、当前A1库哈希与构建来源审计、compiler/三产物SHA重算、OAT结构读取、启动BCP顺序核对全部通过；真实文件安装/二次幂等、run/libart保持字节不变、SHA清单核验通过。夹具 `~/a2hlab/ws/out-speed-aot/verify-f9f3q4kp/`；umask077下目录0755/文件0644核验通过；3项输入失配/路径/接收见证测试通过，69项已知答案测试OK（2 skipped）。未运行设备、没有新RESUMED时间、不声称本轮提速已经实现。
