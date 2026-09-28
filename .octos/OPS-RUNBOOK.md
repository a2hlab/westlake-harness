# 实验室操作手册(怎么操作机器)

`KNOWLEDGE-DIGEST.md` 记**学到了什么**;本文件记**怎么操作**;脚本在 `scripts/lab/`(`westlake-inputs` 的版本化镜像,见其 README)。
凭据(WiFi 密码、服务器账号)不写在这里——仓库是公开的。

## 1. 机器与访问

**Mac(控制端)**
- hdc:`/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc`。`-t` 必须用**完整 connect-key**,8 位前缀会报 `Not match target founded`:
  `5ea34a4500000000000000001123012c`、`5cd1e3dd00000000000000000923012c`、`61b0657200000000000000000324012c`。
- 板子经 hub 接 USB,provision/remount 瞬间掉线过多次,最长 50 分钟不回,只能物理重插。演示前尽量直连。
- 环境:`source ~/orca/workspaces/westlake-inputs/env-mac.sh`(cc/readelf/sha256sum shim + mise 固定的 JDK/Python)。有它 67/69 测试过,没有它 2 fail 4 error。
- **shell 陷阱**:`ls`=eza(带 OSC-8 超链接)、`du`=dust、`grep`=ugrep(复杂正则会超限)、`cat`=bat → 解析输出时用 `/bin/ls`、`/usr/bin/grep`、`command du`。zsh **不拆分 `$var`**(用 `${=var}` 或数组/glob),把整串当一个文件名且被 `2>/dev/null` 吞掉时会得到"假干净"。macOS 自带 bash 3.2 没有 `mapfile`。
- `pgrep -f`/`pkill -f` 会匹配到自己的命令行(在 `hdc shell "…"` 里计数恒 +1)→ 用 `scripts/lab/stop_by_pattern.sh` 或 `pgrep -f '[x]yz'`。

**OH 板**:DAYU600,OpenHarmony 6.1.0.31,1200×1920,纯 64 位用户态。板上 toybox 没有 `awk`/`tr`/`ip`/`route`/`wpa_cli`/`ndc`;hdc shell 是 root、`u:r:su:s0`(permissive)。

**构建 VM `a2hlab`**(OrbStack,Ubuntu 24.04 amd64 走 Rosetta)
- 工作区 `~/a2hlab/ws`,以作者原路径 `/home/dspfac/a2hlab/source-closure/verify/out` bind mount(哈希才对得上 manifest 记录;**VM 重启后要重挂**)。manifest 克隆 `~/a2hlab/manifest`,本地分支 `local-pins-main`。运行时源码是私有 `a2hlab/westlake`(verify 构建基于 main `22b9453`),不是 `A2OH/westlake`。别碰已有的 `oh7x86` 机器。
- 没有 USB → VM 里的工具用 `scripts/lab/hdc_mac.sh` 转发到 Mac 的 hdc。
- **Mac 侧 `~/OrbStack` 视图会消失**(2026-09-28:OrbStack 在跑,VM 里 `/Users/zhaoyue/OrbStack/a2hlab/...` 看得到,Mac 上 `~/OrbStack` 只剩 README、`mount` 里没有 NFS)。旧 `hdc_mac.sh` 从 VM cwd 调用时 Mac 侧 `cd` 失败,**所有 hdc 命令都失败**。现版先 `mac test -d ~/OrbStack/a2hlab/home` 探一次:视图在走原映射;不在就把 `file send`/`install` 的本地参数拷进 `/Users/zhaoyue/.cache/hdc_mac.*` 暂存、`file recv` 收进暂存再拷回 VM(保留远端文件名),用完删除。判路径可见性要在 Mac 侧判,VM 侧 `-e` 永远为真。恢复视图需重启 OrbStack(会重启 VM,重挂 bind mount)。
- VM 没配 git 身份,提交时 `git -c user.name=… -c user.email=…`。`orb -m a2hlab bash -lc '…'` 嵌套引号遇到撇号/heredoc 会坏 → 把脚本写到 `~/OrbStack/a2hlab/home/<user>/…`(VM 里同一个文件)再执行。
- GitHub/PyPI 网络不稳,huaweicloud 镜像可靠;a2hlab 的 LFS 超额,缺的包从原始公开源补并校验哈希(记在 lock 的 `local_substitution`)。

