---
name: reproduce-boat-attack-apk
description: 在直连 OpenHarmony 6.1 的 61AE 或 8605 板上检查、恢复、快速验收、回滚或固定已跑通的 BoatAttack Android APK；可把开机状态固定为运行环境就绪但不自动启动，供演示者从桌面手动点击图标。固定 A 线原始 APK 和精确共享运行代，管理可回滚的 BoatAttack 私有 C7/C4/signal-box，验证 1920×1200 真实赛艇画面、同 PID、五次触摸与无终止性 fatal。用户提到 AttackBoat/BoatAttack、开机不自动拉起、演示手动点开、恢复早上已跑通路径或快速复现时使用；不用于推导新 adapter，也不把同源 HAP 当作 APK 结论。
---

# 复现 BoatAttack Android APK

使用 `scripts/reproduce.sh`。脚本固定 A 线原始 APK，所有兼容修改都位于 APK 外部；不会修改、重签或重新打包 APK。

这个 skill 同时管理两层状态：

- `check/restore/quick/status/rollback` 管理当前 boot 的固定 APK 复现与行为验收；
- `autostart-*` 管理设备原生开机预备服务，使同一固定运行代在 reboot 后恢复 10 个共享挂载、3 个应用私有挂载和 AppSpawnX，但不启动 BoatAttack Activity。

## 命令

```bash
.agents/skills/reproduce-boat-attack-apk/scripts/reproduce.sh check
.agents/skills/reproduce-boat-attack-apk/scripts/reproduce.sh quick
.agents/skills/reproduce-boat-attack-apk/scripts/reproduce.sh status
.agents/skills/reproduce-boat-attack-apk/scripts/reproduce.sh restore
.agents/skills/reproduce-boat-attack-apk/scripts/reproduce.sh rollback
.agents/skills/reproduce-boat-attack-apk/scripts/reproduce.sh autostart-status
.agents/skills/reproduce-boat-attack-apk/scripts/reproduce.sh autostart-install
.agents/skills/reproduce-boat-attack-apk/scripts/reproduce.sh autostart-activate
.agents/skills/reproduce-boat-attack-apk/scripts/reproduce.sh autostart-finalize
.agents/skills/reproduce-boat-attack-apk/scripts/reproduce.sh autostart-reboot-test
.agents/skills/reproduce-boat-attack-apk/scripts/reproduce.sh autostart-uninstall
```

第二个参数可指定 serial，但只接受已验收的 `61ae0be500000000000000000324012c` 或
`5ce2dcee00000000000000000923012c`（8605）。

- 接受态直接运行 `quick`；它不重复 trace、静态 dump、HAP 或 HelloWorld。
- `check` 只读检查固定输入、当前共享代、ZigZag receipt 和三个私有候选。
- `status` 只读显示身份、PID、hash 与 mount。
- `rollback` 仅停止 BoatAttack UID 并卸载三个应用私有 bind；保留原 APK 和共享层。
- `restore` 恢复精确共享运行代和三个 BoatAttack 私有候选；共享代未漂移时不会重跑 ZigZag。若共享代或本 boot receipt 漂移，它调用同候选 `run-light-risk`，只补一次必要的 ZigZag/HelloWorld 门禁，不 reboot、不刷机。

## 开机预备与手动点开

先运行 `autostart-status`。交付演示的接受态是桌面名称为 APK 原始标签 `BoatAttack`，并且 `launch_mode=MANUAL`、`boat_state=STOPPED_READY`、`current_pid=NONE`、共享与私有状态均 ready；不要重复安装。演示者解锁后从桌面点击 BoatAttack 图标即可启动。

