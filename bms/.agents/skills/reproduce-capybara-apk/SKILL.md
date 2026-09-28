---
name: reproduce-capybara-apk
description: 在直连 OpenHarmony 6.1 的 61AE 或 8605 板上检查、恢复、快速验收或回滚已经跑通的固定 Capybara Adventure Android APK 路径；复用当前 boot 已通过 HelloWorld 与 ZigZag Android APK 的共享基线，部署可回滚的 Capybara 私有 C24/C27 SO，并验证 1200×750 真实游戏画面、PLAY、同 PID、五次触摸和无终止性 fatal。用于固定复现，不用于推导新 adapter，也不把 Capybara HAP 当作 APK 结论。
---

# 复现 Capybara Adventure Android APK

使用 `scripts/reproduce.sh`。脚本固定原始 APK 身份，仅在 APK 外生成并 bind mount 四个已接受的应用私有文件；不修改、不重签 APK。

## 命令

- 接受态直接运行 `quick`。
- rollback 或 ZigZag 固定候选状态运行 `restore`、`quick`；需要读回时再单独运行 `check`。
- `status` 只读显示 package、PID、四个私有文件及 mount。
- `rollback` 停止目标 UID、卸载四个私有 bind，保留原始 APK 和共享兼容层。
- `restore` 恢复应用私有候选；若当前是 ZigZag 的较早固定候选，则用现有
  `run-light-risk` 部署 Capybara 已接受共享候选，并在该精确候选上各验证一次
  HelloWorld 与 ZigZag。它不 build、不 reboot、不刷机。

```bash
.agents/skills/reproduce-capybara-apk/scripts/reproduce.sh check
.agents/skills/reproduce-capybara-apk/scripts/reproduce.sh restore
.agents/skills/reproduce-capybara-apk/scripts/reproduce.sh quick
.agents/skills/reproduce-capybara-apk/scripts/reproduce.sh status
.agents/skills/reproduce-capybara-apk/scripts/reproduce.sh rollback
```

第二个参数可指定 serial，但只接受已验收的 `61ae0be500000000000000000324012c` 或
`5ce2dcee00000000000000000923012c`（8605）。

## 共享基线

`check` 要求当前 boot 已有最终共享候选对应的 ZigZag Android APK 通过 receipt；该 receipt 同时关联先行通过的 HelloWorld 证据。boot 和共享候选不变时直接复用，不重复跑 HelloWorld、ZigZag、trace 或 HAP。

若共享候选或 receipt 缺失，直接运行本 skill 的 `restore`。它会对
`strict-20260811T044910Z-68706` 执行一次可回滚的 `run-light-risk`，因此 ZigZag
验证的是 Capybara 即将使用的同一共享候选；不要先调用固定 ZigZag `quick`，后者会恢复较早的
ZigZag 候选。仅恢复 Capybara 私有文件时不触发重复基线。

Capybara HAP 只作原生 OpenHarmony 正向对比；固定 APK 复现不安装 HAP，也不把 HAP 结果当作 APK 结果。

## 固定身份

- APK：`APKS/CapybaraAdventure/dist/capybara-adventure-v1.2.0-unity.apk`
- APK SHA-256：`552b731aa6b6c50871ac218c65665669c089ddb09ec780f414c18e3d685b5730`
- package/activity：`com.Revenko.org.CapybaraAdventure/com.unity3d.player.UnityPlayerActivity`
- C24 `libunity.so`：`d9a8fdb42c73f6d9caf7e63a97e8f0e012e3208f6fa147d994d84ae2834fd378`
- C27 `libil2cpp.so`：`d36f292dcda8ae7f6c7ece9b6176755f68cda8a714f6366a58dc7e0918e5cf46`
- C24 `libcapybara_geometry.so`：`ec080758323afb873f26965efbdd3bab98313e5d7791f59edf7f7e30c5e852be`
- signal box：`7a931c79c0be28468bdd02a626a637431f2447f5fd0aba87176e5acdb071f5da`

候选缺失时，`restore` 从固定 APK 和仓库内源码机械生成相同文件；生成物只放 `.state/`，不得提交 `.so`。

## quick 验收

脚本按当前 1200×750 游戏内容坐标执行：t+3、t+9 取帧，点击 SKIP `(1060,620)`，取主菜单，点击 PLAY `(850,615)`，取游戏帧，再在 `(600,375)` 连续触摸五次并取结果帧。它只做必要判断：

- 原始 package/activity 和 APK hash 正确；
- 1200×750 顶部区域不是纯色，菜单、PLAY 后、五次触摸后的像素状态不同；
- 同一 PID 至少存活 15 秒，五次触摸均成功送达；
- 没有目标 faultlog 或终止性 fatal。

成功后只需查看 receipt 指向的 `menu.jpeg`、`after-play.jpeg`、`after-five.jpeg`，确认分别为真实菜单、游戏和触摸后的状态。屏幕下方白色来自 OpenHarmony 外层 SceneBoard，位于 1200×750 游戏 Surface 之外；它与原生 Android 的黑色底不同，但不阻塞 APK 功能验收。

不要为成功复现追加 hitrace、全量 dump、重复 hash、重复基线或 HAP 校验。

## 失败处理

- 私有 mount、共享候选或当前 boot receipt 缺失：运行一次 `restore`，再运行 `quick`。
- `restore` 的共享部署失败会由 ZigZag driver 自动回滚；不要原地继续试探候选。
- 固定输入漂移：停止，不放宽 hash。
- 已接受路径出现新行为故障：保留本次最小 evidence，回到 `derive-apk-hap-lightup` 定位 first-bad；不要在固定复现 skill 内继续试探 adapter。

写入命令自动领取并释放 `var/state/agent-channel/`。成功后保持 Capybara APK 在前台；仅在用户要求或需要恢复原始 APK 运行态时执行 `rollback`。
