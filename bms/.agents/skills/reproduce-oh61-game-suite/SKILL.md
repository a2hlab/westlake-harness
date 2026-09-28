---
name: reproduce-oh61-game-suite
description: 在直连 OpenHarmony 6.1 的已验收 61AE 或 8605 板上，按共享运行代风险顺序复现 HelloWorld、ZigZag、Capybara Adventure 和 BoatAttack 四个固定 Android APK。用户要求在新机器复现全部游戏、继续下一个游戏、ZigZag 已过不要重跑、准备交接设备或收集四游戏统一 receipt 时使用；支持从 ZigZag 或 Capybara 之后继续，避免机械重复已通过游戏。
---

# 复现 OpenHarmony 四游戏套件

使用 `scripts/reproduce.sh` 编排四个已经验收的单应用 skill。这个 skill 只做顺序、续跑和汇总，不重新推导 adapter，不替换单应用的 APK 身份、像素、触摸、PID 与 fatal 门禁。

## 选择入口

第二个参数必须是已验收板的精确 serial：

- 61AE：`61ae0be500000000000000000324012c`
- 8605：`5ce2dcee00000000000000000923012c`

```bash
# 当前板已有运行环境：依次验收全部四个 APK
.agents/skills/reproduce-oh61-game-suite/scripts/reproduce.sh quick <serial>

# 新板、刷机后或运行代确实漂移：HelloWorld 先 restore，之后依次验收
.agents/skills/reproduce-oh61-game-suite/scripts/reproduce.sh restore <serial>

# 用户明确说 ZigZag 已通过：从 Capybara 继续，不显式重跑 ZigZag
.agents/skills/reproduce-oh61-game-suite/scripts/reproduce.sh continue-zigzag <serial>

# Capybara 也已通过：只继续 BoatAttack
.agents/skills/reproduce-oh61-game-suite/scripts/reproduce.sh continue-capybara <serial>

# 只检查将执行的顺序，不写设备
.agents/skills/reproduce-oh61-game-suite/scripts/reproduce.sh dry-run-continue-zigzag <serial>
```

`continue-zigzag` 和 `continue-capybara` 跳过用户已经验收的显式游戏步骤。Capybara/BoatAttack 的 `restore` 若发现共享 candidate、boot receipt 或公共 Unity 路径改变，仍可按各自 skill 的风险门补一次 ZigZag；这是同候选必要门禁，不是机械重复。

## 固定顺序

完整流程依次执行：HelloWorld → ZigZag → Capybara `restore/quick` → BoatAttack `restore/quick`。Capybara 与 BoatAttack 的共享候选逐级扩展，因此不要在它们之后再调用较早 ZigZag `restore` 覆盖当前运行代。

每一步成功后复用单应用 receipt。套件全部结束才写 `var/state/reproduce-oh61-game-suite/` 汇总 receipt；任一步失败立即停止，不伪造后续成功，也不盲目重试。

## 交接边界

- 结论只来自四个固定 Android APK；同源 HAP 只作既有正向对照。
- 不提交 APK、HAP、`.so`、候选 payload 或超过 100 MB 的现场产物；它们继续保存在本地既有目录。
- BoatAttack 的 APK 原始应用名是 `BoatAttack`。名称应由安装器解析资源，不能用包名或人工的 `Boat Attack` 覆盖。
- 普通套件验收会把最后一个 BoatAttack 留在前台。演示交接若要求“开机后不自动打开、由用户手点”，使用 `reproduce-boat-attack-apk` 的 `autostart-activate`/`autostart-status`，确认 `launch_mode=MANUAL` 与 `current_pid=NONE`；除非用户明确要求，不执行 reboot。
