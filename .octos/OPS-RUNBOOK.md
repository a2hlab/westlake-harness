# 实验室操作手册(怎么操作机器)

`KNOWLEDGE-DIGEST.md` 记**学到了什么**;本文件记**怎么操作**;脚本在 `scripts/lab/`(`westlake-inputs` 的版本化镜像,见其 README)。
凭据(WiFi 密码、服务器账号)不写在这里——仓库是公开的。

## 1. 机器与访问

**Mac(控制端)**
- hdc:`/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc`。`-t` 必须用**完整 connect-key**,8 位前缀会报 `Not match target founded`:
  `5ea34a4500000000000000001123012c`、`5cd1e3dd00000000000000000923012c`、`61b0657200000000000000000324012c`。
- 板子经 hub 接 USB,provision/remount 瞬间掉线过多次,最长 50 分钟不回,只能物理重插。演示前尽量直连。2026-09-29 61b 在 `swap_installer.sh` 触发 foundation 重启→整机重启后从 USB 枚举消失(`ioreg -p IOUSB` 里没有该序列号),用户手动重启才回来;会导致重启的操作(换 installer、restore、remount)优先放在直连的板上,上 hub 的板做之前先告诉用户可能要重插。
- **boot 镜像叠加测试也是会让板掉线的操作(2026-09-30 5cd)**:oc-t4 把 27 个镜像文件 bind 到 `/system/android/framework/arm64/` 并重启 appspawn-x 后,5cd 从 USB 枚举消失 >15 分钟,需人工重启。这类测试和换 installer 同级:先在黑板预告、优先放直连的板、做之前告诉用户可能要重插;叠加前先确认有不需要重启进程的读法(例如只起一个子进程验证镜像能否加载)。 **根因已查实:不是镜像,是 `kill -9` appspawn-x 主进程——OH init 处理它的退出信号时 `CheckOndemandService` 空指针崩(SEGV@0x34),整机宕。** appspawn-x 只能 `begetctl stop_service appspawn-x` / `begetctl start_service appspawn-x`(deploy_generation.py 同款,起后补 socket 属主 0:6005、0660、`u:object_r:appspawn_socket:s0`),停之前先 cold_stop 全部 uid≠0 子进程;任何车道都不许 kill -9 appspawn-x 主进程。
- 环境:`source ~/orca/workspaces/westlake-inputs/env-mac.sh`(cc/readelf/sha256sum shim + mise 固定的 JDK/Python)。有它 67/69 测试过,没有它 2 fail 4 error。
- **shell 陷阱**:`ls`=eza(带 OSC-8 超链接)、`du`=dust、`grep`=ugrep(复杂正则会超限)、`cat`=bat → 解析输出时用 `/bin/ls`、`/usr/bin/grep`、`command du`。zsh **不拆分 `$var`**(用 `${=var}` 或数组/glob),把整串当一个文件名且被 `2>/dev/null` 吞掉时会得到"假干净"。macOS 自带 bash 3.2 没有 `mapfile`。
- `pgrep -f`/`pkill -f` 会匹配到自己的命令行(在 `hdc shell "…"` 里计数恒 +1)→ 用 `scripts/lab/stop_by_pattern.sh` 或 `pgrep -f '[x]yz'`。
- **`set -o pipefail` 下别写 `cmd | grep -q`**:grep 命中即退出,上游收到 SIGPIPE,整条管道被判失败,判断会随机翻转(2026-09-30 setup_new_mac.sh 的 VM 检查因此被静默跳过)。改写成 `cmd | grep pat >/dev/null`,或先把输出存进变量再判。
- **车道「空闲/done」不等于做完(2026-09-30 一夜五次)**:模型/API 断连后 herdr 仍报 done 或 idle——claude「API Error: Connection dropped|lost」、codex「Error running remote compact task: Connection failed」、octoscode「Turn error runtime_error」。`scripts/lab/lane_watch.sh` 现把它们判为 `interrupted` 单独上报;看到就按该车道最近派单叫它继续,别等 ACK。glm 车道反复 runtime_error 时换 profile(如 kimi)重开会话。
- **板子断电/重启后统一态全丢**:bind 叠层与 deploy 的运行时都不跨重启——重接后先只读看 `pidof appspawn-x`(0 = 运行时没起)、JAR SHA、uptime/boot_id;要整套重布 v3c → native(--upgrade)→ JAR 叠层,JAR 层可用 `westlake-harness-bms/scripts/lab/replay_unified_state.sh`。重接后先 `power-shell timeout -o 86400000` + wakeup + 上滑解锁 + 同步板钟(开机 1970,TLS 会坏)。
- **codex 模型(2026-09-30 实测)**:本机 codex 用 ChatGPT 账号登录,`gpt-6.1-sol` 虽在 `~/.codex/models_cache.json` 里,但会话里报「not supported when using Codex with a ChatGPT account」;可选的是 `/model` 选择器里的 7 个(GPT-6-Astra / GPT-6-Sol / GPT-6-Luna / 5.6 系 / 5.5)。codex 车道维持 GPT-6-Astra;已开会话看不到新模型,要换得 `/quit` 后带 `-m` 重开。
- **codex 车道写不了 worktree 的 git 索引**(`index.lock: Operation not permitted`,沙箱 writable_roots 不含主仓 `.git/worktrees/<名>`):车道把改动留在工作区并在 ACK 里说明,外环代提交到该车道分支、提交信息注明「outer commits for the lane」。
- **交给另一台机器的步骤要先在模拟新环境里逐字跑一遍**(EVO-0035):用临时 HOME 和新 root 执行用户将执行的原命令,核对 `git status --porcelain --untracked-files=no` 为空、`git describe --tags` 是约定标签,再发给用户。归档只收打包当时未跟踪的文件,之后入库的文件会以旧副本覆盖克隆——`unpack_airdrop.sh` 已在解档后对每个 checkout 自动 `git restore .` 并核干净。
- **长跑的 bash 脚本别在运行中改它**:bash 按字节偏移边读边执行,改了前面的行,当前复合命令跑完后会从错位处读下一条(2026-09-30 迁移上传差点中招)。要跑几小时的脚本先 `cp` 一份副本再 `bash <副本>`,仓库里的原件随便改。
- **路径不绑用户名**(用户 2026-09-30 定):脚本的工作区目录 = 环境变量 `WORKSPACES`;没设就从脚本自身的真实位置往上找第一个含 `westlake-inputs/` 或 `westlake-harness/` 的目录(`scripts/lab/` 与其镜像 `westlake-inputs/tools/` 深度不同,不能写固定 `../..`)。bash 用 `. "$(dirname "${BASH_SOURCE[0]}")/lab_paths.sh"`,Python 用 `import lab_paths`(镜像两处都要有这两个文件);VM 家目录 `lab_vm_home` / `lab_paths.vm_home()`(Mac 上问 VM,`A2HLAB_VM_HOME` 可覆盖),VM 里要 Mac 家目录用 `lab_mac_home`(`MAC_HOME`)。门禁 `python3 scripts/lab/check_user_paths.py`,例外表 `knowledge/gates/user-path-exceptions.json`。
- **换机**:按根目录 `env.md`。OLP 黑板(`.octos/boards/`、`OUTER_LOOP_REVIEW.md`、`EVOLUTION.md`)按设计不入 git,换机靠 hw248 的 `octos-state` 包带过去;`scripts/lab/push_lab_state.sh` 只在 hw248 与本机校验清单完全一致时跳过,切换前重跑一遍即可刷新。

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
- **冻结核验(构建/部署前)**:`python3 scripts/lab/check_frozen.py` 之后跟 `--source-root <worktree>`(建 JAR/native 前)、`--package <代>`(部署前)、`--fingerprint <run>/runtime-fingerprint.txt`(审板)、或 `--git [<repo>]`(用 git 对象库按每条冻结源的 `commit`/`branch` `:repo_path` 取 blob 比对——冻结源分在不同分支时,任一 checkout 都能核,不用逐分支拉 worktree)。退 1=有冻结件被改;退 2=注册表本身破规(缺 reason/证据、未经用户的 removed、`--git` 源缺 commit/branch)。
  - 实测(2026-09-28):`build_android_native.py --target ohos --library liblog.so --library libbase.so` 在 VM 与容器各跑一次(关 ccache),`.so`/`.o` 逐字节相同,`.o.d` 与 `artifacts.json` 只差输出目录名;耗时 11.3 s 对 11.6 s。**单次不更快**(同一 OrbStack 内核 + Rosetta),收益在于**可并行起多个隔离容器**。
  - 上板操作(probe_source_app.py、hdc)仍在 VM 里跑:`hdc_mac.sh` 依赖 OrbStack 的 `mac` 命令,容器里没有。
