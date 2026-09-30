# 新机器环境清单(env.md)

写于 2026-09-30,对应本仓库 master 与板上状态 **U2**(N2 `51a78bde` + JAR J2 `0715c964`,三块板一致)。
目标:在另一台机器上**完整复现**本实验室——同样的代码、同样的运行包、同样的构建工具链、同样的 APK 语料、同样的板上状态。

凭据(服务器账号、WiFi 密码、GitHub 权限、模型 API key)**不在本仓库**,见 §8,找操作者要。本仓库是公开的。

---

## 0. 东西都在哪

| 内容 | 位置 | 说明 |
|---|---|---|
| 代码、知识、全部分支 | `github.com/a2hlab/westlake-harness`(公开) | master + 所有特性/分析分支 + `wip/20260930/*`(换机时各车道 worktree 里未提交的工作快照)。**用这个**,两个同名仓库的区别见下 |
| **一次搬完(首选)** | 旧 Mac 上 `scripts/lab/pack_airdrop.sh` 打出的一个文件夹(4 GB 分卷 + SHA256SUMS + 解包脚本),AirDrop 或移动硬盘带过去 | 内含全部仓库的 git bundle、全部 worktree 清单、黑板、运行包、板状态、JAR、APK、VM 工具链与源码、原始运行记录。新 Mac 上 `bash <文件夹>/unpack_airdrop.sh <workspaces 目录>` 一条命令还原(§5) |
| 不进 git 的一切的服务器镜像 | hw248 上 `$LAB_STATE_DIR`(操作者告知的目录) | **只放 hw248,不上 GitHub**(仓库公开;商业 APK 有版权)。每个包带 `<包>.SHA256SUMS`;AirDrop 不方便时用 `fetch_lab_state.sh` 从这里拉 |
| 伴随仓库 | `A2OH/westlake`、`a2hlab/westlake`(私有)、`a2hlab/00.Workspace`、`a2hlab/01.OH61AOSP16`(分支 `zhao`)、`a2hlab/manifest`(分支 `local-pins-main`)、`a2hlab/harmony` | 换机时均已与远端同步;它们不进 git 的文件在 hw248 的 `companion-untracked` 包 |
| agent 工具 | `octos-org/octoscode`、`hagency-org/herdr`(分支 `feat/octoscode-agent`)、npm `@octos-org/octos` | 新 Mac 自行安装(§4),不在搬运包里 |

**两个 westlake-harness 的区别**(2026-09-30 核对):

