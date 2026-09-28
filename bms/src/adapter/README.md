# adapter — Android/Unity APK on OpenHarmony 适配层（新人入口 · START HERE）

> 本文件是本目录的**唯一入口**。任何人（尤其入职第一天的新同事）先读这一页，再按"阅读顺序"往下走。
> 建立日期 2026-07-10。旧的 `readme.txt` 已过时（写的是已废弃的 `D:\code\adapter` + ECS scp 工作流），**不要**再把它当入口，见文末"历史内容警告"。

---

## 一句话价值

把**未修改、未重签**的 Android / Unity APK（当前标的：`CardWords`，Unity 2022.3.62f2，arm64-v8a）直接跑在固定目标 **OpenHarmony 6.1.0.31 + AOSP 14（arm64）** 上并上屏可交互。做法 = **bionic↔musl 运行时翻译** + **AMS/WMS/Surface/BMS/输入等 IPC 桥接** + **OH/AOSP 源码补丁**。不改 APK、不做 wrapper/shell，修复做在通用适配层，任何未修改 app 受益。目标版本固定不代表当前混合构建输入已形成 single-generation；精确边界见 `BASE_VERSIONS.md`。

> **这是设计目标 + 当前主攻方向，不是"对任意 APK 已完成"的承诺**。"能跑任意 app"是目标；当前实证范围（已构建 / 已真机验证 / 未闭合）见 `KNOWN_ISSUES.md`。

## 核心约束（先记住这两条，后面到处都是它俩）

1. **单目录可编译、无外链**：编译单元只允许用①本目录 + ②外置 OH/AOSP 源码树与工具链（合规例外）。**禁止**任何其它兄弟项目（Noice / 旧 WestLake / GZ05 等）的代码进入编译。这是**目标约束**；当前**尚未完全闭合**（arm64 AOSP 库无法本仓库自产等），已知缺口诚实登记在 `KNOWN_ISSUES.md`。判定细节见 `GLOSSARY.md#单目录约束` 与 `PROVENANCE.md`。
2. **零设备**：本目录内的开发/文档工作**不碰真机**；真机验证由 codex 在其锁定设备上做（见 `COORDINATION.md` §2 设备锁）。

## 实质进展的强制收工门

任何代码、补丁、构建、测试或设备证据产生实质进展后，必须按 `.agents/skills/unity-kanban-sync/SKILL.md` 更新责任 agent 的状态，重新生成 `/opt/21.Game/02.unity.cardwords/UNITY_RESEARCH_KANBAN.html`，再部署到 Vercel 公网。只有匿名 no-cache 公网响应的 SHA-256 与源 HTML SHA-256 完全相等才算完成；heartbeat 不触发发布。凭据只允许通过 `VERCEL_TOKEN_FILE` 或 `../docs/KANBAN_VERCEL_DEPLOYMENT.md` 记录的受保护默认文件引用，严禁把值写入仓库、HTML、日志或报告。

---

## 阅读顺序（新人第一天照这个走）

| 顺序 | 读什么 | 回答你的问题 |
|---|---|---|
| 1 | **本 README.md** | 这是什么、约束是什么、从哪读起 |
| 2 | `GLOSSARY.md` | bionic↔musl / bridge / stub / overlay / 楼层 / cut 代次 这些黑话是什么 |
| 3 | `ARCHITECTURE.md` | 整体链路（APK→framework→adapter→OH）、`framework/` 13 个模块各干嘛 |
| 4 | `BUILD_ENVIRONMENT.md` → `BUILDING.md` | 前置环境/预检 → 怎么编出 arm64 产物、跑哪个脚本 |
| 5 | `VERIFICATION.md` | "什么算编过了"、本地验收止于哪、真机验证谁做 |
| 6 | `framework/README.md` + `framework/DEPENDENCIES.md` | "我要改某个 IPC 桥，去哪个目录 / 进哪个产物 / 依赖方向" |
| 7 | `KNOWN_ISSUES.md` | 当前能力范围 + 单目录无外链未闭合缺口 |
| 8 | 深层权威文档（见下表） | 版本身份 / 可复现 / 交接 / 协同 的权威细节 |

## 权威文档优先级表（冲突时以高优先级为准）

| 主题 | 权威文件 | 说明 |
|---|---|---|
| 依赖基座**版本身份** | `BASE_VERSIONS.md` | OH/AOSP 精确版本的**唯一权威**；`COORDINATION.md` 的版本行不作权威 |
| **来源 / 可复现 / 0外链审计** | `PROVENANCE.md`（63KB） | 每个外部输入的溯源、单目录约束的缺口清单 |
| **交接**（L04–L14 楼层状态） | `HANDOFF_L04_L14.md` | 当前进度、下一道门 |
| **Claude↔Codex 协同握手** | `COORDINATION.md`（V3，按 30KB 轮转，历史在 `coordination/archive/`） | 开工前读、收工前 append；设备/文件锁在此 |
| **stub 符号清单** | `third_party/oh_stubs/STUBS_MANIFEST.md` | 27 个链接期符号 stub 的来源/哈希/parity |
| **6.1.0.31 头覆盖** | `build/oh_headers_631_overlay/README.md` | 4 个接口头 overlay 为何存在 |
| 历史 / 噪声目录说明 | `LEGACY_CONTENT.md` | 哪些目录是备份/废弃、能不能删、别从里面复制方案 |

---

## 我想立刻做 X（速查）

- **想 build** → `BUILD_ENVIRONMENT.md`（预检）→ `BUILDING.md`
- **什么算编过了 / 验收口径** → `VERIFICATION.md`
- **想看整体架构** → `ARCHITECTURE.md`
- **想改一个 IPC 桥 / 找模块** → `framework/README.md` + `framework/DEPENDENCIES.md`
- **看懂黑话** → `GLOSSARY.md`
- **知道基座是哪个 OH/AOSP 版本** → `BASE_VERSIONS.md`
- **当前能力范围 / 无外链缺口** → `KNOWN_ISSUES.md`
- **证明某个二进制来源合规（无外链）** → `PROVENANCE.md`
- **当前攻关到哪一层、下一步** → `HANDOFF_L04_L14.md` + `COORDINATION.md`

---

## 历史内容警告（重要，防止"错误复活"）

以下是**备份/废弃/历史**内容，**不是**当前实现，**禁止**从里面复制方案（兼容层代码常"能编译但语义错"）：
`_routeb_bak_20260628/`、`_routeb_dev_bak/`、`build/_deprecated/`、`doc/bkup/`、`doc/bk.*.html`、`doc/*.old.html`、`doc/v1.0-* / v1.1-* / V1.2-*`、各处 `*.sh.bak / *.orig / *.devbak`、以及顶层 `readme.txt`。逐项说明见 `LEGACY_CONTENT.md`。
