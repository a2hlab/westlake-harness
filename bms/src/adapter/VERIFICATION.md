# VERIFICATION.md — 验收口径（本地构建门禁 + 设备验证边界）

> 目的：把"什么算编过了""本地验收止于哪""谁做真机验证、结果记哪"一次讲清，消除口径歧义。
> 建立日期 2026-07-10。构建步骤见 `BUILDING.md`；能力/缺口边界见 `KNOWN_ISSUES.md`。

---

## 1. 本地构建门禁（gate — 本目录内可自证，零设备）

对 arm64 主产物 `liboh_adapter_bridge.so`：

| 门禁项 | 判据 | 命令/信号 |
|---|---|---|
| G1 strict link | 脚本报 `mode = strict`，未回退 relaxed | 编译脚本末尾输出 |
| G2 目标架构 | ELF 64-bit LSB, ARM aarch64 | `file out/adapter/liboh_adapter_bridge.so` |
| G3 无外链 | 每个编译输入 ∈ {本目录, 外置 OH/AOSP, 工具链} | `KNOWN_ISSUES.md` 缺口清单 + 人工核对 |

**关于 undefined 符号（易错点）**：动态库的 `nm -u` 一定会列出由 `DT_NEEDED` 库运行时提供的导入符号，这是**正常**的。门禁 G1 的真正含义是**链接期 `-Wl,--no-undefined` 通过**（所有 UND 都能被声明的依赖库解析），**不是**"动态符号表里没有 UND"。因此：
- 判 strict/relaxed **看脚本的 mode 输出**，不要拿 `nm -u` 非空当失败。
- 若走了 relaxed，才需 `readelf -d` + `nm -u` 逐个确认 UND 都能 runtime 找到（见构建脚本 `[BR-2]`）。

**非门禁参考值**（会正常波动，勿据此判失败）：DT_NEEDED 条数（~32）、产物体量（~1.4M）。

## 2. 本地验收止于哪（重要边界）
本地/本目录能自证的**上限 = 静态正确性**：能编、strict link、架构对、符号可解析、无外链。
**本地不能证**：运行时结构体布局 / vtable-slot / IPC parcel 与真机 6.1.0.31 是否一致（`nm -C` 符号核对通过 ≠ 运行时布局正确，见 `BASE_VERSIONS.md` §三·风险①）。这些必须真机验证。

## 3. 设备验证边界（谁做、怎么记）
- **零设备纪律**：在本目录做开发/文档的人（含 Claude）**不碰真机**。这**不是**说"永远不需要设备验收"，而是**设备验收由 codex 在其锁定设备上做**（5bb5b / 5eab，见 `COORDINATION.md` §2 设备锁）。
- **流程**：本地过 G1–G3 → 在 `COORDINATION.md` 记录 host gate 结果 → codex 领取并在设备做诊断热换 / truly-cold 验证 → 结果按 `device_verified(scoped)` / `truly-cold` 分级回填 `COORDINATION.md` §3 与 `HANDOFF_L04_L14.md`。
- **验收级别**（强度递增）：`build_pass`（host 编过）< `device_verified(scoped)`（手工 listener / 非冷 / N=1）< `truly-cold`（Enforcing + production init + reboot 冷 fork，最强）。术语见 `GLOSSARY.md`。

## 4. 一句话
**本地绿 = 静态正确 + 无外链；真机绿 = codex 的 truly-cold。** 两者都过才叫这一层通过，任一缺失都要在 `COORDINATION.md` 如实标级，不得把 `build_pass` 说成 `device_verified`。
