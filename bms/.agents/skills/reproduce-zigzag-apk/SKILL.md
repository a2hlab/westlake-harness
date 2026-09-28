---
name: reproduce-zigzag-apk
description: 在直连 OpenHarmony 6.1 的 61AE 或 8605 板上复现固定 ZigZag Android APK；自动管理设备通道，按共享层风险决定是否回归 HelloWorld，再验证游戏像素、触摸和存活。用于快速显示、重跑、恢复、验收或诊断已经接受的 ZigZag APK 路径，并明确区分作为正向对比案例的 ZigZag HAP。
---

# 复现 ZigZag Android APK

使用确定性 wrapper `scripts/reproduce.sh`。wrapper 负责固定输入和最终 receipt；它调用已接受的 `src/tools/devices/zigzag-apk-lightup.sh`，复用未变化的共享运行层并直接完成 ZigZag 真机验收。普通复现不要重演调查，也不要重建二进制。

## 选择模式

- 正常运行 `quick`。共享运行层未变化时不重启、不重新部署，也不重复运行 HelloWorld；直接执行 ZigZag 的目标验收。若发现候选未部署或运行代漂移，部署后自动补一次必要的 HelloWorld 回归。
- `check` 是按需静态审计，不是 `quick` 的前置步骤。只在用户明确要求、`quick` 报告固定输入/运行代漂移或准备 `restore` 时运行。
- 只在用户要求干净重建、刷机后，或 `quick` 报告 PR03/backing generation 漂移时运行 `restore`。它恢复 PR03、重启目标板、部署并持久化候选，然后执行相同轻量验收。
- 使用 `status` 只读查看当前 boot、已安装 APK/Tuanjie hash、进程、mission 和持久化事务。
- 使用 `dry-run-quick` 或 `dry-run-restore` 验证输入并打印精确写入命令，不修改板子。

从仓库根目录运行：

```bash
.agents/skills/reproduce-zigzag-apk/scripts/reproduce.sh quick
.agents/skills/reproduce-zigzag-apk/scripts/reproduce.sh check
.agents/skills/reproduce-zigzag-apk/scripts/reproduce.sh restore
```

第二个参数可指定 serial，但只接受已验收的 `61ae0be500000000000000000324012c` 或
`5ce2dcee00000000000000000923012c`（8605）。

## 保持固定身份

- 把 `src/vendor/samples/apks/ZigZag/project/dist/zigzag.apk` 视为目标 Android APK，要求 SHA-256 为 `aaa7c9cce4886eef1280e917fd25bf434c53065cf0bf8b5704b83738137275bc`；本机迁移前目录 `APKS/` 仅作兼容回退。
- 要求 package/activity 为 `com.a2hlab.bridge.zigzag/com.unity3d.player.UnityPlayerActivity`。
- 要求持久化候选 `strict-20260809T160651Z-21101` 及其 `eglGetProcAddress` Tuanjie resolver 修复。
- 禁止替换成 `src/vendor/samples/haps/ZigZag/dist/zigzag-control-fmtfix.hap`；后者只是原生 OpenHarmony 正向对比案例。
- 本 skill 不调用 `src/tools/devices/zigzag-apk-lightup.sh build`，因为 build 会生成新候选，使固定候选和 13 个 payload 的身份失配；新候选应进入 `derive-apk-hap-lightup`，而不是冒充固定复现。
- 不放宽 hash，不使用 SSH/mac-server/Docker，也不接受其他 ROM/板子，以免把不同输入或设备状态混入已接受结果。

## 按风险执行

HelloWorld 只在共享运行层可能变化时作为状态闸：首次部署候选、候选/运行代漂移、reboot/restore，或证据指向公共路径回归。共享层未变化的普通 `quick` 复用最近一次通过结果。

1. 风险触发时，先证明精确 HelloWorld 显示真实首帧，`CHANGE COLOR` 触摸改变解码像素且回调送达；未触发时跳过。
2. 启动目标 ZigZag Android APK，确认 package/activity 和目标 PID，防止把 HAP、桌面或 fallback 画面误认成 ZigZag。
3. 普通显示仅采集当前任务需要的最小证据；正式验收才采集 t+3/9/15、五次点击后的游戏像素、同 PID 存活与 fatal 状态，并要求 `TopScore` 增长。

风险触发的 HelloWorld 未绿时不得宣称 ZigZag 成功。若 ZigZag 退出后屏幕显示 HelloWorld，应把它记录为 fallback foreground，而不是 ZigZag 画面。

## 处理结果

成功时报告 wrapper receipt 和 ZigZag evidence；只有本次风险触发了 HelloWorld 才附其 evidence。只声明 `DEVELOPER_REPRODUCIBLE_LIGHT`，不签发独立 verdict。

失败时按原因只走一条路：

- `quick` 或按需 `check` 报固定输入/driver 漂移：停止，先确认是否有意更新固定复现；不要自行 build。
- `quick` 明确报告 PR03/backing 或刷机后的状态漂移：使用 `restore`。
- 必要的 HelloWorld 回归或 ZigZag 行为失败：保留最小 evidence 和自动 rollback 结果，在本 skill 外按 `docs/zigzag-apk-lightup.md` 调查 first-bad；不要盲目重试或直接改代码。

不要原地删除活动 PR03 backing 目录。

wrapper 在写入模式领取和释放 `var/state/agent-channel/`。除非用户要求 rollback，成功后保持 ZigZag Android APK 在前台。