**构建服务器 `ssh hw248`**(共享 x86,网络快)
- 有板子同版 OH 6.1.0.31 源码 `/opt/build-trees/oh610_lts_source`(产品 wukong100,`out/wukong100/gen` 有 IDL 生成物)、NDK r27c、AOSP14/16 源码树。
- **规矩**:OH 源码树一律只读;只在自己新建的 `/opt/build-runs/<日期>-oh6.1.0.31-<主题>/` 下写(目录名必须写明 OH 版本),只拷需要的文件,自带 CCACHE_DIR;共享树里不跑 `hb build`/`prebuilts_download.sh`;不碰别人的 lock 和 home。**绝不混入 OH7**(`/a2hlab/ohos/*7.0*`)。

**安卓参考机** `N100CU025C18D000128`(UNISOC,Android 16 userdebug,1200×1920,`su 0` 可用;adb 在 `~/Library/Android/sdk/platform-tools/adb`)
- 预装头条 13.9.0 与语料 APK 逐字节相同,**别重装**。机上有用户自己的头条数据:`pm clear` 前先 `su 0 tar --selinux --numeric-owner -cf` 备份 `/data/user/0`、`/data/user_de/0`、`/data/media/0/Android/data` 下该包,**并记录 `dumpsys package` 的运行时权限**(pm clear 会重置,曾经没记导致无法恢复)。
- 两个窗口会吃点击:系统通知授权弹窗、二次启动 ~8 s 的登录推广页;`mCurrentFocus` 是它们时按 BACK。点"热点"会滚动 tab 条,固定 x 坐标会点到别的 tab。
- 很可能就是第 4 块 D600(与 OH 板同 SoC uis7885),其 `/apex/com.android.runtime`、`/apex/com.android.art` 可作 arm64 Bionic/ART 来源(推断,未证实)。
- 计时:atrace 主线程 `deliverInputEvent … eventTimeNano=`;screenrecord 内嵌 Winscope 轨可把 `date +%s.%N` 对齐到帧。报告在分支 `analysis/android-reference-26`。

## 2. 新板上手

1. `scripts/lab/board_setup.sh <serial>`:从 Mac 同步时钟(板子开机是 1970,TLS 会坏)、`power-shell timeout -o 86400000`(默认 30 s 灭屏会把锁屏盖到 app 上;2147483647 会被静默拒)、上滑解锁、装 host HAP、建 framework stage(那串没有文档的 stage 参数就在脚本里)。
2. 固件门:`probe_framework_vm.py` 要求板上 47 个库与 `westlake/native/oh61-firmware-abi.json` 哈希一致,即作者那份 6.1.0.31 镜像;OH 7.x 过不了。报告 `framework-N/device-report.json` 需 `passed=true`(files=306)。老的 framework 目录可能已被删,重建到新的 out 目录。
3. 网络:板上没有 WiFi 命令行,在板子 UI 上切网;保存过的网络和 IP 会变,别写死。**判网看 app 屏幕,别看 `hdc shell ping`**(shell 走 main 路由表,app 走 per-network 策略路由,见 DIGEST F)。

## 3. 头条

- 上屏:`bash benchmark/2026-09-27-device-provisioning/provision_toutiao.sh <完整 connect-key>`。热板 25–40 s、刚开机 90–150 s 到 READY+feed。交付包在 `~/a2hlab-provision/ttbundle`(MANIFEST 校验)。脚本 150 s 窗口在刚开机的板上会超时误判 FAIL,**以截图为准**。
- 状态:`/data/local/tmp/operator45/selfheal48/state`(重启不清,先删再验);黑屏先看 ZOrder:`hidumper -s WindowManagerService -a '-a' | grep -E 'SCBScreenLock|imehost0'`。截图:`snapshot_display -f /data/local/tmp/x.jpeg`(后缀必须 .jpeg)再 `hdc file recv`。
- 首启会弹"个人信息保护指引",点"同意"(`uinput -T -c 595 1270`)。
- 13 图标常驻 demo(61b):开机后 `persist_demo.sh 61b06572 up`(参数顺序 `<SERIAL> <CMD>`)。
- **别在唯一能用的演示板上做实验**(重启测自启、删运行时目录都会让头条下屏)。清理别的 app 时豁免两个 `c91d26bf` 目录(DIGEST F)。

## 4. 新 app

`probe_source_app.py`(VM `~/a2hlab/manifest/tools/`),可用的完整命令见 `benchmark/2026-09-27-app-breadth-sweep/sweep_config.5ea34a45.sh`,坑见 `benchmark/2026-09-27-bridge-demo/README.md`。不重新 stage 直接重拉见 `benchmark/2026-09-28-persistent-demo/README.md`。**亮不亮只看截图**(alive≠LIT)。

## 5. 构建

