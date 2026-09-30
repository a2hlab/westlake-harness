# 5ea 部署预备:graphics-session-sync 32df 单文件替换(cc-wiki #80)

纯 Mac 侧准备,**未碰板**。放行(黑板『5ea 放行 cc-wiki』)后按本 PLAN 执行。
截图是地面真相,每个结论贴 t20 路径 + facts 行(FLAW-007)。

## 变更本体(单文件替换,不是整包升级)

| 项 | 值 |
|---|---|
| 板 | `5ea34a4500000000000000001123012c` |
| 预备 boot | `51812b02-ec64-4d36-821c-ffd94531fb45`(部署前须复核仍是此 boot) |
| 包 | `/Users/zhaoyue/orca/workspaces/westlake-runtime-graphics-session-sync-32dfac83-5ea` |
| Manifest SHA256 | `30f63ef76b14a8ba2c1334940c66f5cc0e98aa4862152b81e6379f35d0b62c12` ✔ 核对匹配 30f63ef7 |
| 替换目标 | `/system/android/lib64/liboh_android_runtime.so` |
| 新 runtime SHA256 | `32dfac830320394d0b62781afcde68537d3b5fff372b5170d7a53baa069013b7` |
| 回滚 runtime SHA256 | `9e14bf2005290c6e9e689fa779a1019bfcded7436c3a36d7a4973f462f46cd0f`(v3c 现驻) |
| 5ea dry-run | passed=True, file_count=281, device_io=False(`handoff/evidence/dry-run-5ea.json`) |
| 账本 | `/Users/zhaoyue/orca/workspaces/westlake-generation-state/5ea.../51812b02-...-74d1d6d48210.json`,现引 v3c 668e4f7c,active_verified,零 single_replacement |

只有 runtime 9e14bf20→32dfac83 变;installer/host/ANL/TLS/Java 字节不动。

## JAR overlay 纪律(部署前后必做)

现驻 overlay = **r17p a0ed5c4f**(bind-mount);generation baked = **r8b d5000c4e**。
native 替换前先 retire overlay 回 baked,替换后原样 restore 并校 SHA。

| 项 | 值 |
|---|---|
| overlay SHA(restore 后须等于) | `a0ed5c4fedd952762256a24ab7801deb3ad6e696a0204853ce5000316336d173` |
| baked SHA(retire 后应回到) | `d5000c4e19e74e3ec7a72300ed425fa2c5ba521aa4b04cb6e688e165e6ba5554` |
| restore 本地源 | `/Users/zhaoyue/orca/workspaces/vm-copies/r17p-a0ed5c4f/oh-adapter-runtime.jar` |
| 现驻 receipt | `benchmark/2026-09-29-wikipedia-line/deploy/r17p-after-hwui-rollback/receipt.json` |

## 权属分工(关键)

`deploy_generation.sh --replace /system/…` = 板上 /system 写,**我的分类器拦** → **外环跑**。
JAR overlay retire/restore 走 `deploy_jar.sh`(userspace bind-mount)= **cc-wiki 跑**。
读操作(boot/SHA 复核、启动、截图、facts)= cc-wiki 跑。

## 执行序(放行后)

**S0. 取锁 + 只读复核(cc-wiki)** — 不满足任一项即停,黑板报警:
```sh
S=5ea34a4500000000000000001123012c
hdc -t $S shell "cat /proc/sys/kernel/random/boot_id"        # 须 = 51812b02-ec64-4d36-821c-ffd94531fb45
hdc -t $S shell "sha256sum /system/android/lib64/liboh_android_runtime.so"   # 须 = 9e14bf20…(现驻 v3c)
hdc -t $S shell "sha256sum /system/android/framework/oh-adapter-runtime.jar" # 须 = a0ed5c4f…(现驻 r17p)
# 账本 status=active_verified 且无 single_replacements
```
boot 或 active SHA 变了 → 用 `prepare_for_base.py` 对新 active 重新预备,勿用陈旧预备(BOARD-HANDOFF 明示)。

**S1. retire JAR overlay r17p → baked d5000c4e(cc-wiki,deploy_jar rollback)**
```sh
benchmark/2026-09-29-wikipedia-line/deploy_jar.sh rollback <r17p-receipt-dir>
# 校:effective SHA 回到 d5000c4e…;mount layers 减 1
```

**S2. deploy_generation --replace(外环跑;黑板贴完整命令)** — LANE=cc-wiki 持锁车道:
```sh
/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/scripts/lab/deploy_generation.sh \
  5ea34a4500000000000000001123012c \
  /Users/zhaoyue/orca/workspaces/westlake-runtime-graphics-session-sync-32dfac83-5ea \
  --replace /system/android/lib64/liboh_android_runtime.so --lane cc-wiki
```
脚本自带 maps/SHA 门禁(见下);不过则 RuntimeError,须先 --rollback。

