# 给在本仓库工作的 agent(codex / kimi / Claude 等)

## 开工
0. 新机器 / 换机:先按根目录 `env.md` 备环境(工具清单、目录布局、从 hw248 取不进 git 的制品、凭据清单、冒烟自检)。
1. 先读 `.octos/KNOWLEDGE-DIGEST.md`(已确认的事实、方法论陷阱、稳定基线——别重新论证),再读 `.octos/OPS-RUNBOOK.md`(机器怎么操作)。
2. 新确认的根因、新踩的坑,精炼成一行追加进 DIGEST;操作方法的变化写进 RUNBOOK。**知识放仓库,不要只留在某个 agent 的私有记忆里**——别的 agent 和别的会话看不到。
3. 回复用户用中文(代码、命令、标识符保持原样)。

## 怎么积累
- 发现写成 `benchmark/<YYYY-MM-DD>-<主题>/`:`README.md`(英文、证据先行、给数字、先写原来错在哪、这次立下什么规则)+ `results.json` + 小的证据文件;再在根 `README.md` 的 Layout 表加一行加粗。
- 多步任务用 agent-spec 契约规划:`specs/<主题>/` 下放 `project.spec.md`(共享约束)+ `t<N>-<名>.spec.md`(用 `depends:` 连依赖)。交给 agent 前 `agent-spec lint specs/<主题>/t*.spec.md --min-score 0.7` 必须过(project spec 没有场景,不进这道门)。agent-spec 的测试层只会跑 `cargo test`,所以 `测试:` 选择器指向 `tools/spec-checks/` 里的 Rust 测试,由它转调真正的检查器(Python unittest / 脚本 / 板上 probe);要读截图才能判的场景标 `审核: human`,测试通过也只到 pendingreview。
- **进化环**(octoloop outer 第 5 步):改判/R2 记档由常驻哨采进 `.octos/EVOLUTION.md`,定期 `olp-evo-harvest.sh`+`olp-evo-retro.sh`(`OLP_EVO_REVIEW_BOARD=.octos/boards/app-lighting.md`)出简报;外环人工判跨条目复发,落成 `knowledge/context/evolution/FLAW-NNN.md` 记录(每次最多 3 条),同时把规则精炼成一行进 DIGEST/RUNBOOK、能改工具的改工具。
- `*.png/*.jpeg/*.jar/*.stderr` 默认被 `.gitignore` 忽略;README 引用到的证据截图用 `git add -f`,大二进制和 stderr 日志不入库。
- **仓库是公开的**(github.com/A2OH/westlake-harness):不提交密码、服务器账号、个人数据。
- **脚本不写死跟用户绑定的绝对路径**(用户 2026-09-30 定,`/Users/<名>`、`/home/<名>` 都不行):工作区用 `WORKSPACES`(`scripts/lab/lab_paths.sh` / `lab_paths.py` 解析)、家目录用 `$HOME`/`Path.home()`、仓库用脚本自身位置、hw248 路径走环境变量;门禁 `python3 scripts/lab/check_user_paths.py`,例外只进 `knowledge/gates/user-path-exceptions.json`(录制的证据、作者原构建路径等)。
- 上板的运行时产物(.so / jar / boot image),其源码快照、补丁序列、工具链哈希与构建脚本必须一并入库或存到持久位置(大文件放 hw248 `/home/alvin/`,仓库里记路径与哈希)。只留产物会让修复锁死在一台会消失的构建机上(DIGEST E.7「B6 为什么慢」)。

## 提交与推送
- commit-msg hook 拒收 Claude 署名行(`Co-Authored-By: …Claude`、`Generated with Claude Code`)。不要 `--no-verify`。
- **推送一律等用户明示。** 内环的报告在自己的 worktree + `analysis/…` 分支上提交,然后在黑板 ACK。

