# BUILD_ENVIRONMENT.md — 构建环境前置 + 只读预检

> 目的：让新人知道构建 `liboh_adapter_bridge.so`（arm64）需要哪些外部输入、放在哪、怎么一键预检。
> 建立日期 2026-07-10。构建步骤见 `BUILDING.md`；缺口见 `KNOWN_ISSUES.md`。
> **诚实前提**：本项目当前是**单工作站**工程，下列绝对路径是本机现状而非可移植配置；换机需自行提供等价物，可复现缺口见 `KNOWN_ISSUES.md`。

---

## 1. 需要的外部输入

| 输入 | 环境变量（可覆盖） | 本机路径 / 默认 | 版本身份（权威见 `BASE_VERSIONS.md`） |
|---|---|---|---|
| OH 交叉 SDK（clang + musl sysroot） | `OH_SDK` | `/opt/17-TestLab/17.03-D600/apps/d600-sdk-full/native` | 6.1.0.105 / api23 / clang 15.0.4 |
| 外置 OH 源码树 | `OH_ROOT` | `$HOME/oh`（本机参照 HanBing 树） | api24 代次 / sdk 26.0.0.18 |
| 外置 AOSP 源码树 | `AOSP_ROOT` | `$HOME/aosp` | AOSP 14 |
| 预构建 AOSP native 库 | （消费）| `out/aosp_lib64`（22+ `.so`） | 外部预构建输入，见 `KNOWN_ISSUES.md` §2 缺口B |
| 链接期符号 stub | （自动）| `third_party/oh_stubs/lib`（27 库） | 6.1 wukong100 arm64（`STUBS_MANIFEST.md`） |
| 6.1.0.31 头覆盖 | （自动）| `build/oh_headers_631_overlay/`（4 头） | 见该目录 README |

> 用 `FORCE_OH_SDK=1` 时，工具链+sysroot 全来自 `OH_SDK`，bridge 的 OH 符号靠 stub 解析，**不需要**完整 `$OH_ROOT/out/wukong100` 平台树（见 `BUILDING.md` §1"这两件事别混"）。

## 2. 只读预检（跑构建前先粗查关键输入，不碰设备）

> 注意：预检**只做存在性粗查**，全绿**不保证** happy path 一定能编（外置源码树的具体头/产物是否齐全需真编时才暴露）。它的作用是尽早发现"最常见的缺输入"。

```bash
cd /opt/21.Game/02.unity.cardwords/adapter
OHSDK="${OH_SDK:-/opt/17-TestLab/17.03-D600/apps/d600-sdk-full/native}"
OHR="${OH_ROOT:-$HOME/oh}"; AOSPR="${AOSP_ROOT:-$HOME/aosp}"
echo "OH_SDK    : $OHSDK"; ls "$OHSDK" >/dev/null 2>&1 && echo "  OK" || echo "  MISSING (需提供 OH SDK)"
echo "OH_ROOT   : $OHR";   [ -d "$OHR" ] && echo "  OK(目录在)" || echo "  MISSING (FORCE_OH_SDK 模式下 bridge 可不依赖其平台产物, 但源码头仍可能需要)"
echo "  └ wukong100 平台树: $([ -d "$OHR/out/wukong100" ] && echo 存在\(可走默认模式\) || echo 无\(需 FORCE_OH_SDK=1\))"
echo "AOSP_ROOT : $AOSPR"; [ -d "$AOSPR" ] && echo "  OK(目录在)" || echo "  MISSING (bridge 用到的 AOSP 头/源缺失时会报)"
echo "oh_stubs  : $(ls third_party/oh_stubs/lib 2>/dev/null | wc -l | tr -d ' ') 库 (期望 27)"
echo "overlay   : $(ls build/oh_headers_631_overlay/foundation 2>/dev/null | wc -l | tr -d ' ') 项 (期望非空)"
echo "aosp_lib64: $(ls out/aosp_lib64/*.so 2>/dev/null | wc -l | tr -d ' ') 个 .so (期望 22+)"
which clang >/dev/null 2>&1 && echo "host clang: OK" || echo "host clang: (SDK 自带即可)"
```
- `OH_SDK` 缺 → 无法交叉编译，必须提供。
- `OH_ROOT`/`AOSP_ROOT` 缺 → bridge 编译用到的外置源码头会报"file not found"，需提供对应源码树（版本见 `BASE_VERSIONS.md`）。
- `oh_stubs` 不足 27 / `overlay` 空 → 见 `STUBS_MANIFEST.md` / overlay README 重新生成。
- `aosp_lib64` 缺 → 见 `KNOWN_ISSUES.md` §2 缺口B（本机无法自产，需外部提供）。

## 3. 磁盘/资源
- 仓库自身约 200MB（含 `doc/` 34M、`third_party/` 47M、`framework/` 14M）；`out/` 产物另计（gitignore）。
- 外置 OH/AOSP 源码树各数十 GB（不在本仓库），需另行准备。

## 4. 换机 / 可复现提醒
本机绝对路径（`/opt/17-TestLab/...`、`$HOME/oh`、`$HOME/aosp`）是**已知不可移植点**。要在别的机器复现，需提供同版本 OH SDK / OH 源码树 / AOSP 源码树并设对应环境变量；精确版本锚见 `BASE_VERSIONS.md`，未闭合的可复现缺口见 `KNOWN_ISSUES.md`。