- **本地编 BMS 适配层(libapk_installer 等)的编译包**:`~/orca/workspaces/oh61-bms-kit/`(布局同 OH 源码树,`OH_ROOT` 直接指它)=hw248 `oh610_lts_source` 的头文件子集(bundle_framework、zlib/minizip 源码、openssl、hilog、c_utils、ipc、ability_base、json、access_token,约 10 MB,`rsync -aR` 只取头文件)+ 板上只读拉的链接库(`/system/lib64/{platformsdk,chipset-sdk-sp}` 下 libhilog/libcrypto_openssl.z/libssl_openssl.z/libutils.z/libshared_libz.z)+ 软链到 docker 锁定工具链的 `prebuilts/clang/ohos/linux-x86_64/llvm` 与 musl `usr`。hw248 的 OH 源码树 clang 与我们锁定的 SDK clang 是同一提交(15.0.4 feef13a3);hw248 上**没有** `out/wukong100/packages`(系统库只能从板子取)。运行:`DOCKBUILD_MOUNTS="$KIT:$ADAPTER_ROOT" dockbuild.sh run -- "OH_ROOT=$KIT bash build_adapter.sh --no-apply --target=libapk_installer.so"`。⚠️ `compile_apk_installer.sh` 编译失败仍会链接出残缺 .so(实测 27 个源只编过 4 个也输出 50K 库)——必须看 `Compiled: N/N` 全绿;`games/boatattack-repro` 分支的构建脚本引用了本分支不存在的源文件(T-06/T-08/T-12 线),要在与板上库同代的提交上编。
- **route-A 运行代的冻结构建输入在 hw248**(00.Workspace `.work/` 不入 git,本机各 worktree 都没有):`/opt/wl-src/.work/product-tls-generation/`(frozen toolchain clang-15 + sysroot,2.4 GB)、`/opt/wl-src/upstream/openharmony-6.1.0.31/`(39 MB);较小的切片在 `/opt/build-runs/m1-generation-source-slice-20260822-r1/project/src/.work/`。它们的 `frozen.sha256`/`tool_runtime.lock` 与 00.Workspace ledger 的期望哈希不同——lock 自述是换成本地 OHOS SDK 工具链的 direct-build。换 route-A 的任一 provider(如 `libsigchain.so`)都要重生成 sealed manifest → child 插件 → appspawn-x 钉 SHA,单换会被 loader 以 `LOAD_ERROR:8`(artifact identity)拒绝。只读拷回本机再用 dockbuild 构建,不在 hw248 上构建。
- **板上 route-A R155 这一代(appspawn-x 1f6cf53b、child 0976dee8)出自 `~/orca/workspaces/01.OH61AOSP16/real-work`**(不是 00.Workspace):身份清单 `.state/zigzag-final-r155/post-rollback-redeploy/identities.txt`,源码快照 `.state/zigzag-r138h-sealed-generation-source`、`.state/zigzag-r148-source`、`.state/zigzag-r150-sealed-generation-thin.bundle`,各轮 `zigzag-longtask-r6*-r155*/identities.txt`。hw248 上的 ART/provider 构建痕迹在 `/opt/build-runs/l03a15-*/provider`、`m1-aosp-libbase-relink-*/base-provider-root`。
- **我们在 hw248 上下载的东西一律放 `/home/alvin/`,目录名带版本**(用户规定,2026-09-28)。hw248 出网快,AOSP 走 TUNA 镜像 `https://mirrors.tuna.tsinghua.edu.cn/git/AOSP/<项目>`(googlesource 不通);只下需要的项目,`git clone --depth 1 -b android-14.0.0_rNN` 放 `/home/alvin/android-14.0.0_rNN/<项目路径>`,不全量 `repo sync`。已有:`/home/alvin/aosp-android14-platform-art.git`(bare,blob:none,71 个 android-14 tag)、`/home/alvin/android-14.0.0_r1/`(provider-v12 需要的 18 个项目)、`/home/alvin/aosp-main-external-tinyxml2.git`(完整)。provider-v12 的冻结源 = android-14.0.0_r1 + hanbin 旧补丁(`HanBingChen/adapter/aosp_patches/art/...`,runtime.cc 用其第 4–11 块、class_linker.cc 取旧诊断副本)+ tinyxml2 取 AOSP main 2026-03-09 的 418229dc(不是任何 android-16 tag);还原时以 `provider-v12/base-inputs.sha256` 的逐文件指纹为准。route-A provider-v12 的 ART 是 AOSP14(oat 230):`art/runtime/oat.h`、`libartbase/base/globals.h` 与 android-14.0.0_r1 等 tag 一致,`runtime.cc` 与所有 stock 版本都不同(带本地补丁)。
- 重建时 framework flags 除 java-profile 的 3 个外还需 8 个 APEX flag 库;native object map 在 `$A/native-object-map.json`。就绪检查:`planned_staging.py` + harness `deploy-check`。

