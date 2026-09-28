# Infrastructure

可执行接入与凭证**真文件**。树形说明（给模型按枝展开）在：

→ [`../knowledge/infra/`](../knowledge/infra/)

## 本目录（真源文件）

| 路径 | 作用 |
|---|---|
| [`access.md`](./access.md) | 真实凭证全文（与斧仓 ACCESS 对齐；勿和谐删除） |
| [`git-hooks/pre-push`](./git-hooks/pre-push) | 上游仅 main；fork 可推 feature |
| [`hosts.example.yaml`](./hosts.example.yaml) | 主机模板（无密码） |
| [`paths.example.env`](./paths.example.env) | 路径模板 |
| [`bin/`](./bin/) | 稳定命令入口 |

说明类长文已迁入 `docs/archive/knowledge-map/infra/{access,git,hosts,axe}/`，此处不再摊长表。

## 安装 pre-push

```bash
cp src/tools/infra/git-hooks/pre-push "$(git rev-parse --git-common-dir)/hooks/pre-push"
chmod +x "$(git rev-parse --git-common-dir)/hooks/pre-push"
```