- 全量:`scripts/lab/rebuild_all.sh`(约 40 分钟,可续跑)。主机 dex2oat 在 Rosetta 下需 `LD_PRELOAD=~/a2hlab/tools/libmap32bit.so`(源码 `scripts/lab/map32bit_shim.c`),否则 oat/vdex 与记录对不上。westlake 的 libart/boot.oat 是 **oat 247**,AOT 必须用 westlake 自己的 host dex2oat(AOSP 的是 oat 230)。
- **只重建受影响的最小单元**(#36):改一个文件只重编那个 .so + relink,下游只在输入真变了才重跑。单库:`tools/build_android_native.py --workspace <verify> --out <dir> --target ohos --library liblog.so`(库名要带 `.so`)。
- #27 全修复集成构建:westlake 工作树 `~/a2hlab/ws/westlake-all0925` 的 `tests/integrate-all-0925/`(不在本仓库),产物 `~/a2hlab/ws/out-all0925`,空目录重建约 8 分钟且确定性。**WebView 打包坑**:`package_webview_gpu_candidate.py` 只从 shim 构建取 plat_support,`libandroid.so`/`libwebview_bionic_shim.so` 来自基础载荷 → shim 修复不覆盖就进不了候选包,打包后用 verify.sh 核哈希。
- 从目录名不同的工作树构建会改变 libart 等的字节(路径串躲过了 `-ffile-prefix-map`),功能无差异。
- WebView 输入不用编 Chromium:引擎 = AOSP android-13.0.0_r80 预编译 arm64 + 11 处 `.dynstr` 导入改名(逐字节可复现);APK = 该预编译 + westlake smali 类作 classes2.dex,本地签名;4 个边界库来自 `westlake-inputs/tools/scratch/build_webview_shims.sh`(scratch 未镜像)。载荷在 `out/webview-input-source`。集成候选包预期哈希:libandroid 76512d97…、bionic shim 4b19a817…、plat_support aef81ea2…。
- **小 native shim 不一定进 VM**(2026-09-28 实测,GLESv1_CM stub 同源同参数三处编译):
  - Mac 本机:DevEco 自带 OH clang `…/sdk/default/openharmony/native/llvm/bin/clang --target=aarch64-linux-ohos --sysroot=…/native/sysroot`,导出集合与 VM 产物一致,但**字节不同**(DevEco 编译器提交 `99548401`,VM 锁定的是 `feef13a3`,差在 `.comment`)→ 适合快速迭代,不适合要对上记录哈希的交付物。zsh 下参数串要 `${=FLAGS}`,否则 `-shared` 丢失、报 `undefined symbol: main`。
  - OrbStack docker(`--platform linux/amd64`,如现有镜像 `oh7-native-closure`)+ 把 VM 的 `~/a2hlab/ws/toolchains/ohos-sdk/native/{llvm,sysroot}`(2.3 GB,`orb … tar | docker run -i … tar -x` 约 9 s)拷进 volume → **逐字节复现** `a1ae3950…b37bf`。VM 里的 `clang` 是 `exec ccache <绝对路径>/clang-15` 的包装脚本,容器里直接调 `clang-15`。
  - 所以 VM 不是能力上必需,而是 346 GB 的工作区状态(verify 树、out-*、锁定工具链)都在那里;大件(libart、boot image、全量重建)仍在 VM 或 hw248 上做。
- **构建默认走 docker:`westlake-inputs/tools/dockbuild.sh`**(镜像 `scripts/lab/dockbuild.sh`)。OrbStack 容器能直接挂 VM 的文件系统(`/mnt/machines/a2hlab/...`,不用拷贝),脚本把 `~/a2hlab`、作者路径 `/home/dspfac/a2hlab/source-closure/verify`、ccache、`westlake-inputs` 都挂在 VM 里的原路径,uid 501 → 现有 `build_*.sh` 原样可跑,产物写回 VM 工作区。
  - `dockbuild.sh image`(一次,约 90 s,apt 走华为云镜像)/ `check`(自检挂载)/ `run [-n 名] -- <命令>` / `cc <clang 参数>`(锁定 clang-15 + sysroot,cwd 为 Mac 当前目录)。
  - 实测(2026-09-28):`build_android_native.py --target ohos --library liblog.so --library libbase.so` 在 VM 与容器各跑一次(关 ccache),`.so`/`.o` 逐字节相同,`.o.d` 与 `artifacts.json` 只差输出目录名;耗时 11.3 s 对 11.6 s。**单次不更快**(同一 OrbStack 内核 + Rosetta),收益在于**可并行起多个隔离容器**。
  - 上板操作(probe_source_app.py、hdc)仍在 VM 里跑:`hdc_mac.sh` 依赖 OrbStack 的 `mac` 命令,容器里没有。
- **本地编 BMS 适配层(libapk_installer 等)的编译包**:`~/orca/workspaces/oh61-bms-kit/`(布局同 OH 源码树,`OH_ROOT` 直接指它)=hw248 `oh610_lts_source` 的头文件子集(bundle_framework、zlib/minizip 源码、openssl、hilog、c_utils、ipc、ability_base、json、access_token,约 10 MB,`rsync -aR` 只取头文件)+ 板上只读拉的链接库(`/system/lib64/{platformsdk,chipset-sdk-sp}` 下 libhilog/libcrypto_openssl.z/libssl_openssl.z/libutils.z/libshared_libz.z)+ 软链到 docker 锁定工具链的 `prebuilts/clang/ohos/linux-x86_64/llvm` 与 musl `usr`。hw248 的 OH 源码树 clang 与我们锁定的 SDK clang 是同一提交(15.0.4 feef13a3);hw248 上**没有** `out/wukong100/packages`(系统库只能从板子取)。运行:`DOCKBUILD_MOUNTS="$KIT:$ADAPTER_ROOT" dockbuild.sh run -- "OH_ROOT=$KIT bash build_adapter.sh --no-apply --target=libapk_installer.so"`。⚠️ `compile_apk_installer.sh` 编译失败仍会链接出残缺 .so(实测 27 个源只编过 4 个也输出 50K 库)——必须看 `Compiled: N/N` 全绿;`games/boatattack-repro` 分支的构建脚本引用了本分支不存在的源文件(T-06/T-08/T-12 线),要在与板上库同代的提交上编。
- 重建时 framework flags 除 java-profile 的 3 个外还需 8 个 APEX flag 库;native object map 在 `$A/native-object-map.json`。就绪检查:`planned_staging.py` + harness `deploy-check`。

## 6. OctoLoop 现场

- 黑板 `.octos/OUTER_LOOP_REVIEW.md` 只追加,写入用 `~/workspace/octoscode/scripts/olp-board-append.sh`;机读视图 `scripts/lab/board_status.py --lane <车道> --open`(旧的 `board_acks.py` 认不出 `ACK(done: …)`)。
- **结构化调度**(Markdown 仍是唯一事实源,只加行首定式):车道用 `board_note.sh` 写 `PROGRESS(N)`(每里程碑或 ≤20 分钟)与 `LOCK/UNLOCK(<serial>)`(flock 持有进程真互斥,exit 75=别人持有);依赖取 spec 的 `depends:`。外环看 `board_status.py <板> --schedule --text`,哨用 `--watch`(ACK、可派发、停滞、锁异常即退出)。看板:`board_dash.sh --loop 30`(herdr `app-lighting` 工作区 `dash` 标签页)。
- **一个战役一块新黑板**(2026-09-28 用户决定):`.octos/boards/<战役>.md`,编号从 #1 起;`.octos/OUTER_LOOP_REVIEW.md` 只做索引。车道名写在条目标题 `[cc-tN]`,`board_status.py <板> --lane <车道> --open` 取自己的条目。
- **旧板归档方法**:在 `flock -x <板>.lock` 下把旧内容 `head -n <边界前一行>` 原样移进 `.octos/archive/OUTER_LOOP_REVIEW-<年月>-<战役>.md`,用 `cat 归档 <(tail -n +<边界>) | cmp - 原板` 证明逐字节无损,再写新头部 + 在途条目。换本前先确认没有挂着的侦听哨(哨按行数基线判定)。2026-09-28 头条战役 #1–#50(4009 行)已归档,新板从 #51 起。
- **codex 窗格会弹交互式提问**(屏幕显示 `? 1 question  ⌥+↑ to answer`,herdr 状态 `blocked`):这时 `herdr agent prompt` 只会进队列,不回答问题,车道会一直卡住。处理:`herdr pane send-keys <pane> alt+up` 调出问题,读选项,`enter` 提交(或用方向键换选项)。`lane_watch.sh` 把 blocked 当作停下,能抓到。octoscode 的排队消息则要 `esc` 才会中断当前轮并发送;Claude Code 的消息会在轮中自动插入。
- herdr server 必须由用户自己起,不要从 agent 会话里 nohup。octoscode stdio 模式要带 `--session <名>`。
- 复验:`git worktree add --detach ~/.octos/outer/verify/<名> <commit>` → 逐字重跑验收 → 落判词 → 删 worktree。
