---
name: reproduce-helloworld
description: 在直连 OpenHarmony 6.1 的 61AE 或 8605 板上，以精确 APK、PR03 payload 和已接受 runtime-generation 检查复现固定 G1 HelloWorld Android APK；采集真实首帧像素，验证 CHANGE COLOR 触摸进入 Android main Looper，并生成开发者可复现证据。用于快速显示、重跑、检查、恢复或诊断已经跑通的 HelloWorld APK 路径，不涉及 ZigZag。
---

# 复现 HelloWorld

使用 `scripts/reproduce.sh`。普通复现不要重建二进制，也不要重演历史 G1 调查。

## 选择模式

- 正常复现只运行 `quick`。它会完成必要的身份/runtime preflight，不部署、不重启；随后启动已安装的 HelloWorld APK，采集触摸前后像素，点击 `CHANGE COLOR`，并验证 RED 回调和稳定 child PID。
- `check` 是独立的只读审计入口，不是 `quick` 的强制前置步骤。只在用户明确要求静态检查、`quick` 报告身份或 runtime 漂移、准备 `restore`，或需要单独生成机器状态读回时运行。
- 只在刷机后、已安装 APK 漂移、runtime-generation 漂移或用户明确要求干净重建时运行 `restore`。它调用固定 PR03 restore driver，只重启一次，再检查同一首帧/触摸 oracle。
- 使用 `status` 只读查看身份、runtime profile、进程和 mission。
- 使用 `dry-run-quick` 或 `dry-run-restore` 在 preflight 后打印将执行的精确写入动作。

从仓库根目录运行：

```bash
.agents/skills/reproduce-helloworld/scripts/reproduce.sh quick
.agents/skills/reproduce-helloworld/scripts/reproduce.sh check
.agents/skills/reproduce-helloworld/scripts/reproduce.sh status
.agents/skills/reproduce-helloworld/scripts/reproduce.sh restore
```

可选 serial 只接受已验收的 `61ae0be500000000000000000324012c` 或
`5ce2dcee00000000000000000923012c`（8605）。

## 保持固定身份

这些限制用于防止把 HAP、同名应用、旧 payload 或其他设备上的画面误认成当前 HelloWorld Android APK 的结果。

- 要求 APK SHA-256 为 `2d122a7973ffd68c799700aaaaaa0593e5deec30bac83e22a9dc1bf9f64319fd`。
- 要求 package/activity 为 `com.example.helloworld/com.example.helloworld.MainActivity`，OpenHarmony `bundleType=10`。
- 只接受精确 PR03 touch closure 或精确已验收 ZigZag runtime superset；两者均有当前 HelloWorld 回归设备证据。
- 不接受 OH HAP、其他同名 HelloWorld、其他 ROM/板子、SSH/mac-server、Docker、放宽 hash，或没有触摸回调和解码像素变化的截图。

## 处理结果

成功时报告 wrapper receipt 和关联 evidence 目录，只声明 `DEVELOPER_REPRODUCIBLE_LIGHT`，不签发独立 verdict。

失败时按原因处理：若 `quick` 的 preflight 报告固定输入漂移，再按需运行 `check` 并确认是否有意更新基线；明确的安装或 runtime 状态漂移才使用 `restore`；身份通过但首帧、触摸或 PID 失败时保留 evidence，在本固定复现 skill 外调查。不要放宽 hash 或盲目重试。

写入模式负责领取和释放 `var/state/agent-channel/`。除非用户另有要求，成功后保持 HelloWorld Android APK 在前台。