**S3. maps 检查项(deploy_generation 自动核 + cc-wiki 复看 out/maps.txt、sha256.json)**
- child `/proc/<pid>/maps`:`libart.so`、`libopenjdkjvm.so`、`liboh_adapter_bridge.so` 均在
- `liboh_adapter_bridge.so` **仅**映射自 `/system/android/lib64/liboh_adapter_bridge.so`(单份),bridge SHA==`84695d62…`
- 替换文件 device SHA==`32dfac83…`(**不得**残留 9e14bf20);单份 ART
- gate.passed==true 且 sha256_passed==true(否则脚本已抛错)

**S4. restore JAR overlay r17p(cc-wiki,deploy_jar deploy)**
```sh
benchmark/2026-09-29-wikipedia-line/deploy_jar.sh deploy \
  /Users/zhaoyue/orca/workspaces/vm-copies/r17p-a0ed5c4f/oh-adapter-runtime.jar \
  a0ed5c4fedd952762256a24ab7801deb3ad6e696a0204853ce5000316336d173 \
  r17p-restore-after-32df <receipt-dir>
# 校:effective(shell)与 effective(appspawnx)均 = a0ed5c4f…
```

**S5. 测试矩阵(cc-wiki;每条贴 t20 路径 + facts 行,FLAW-007)**
顺序:先对照,再目标,再图形墙群。
1. **helloworld(对照)** — 必须仍 lit(证明 32df 没伤基线)。ZZ(zigzag)只记不判(5cd 上因 libmediandk.so 缺失死,与图形无关)。
2. **wikipedia 欢迎页** — t5/t20 都截。预期:5ea 双建 abort 若被 32df 解 → 过渲染墙,像 61b 一样露 tagsoup 终墙(首屏未稳定,feed 上屏)或直达欢迎页。读图判,别预设。
3. **fd-AppManager / fd-k9 / fd-tusky** — 原 BLAST-white,读 t20 看是否出图(5cd:AppManager 出 splash『正在验证』、k9/tusky alive t20=yes 未读图)。
4. **newpipe / noice** — newpipe(conscrypt 已修,ACRA onAbilityDied SIGKILL)、noice(hwui exit134);看 32df 是否改变。

**回滚(任一 regression:helloworld 不 lit / 目标退化)**
```sh
# a) cc-wiki:retire r17p → baked
benchmark/2026-09-29-wikipedia-line/deploy_jar.sh rollback <r17p-receipt-dir>
# b) 外环:撤销 native 替换(回 9e14bf20)
/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/scripts/lab/deploy_generation.sh \
  5ea34a4500000000000000001123012c \
  /Users/zhaoyue/orca/workspaces/westlake-runtime-graphics-session-sync-32dfac83-5ea \
  --replace /system/android/lib64/liboh_android_runtime.so --rollback --lane cc-wiki
# c) cc-wiki:restore r17p a0ed5c4f(同 S4)
```

## 5cd 基线(cx-t0 32df+r17q,graphics-32df-r17q-5cd)

facts(原样,cx-t0 evidence/facts.txt):RUNTIME fingerprint=4b2e19554149;9 key,18/18 截图,alive_t5=8 alive_t20=8。
- fd-AppManager/fd-auxio/fd-droidify/fd-k9/fd-mobile/fd-tusky/helloworld/termux 全 `alive t5=yes t20=yes`;zigzag `t5=no t20=no`。
- observations:8/8 应用 `OH_GfxShim: BLASTBufferQueue registered 13/13`;auxio/droidify/AppManager/mobile 有 `SC.create sessionId`。zigzag first_fatal=`libtuanjie.so 需 libmediandk.so`(ULE,与图形无关)。

**cc-wiki 自读 5cd t20(FLAW-007,5cd 非我板)**:
- fd-AppManager:自身 splash 出图『App Manager / 正在验证… / 4.1.1(451)』——BLAST-white→splash,但卡验证,非主列表。
- termux:**纯白**(仅状态栏)——alive t20=yes 但白。
- helloworld/auxio/droidify:外环报『已出图』;cc-wiki 未读原图(以 cx-t0 facts alive t20=yes 计)。

**结论**:32df 让多数图形会话从全白恢复到出图(每会话独立 SurfaceControl),但**非万能**——termux 仍白。5ea 上逐个读图判,勿照搬。

## 待外环
- 放行信号:黑板『5ea 放行 cc-wiki』。
- S2/回滚 b 的 deploy_generation 由外环跑(我黑板贴命令)。
