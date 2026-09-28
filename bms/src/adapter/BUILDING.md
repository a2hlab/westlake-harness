# BUILDING.md — 单目录 arm64 构建（唯一 happy path）

> 目的：让新人在干净环境里跑出 arm64 主产物 `liboh_adapter_bridge.so`，并知道"成功长什么样"、出错去哪查。
> 建立日期 2026-07-10。版本基座见 `BASE_VERSIONS.md`；术语见 `GLOSSARY.md`。
> 本页只写**单目录 arm64 bridge**这一条主线；其它产物（installer/runtime/jar、armv7）见 `build/README.txt`。

---

## 0. 一句话
本项目的单目录 arm64 主产物 = **`liboh_adapter_bridge.so`**（JNI 桥，AArch64 ELF64）。
主编译入口 = **`build/inner/compile_oh_adapter_bridge_arm64.sh`**。成功判据 = **strict link 成功（`-Wl,--no-undefined` 未回退 relaxed）+ 链成 AArch64 ELF64**（为何"`nm -u` 非空"不算失败见 §3 / `VERIFICATION.md`）。

## 1. 前置条件（输入）

| 输入 | 环境变量 | 默认 / 本机值 | 说明 |
|---|---|---|---|
| 外置 OH 源码树 | `OH_ROOT` | `$HOME/oh`（本机实际参照 HanBing 树，见 BASE_VERSIONS §一①） | api24 代次；提供头 + arm64 平台库 |
| 外置 AOSP 源码树 | `AOSP_ROOT` | `$HOME/aosp` | AOSP 14 |
| 本仓库根 | `ADAPTER_ROOT` | 脚本自推导（`.../adapter`） | 一般不用设 |
| OH 交叉 SDK | `OH_SDK` | `/opt/17-TestLab/17.03-D600/apps/d600-sdk-full/native`（6.1.0.105 / api23 / clang 15.0.4） | musl sysroot + clang |
| 链接期 stub | （自动）| `third_party/oh_stubs/lib`（27 库） | 提供 OH 库导出符号（见 STUBS_MANIFEST.md） |
| 6.1.0.31 头覆盖 | （自动）| `build/oh_headers_631_overlay/`（4 头） | `-I` 优先命中，覆盖 api24 头 |

**两种 sysroot 模式**：
- **默认**：当 `$OH_ROOT/out/wukong100` 完整平台树存在时，用 OH-tree clang + 平台库。
- **`FORCE_OH_SDK=1`**：强制用 `OH_SDK`（D600 SDK）的 sysroot + 工具链。**没有完整 OH 平台树时用这个**（单目录 round3 的自包含路径）。

**这两件事别混（重要）**：
1. **bridge 链接 OH 符号靠 `third_party/oh_stubs/`（链接期符号 stub），不需要完整 OH 平台产物树**。所以 `FORCE_OH_SDK=1` 提供工具链+musl sysroot 后，bridge 的 arm64 link 即可自洽完成。
2. `BASE_VERSIONS.md`/`PROVENANCE.md` 说的"本机 OH_ROOT 从未为 arm64 跑过 ninja、编不出 arm64 库"，指的是**另一个被消费的预构建输入** `out/aosp_lib64`（22+ 个 AOSP native `.so`），它是 bridge 的**输入**而非 bridge 自身的 link。这是独立的第三缺口，不阻塞 bridge 编译本身，但属"无外链自包含未完全达成"，见 `KNOWN_ISSUES.md`。

## 2. 怎么跑（happy path）

arm64 bridge 脚本是**受保护的内部 helper**（顶部有 `BUILD_INNER_INVOKED` 守卫），直接裸调会被拒。单目录 arm64 构建这样跑：

```bash
cd /opt/21.Game/02.unity.cardwords/adapter
# 单目录自包含（无完整 OH 平台树时）：强制 SDK sysroot
BUILD_INNER_INVOKED=1 FORCE_OH_SDK=1 \
  bash build/inner/compile_oh_adapter_bridge_arm64.sh
```
- 若你有完整 `$OH_ROOT/out/wukong100` 平台树，可去掉 `FORCE_OH_SDK=1` 走默认模式。
- 产物：`out/adapter/liboh_adapter_bridge.so`。

> 说明：顶层包裹脚本 `build/build_adapter.sh --target=liboh_adapter_bridge.so` 当前 dispatch 的是 **armv7** 版 `compile_oh_adapter_bridge.sh`；**arm64 单目录**这条主线走上面的直接受保护调用。

## 3. 成功长什么样（验收判据，权威定义见 `VERIFICATION.md`）
**门禁（gate，必须满足）**：
- 脚本末尾打印 link **mode = strict**（不是 relaxed）——即 `-Wl,--no-undefined` 未回退。
- 产物 `file out/adapter/liboh_adapter_bridge.so` = **ELF 64-bit LSB, ARM aarch64**。
- 无外链自检通过（见 §5）。

**参考值（非门禁，会随链接器/裁剪正常波动，勿据此判失败）**：`readelf -d` 的 DT_NEEDED 条数（约 32）、产物体量（约 1.4M）。

**关于 `nm -u`**：动态库 `nm -u` **本来就会**列出由 `DT_NEEDED` 库在运行时提供的导入符号，所以"`nm -u` 非空"**不等于**失败。strict 门禁的真正含义是：**所有 UND 都能被声明的 DT_NEEDED 库解析**（`--no-undefined` 通过），而非动态符号表里没有 UND。判据以脚本报 `mode=strict` 为准，细节见 `VERIFICATION.md`。

**relaxed 不算过**（见脚本 `[BR-2]`）：relaxed 会把真正无法解析的 undefined 推到 runtime，编译"成功"但设备上首次调用才崩。看到 relaxed 必须查为什么 strict 失败，不要将就。

## 4. 常见故障 → 去哪查（按构建阶段）

| 现象 | 可能原因 | 查这里 |
|---|---|---|
| `[GUARD] … invoke via build_*.sh` | 没设 `BUILD_INNER_INVOKED=1` | 本页 §2 |
| `WARN … api24 parcel skew` | 6.1.0.31 头镜像软链已删，只剩 4 头 overlay | `BASE_VERSIONS.md` §三·风险① |
| link 落 relaxed / 有 UND | stub 缺符号 / 新依赖没加 | `STUBS_MANIFEST.md`；脚本 `[BR-2][BR-3]` |
| sources 漂移 / 符号重复 | framework 新增 .cpp 没同步 `jni/BUILD.gn` | 脚本 `[BR-1]`；`framework/README.md` |
| `@CriticalNative` SIGSEGV | `CRITICAL_JNI_PARAMS_COMMA` 宏走错分支 | 脚本 `[BR-4]` |
| `dynamic_cast`/`typeid` 跨 .so 返 null | RTTI 不对齐 / hidden visibility | 脚本 `[BR-5]`、skia RTTI shim |
| 缺 `out/aosp_lib64` 预构建库（**不是** bridge 自身 sysroot） | 该输入需外部提供；本机 OH_ROOT 从未为 arm64 跑过 ninja、无 musl aarch64 sysroot 自产不出（缺口B） | `KNOWN_ISSUES.md` §2 缺口B、`PROVENANCE.md` |

## 5. 无外链自检（编完必看）
产物的每个编译输入必须落在：①本目录 ②外置 OH/AOSP 源码树/工具链。若引入任何兄弟项目（Noice/GZ05/旧WestLake）代码即**外链**，不合规。当前已知未闭合缺口诚实记录在 `BASE_VERSIONS.md` §三 与 `PROVENANCE.md`。
