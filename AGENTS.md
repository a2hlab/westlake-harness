# 给在本仓库工作的 agent(codex / kimi / Claude 等)

## 开工
1. 先读 `.octos/KNOWLEDGE-DIGEST.md`(已确认的事实、方法论陷阱、稳定基线——别重新论证),再读 `.octos/OPS-RUNBOOK.md`(机器怎么操作)。
2. 新确认的根因、新踩的坑,精炼成一行追加进 DIGEST;操作方法的变化写进 RUNBOOK。**知识放仓库,不要只留在某个 agent 的私有记忆里**——别的 agent 和别的会话看不到。
3. 回复用户用中文(代码、命令、标识符保持原样)。

## 怎么积累
- 发现写成 `benchmark/<YYYY-MM-DD>-<主题>/`:`README.md`(英文、证据先行、给数字、先写原来错在哪、这次立下什么规则)+ `results.json` + 小的证据文件;再在根 `README.md` 的 Layout 表加一行加粗。
- 多步任务用 agent-spec 契约规划:`specs/<主题>/` 下放 `project.spec.md`(共享约束)+ `t<N>-<名>.spec.md`(用 `depends:` 连依赖)。交给 agent 前 `agent-spec lint specs/<主题>/t*.spec.md --min-score 0.7` 必须过(project spec 没有场景,不进这道门)。agent-spec 的测试层只会跑 `cargo test`,所以 `测试:` 选择器指向 `tools/spec-checks/` 里的 Rust 测试,由它转调真正的检查器(Python unittest / 脚本 / 板上 probe);要读截图才能判的场景标 `审核: human`,测试通过也只到 pendingreview。
- 不写 `knowledge/context/evolution/` 记录(那是别的仓库的约定)。
- `*.png/*.jpeg/*.jar/*.stderr` 默认被 `.gitignore` 忽略;README 引用到的证据截图用 `git add -f`,大二进制和 stderr 日志不入库。
- **仓库是公开的**(github.com/A2OH/westlake-harness):不提交密码、服务器账号、个人数据。
- 上板的运行时产物(.so / jar / boot image),其源码快照、补丁序列、工具链哈希与构建脚本必须一并入库或存到持久位置(大文件放 hw248 `/home/alvin/`,仓库里记路径与哈希)。只留产物会让修复锁死在一台会消失的构建机上(DIGEST E.7「B6 为什么慢」)。

## 提交与推送
- commit-msg hook 拒收 Claude 署名行(`Co-Authored-By: …Claude`、`Generated with Claude Code`)。不要 `--no-verify`。
- **推送一律等用户明示。** 内环的报告在自己的 worktree + `analysis/…` 分支上提交,然后在黑板 ACK。

## 判定
- **截图是地面真相**。进程活着、`state=READY`、脚本打印 PASS 都不算上屏;以 `snapshot_display` 截图为准(DIGEST B.7)。
- 查进程计数别用裸 `pgrep -f`(会匹配到自己),见 RUNBOOK。

## 板子纪律
- 板子写操作前先做只读检查。
- 用户说「保持」「别动」时,对那块板**零改动**,直到用户说「拉起」;心跳只做只读巡检。
- **不要在唯一能用的演示板上做实验**(重启测自启、删运行时目录、换配置)。用空闲板,或先问。
- 2026-09-28 起三块 OH 板(5ea34a45 / 5cd1e3dd / 61b06572)全部放开为实验板,当前没有演示板;以后用户再指定演示板,以用户当时的话为准。多板并行时每块板同一时刻只跑一个上板任务,只对白名单序列号下命令。安卓参考机允许安装测试 app 做对照(头条和用户数据仍不动)。

## 做事方式
- 可行性有疑问时,别写设计文档或"N 人日"估算来回推,**立刻做最小的关键实验**:写清关键点、通过/失败判据、失败后的退路,结果说了算。agent 一小时就能写完"几人日"的代码。
- **上板是为了确认预测**:新一批 app 或新一代运行时上板前,先跑静态扫描——JNI 覆盖矩阵、系统服务覆盖、manifest 分类、构建脚本体检(B10,`specs/bms-copy/b10-static-wall-prediction.spec.md`),产出「每个 app 预计撞哪几堵墙」的预测表,按挡住的 app 数排序,先修影响面最大的那堵。
- 派单条目必须引用预测表里对应的行;每轮上板后对照预测与实测,预测漏掉的墙补进扫描器,下次提前抓到。
- 能做成门禁的就做成门禁:例如 JNI 缺失清单(扣除逐条写明理由、经外环认可的例外)不为空时,`deploy_generation.sh` 拒绝部署。
- 任务路由:codex/GPT-Astra 会以"网络安全"内容策略拦截内存破坏诊断、hook、守卫页/写拦截、二进制补丁类任务——窗格先 ACK,然后显示 `This content can't be shown … cybersecurity requests may still be limited` 并转为 idle,看着像卡住,其实是拒绝。这类任务交给 Claude agent。
