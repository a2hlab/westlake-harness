# 演示制品：按版本取回，不依赖 worktree

源码、补丁、构建说明和文件清单保存在 Git 主线；大型二进制、SDK、原始构建日志保存在私有 SHA256 制品库。一个发布 ID 固定一份清单，禁止覆盖。同名 `.so` 不是版本标识，完整 SHA256 才是。

当前版本入口：[61b T150 制品及构建清单](../../benchmark/2026-10-26-demo-artifact-recovery/intake/README.md)。恢复验收和边界见[本轮证据](../../benchmark/2026-10-26-demo-artifact-recovery/README.md)。

## 换一台 Mac 如何取回

1. 安装 Git、Python 3、支持 `--protect-args` 的 rsync（Homebrew rsync）；按根目录 [env.md](../../env.md) 配置所需开发环境。仅取回字节不需要先安装完整构建环境。
2. 从远程仓库检出记录了该发布的主线 commit，使用仓库中的 manifest，不能用聊天里的短 SHA 或服务器上可变的 `latest` 代替。
3. 在新机器上配置自己的 SSH 凭据及服务器 alias。凭据不在仓库，也不能从 worktree 备份中恢复。
4. 运行下面的命令。`cache`、`demo`、`receipt.json` 必须尚不存在；父目录先建好。

```bash
git clone https://github.com/a2hlab/westlake-harness.git
cd westlake-harness

export WESTLAKE_ARTIFACT_REMOTE=hw248
export WESTLAKE_ARTIFACT_REMOTE_STORE=westlake-artifact-store
RECOVERY_ROOT="$HOME/.local/share/westlake/recovered-demo"
mkdir -p "$RECOVERY_ROOT"

python3 scripts/lab/artifact_fetch.py \
  --manifest benchmark/2026-10-26-demo-artifact-recovery/intake/manifest.json \
  --cache "$RECOVERY_ROOT/cache" \
  --dest "$RECOVERY_ROOT/demo" \
  --receipt "$RECOVERY_ROOT/receipt.json"
```

命令只从指定服务器下载所需 SHA 对象，校验全部大小和 SHA，再复制到新的恢复目录。网络失败、缺件、坏件均返回非零，不从旧 worktree 偷偷补件。成功时 receipt 中 `success=true`，并记录使用的 manifest 完整 SHA、下载命令及校验结果。可以再运行：

```bash
python3 scripts/lab/artifact_store.py verify \
  --manifest benchmark/2026-10-26-demo-artifact-recovery/intake/manifest.json \
  --store "$RECOVERY_ROOT/cache"
```

`demo/runtime` 是运行集合，`demo/deployment/rollback` 是回滚件，`demo/build` 是归档构建材料。精确路径以 manifest 为准。恢复目录不会自动安装、启动程序或改设备；目标板的系统版本、安装路径、权限和配置仍须按原部署记录核对。

## 如何构建、哪些还不能重建

详见[逐组件状态](../../benchmark/2026-10-26-demo-artifact-recovery/intake/build-status.json)及 intake README 的路径重定位说明。

| 对象 | 已保存内容 | 可作出的结论 |
|---|---|---|
| `3291…` 演示候选库 | 精确二进制、5 个编译单元、SDK/头文件/工具链、链接输入、原始日志 | 原二进制可恢复；本轮收齐增量重编和重链所需输入，不能称为整个库全源码重建 |
| `b0e…` 回滚库 | 精确二进制和原编译/重链回执 | 可恢复回滚字节；完整源构建闭包尚未证明 |
| 宿主 HAP | 已签名 HAP、对应源码/ABC/编译器和日志 | 可恢复原 HAP；签名环境及编译器共享依赖尚未独立闭合 |
| ART、运行库、BCP JAR、boot | 清单中的精确历史运行字节 | 可按 SHA 取回；并非每件都有完整源代码、工具链及原构建日志闭包 |
| 第三方 APK | 私有库中的精确安装包及对应 native 文件 | 字节可恢复，不宣称拥有第三方源码或可以重建 |

103 个复用链接输入实际为 **46 个 `.o`、56 个 `.so`、1 个 `.a`**。保留这些输入可以避免丢失已验证链接基线，但不等于它们全部已有源码重编证明。

## 新版本如何归档

构建时把 stdout、stderr、退出码、源码 commit/补丁、工具链版本及哈希写入持久目录。生成新的 manifest，包含每个文件的路径、SHA256、大小、mode、role，以及构建和实测证据。然后：

```bash
python3 scripts/lab/artifact_store.py ingest \
  --manifest release.json --source-root "$RELEASE_STAGE" --store "$ARTIFACT_STORE"
python3 scripts/lab/artifact_publish.py \
  --manifest release.json --store "$ARTIFACT_STORE" --receipt "$PUBLISH_RECEIPT"
```

发布先传入远端独立暂存区，校验后放入对象库，最后发布不可覆盖的 release 清单。已有 SHA 对象损坏时拒绝发布，不能用上传覆盖来掩盖损坏。每个正式版本都要做一次远程空缓存恢复；仅上传成功不算恢复验收。

## 什么时候可以删除 worktree

只有该 worktree 的全部有用改动已进入远程 Git，需保留的产物和证据已归档，且远程空缓存恢复通过，才对这个 worktree 单独判定可删除。本轮的演示归档不授权或证明所有实验 worktree 都可删除。

本机 CAS 与独立服务器是两个故障域；服务器访问权限、磁盘健康和异地备份仍需维护。当前流程未配置自动定时备份或第三处异地副本。不要让唯一服务器副本随清理命令或账号退役一起消失。