## 判定
- **截图是地面真相**。进程活着、`state=READY`、脚本打印 PASS 都不算上屏;以 `snapshot_display` 截图为准(DIGEST B.7)。
- 查进程计数别用裸 `pgrep -f`(会匹配到自己),见 RUNBOOK。
- ACK 里的截图数、存活数一律贴运行目录里 `facts.txt`(或 `scripts/lab/run_facts.py <运行目录>`)的原样输出(它从 `record.json` 的 `captured` 与进程表逐项数),不按计划写;数不出来写 unknown(#63、#71 两次把 0 张报成 26 张)。

## 板子纪律
- 板子写操作前先做只读检查。
- 用户说「保持」「别动」时,对那块板**零改动**,直到用户说「拉起」;心跳只做只读巡检。
- **不要在唯一能用的演示板上做实验**(重启测自启、删运行时目录、换配置)。用空闲板,或先问。
- 2026-09-28 起三块 OH 板(5ea34a45 / 5cd1e3dd / 61b06572)全部放开为实验板,当前没有演示板;以后用户再指定演示板,以用户当时的话为准。多板并行时每块板同一时刻只跑一个上板任务,只对白名单序列号下命令。安卓参考机允许安装测试 app 做对照(头条和用户数据仍不动)。
- **三板统一态、全量分片**(用户 2026-09-30 定):三块板平时保持同一个统一态(同一 native 包、runtime、JAR、安装器,以 `runtime-fingerprint.txt` 逐件一致为准),全量按 key 三板分片跑(一轮约 30 分钟),「一个修复在多个 app 上生效」也三板并行验。专项实验(如 Wikipedia)改成**短窗叠加**:在某块板叠上实验件、做完立刻回滚到统一态,不长期占一块板做专线。
- **上板窗口**:单项实验 ≤30 分钟;一次性批量验证可到 45 分钟。用完即释放锁。

## 做事方式

### 每轮怎么做
1. **验证过的就抄**:修墙先在 Westlake、00.Workspace、real-work 里找验证过的实现,谁做得全抄谁;都没有才自己写。README 写来源路径与 commit。
   **找源码的顺序**(用户 2026-09-30 定):先本地(Mac `~/orca/workspaces/` 下各树与 vm-copies)→ 再 OrbStack 机器(`orb -m a2hlab`)→ 再远程 hw248;三处都没有,就在 hw248 上下载(AOSP/OH 上游对应版本),不凭记忆推断源码。
2. **先预测再上板**:新一批 app 或新一代运行时上板前跑静态扫描(B10:JNI 覆盖、系统服务覆盖、manifest 分类、构建脚本体检),出机器可读的预测表,按挡住的 app 数排序,先修影响面最大的墙;派单引用预测表的行。扫描限时、能用就收,板子不等扫描。
3. **修好并验证过的公共 API 就冻结**(用户 2026-09-30 定,程序靠冻结积累;同日定为分级冻结):扫描发现的公共 API 墙(系统服务、JNI、manifest 投影、安装器授权……)修好后,只要 **≥2 个不同 app 过了这堵墙**——其中至少 1 个 app t20 截图亮,其余 app 由日志证明这个 API 的失败消失、首个致命点换到了别处(验证的是 API,不是 app)——外环当轮就登记进 `knowledge/frozen/frozen.json`(可读版 `knowledge/frozen/FROZEN.md`):API、实现文件路径 + git blob 或产物 SHA、验证过的 app 与截图/facts 证据。冻结后:
   - 任何构建与部署前跑 `python3 scripts/lab/check_frozen.py`,与登记不符就拒——不许悄悄改;
   - 新修复另起文件,不往冻结文件里加东西;冻结前先把实现拆成只含这一项的独立文件;
   - **外环可批的改动只有三种**:① 单变量对照(`compare_runs.py` 判 `variables: 1`)证明冻结项本身有缺陷;② 平台/ABI 变化必须重编;③ 同一产物里加新功能且原行为保留。条件:新版本让该条原证据里的每个 app 重新达到原证据的程度(原来 t20 亮的仍亮,原来过墙的仍过墙)、统一态全量不回退;先在 frozen.json 登记新版本(原因、对照、重验证据、全量路径)再部署,早报通知用户;
   - **删除或削弱冻结行为只有用户能批**。
   未冻结的改动默认单文件替换、带回滚,由 `deploy_generation.sh` 把关(SHA、单份 ART、桥接库版本、子进程 maps),不整代重建(B9)。
4. **按簇批量出版,一批修复一次上板**(用户 2026-09-30 重申):派单按死因簇表(cc-t3 的死 app 聚类、cx-bms 的漏报墙表)成批派,**每轮 JAR 只出一个版本、合进所有 JAR 层的簇;native 只出一个版本、合进所有 native 层的簇**,一次上板三板分片跑全量、读截图确认;出现回退再对半拆定位。不要一两堵墙出一版。对照预测与实测,漏掉的墙补进扫描器。
   **构建轮数只数源码/链接失败**:容器挂载、路径、工具链缺失这类环境失败修好就重跑,不计入轮数上限。
5. **门禁用例外表写法**:判据按最严写,另设例外表,每条写对象、理由、证据,外环认可才进表;扣除例外后仍有问题就拒绝(例:JNI 缺失扣除例外后不为空,`deploy_generation.sh` 拒绝部署)。放宽加例外,收紧删例外,门禁代码不动。
6. **提问不阻塞**:能按契约和黑板判断的自己定,写进 PROGRESS;只有越出契约边界(改禁止路径、动别的板、改验收标准)才问。

### 例外
- 运行时行为(信号处理顺序、namespace 走错、白屏、渲染线程偶发崩溃)静态看不出:别写设计文档或估算,**直接做最小关键实验**——写清通过/失败判据与退路,结果说了算。
- codex/GPT-Astra 会拒绝内存破坏诊断、hook、守卫页/写拦截、二进制补丁类任务(先 ACK,再显示 `This content can't be shown … cybersecurity requests may still be limited` 转 idle,像卡住其实是拒绝),这类交给 Claude agent。