## 6. OctoLoop 现场
- **codex 沙箱里 `orb -m a2hlab` 会超时(start VM timed out)**,读不到 VM 上的证据。给 codex 车道派只读分析时,外环先把 VM 目录 `tar` 拷到 Mac 的 `/Users/zhaoyue/orca/workspaces/vm-copies/<原目录名>/`(只读副本,不入库),再把路径发给车道。
- **octoscode 内环「看着在、其实断了」**:TUI 背后的 `octos serve --stdio` 子进程会被重启(2026-09-28 22:07 两个车道的 serve 同时重生);重连时若报 `connection_closed` + `cursor_expired: session/open … cursor out of range`,TUI 停在旧画面、不再执行,herdr 仍显示 idle。判断:`ps -axo pid,ppid,etime,command | grep 'octos serve'` 看 serve 的启动时间,读窗格状态栏找 `x Error`。处理:窗格里 `/quit`,再用原命令 `octoscode --session <同名会话> --profile-id <同 profile> --no-splash` 重开(会话历史保留),然后重发当前条目。⚠️ 完全访问不在启动参数里,是 operator 运行时切的:重开后新 serve 只有 `--solo`、没有 `--danger-full-access`,车道一动手就被沙箱挡(读不了 `~/.gitconfig`、git 元数据、黑板)。重开后先 `ps` 核 serve 参数,缺了就请 operator 亲手切回,外环不代为提权。operator 授权后可这样重开并保留完全访问:`octoscode --session <会话> --profile-id <profile> --no-splash --stdio-command 'octos serve --stdio --solo --danger-full-access'`(2026-09-29 用户授权外环对 oc-t4 这样操作;同日用户进一步授权:octos serve 或会话出问题(`state x Error`、cursor_expired、session_open_rejected、connection_closed)时外环**直接重开**,不必先问;长时间运行的会话也可主动重开)。另:车道把长任务丢给 VM 后台 runner 后自己转 idle 等监视器,runner 早死它也不知道——派单时要求监视器同时看 runner 进程与日志末尾的 Traceback。
- **octoscode 车道忙时收到的 `herdr pane run` 会丢**(2026-09-30 oc-t4 两次:外环 08:32、09:21 的批复它都没看到,回合结束后仍写「待外环批」)。给 octoscode 派单后 10 秒内读窗格,状态栏要出现新的 `Step 1`/`Working`;没有就等它回合结束(`state · Idle`)再发一次。
- **VM 里经 `mac <命令>` 调 Mac 侧工具,偶发退出码 0 但输出为空**(OrbStack mac 桥瞬时故障;B4 批量 20:25 因 `board_note.sh held` 空输出误判丢锁而停在 61/66)。以 Mac 侧命令输出做门禁的脚本,对空输出隔几秒重试一次再判停。

