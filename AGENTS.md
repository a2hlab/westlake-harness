# 给在本仓库工作的 agent(codex / kimi / Claude 等)

## 开工
1. 先读 `.octos/KNOWLEDGE-DIGEST.md`(已确认的事实、方法论陷阱、稳定基线——别重新论证),再读 `.octos/OPS-RUNBOOK.md`(机器怎么操作)。
2. 新确认的根因、新踩的坑,精炼成一行追加进 DIGEST;操作方法的变化写进 RUNBOOK。**知识放仓库,不要只留在某个 agent 的私有记忆里**——别的 agent 和别的会话看不到。
3. 回复用户用中文(代码、命令、标识符保持原样)。

## 怎么积累
- 发现写成 `benchmark/<YYYY-MM-DD>-<主题>/`:`README.md`(英文、证据先行、给数字、先写原来错在哪、这次立下什么规则)+ `results.json` + 小的证据文件;再在根 `README.md` 的 Layout 表加一行加粗。
- 不建 `.spec` 契约,不写 `knowledge/context/evolution/` 记录(那是别的仓库的约定)。
- `*.png/*.jpeg/*.jar/*.stderr` 默认被 `.gitignore` 忽略;README 引用到的证据截图用 `git add -f`,大二进制和 stderr 日志不入库。
- **仓库是公开的**(github.com/A2OH/westlake-harness):不提交密码、服务器账号、个人数据。

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

## 做事方式
- 可行性有疑问时,别写设计文档或"N 人日"估算来回推,**立刻做最小的关键实验**:写清关键点、通过/失败判据、失败后的退路,结果说了算。agent 一小时就能写完"几人日"的代码。
- 任务路由:codex/GPT-Astra 会以"网络安全"内容策略拦截内存破坏诊断、hook、守卫页/写拦截、二进制补丁类任务——窗格先 ACK,然后显示 `This content can't be shown … cybersecurity requests may still be limited` 并转为 idle,看着像卡住,其实是拒绝。这类任务交给 Claude agent。