- `autostart-install` 把冻结 payload 放到 `/data/boatattack-autostart/`，备份并安装 `/system/etc/boat-attack-autostart.sh` 与 init cfg，然后立即执行一次开机预备。安装过程登记目标板设备通道，校验全部固定 hash，并把根分区恢复为只读；结束时 BoatAttack 必须没有 PID。
- `autostart-activate` 不 reboot，只清除 `DISABLED` 并执行同一预备脚本；它会停止已有 BoatAttack 进程并恢复挂载，适合把当前 boot 收回到可手点的演示状态。
- `autostart-finalize` 不重启或启动应用，只在独占设备通道内把根分区恢复为只读，再执行严格状态门；当前 boot 的共享门若留下 `rw`，在最终交付前运行一次。
- `autostart-reboot-test` 会真实 reboot，只能在用户明确要求验证重启或设备确实需要恢复时执行。它等待新 boot receipt 到达 `READY`，验证 13 个挂载全部来自固定 payload，并额外等待 10 秒确认 BoatAttack PID 仍为零。
- reboot 改变 boot receipt，因此 `autostart-reboot-test` 后按共享风险运行一次 `restore`，只补当前 boot 必需的 ZigZag/HelloWorld 门禁。目标 APK 的完整行为结论仍来自同一固定候选的 `quick`；演示交付前再运行 `autostart-activate` 并回到桌面，使状态恢复为 `STOPPED_READY`。
- `autostart-uninstall` 只在用户明确要求撤销持久化启动时执行。它创建 `DISABLED`、停止 BoatAttack、卸载私有挂载并恢复安装前的 system 脚本/cfg；活跃 AppSpawnX 下共享挂载延迟到下次 reboot 消失。

若其他任务已登记目标板写通道，任何会改状态的命令都应停在门禁上；不要强删锁或绕过通道。`autostart-status` 和普通 `status` 可用于只读判断。

## 固定身份

- APK：`APKS/BoatAttack/dist/boat-attack-a.apk`
- SHA-256：`8dc636657cccdad1310332928b8cc8eca7da03f4b528de6fb0c63118173e0444`
- package/activity：`com.Unity3d.BoatAttackDay/com.unity3d.player.UnityPlayerActivity`
- C7 `libunity.so`：`1bea0fae1e6e76db15f17fca2bfa91b9c303ce278d6a4dcfba6af233b68b64ac`
- C4 `libil2cpp.so`：`f6b806b5c55e702b98caa2e85d2f9afb678bc47dcc4067017b33f5269afed746`
- signal box：`7a931c79c0be28468bdd02a626a637431f2447f5fd0aba87176e5acdb071f5da`
- 共享候选：`strict-boat-assembled-20260924T074522Z-25403`

> 2026-09-24 起 APK 与 C4 `libil2cpp.so` 为同源重编产物（Unity-Technologies/BoatAttack@dfaa9ef + Unity 2020.3.23f1 + CM vcam1 priority 1000→0 补丁），非 8/13 原件；构建脚本见 `APKS/BoatAttack/build-a.sh`。C7 `libunity.so` 仍为 8/13 身份，pin 链问题见黑板第 2 条 ACK。

候选缺失时，`restore` 从固定 APK、固定 rename map 和精确偏移机械重建相同 SO；产物只放 `.state/`，不得提交 `.so`。

## quick 验收

脚本冷启动后采 t+3/9/15，等待比赛 HUD，再执行五次归一化动作：加速、左转、加速、右转、重置。成功要求：

- 原 APK 身份正确，RenderService live queue 的首个及全部保留 Unity buffer 均为
  `1920×1200`，全屏显示真实、变化且等比的赛艇像素；
- 同一 PID 存活至少 15 秒；
- 五次动作均送达，帧状态发生显著变化；
- 没有目标 faultlog、生命周期超时、native fatal 或 FDSAN。

固定 quick 用帧差和动作序列做自动门禁；需要人眼复核时查看 receipt 所指 evidence 中的 `ready.jpeg` 与五张 `touch-*.jpeg`。

## 失败处理

- 固定输入或 hash 漂移：停止，不放宽 hash。
- 私有 mount 缺失：运行一次 `restore`，再 `quick`。
- 共享代/receipt 漂移：让 `restore` 完成同候选风险门禁，不单独机械跑 HelloWorld。
- autostart receipt 为 `FAILED`：保留 `/data/boatattack-autostart/receipt.env` 和 `launch.txt`，按 `failed_step` 处理最早失败；不要用重复 reboot 掩盖失败。
- receipt 已 `READY` 但出现 `activity_start` 非 `DEFERRED_TO_USER`、`pid` 非 `NONE` 或 reboot 后自动出现目标 PID：判定手动演示模式失败，不接受“随后停止进程”作为开机门禁替代。
- autostart 已 `READY` 但目标行为门失败：以 `quick` 证据为准，保留最小 evidence，回到 `derive-apk-hap-lightup` 定位 first-bad。
- 已接受路径出现新行为故障：保留本次最小 evidence，回到 `derive-apk-hap-lightup` 定位 first-bad；不要在本 skill 内试探新补丁。

BoatAttack 同源 HAP 只作 B 线正向对照；本 skill 不安装 HAP，也不把 HAP 画面作为 C 线结论。