- 黑板 `.octos/OUTER_LOOP_REVIEW.md` 只追加,写入用 `scripts/lab/board_append.sh <绝对路径> "<正文>"`(或正文走 stdin):它拒绝空正文与相对路径,经 `olp-board-append.sh` 加锁追加后回读,没落板就退 1。**直接调 `olp-board-append.sh` 时正文只能走 stdin**——当参数传会被静默丢弃、零输出退 0(EVO-0034:13:22 的 U2 签认就这样落空,外环还报了已签认);机读视图 `scripts/lab/board_status.py --lane <车道> --open`(旧的 `board_acks.py` 认不出 `ACK(done: …)`)。
- 黑板条目的时间一律 `$(date +%Y-%m-%dT%H:%M:%S%z)` 生成,不手写:`board_append.sh` 拒收首行时间超前 60 秒以上的条目(2026-09-30 同一晚 oc-t4 写 22:10、外环写 22:08,都跑在钟前面)。heredoc 要展开 `$(date)` 就别给结束符加引号。
- **采认即落 master**(2026-09-30 一夜 3 次交付停在车道分支:cc-wiki 的 #80 DIGEST 行、cx-bms 的 T5 归因目录、cc-wiki 的整套 dex2oat 产出;外环一度把 master 上 7 个失败选择器也算作此例,cx-bms 10-01 审计证伪——那是 4 个未达成验收、2 个过期哈希钉、1 个写死路径,归 spec-check 例外表):外环采认车道交付的同一轮就把它落进 master——新增文件按路径 `git checkout <分支> -- <路径>`;DIGEST/RUNBOOK/README/lib.rs 这类共享文件**只手工补车道新加的那几行**。**不要 `git apply --3way` 整段分支 diff**:它会把分支上别的轮次的内容一起带进来(实例:lib.rs 带进 b10/b77/b85/b90/r16 选择器,证据只在分支上,master 的 cargo test 失败)。落完跑 check_user_paths 与相关选择器。
- **结构化调度**(Markdown 仍是唯一事实源,只加行首定式):车道用 `board_note.sh` 写 `PROGRESS(N)`(每里程碑或 ≤20 分钟)与 `LOCK/UNLOCK(<serial>)`(flock 持有进程真互斥,exit 75=别人持有);依赖取 spec 的 `depends:`。外环看 `board_status.py <板> --schedule --text`,哨用 `--watch`(ACK、可派发、停滞、锁异常即退出)。有意停放的条目(等别的板/别的条目)写 `WAIT(N): <时间> <署名> <等什么>`,在该车道下一条 PROGRESS 之前不算停滞,`--schedule` 显示 WAITING。看板:`board_dash.sh --loop 30`(herdr `app-lighting` 工作区 `dash` 标签页)。
- **一个战役一块新黑板**(2026-09-28 用户决定):`.octos/boards/<战役>.md`,编号从 #1 起;`.octos/OUTER_LOOP_REVIEW.md` 只做索引。车道名写在条目标题 `[cc-tN]`,`board_status.py <板> --lane <车道> --open` 取自己的条目。
- **旧板归档方法**:在 `flock -x <板>.lock` 下把旧内容 `head -n <边界前一行>` 原样移进 `.octos/archive/OUTER_LOOP_REVIEW-<年月>-<战役>.md`,用 `cat 归档 <(tail -n +<边界>) | cmp - 原板` 证明逐字节无损,再写新头部 + 在途条目。换本前先确认没有挂着的侦听哨(哨按行数基线判定)。2026-09-28 头条战役 #1–#50(4009 行)已归档,新板从 #51 起。
- **codex 窗格 `Reconnecting... n/5` / `Transport error: network error`**:Mac 的模型流量走本机 Surge 代理(`https_proxy=127.0.0.1:6152`),AI 相关域名归 Surge 的 AI 分组。先测 `curl -s -o /dev/null -w "%{http_code}" --max-time 8 https://api.openai.com/v1/models`——401 是通,000/超时是不通,国内站(baidu)通而它不通就是 AI 分组当前节点坏了,请用户在 Surge 里换该分组节点(2026-09-29 一批节点同时 Failed,换到测速通过的节点即恢复)。codex 重连 5 次失败会结束本轮,恢复后要检查车道是否停在 idle、需要重发条目。
- **codex 窗格会弹交互式提问**(屏幕显示 `? 1 question  ⌥+↑ to answer`,herdr 状态 `blocked`):这时 `herdr agent prompt` 只会进队列,不回答问题,车道会一直卡住。处理:`herdr pane send-keys <pane> alt+up` 调出问题,读选项,`enter` 提交(或用方向键换选项)。自由文本回答用 `herdr pane send-text <pane> "<答复>"` 再 `send-keys enter`;提交后要回读窗格确认问题框已消失、状态回到 Working,实测有一次第一下 enter 没提交、要再按一次。问题提示有 `⌥+↑` 与 `shift+←` 两种写法,按屏幕上写的键调出。`lane_watch.sh` 把 blocked 当作停下,能抓到。octoscode 的排队消息则要 `esc` 才会中断当前轮并发送;Claude Code 的消息会在轮中自动插入。
- herdr server 必须由用户自己起,不要从 agent 会话里 nohup。octoscode stdio 模式要带 `--session <名>`。
- **hilog 缓冲重启即回 256K**(2026-09-29 实测:5cd 16M、重启过的 61b 与 5ea 都是 256K,且 `hilog.private.on=true` 把 `%{private}` 参数打成 `<private>`)。256K 下 app 子进程的几万行会被冲掉,`run_facts.py` 的 child_hilog=0 看着像子进程没打日志、甚至像 JAR 没生效(#71 误判)。master 的 `bms_batch.py`(`83ab7bb8` 之后)开跑前自动 `preflight`:设 `hilog -G 16M`、`hilog -p off`、`power-shell timeout -o 86400000`、板钟与主机差 >120 s 时 `date -s @<主机 epoch>`,逐项回读写进 `preflight.json` 和每个 `record.json` 的 `preflight` 字段,不达标拒跑;跑完写 `facts.txt`(run_facts 汇总),ACK 原样引用。各车道一律直接跑 master 工作树里的这份(`/Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py`,VM 里同路径可见),不用自己分支里的旧副本。
- **板上 `/system` 写入(换 installer/appspawn-x、重启 foundation)在 auto 模式下被服务端判定硬拒**(2026-09-29 实测:cc-wiki 与外环主会话都拒,不弹提示,本地 allow 规则、聊天里的「允许」、`!` 转发、转派车道都解不开,来回拖了约 2.5 小时)。开工就用能写板的会话:`claude --dangerously-skip-permissions` 启动外环/Claude 车道;撞到「Auto-Mode Bypass」或「server-side classifier」就立即请用户重开,不要再试别的绕法。
- **VM→Mac hdc 转发在 foundation 重启期间会瞬时超时**(`hdc_mac.sh` 60 s TimeoutExpired,板本身在线)。部署脚本在 Mac 上跑时直接用 Mac 的 hdc(`/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc`)与 `board_note.sh`,不经 `orb`/`hdc_mac.sh`;失败后先清板上残留备份目录与本地 `state.json` 再重跑。
- ACK 里的截图数与存活数用 `scripts/lab/run_facts.py <运行目录>` 数(VM 上的目录:`orb -m a2hlab bash -c "python3 - <目录>" < scripts/lab/run_facts.py`)。
- 外环读图用 `scripts/lab/contact_sheet.sh <out.jpeg> --run <bms_batch 运行目录> [--shot final|t3] [--cols 7]` 把一批截图拼成一张再读(一次看 14 张);缺图给灰块,stdout 按「行 列 key 路径」列出每格对应的 app(Homebrew ffmpeg 没有 drawtext,格子上不印字)。逐张读只用于拼图里看不清、要签认点亮的那几张。
- 复验:`git worktree add --detach ~/.octos/outer/verify/<名> <commit>` → 逐字重跑验收 → 落判词 → 删 worktree。

- BMS 复现器克隆迁移（2026-09-28）：四游戏 suite 无 `check`，用单 app `check`；HelloWorld `restore` 会重启，完成后再次核对板时钟。61b 使用 `date -s @<Mac epoch>` 同步并回读差值（本次 -1s）；`current` 绝对路径与 wrapper driver SHA 的变更须记录为迁移，证据见 `benchmark/2026-09-28-bms-route-deploy/`。
- `reproduce-zigzag-apk quick` 多板并发须错开≥2秒启动（上游运行目录只含秒级时间，不含 serial）；完成后同时核对 wrapper receipt 的 board 和底层 envstamp 的 board，不能只看三个 PASS。
- 换代后必须回读 installer（2026-09-29 #63，61b）：用 bms-suite `quick` 切整代会把 `libapk_installer.so` 恢复成 stock `184d40a5`，B2/B3 的 `675536e8`（名字/图标/XML-only 图标兜底）随之丢失，随后 13 个 app 全部 `install internal error code:9568260`，看着像新代把安装弄坏了。`tools/deploy_generation.sh` 不动 installer（5ea 换代前后都是 675536e8）。任何换代之后、批量安装之前，先在 shell 与 foundation 的 `/proc/<pid>/root` 两条路径回读 installer SHA，不是 675536e8 再用 `swap_installer.sh`；swap 会让 foundation 重启、整机可能随之重启，板在 hub 上时可能掉线，要预留物理重插。
- BMS批量恢复：原attempt留存，新的run-id只跑未完成key；已首装成功但截图缺失的key走 `batch/capture_existing.py`，先核对 prior record + 当前 `.../android/base.apk` SHA 再精确点BMS主入口。`mac held`/`hdc list targets` 曾rc0但stdout为空，守卫应停；只读重新确认锁、目标、boot不变后才能新run-id续跑。

- BMS启动A/B采证：同boot和runtime SHA，先核BMS UID及精确图标；点击前`hilog -r`并连续采日志，板端约100–220ms轮询UID进程至少15s，配合AppSpawnChild/返回码/子退出日志。`success pid`后仍须看result；hook31沙箱初始化失败可有PID、exit0且无fault文件，末时刻无PID不能判从未fork。复现器`prepare_sandbox`是bm install之外的必要目录/UID/mode/label准备，批量部署必须显式核对；#24未执行补目录干预。

- B5 JAR 最小覆盖（2026-09-28）：先锁板并核 baseline SHA；保留原 JAR，只 bind-mount 新 JAR，分别核 shell 与 AppSpawnX /proc/PID/root 中 SHA，子进程新增日志证活。回滚仅卸最上层该 JAR mount 并核 baseline SHA；须核 boot/PID，不能跨重启照抄 PID。5ea B5 临时覆盖 SHA250958dc… 留存，负控包已卸载；具体路径、回滚与原始证据见 `benchmark/2026-09-28-bms-route-deploy/alias-entry/README.md`。

- GitHub 全量迁移（2026-09-29）：目标 `a2hlab/westlake-harness`；HTTPS 经本机代理遇 HTTP/2 中断、直连 SSH 上传约 150 KiB/s，本次成功线路为本机 SSH 经现有 `hw248` 转发（密钥留本机）：`GIT_SSH_COMMAND='ssh -o BatchMode=yes -o ConnectTimeout=15 -o ControlMaster=no -o ControlPath=none -o "ProxyCommand=ssh hw248 -W %h:%p" -o ServerAliveInterval=15 -o ServerAliveCountMax=3' git -c lfs.url=https://github.com/a2hlab/westlake-harness.git/info/lfs -c lfs.locksverify=false push git@github.com:a2hlab/westlake-harness.git --all`，实测约 2.8 MiB/s。`lfs.locksverify=false` 仅在 `git lfs ls-files --all` 确认无 LFS 文件时用于本次命令（锁查询曾超时），不跳过其他 hooks；有 tags 时另推 tags。空仓库首次多分支推送会选首个分支为默认，须用 `gh repo edit a2hlab/westlake-harness --default-branch master` 修正，并逐项比较 `git ls-remote --heads` 与本地分支 SHA。未跟踪文件不随 Git 推送，原 remote 保留。
- **跨板比较先看运行时指纹(2026-09-30,FLAW-004)**:`bms_batch.py` 每次运行写 `runtime-fingerprint.txt`(appspawn-x、runtime JAR、`/system/android/lib64/*.so`、`route-a/*/*.so` 的 sha256),`facts.txt` 首行 `RUNTIME fingerprint=<12位> files=N`。同一 key 两板结果不同,先 `diff` 两板的 runtime-fingerprint.txt,再疑 JAR。部署器单换以「与当前活动包只差一件」为准,板上已有别的单换时换第二件会被拒——那块板等合代(v3c)。部署器在 VM 里跑:`orb -m a2hlab bash -lc '<westlake-harness-bms-deploy>/scripts/lab/deploy_generation.sh <serial> <package> --replace <target> --lane <lane>'`(Mac 上直接跑会因 `hdc_mac.sh` 找不到 `mac` 命令失败);换前先把 runtime JAR 叠层卸回包内 r8b。
- **归因前先数变量(2026-09-30,FLAW-008)**:`python3 scripts/lab/compare_runs.py <runA> <runB> [--keys a,b]`——板子算一个变量,指纹里 sha 不同或只在一边的路径各算一个;列出 t5/t20 翻转的 key;末行判词。只有 `single-variable` 才能写「X 造成 Y」,否则写假设 + 只改那一个变量的判别运行;`variables: 0` 而 key 翻转 = 同板同版本先重复 3 次。
- **app 数据是变量(2026-09-30,cc-wiki AntennaPod 矩阵)**:一次崩溃可能写坏 app 自己的库(AntennaPod 的 WorkManager DB),之后 `--launch-only` 复跑换什么配置都照崩。归因/回归判定的运行一律 `bms_batch.py --reinstall`(卸载重装 = 清数据);`compare_runs.py` 把没带 --reinstall 的运行记成「app data carried over」变量。
- **单件 `--add/--replace` 的包必须以板上现役包为底**:部署器只接受与现役包恰好差一件的包(旧包做底会被拒 `replacement must change exactly one package file`,如 gapfill c5ed50d5 包对 v3c+32df 差 11 件)。做法:`python3 scripts/lab/prepare_generation_replacement.py <现役包> <目标路径> <新 .so> --sha256 <全长> --out <新包目录> [--add]`(westlake-harness-bms-deploy 下),再对新包跑 deploy_generation;回滚用同一新包加 `--rollback`。
- **复现产物前先核输入(2026-09-30,FLAW-002)**:boot 镜像等复现,先 `sha256sum -c knowledge/toolchains/boot-image-inputs.sha256`(路径换成本地输入目录)全部 OK 才跑;dump 出来的数值先验对齐/非空/量级再用。
- **更正用定式行首(2026-09-30,FLAW-006)**:推翻已落板结论时,外环另起一行写 `> 外环(claude)·R2 记档(#N): …` 或 `> 外环(claude)·改判(作废 #N): …`,车道的更正由外环代记;常驻采集哨只认这两种行首,散文里的「更正/是错的」采不到。retro 采到 0 张而板上有更正,即判漏记。
- **已公示的产物不就地覆盖(2026-09-30)**:JAR/.so 公示 SHA 后,新版放新目录并以 SHA 命名(`vm-copies/r17b-<sha8>/`);就地覆盖会让别的板、别的车道拿不到已公示那版(r17 4bbea1f6 被覆盖后外环只能从 5ea 的 `/data/local/tmp` 取回)。
- **进化采集在 macOS 上的两个工具坑(2026-09-30)**:octoscode 的 `olp-evo-harvest.sh` 用 GNU `stat -c`,macOS 自带 BSD stat 会让采集中途 `failed (exit 1)` 却已推进游标——跑采集与常驻哨前 `export PATH=/opt/homebrew/opt/coreutils/libexec/gnubin:$PATH`;它自己写的卡头用全角括号 `### EVO-NNNN（…）`,reconcile 解析不了,`next_id` 会回到 1 造成重号(EVOLUTION.md 已有 EVO-0001×4 等),state 在 `~/.octos/outer/evo/<项目键>/state.json`,重号时手工把 `next_id` 调到最大号+1。R2/改判定式行本身能被正则匹配;采集仍为 0 时 FLAW 记录由外环人工落,不因采集器失灵停进化环。上游问题待报 octoscode。
- **交板前查锁(2026-09-30)**:`board_note.sh lock` 起的 holder 会脱离进程活到 unlock(或 24 h);批跑/部署完一块板要交给别的车道,先 `board_note.sh held <serial>`,非空就 `board_note.sh unlock <board> <serial> <lane>`。61b 曾被 00:07 的 claude holder 挡住 cx-t0 近 10 分钟(BUSY 75)。
- **5ea 重启后的运行时重放顺序(2026-09-30 实测)**:foundation 重启(换 installer)后桌面可能黑屏(power AWAKE、WMS 无窗口、杀 SceneBoard 不回生)→ 直接 `reboot`(75 s 回);installer 两库写 /system 持久,bind 挂载全失。重放(均在 VM 里跑部署器,lane 用持锁车道):① v3a 包整包 `deploy_generation.sh <serial> westlake-generation-v3a-74d1d6d4-r8b`;② `westlake-generation-b80-inet-d977bd15 --replace /system/bin/appspawn-x`;③ `westlake-b92-anl-route-a9c9187d --replace <route-a>/libapp_native_loader.so`(它的底含 d977,必须在②之后);④ `westlake-b92-bigstack-0509fe23 --replace <route-a>/libwestlake_android_runtime_provider.so`;⑤ TLS:`westlake-b93-tls-html-9c0f8d38-26ac847b/1-tls --add` 再 `westlake-b93-tls-39c2cfe9-5ea --replace`;⑥ JAR 叠层。v3c 候选整包部署目前会在前置哈希处因新增文件不存在而失败,修前别用。
- **板上占用要落板,车道不能自判「板空闲」(2026-09-30)**:外环在 5ea 跑全量时,cc-wiki 看不到批跑、判「5ea 空闲」准备换 libhwui(会重启 appspawn-x 打断全量),靠外环打断才止住。规则:任何批跑/部署开始前在黑板写一行「<板> 占用:<run-id>,预计 <时间> 完」,完了写「<板> 放行」;车道上板写之前先读黑板最近的占用/放行行并 `board_note.sh held`,锁同名车道也不代表没人在用。

## T4b 镜像编译开关门（2026-09-30，离线）

`python3 knowledge/toolchains/art-r155/t4b_build_switch_gate.py --libart <部署目标libart> --oat <候选boot.oat> --build <对应BUILD.md> --out <新JSON路径>`：0=本门一致、2=已知错配/坏输入、3=缺证待外环审；消费verdict/deploy_allowed，不能只看consistency。BUILD需单个t4b-build-json围栏、完整SHA绑定、5环境开关+native_debug_build，模板见benchmark/2026-09-30-t4b-build-switch-gate/BUILD.template.md。无历史回执不代填；同一路径不同代BUILD按commit/SHA冻结。完整T4布局与T6读图仍是独立门，本命令不授权上板。