| | `A2OH/westlake-harness` | `a2hlab/westlake-harness` |
|---|---|---|
| 身份 | **原始仓库**(上游,2026-08-20 建,A2OH 组织) | **你自己上传的**(2026-09-29 在 a2hlab 组织新建,不是 fork) |
| 内容 | master 停在 `60afc31d`(2026-09-26,PR #20),6 个分支 | master = 原始 master 全部内容 + 本次战役 213 个提交,71 个分支(含全部车道分支与 `wip/20260930/*`) |
| 权限 | 当前 gh 账号只读(push=false) | 可推(admin) |
| 本地 remote 名 | `origin`(只读上游,用来看别人的新提交) | `a2hlab`(日常 push 到这里) |

两者没有冲突:原始 master 的每个提交都包含在 a2hlab 的 master 里(`git merge-base --is-ancestor origin/master a2hlab/master` 为真)。以后要回馈上游,从 a2hlab 的分支向 A2OH 提 PR。

取制品:`scripts/lab/fetch_lab_state.sh`(§5)。旧机器上生成/补传镜像:`scripts/lab/push_lab_state.sh`(可续传,已校验的包自动跳过)。

---

## 1. 机器角色

| 角色 | 本机现状 | 新机器要求 |
|---|---|---|
| **控制端**:跑外环与各车道 agent、hdc 连板、截图读图、跑 `bms_batch.py` 横扫 | MacBook,macOS 26.6.2 arm64,1.8 TB 盘 | **推荐 Apple Silicon Mac**。脚本用了 `orb`(OrbStack)、DevEco 的 macOS hdc、BSD/GNU 工具混用;换 Linux 要逐个改脚本 |
| **构建**:运行时 .so / JAR / boot image | OrbStack VM `a2hlab`(Ubuntu 24.04 amd64,走 Rosetta)+ docker 镜像 `a2hlab-build:24.04` | 同上;盘留 ≥ 100 GB(android-source 16 GB + 工具链 6 GB + 各代 out) |
| **远程构建/存档**:AOSP/OH 源码树、dex2oat、大文件 | `ssh hw248`(x86-64,32 核 62 GB,Linux) | 新机器配好同名 ssh 别名即可,见 §8 |
| **板子** | 3 块 DAYU600(OH 6.1.0.31)经 USB hub + 1 台安卓参考机 | 板子随控制端搬走;见 §7 |

---

## 2. 目录布局

**workspaces 目录 = 本仓库的上一级目录**,放在哪、叫什么都行(例如新 Mac 上的 `~/alvin/`)。脚本不写任何带用户名的绝对路径(用户 2026-09-30 定,门禁 `scripts/lab/check_user_paths.py`):先看环境变量 `WORKSPACES`,没有就从脚本自身位置往上找含 `westlake-inputs/` 的目录;家目录下的东西一律 `$HOME/...`。不需要建 `/Users/<旧用户名>` 软链。黑板和旧文档里出现的 `/Users/zhaoyue/orca/workspaces/...` 是旧机器上的历史路径,读的时候换成你的 workspaces 目录。

```
~/orca/westlake/                          A2OH/westlake(Westlake 主仓,抄验证过的实现从这里找)
<workspaces>/
  westlake-harness/                       本仓库 master(外环在这里)
  westlake-harness-<名>/                  各车道 worktree,见 §3 表
  westlake-inputs/                        APK 语料 apks/(18 GB)+ tools/ + webview/ + board/ + venv/ + *.json 语料清单
  westlake-b90-controls-inputs/           对照 app 清单
  westlake-generation-v3c-candidate/      基础运行代包(U0/U1/U2 共同底座)
  westlake-generation-n2-51a78bde/        当前板上 native(U2)
  westlake-generation-n1-aa57845c/        上一版 native(U1,回滚用)
  westlake-runtime-asset-fd-53f00423/     U0 的 runtime 替换包
  westlake-installer-background-launcher-6aadb8b4*/   FZ-001 安装器(已冻结)
  westlake-generation-state/<序列号>/     每块板的部署状态 + 原厂文件备份(回滚必需,随板走)
  vm-copies/                              各版 JAR(j2-0715c964 是当前板上的,j3-75c2068c 是下一版候选)
  oh61-bms-kit/                           本地编 BMS 适配层的头文件/库子集
  00.Workspace/                           a2hlab/00.Workspace
  01.OH61AOSP16/real-work/                a2hlab/01.OH61AOSP16(分支 zhao)
~/workspace/octoscode/                    octos-org/octoscode(olp-* 脚本从这里调)
~/workspace/herdr/                        hagency-org/herdr
~/.octos/                                 octos 状态:profiles/(含 key,不入库)、board-locks/、outer/evo/
```

VM `a2hlab` 里(`~` = VM 用户的家目录,OrbStack 下与 Mac 用户同名):

```
~/a2hlab/ws/                    构建工作区;必须 bind mount 到作者原路径 /home/dspfac/a2hlab/source-closure/verify
  toolchains/                   clang-15(feef13a3)、ohos-sdk、jdk21、android-build-tools35、kotlin1822、rust194
  android-source/               AOSP 源码子集(16 GB)
  inputs/                       构建输入(3.8 GB)
  westlake/                     a2hlab/westlake @ 22b9453
~/a2hlab/manifest/              a2hlab/manifest 分支 local-pins-main
~/a2hlab/tools/libmap32bit.so   Rosetta 下主机 dex2oat 需要 LD_PRELOAD 它
```

---

## 3. 仓库

用 §5a 的解包脚本时仓库已经就位、remote 已配好,这一节可跳过。手工克隆:

```sh
cd <workspaces>                                                       # 例如 ~/alvin
git clone https://github.com/a2hlab/westlake-harness.git              # 你自己上传的那份(全)
cd westlake-harness
git remote rename origin a2hlab
git remote add origin https://github.com/A2OH/westlake-harness        # 原始上游,只读
git fetch --all
```

- **推送去 `a2hlab`**(原始仓库 A2OH 当前账号无推送权限)。推送一律等用户明示(AGENTS.md)。
- commit-msg 钩子:本机放在 `~/.config/git/hooks`(`git config --global core.hooksPath ~/.config/git/hooks`),拒收 Claude 署名行。新机器照样配,不要 `--no-verify`。
- 车道 worktree 按需重建,例如 `git worktree add ../westlake-harness-bms-deploy feat/bms-route-deploy`。当前车道对应关系:

| worktree | 分支 | 车道 |
|---|---|---|
| westlake-harness | master | 外环(claude) |
| westlake-harness-bms-deploy | feat/bms-route-deploy | 部署/横扫工具 |
| westlake-harness-bms | analysis/bms-route-study | cx-bms(codex,静态预测/打分) |
| westlake-harness-t0 | feat/app-lighting-t0 | cx-t0(codex,native 批次) |
| westlake-harness-t3 | feat/app-lighting-t3 | cc-t3(claude,JAR 批次) |
| westlake-harness-t4 | feat/app-lighting-t4 | oc-t4(octoscode/glm,dex2oat/boot image) |
| westlake-harness-wiki | feat/wikipedia-line | cc-wiki(claude,Wikipedia/Skia) |
| westlake-harness-walls | feat/bms-walls | 墙分诊 |
| westlake-harness-b4 | feat/bms-sweep | 横扫 |

- 换机时有未提交改动的 worktree,文本部分已快照到 `wip/20260930/<原分支>`(车道自己的分支没动)。在新机器上续做:`git checkout <原分支> && git checkout wip/20260930/<原分支> -- .`,或直接 `git merge --squash`。截图/运行目录不在快照里,在 hw248 的 `harness-untracked` 包(§5)。
- worktree 重建后,`harness-untracked` 解包会把原始运行目录放回各 worktree 的原位置(路径按 `westlake-harness-<名>/…` 存)。

---

## 4. 工具清单(控制端 Mac)

| 工具 | 本机版本 | 装法 / 备注 |
|---|---|---|
| Homebrew | — | `git gh python@3.14 ffmpeg coreutils zig jq zstd rsync mise node` |
| git / gh | 2.55.0 / 2.97.0 | `gh auth login`,账号要有 a2hlab 组织写权限 |
| Python | 3.14.6(brew)+ 3.12(mise,venv) | `westlake-inputs/venv`:mise 的 Python 3.12 建,`pip install androguard==4.1.4 apkInspector==1.3.7 lxml==6.1.3 PyYAML==6.0.3`(venv 不跨机器拷,重建) |
| JDK | Temurin 21.0.6+7 | 由 `westlake-inputs/mise.toml` 钉,`cd westlake-inputs && mise install` |
| GNU coreutils | brew | 进化环采集要 GNU `stat`:`export PATH=/opt/homebrew/opt/coreutils/libexec/gnubin:$PATH` |
| ffmpeg | 8.1.2 | `scripts/lab/contact_sheet.sh` 拼图 |
| DevEco Studio | 6.1.1 | 取 hdc:`/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc`(3.2.0d);其 `native/llvm` 可做快速迭代编译(字节与锁定工具链不同,不做交付物) |
| Android SDK | platform-tools(adb 1.0.41)、build-tools 34/36.1/37、NDK 23.1.7779620 | `~/Library/Android/sdk`;`env-mac.sh` 用 NDK 的 clang/llvm-readelf 做 host shim |
| OrbStack | 2.2.3 | 建 VM `a2hlab`(§6) |
| Docker | 29.4.0(OrbStack 自带) | 构建镜像 `a2hlab-build:24.04`(§6) |
| Rust / cargo | 1.94.0 | 装 octoscode、herdr 依赖;agent-spec |
| Zig | 0.16.0(mise)| herdr 需要 0.16;brew 的 0.15.2 不够。依赖预取 `scripts/lab/zig_prefetch_build.sh` |
| Node | 26.5.0 | `npm i -g @octos-org/octos`(rc 标签可能落后 GitHub release,见 §8) |
| octos / octoscode | 2.0.3-rc.12 / 0.3.0-rc.11 | octoscode:`git clone https://github.com/octos-org/octoscode ~/workspace/octoscode && cargo install --path ~/workspace/octoscode --locked` |
| herdr | 0.9.1 | `git clone -b feat/octoscode-agent https://github.com/hagency-org/herdr ~/workspace/herdr`,用 Zig 0.16 构建;server 由用户自己的终端起 |
| Claude Code | 2.1.285 | 外环与 cc-* 车道 |
| codex-cli | 0.158.0 | cx-* 车道,`--dangerously-bypass-approvals-and-sandbox` |
| kimi-code | `~/.kimi-code/bin/kimi` | kimi 车道 |
| agent-spec | 1.4.0 | `agent-spec lint specs/<主题>/t*.spec.md --min-score 0.7` |

每次开工前:`source <workspaces>/westlake-inputs/env-mac.sh`(cc/readelf/sha256sum shim + mise 钉住的 JDK/Python;不 source 时测试 2 fail 4 error)。

**shell 陷阱**:本机 `ls/cat/grep/du/df` 被别名成 eza/bat/ugrep/dust/duf,脚本里一律写 `/bin/ls`、`/usr/bin/grep`、`command du`;zsh 不拆分 `$var`。新机器若没有这些别名,反而更干净。

---

## 5. 搬运代码与制品

### 5a. AirDrop / 移动硬盘(首选,一次搬完)

旧 Mac:

```sh
scripts/lab/pack_airdrop.sh            # 输出 <workspaces>/_airdrop-<日期>/,约 50 GB;可重跑,只补缺的
```

把整个 `_airdrop-<日期>/` 文件夹 AirDrop(或拷移动硬盘)到新 Mac,然后在新 Mac 上:

```sh
brew install zstd
bash ~/Downloads/_airdrop-<日期>/unpack_airdrop.sh ~/alvin     # 参数 = 你的 workspaces 目录
```

它依次:①逐文件核 SHA256SUMS;②从 bundle 克隆 westlake-harness(远程 `a2hlab` 指回 GitHub,`origin` 为只读上游)、Westlake(到 `~/orca/westlake`)、00.Workspace、real-work、harmony;③重建 61 个 worktree(含 `wip/20260930/*` 以外的全部车道分支);④解运行状态,顺序为 live → inputs-tools → 历史代包 → 伴随仓库未跟踪文件 → 原始运行记录 → 黑板(最后,保证最新)→ VM 包(到 `<workspaces>/_a2hlab/`)。重跑会跳过已完成的部分。新 Mac 需约 200 GB 空闲。

| 分卷成员 | 解到 | 内容 |
|---|---|---|
| `git/*.bundle` + `repos.tsv` + `worktrees.tsv` | 各仓库位置 | 全部 ref;worktree 清单(路径 + 分支) |
| `live` | `<workspaces>/` | 当前运行包(v3c 底座、N2、N1、asset-fd、FZ-001 安装器)、`westlake-generation-state`(三板部署状态与原厂备份,回滚必需)、`vm-copies`(全部 JAR)、`westlake-inputs`(含 18 GB APK,不含 venv/tools)、`oh61-bms-kit`、`westlake-b90-controls-inputs` |
| `inputs-tools` | `<workspaces>/westlake-inputs/tools/` | 车道日常调用的脚本副本(每次打包都重打,保证与仓库一致) |
| `a2hlab-vm` | `<workspaces>/_a2hlab/` → VM `~/a2hlab/` | 锁定工具链 clang-15(feef13a3)/ohos-sdk/jdk21/build-tools35/kotlin/rust、`android-source`(16 GB)、构建输入、`westlake` 源码、`westlake-all0925`、`art-108`、`tools/`(libmap32bit.so)、`manifest/` |
| `harness-untracked` | `<workspaces>/` | 61 个 worktree 里 git 不跟踪的文件:各次横扫原始运行目录(截图、hilog、faultlog)、`bms/src/.work`(route-A 各代生成物与冻结工具链) |
| `workspaces-history` | `<workspaces>/` | 历史代包(v2/v3/b87/b92/b93/flutter/html-compat…)与一次性源码树 |
| `companion-untracked` | `<workspaces>/` | 00.Workspace、real-work(18 GB 构建产物)、westlake-bms-suite、harmony-main-adapter 里 git 不跟踪的文件 |
| `octos-state` | `<workspaces>/westlake-harness/.octos/` | OLP 黑板(按设计不入 git) |

大成员按 4000 MB 分卷,AirDrop 中断只需重传失败的那一卷。tar.zst 按文件名排序后用 `zstd --long=31` 去重(52 GiB 原始运行记录压到约 4 GiB);手工解包:`cat <成员>.part* | zstd -d --long=31 | tar -xf - -C <目标>`,同目录 `<成员>.tar.zst.files` 是成员清单。

### 5b. 从 hw248 拉(不在一处时)

同一批制品在 hw248 上有镜像(不含 git bundle 以外的仓库),目录由操作者告知:

```sh
export LAB_STATE_DIR=<hw248 上的镜像目录>
scripts/lab/fetch_lab_state.sh --list
scripts/lab/fetch_lab_state.sh --into-vm               # 上板要的全部 + VM 工具链
scripts/lab/fetch_lab_state.sh a2hlab-source harness-untracked workspaces-history companion-untracked git
```

旧机器补传:`LAB_STATE_DIR=… scripts/lab/push_lab_state.sh`(只在 hw248 与本机校验清单完全一致时跳过)。

制品没下完也能先跑代码侧:单测、静态扫描、`check_frozen.py`。上板必须先有 `generations` + `generation-state` + `vm-copies` + `apks`。

---

## 6. 构建环境

**OrbStack VM**(与本机一致):

```sh
orb create --arch amd64 ubuntu:noble a2hlab
orb -m a2hlab bash -lc 'sudo apt-get update && sudo apt-get install -y build-essential ccache git git-lfs python3 python3-yaml python3-venv rsync unzip zip xz-utils zstd xxd'
# 解 a2hlab-toolchains / a2hlab-source 到 VM ~/a2hlab 后:
orb -m a2hlab bash -lc 'A=/home/dspfac/a2hlab/source-closure/verify; sudo mkdir -p $A && sudo mount --bind ~/a2hlab/ws $A'   # VM 每次重启后都要重挂
orb -m a2hlab bash -lc 'git clone https://github.com/a2hlab/westlake.git ~/a2hlab/ws/westlake && git -C ~/a2hlab/ws/westlake checkout 22b9453'
```

- apt 与 PyPI 走华为云镜像(`mirrors.huaweicloud.com`),GitHub 直连不稳。
- VM 里没有 USB,需要 hdc 的脚本经 `scripts/lab/hdc_mac.sh` 转发到 Mac。
- VM 没配 git 身份,提交时 `git -c user.name=… -c user.email=…`。

**docker 构建(默认路径)**:`scripts/lab/dockbuild.sh image`(一次,约 90 s)→ `dockbuild.sh check` → `dockbuild.sh run -- <命令>`。镜像只提供 userland,工具链从挂进来的 `~/a2hlab/ws/toolchains` 取,所以镜像不影响产物字节。

**dex2oat / boot image**:官方 android-14.0.0_r16 host dex2oat 在 hw248 `/home/alvin/aosp-14.0.0_r16-dex2oat`,配方与哈希见 `knowledge/toolchains/dex2oat-a14.md`,不要重新找。

**冻结检查**:构建前 `python3 scripts/lab/check_frozen.py --source-root <worktree>`,部署前 `--package <代包目录>`(规则见 `knowledge/frozen/FROZEN.md`)。

---

## 7. 板子

| 序列号(hdc `-t` 用完整串) | 当前状态 |
|---|---|
| `5ea34a4500000000000000001123012c` | U2 |
| `61b0657200000000000000000324012c` | U2 |
| `5cd1e3dd00000000000000000923012c` | U2 |
| 安卓参考机 `N100CU025C18D000128`(adb) | 头条与用户数据不动 |

- DAYU600,OpenHarmony 6.1.0.31,1200×1920;hdc shell 为 root。上手流程见 `.octos/OPS-RUNBOOK.md` §2。
- **搬板**:板上状态不变,只需在新机器上 `hdc list targets` 看到三块板,再跑一次只读体检(`scripts/lab/run_facts.py`、HW 对照)。`westlake-generation-state/` 要带旧机器**最后一次部署之后**的版本,否则回滚会找不到原厂备份。
- **两台控制端不要同时连同一块板**;板锁在各自机器的 `~/.octos/board-locks/`,互相看不见。
- **绝不 `kill -9` appspawn-x 主进程**(init 会崩、整机掉线);停起用 `begetctl stop_service/start_service appspawn-x`。
- 板子要连 WiFi 才能跑联网 app;Wikipedia 在本地网络下受 DNS 污染,需要代理/VPN(DIGEST)。

---

## 8. 凭据与账号(不入库,找操作者要)

| 项 | 用途 | 放哪 |
|---|---|---|
| hw248 ssh 登录 | 远程构建、制品镜像 | `~/.ssh/config` 里 `Host hw248`,用密钥 |
| GitHub 账号(a2hlab 组织写权限) | 推送、拉私有仓库(a2hlab/westlake、manifest、00.Workspace…) | `gh auth login` |
| 板子 WiFi 名与密码 | 板上联网 | 只在板上配置 |
| 模型 API:Anthropic(Claude Code)、OpenAI(codex)、Moonshot(kimi)、智谱(glm-5.3) | 各车道 | `~/.octos/profiles/{kimi,glm}.json`(结构:`config.llm.primary.{family_id,model_id,route.base_url}`)、各 CLI 自己的登录 |
| VM git 身份 | VM 内提交 | 提交时 `-c user.name/-c user.email` |

---

## 9. 冒烟自检(按顺序,全过才算环境就绪)

```sh
source <workspaces>/westlake-inputs/env-mac.sh
cd <workspaces>/westlake-harness
python3 -m unittest scripts/lab/test_check_frozen.py scripts/lab/test_compare_runs.py   # 15 + 7 通过
python3 scripts/lab/check_frozen.py --package ../westlake-generation-n2-51a78bde         # 0 violation
(cd tools/spec-checks && cargo test)                                                     # agent-spec 测试层
$HDC list targets                                                                        # 三块板
scripts/lab/dockbuild.sh check                                                           # 构建挂载
ssh hw248 "ls $LAB_STATE_DIR"                                                            # 制品镜像可达(用 5b 时)
herdr --version && octos --version && octoscode --version && codex --version && claude --version
```

然后按 AGENTS.md「开工」读 `.octos/KNOWLEDGE-DIGEST.md` 与 `.octos/OPS-RUNBOOK.md`。外环上岗按 `/octoloop outer`;车道重建按 RUNBOOK §6。

---

## 10. 切换当天(旧机器 → 新机器)

hw248 上的镜像是 2026-09-30 下午的快照;黑板和 `generation-state` 之后还会变。真正切换时:

1. 旧机器:各车道收口、提交;`ls ~/.octos/board-locks/*.holder` 为空(三块板锁都已释放)。
2. 旧机器:`scripts/lab/push_lab_state.sh --steps live,git`——只重传有变化的包(黑板、generation-state、git bundle),其余按校验清单跳过;再 `git push a2hlab --all`。
3. 板子与 hub 的 USB 改接新机器。**此后旧机器不再对板做任何写操作**。
4. 新机器:按 §3 拉代码,`scripts/lab/fetch_lab_state.sh --into-vm`,跑 §9 冒烟自检,对三块板做只读体检后再派单。
