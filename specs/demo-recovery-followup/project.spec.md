spec: project
name: "Demo recovery repair and API evidence follow-up"
---

## 约束

- 全部工作在各自 worktree 离线完成，不联系板子、VM、远端，不写现有 seal run、签名、计划、冻结表或部署目录，不推送。
- 当前 61b boot ac87bbbe 的原始证据只读；guardian 已退出、stop 早于 SIGSEGV，snapshot 失败与 unknown 已证，具体权限根因与 stop actor 未证。
- 保留用户现存 app-data/data/webview；不得自动点击隐私同意；不得杀 U13 主 appspawn-x、按名称 kill 或清理非 Route B 进程。
- 修复只作为独立候选交件；现有 driver、plan、placement 不改。上板、重启、清 stop、重签需要外环另行审查具体方案，不由此任务触发。
- 每项结论附本地来源路径与 SHA256，历史来源保留历史范围；unknown 不强填，不将 AOSP 源码版本、SDK level 或构建号混称实测兼容。
- 每路交英文 README、results.json、landing-paths.txt；代码与证据在同包，原始测试输出持久保存。只提交自己的明确路径，禁止 git add -A，不切别人的工作树分支。

## 已定决策

- cx-t0 负责恢复候选和行为测试；cx-bms 独立审查部署对象与准备最小执行/回滚配方；oc-t4 补冻结 API 版本绑定，三路写入路径互斥。
- 以功能断言验候选脚本；离线测试通过不代表板上上屏或可签封板。内存崩溃根因修复不在本轮范围。
