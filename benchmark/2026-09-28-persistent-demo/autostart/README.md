# Toutiao 关机开机自恢复（standalone, 无 hdc）— 根因与现状

**日期**: 2026-09-28  ·  **板**: 5cd1e3dd00000000000000000923012c (DAYU600 / OH 6.1.0.31)
**目标**: 板子断电重启后，**无 Mac/hdc 介入**，头条 feed 自动回到物理屏。
**现状**: **未达成**。可靠上屏路径仍是 Mac 侧 `provision_toutiao.sh <fullkey>`（热板 25–40s，
刚开机 90–150s）。

## TL;DR

| init 服务 `secon` | 脚本是否执行 | 结果 |
|---|---|---|
| 不设 | 否 | init 域被 SELinux 挡在 `/data` 脚本外 |
| `u:r:su:s0` | **是**（`boot_toutiao.log` 写出 `[boot] start uptime=10…watchdog+keeper launched uptime=51`） | spawn 子进程 `PR_SET_KEEPCAPS(0)` EPERM → abort，看护卡 `BOOTSTRAP` |
| `u:r:sh:s0` | **否**（uptime 91s+ 仍无 `boot_toutiao.log`，`state` 未重建，`pgrep -f '[b]oot_toutiao.sh'`=0） | 服务没跑起来；原因未查（疑 init→sh 的服务域转换不被允许） |

**5cd 当前装的是 sh 版 cfg**（最后一次实验留下的）。两版都不能自启到 feed。

## su 域失败的根因（实证）

spawn 子进程 stderr（`<RT>/private-tmp/adapter_child_<pid>.stderr`）：
```
[AppSpawnX][D] Set UID to 20010053
[AppSpawnX] applySELinux: child secon transitioned successfully (apl=normal)
[WESTLAKE-APP-PRIV] PR_SET_KEEPCAPS(0) failed: Operation not permitted
[AppSpawnX][E] wl_finalize_app_privileges failed, ret=-1 – aborting child
```
SELinux 转换、DAC 降权都成功，唯独 `PR_SET_KEEPCAPS(0)` EPERM。该 prctl 只在
`SECBIT_KEEP_CAPS_LOCKED` 被设时返回 EPERM——`su` 域进程继承了锁住的 securebits。
同一套看护脚本从 hdc shell（`sh` 域，未锁）跑 → 每次都 READY/feed。

## 推荐修法（未实施）

**改 runtime，不改域**：`wl_finalize_app_privileges` 里，`PR_SET_KEEPCAPS(0)` 返回 EPERM 时先
`prctl(PR_GET_KEEPCAPS)`；已是 0 就当成功继续（目标状态本来就达成了，只是锁不让"再设一次"）。
这样 su 域 init 自启就能走通，不需要找能跑的 SELinux 域。

## 排除的岔路：secreset（清 securebits）

`secreset.c`：root 下 `prctl(PR_SET_SECUREBITS, 0)` 清锁再 exec。自检在 sh 域即
`PR_SET_SECUREBITS(0) failed: Operation not permitted`——需要 CAP_SETPCAP 且各域都被拒。
方向也不对：要害是锁住后"再设 keepcaps"被拒，而不是锁本身。只留源码存档，
重建：`aarch64-unknown-linux-ohos-clang -static -Os -o secreset secreset.c`（OH SDK llvm）。

## 文件

| 文件 | 说明 |
|---|---|
| `boot_toutiao.sh` | 开机脚本，镜像 `provision_toutiao.sh` 第 6+7 步（重建 `$RT/private-tmp/asx` 挂载点 + chown/restorecon → 起看护 + keeper）。su 域下已验证能跑到底。 |
| `wl_toutiao.cfg` | init 服务，`secon=u:r:sh:s0`（**实测不执行**）。 |
| `wl_toutiao.su.cfg` | init 服务，`secon=u:r:su:s0`（**实测执行，但 keepcaps 失败**）。改 runtime 后应用这版。 |
| `secreset.c` | 已证伪的死路，仅存档。 |

安装：`hdc shell "mount -o rw,remount /"` → `hdc file send <cfg> /system/etc/init/wl_toutiao.cfg`
→ `hdc file send boot_toutiao.sh /data/local/tmp/operator45/boot_toutiao.sh`。
**/system 可 remount 写**（早先"OH /system 只读做不了自启"的说法不对）。

## 实验中踩的坑

- `hdc shell "… pgrep -f X …"` 计数恒 +1：`pgrep -f` 匹配到包着它的 `sh -c` 命令行。
  用 `pgrep -f '[X]yz'`。本次 sh 域"脚本在跑"的初判就是这个假阳性。
- `state` 文件在 `/data`，重启不清：开机后读到 `READY` 可能是上一轮残留。验证前先删。
- `provision_toutiao.sh` 150s 窗口在刚开机的板上会**超时误判 FAIL**（窗口到点时 state 差一步
  到 READY）。以截图为准。
- 板子插在 hub 上，USB 在 provision/remount 瞬间掉过三次，最长 50 分钟没回，只能物理重插。
