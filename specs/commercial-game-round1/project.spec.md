spec: project
name: "Commercial game round one: Genshin input and reuse qualification"
satisfies: [REQ-COMMERCIAL-GAME]
---
## 意图
以此前指定的原神作为首个商业游戏目标，先取得精确输入与公共能力差异。后续按实际阻塞推进最小启动、资源加载和交互，不把BoatAttack亮屏视为原神可玩。
## 约束
- 本阶段只有输入定位与静态复用两条车道；61b、5cd、5ea均无设备写入，不取板锁。后继上板契约由外环按精确包及空闲板fresh状态派发，61b保持演示版。
- 原始argv/rc/stdout/stderr及输入SHA保存在持久私有目录；公开仓库仅小证据及别名，不提交APK、资产、凭据或账号信息。所有失败保留。
- CC仅包定位/普通静态工具；REA如需使用只交Codex或octoscode，并先给精确对象与问题。不开绕过授权、反作弊或保护机制任务。
- 独立worktree与analysis分支，内环只提交不推送、不修改主树；旧知识和失败记录不覆盖。不扫整盘或递归grep二进制。
## 已定决策
- t1现有CC窗口执行；t2现有octoscode执行；外环观测正信号与负状态、复核与合入。无需为没有输入的动态任务提前占用板。
- 优先本地已有索引及manifest，再OrbStack a2hlab，再hw248，再仓库已记载的macserver制品路径。网络只读访问已有环境获本轮任务授权；本阶段不下载新游戏、不登录、不运行APK。
