spec: project
name: Worktree independent artifact recovery
satisfies: [REQ-ARTIFACT-RECOVERY]
---
## 意图
从独立制品存储恢复演示版本，删除原worktree后仍可按清单获取精确二进制及构建资料。恢复能力和完整源码重建能力分别记录。
## 约束
- 不删除现有worktree、不改演示板、不改冻结行为、不上传商业APK到公开仓库。
- 二进制内容以完整SHA256寻址，发布清单不可覆盖；目录不得包含用户绑定绝对路径。
- 不依赖待删除worktree或本机缓存完成恢复验收；真实另一台Mac未测就写未测。
- 复用现有传输/指纹工具；不部署Gitea/Nexus、不重写构建系统。
