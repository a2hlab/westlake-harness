# Access

记录账号角色、访问申请方式和所需环境变量名；不要记录密码、Token、私钥或真实凭证。

## macserver(2026-08-05 owner 更新)

macserver(`alexyang@192.168.8.24:58222`)为常规工作机,**鼓励使用**,读写均不受限。
其上有现成的安卓基准环境(模拟器 + 原神 + hdc)与板子 hub;需要机器时优先用它,
动手前先看那台上已经有什么,不要在本机重装。允许的写入包括:

- `git push` / `fetch`
- `src/tools/ax_human_board_deploy.sh` 等 scp/ssh 部署与远端进程操作
- artifact cache(`src/tools/infra/demo-artifact-cache.json` primary store)的 rsync+ssh 写入

2026-08-04 立的"本机禁写 macserver"已由 owner 于 2026-08-05 取消,裁决见
`var/state/decisions/20260805-macserver-write-ban-lifted.md`。

### 先确认自己在哪台机器上

agent 可能**本身就跑在 macserver 上**,这种情况下上述操作是本地操作,不需要 ssh、
scp 或隧道。开工前先确认:

```sh
hostname; whoami; uname -a
ls -d /Users/mac-server /Users/alexyang 2>/dev/null   # 存在则大概率已在 macserver 上
hdc list targets                                       # 能直接列出板子则板子是本机 USB 直连
```

已在 macserver 上时:直接读写路径、直接 `hdc`,不要绕 `ssh macserver ...`;
Desktop/code 这类工作目录就是本地目录。不在 macserver 上时才走 ssh/scp。
把"远程"当默认假设会多绕一层隧道,并在隧道挂掉时产生与实际问题无关的排查。

## 开发板

reboot / wipe / flash / 覆盖 substrate / 替换 framework jar **不禁止,并且鼓励**——
状态可疑就刷成干净态再继续,不必在脏状态上反复调试;现场运维可断电重插与重新刷机。
授权真源 `docs/guides/board-risk-policy.md`,`BOARDS.toml` 的 `forbidden` 字段已作废。

## 仍然生效的约束(来自全局规则)

只作用于宿主机(macserver / AlexPC / alexyLinux),不作用于开发板:

- 不重启宿主机;不停止 ssh / 隧道 / 代理 / 远程桌面 / 容器 / web 服务;
  不按名字批量 kill,只对确认过 PID/exe/cmdline/owner 的自有进程操作。


