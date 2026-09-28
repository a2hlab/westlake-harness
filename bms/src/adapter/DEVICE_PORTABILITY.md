# DEVICE_PORTABILITY.md — 一份 adapter 源码能否驱动多设备（D600 + D200）的架构裁决

> 目的：回答用户的架构判断题——**能否用一份 adapter 源码驱动两个设备（D600 uis7885 / D200 dayu200-rk3568），只是编译 2 次（甚至 1 次），而不是维护 2 个 adapter 版本？这里的约定是什么？**
> 建立日期 2026-07-10。纯只读分析 + 推理 + codex 挑刺，未改代码、未碰设备。
> 版本身份权威见 `BASE_VERSIONS.md`；来源见 `PROVENANCE.md`；本文件只谈"多设备可移植性约定"。

---

## 0. 一句话裁决

**原则可取、现状 Not Proven**：adapter **应当**绑 OH 版本、不绑 SoC——一份 source of truth，per-device 换 OH 产物树重编即可，**无需源码分叉**；board 差异走「OH HDI/vendor 层吸收 + 运行期能力探测 + 构建配置参数化」三条通道。但要落到"编 2 次就跑两台"，当前仓库**尚未达成**，有三处硬缺口（§6），其中**最大的一条是架构维度**：仓库现状把 D200/rk3568 接成 **arm32（armv7）**、D600/wukong100 接成 **arm64**——若两台真按同一 arm64 部署，是最干净的同架构 2 编；若 D200 仍是 arm32，则多出一个**架构维度**（非板级分叉，但编译期必须分型）。

---

## 1. ★关键事实校正：两台的架构在本仓库里并不相同

任务前提写「两台都是 arm64」，但**本仓库构建脚本的实证与此不符**：

| 设备 | OH product | 本仓库实际目标三元组 | lib 路径 | 证据 |
|---|---|---|---|---|
| **D600** (uis7885) | `wukong100` | `aarch64-linux-ohos`（**arm64**） | `system/lib64` | `compile_oh_adapter_bridge_arm64.sh:168,225`；`cross_compile_arm64.sh:67` |
| **D200** (dayu200/rk3568) | `rk3568` | `arm-linux-ohos -march=armv7-a`（**arm32**） | `system/lib` | `compile_oh_adapter_bridge.sh:155,485`；`config.sh:19`；`cross_compile_arm32.sh:12` |

**为什么这是头号变量**：架构差异**不是**板级差异、**不能**靠 HDI/vendor 层吸收——它直接改变 adapter 的 `.o`：ELF32/64、指针宽度、JNI ABI、结构体布局/对齐、以及 ART 桥接里 TLS/线程偏移（bionic↔musl 翻译层对 arm32 是 0x4、arm64 是 0x8 一类的偏移，见 codex 反证）都随架构变。链接的 stub / AOSP 预编译库也必须按架构分型（`out/aosp_lib` vs `out/aosp_lib64`，脚本注释 `arm64.sh:24` 明确二者要隔离避免撞目录）。

**两种情形下的"编 2 次"含义不同**：
- **若 D200 实际部署为 arm64**（与任务前提一致）：需要为 rk3568 跑一棵 **arm64 product 产物树**（当前仓库只有 rk3568 的 arm32 流水线，arm64-rk3568 未接线）。达成后是**同架构、双产品**，2 编最干净、最接近"一份源码"。
- **若 D200 保持 arm32**：一份源码仍可（不分仓、不 `#ifdef` 板名），但跨越**两个维度**（arch × product）。arch 差异由可移植 C/编译器天然处理，但 stub/AOSP 库、ART 偏移常量、`-march`/`--target`/sysroot 必须**编译期按架构选择**——这是合法的"架构源集(architecture source-set)"分型，不是板级源码分叉。

> 落地前必须先向用户/codex 确认 D200 的真实用户态架构。本文其余结论对"同架构 2 编"与"跨架构 2 编"都成立，只是后者多一层架构分型。

---

## 2. 分层归属表（adapter 依赖的接口，各归哪一层）

判据：这一层的差异是**跨 SoC 相同的 OH-版本级**，还是**SoC/板级敏感**；board 敏感项**在 adapter 之上/之下/之内**如何吸收。

| 接口/组件 | 归属层 | 跨 D600/D200 是否相同 | board 差异吸收在哪 | 证据 |
|---|---|---|---|---|
| BMS/appspawn/ActivityThread(AMS/ATMS)/WindowSession/InputChannel/RenderService **inner_api**（IPC 接口形状、zidl parcel、结构体布局、vtable 槽） | **OH-版本级** | 同一 6.1.0.31 应相同 | — | `framework/{activity,window,surface,broadcast,package-manager}/jni/*` 全部 include OH inner_api 头 |
| OH `GraphicPixelFormat` 枚举映射（Android→OH 像素格式值） | **OH-版本级** | 相同（取自 OH `surface_type.h`） | — | `framework/surface/jni/pixel_format_mapper.h:44-52` |
| 27 个链接期 stub 符号集 / SDK 工具链(clang/musl sysroot) | **OH-版本级**（但 arch 相关） | 符号名同；**arch 分型** | 按架构选 lib/lib64 | `STUBS_MANIFEST.md`；`BASE_VERSIONS.md §一②③` |
| **GPU/EGL 驱动**（`libmali.so.0` / `libEGL_impl.so`） | **SoC/板级**，在 **adapter 之下** | 否（驱动 blob 随板） | OH vendor/HDI；adapter 只 `dlopen("libmali.so.0")` **按 soname 运行期解析**，非硬编码 vendor 路径 | `framework/core/jni/adapter_bridge.cpp:73-78` |
| **gralloc/HDI buffer**（stride/对齐/AFBC 压缩/DMA-BUF fence & usage） | **SoC/板级**，在 **adapter 之下** | 否 | OH HDI；**须运行期探测**（不可假设固定 usage/format 组合） | codex 反证；`pixel_format_mapper.h`（usage 映射表） |
| **display 分辨率/DPI/rotation** | **SoC/板级**，被 **adapter 运行期吸收** | 否（每板不同） | **运行期 QUERY** OH DisplayManager，FALLBACK 仅查询失败时兜底 | `framework/activity/java/OhDisplayProvider.java:40-66`（`getDisplayInfo(0)` → appWidth/DPI/rotation） |

**结论**：adapter **源码里没有 board 常量、没有 `#ifdef SoC` 分叉**。GPU/gralloc/HDI 全在 inner_api ABI 边界**之下**由 OH vendor 层吸收；display 几何由 adapter **运行期探测**。唯一编进 `.o` 的差异是**架构**（§1）与**编译期 GN 产物选择**（§3）。

---

## 3. 构建维度：board 是硬编进 `.o`，还是只体现在"选哪棵 OH 产物树"？

**结论：board 主要体现在外置 OH 产物树的选择（`out/<product>`），不是编进 adapter 逻辑**——但当前脚本有 drift。

- 参数化**已部分存在**：`build/config.sh:20 OH_PRODUCT_NAME="rk3568"` + `:24 $OH_ROOT/out/$OH_PRODUCT_NAME`；`ninja_patches/patch_*.sh` 用 `${OH_PRODUCT_NAME:-rk3568}`；`build_ohos_service.sh` 全程 `out/$OH_PRODUCT_NAME`。
- 但**新的 arm64 bridge 脚本 drift 成硬编码** `out/wukong100`（`compile_oh_adapter_bridge_arm64.sh:167,244-248,313,462,630` 等一片直写 wukong100），未走 `$OH_PRODUCT_NAME`；armv7 脚本对称硬编码 `out/rk3568`。修法 = **un-hardcode 回 `$OH_PRODUCT_NAME`**，纯构建配置，非源码改动。
- adapter `.o` 的 include 来自 OH inner_api 头 + GN 算出的 `include_dirs`（脚本注释 `arm64.sh:453`「GN already computed... 225 entries」）——这些是**版本级 API/gen 头**，board 差异落在 vendor 层、不进这些头。**但见 §4 的 GN 宏反证**：GN 产物选择可能把编译期宏也一起换掉，不止是路径。
- `out/wukong100`(D600) vs `out/rk3568`(D200) 差异**会不会渗进 `.o`**：路径本身不会；**但产物树承载的 gen 头 + GN 宏若不同就会**（§4）。故必须**隔离产物/缓存目录**（`out/aosp_lib` vs `out/aosp_lib64`、独立 ccache/thinlto-cache），否则两板产物互相污染。

---

## 4. ABI 稳定性：同一 OH 6.1.0.31，两板的平台库 ABI 是否一致？

**裁决：同 OH 版本号 ≠ 自动 ABI 兼容。** 版本号是必要不充分条件；真正的充分条件是「同版本 **且** 共享组件的 GN 产物参数一致」。具体机制（codex 反证，已采纳）：

1. **GN 产品宏 / source set 可变**：同一 OH 版本，不同 product 的 `gn args` 可开关编译期宏、增删 source。典型杀手例：**`RS_PROFILER_ENABLED`** 条件会给 RenderService 某类**新增一个虚函数 `Patch()`**，从而**改动 vtable 槽位**。若 wukong100 与 rk3568 该宏取值不同，adapter 对该 vtable 槽的假设在**同一 6.1.0.31 上仍会错位**。
2. **dynsym 一致 ≠ struct/parcel 一致**：导出符号集相同，不证明结构体布局 / IPC parcel 打包一致（同名符号背后布局可因宏而异）。
3. **本仓库现状**：arm64 bridge 脚本复用了 rk3568/armv7 的宏与 ninja 片段（`arm64.sh:453-462` sed 自 `out/wukong100` 的 ninja，但注释仍写 rk3568 include 集），且 `BASE_VERSIONS §三·风险①` 的 **~13 个 appmgr/zidl 头偏差未闭合**。
4. **~13 头偏差的定性（回答任务第 3 问）**：`ScheduleMemoryLevel`/`NotifyAppForceLandscape`/appmgr/zidl 的偏差是 **api24 ↔ 6.1.0.31 代次(generation)偏差，不是 board 偏差**。两板同为 6.1.0.31 会有**相同**的 IPC 形状。故这条偏差**正交于 D600/D200 之分、对两板等同影响**，**不构成 per-device 分叉理由**；修法是让单一源码对齐 6.1.0.31（同时惠及两板），而非按设备分叉。

**推论**：一份源码对两板"二进制兼容"成立的前提是——两板的 **platform（非 chipset）库确为同一 6.1.0.31 patch、且共享组件 GN 宏一致**。这必须**逐库 dynsym + build-id + 结构体/vtable 抽样**验证到设备，不能凭版本号假定（当前 `BASE_VERSIONS §一②↔④` 已标 PENDING）。

---

## 5. 一份源码可行性裁决（回答任务第 4 问）

| 选项 | 裁决 |
|---|---|
| **A. 理想态**：一份源码 + per-device 换 OH 产物重编 N 次，**零源码分叉** | **原则成立、是目标**。板差全部可由 HDI/vendor(§2 之下) + 运行期探测(display/gralloc) + 构建配置(§3) 吸收。 |
| **B. 需少量 board 参数化**（build flag / 运行期探测），仍单一源码 | **这是现实落点**。必须做的参数化：①`OH_PRODUCT_NAME` 选产物树（un-hardcode wukong100）；②**架构分型**（arm64 vs arm32：`--target`/`-march`/sysroot/stub/aosp_lib 按 arch 选）；③运行期探测 gralloc usage/DMA-BUF fence（不可写死）。**均非源码分叉**。 |
| **C. 不可避免的 per-device 源码分叉** | **不需要**。未发现任何必须在源码里按 SoC 名 `#ifdef` 的点。GPU soname、display 几何、buffer 格式都能用运行期探测替代静态分叉。**渲染/present 层若遇 GPU 驱动 quirk（如 Mali blob 版本差异），也走运行期分支/探测，禁止编译期按板名分叉。** |

**净结论**：**能——一份 source of truth，编 2 次（两产物树；同架构则纯双产品，跨架构则叠一层架构源集）。零源码分叉，仅需 build 参数化 + 运行期探测。** 但"编 2 次即两台都跑"是**尚未验证的目标**（§6 缺口 + §4 ABI 未闭合），当前只有 D600/arm64 这一条被真机推进过。

---

## 6. 达成"编 2 次跑两台"的未闭合缺口

1. **架构维度未统一**（头号）：仓库把 D200 接成 arm32、D600 接成 arm64。需先确认 D200 真实架构；若要 arm64-D200，需接线 rk3568 的 arm64 product 产物树（当前不存在）。
2. **产物树/缓存未隔离**：脚本硬编码单一 product，未按设备隔离 `out/`、ccache、thinlto-cache、`aosp_lib`/`aosp_lib64`，两板并存会互污。
3. **ABI 未逐库验证到 D200**：§4 的 GN 宏 / vtable / struct / dynsym / build-id 只在 wukong100 侧有 parity 记录，rk3568 侧未做；`~13 头偏差`对两板同样未闭合。
4. **GPU/gralloc 运行期探测未做实**：libmali soname/namespace、DMA-BUF fence/usage 目前靠"两板恰好都是 Mali"侥幸，未写成板无关的探测。

---

## 7. 约定建议（回答任务第 5 问"这里的约定是什么"）

> **可写进文档的一条约定（建议纳入 `BASE_VERSIONS.md` 或 `ARCHITECTURE.md`）：**
>
> **「adapter 绑 OH 版本，不绑 SoC。」**
> 一份 source of truth，禁止在源码里出现 board 常量或按 SoC 名的 `#ifdef` 分叉。board 差异只走三条通道：
> 1. **OH HDI/vendor 层吸收**：GPU/EGL 驱动、gralloc、display HDI 在 inner_api ABI 边界之下，adapter 只按 **soname 运行期 dlopen** + 走 inner_api，不碰 vendor 路径。
> 2. **运行期能力探测**：DPI/分辨率/rotation（已由 `OhDisplayProvider` QUERY 实现）、gralloc usage/DMA-BUF fence——**探测，不写死**。
> 3. **构建配置参数化**：`OH_PRODUCT_NAME` 选 `out/<product>` 产物树；**架构**（arm64/arm32：`--target`/`-march`/sysroot/stub/aosp_lib）按架构源集选择。
>
> **per-device = 换 OH 产物树重编 + 各自 dynsym/build-id/vtable parity 验证**，不是维护第二份源码。
> **同 OH 版本号不等于 ABI 兼容**：共享组件的 GN 产物宏（如 `RS_PROFILER_ENABLED` 改 vtable）必须一致，且逐库验证到每台真机，才认二进制兼容。

---

## 8. 与 `BASE_VERSIONS.md` / 单目录约束的协同

- **单目录 source of truth 不变**：本约定与"单目录依赖 + 无外链"完全一致——一份 `framework/` 源，多份**外置** OH 产物树。多设备**不复制源码**，只多几棵外置产物树引用。
- **BASE_VERSIONS 要按 device 扩展，但"加一列"不够**（codex 反证，已采纳）：
  - **共享行（不复制）**：OH 目标版本(6.1.0.31)、AOSP 14、① 头 oracle、③ SDK 工具链——这些是版本级、两板共用。
  - **per-device 必须钉的完整 build profile**（不止两列）：`arch`（arm64/arm32）、设备 `fingerprint`/build-id、该 product 的 **repo/GN args**（含 `RS_PROFILER_ENABLED` 等改 ABI 的宏）、头/gen/sysroot 哈希、**逐库 sha256 + build-id + 符号版本**、产物/缓存隔离路径。
  - **验收门（CI，禁降级）**：strict-link 不得回退 relaxed；校验 ELF arch/UND/IPC 形状；**两板各自 truly-cold 冷启 ×2**；build-id 只对**各自基线**有效，不跨板复用。
- 具体做法：在 `BASE_VERSIONS.md` 现有「四身份」框架下，为 **② stub 符号源 / ④ 设备运行时**各**按 device 分块**（D600 已有 wukong100/arm64 数据；新增 D200 rk3568 分块，arch 与逐库哈希待补），① 头 oracle / ③ SDK 作为共享块不动。

---

## 9. codex 挑刺记录（20 年架构师人设，1 轮，阻塞直连）

codex **认可**核心原则「单源、按产品重编、板差走 HDI/能力探测」，但判**现状 Not Proven**，提出三条具体反证，**本文全部采纳**：

| # | codex 反证（机制） | 处置 |
|---|---|---|
| 1 | **D200=arm32 / D600=arm64**：ELF/JNI、ART 偏移 0x4/0x8、stub/AOSP 库须编译期按 arch 分型；硬码 rk3568 属性/显示/instructionSet；libmali soname/namespace 随板变；DMA-BUF fence/usage 须探测 | **采纳**，升为 §1 头号变量 + §2/§6/§7 |
| 2 | **同 OH 号不保证 ABI**：GN 产品宏/源集可变；`RS_PROFILER_ENABLED` 条件新增虚函数 `Patch()` 改 vtable；dynsym 同 ≠ struct/parcel 同；arm64 脚本复用 rk3568/armv7 宏，13 头偏差未闭合 | **采纳**，写成 §4 全节 |
| 3 | **BASE_VERSIONS 加列不够**：须钉全 machine profile（arch/fingerprint/repo-GN/头-gen-sysroot 哈希/逐库 sha-buildid-符号版本），缓存输出隔离，CI 禁降级、验 ELF/UND/IPC + 两板冷启 ×2，build-id 只对各自基线 | **采纳**，写成 §8 |

**无重大分歧**：codex 未推翻"一份源码可行"的核心，反而收紧了达成条件。唯一需向用户回证的开放项 = **D200 真实用户态架构（arm64 还是 arm32）**——本仓库证据指向 arm32，与任务前提"都是 arm64"冲突，落地前须澄清。

---

## 10. 遗留验证清单（交接）

- [ ] 向用户/codex 确认 D200 部署架构（arm64 vs arm32）——决定是"同架构 2 编"还是"跨架构 2 编"。
- [ ] un-hardcode `compile_oh_adapter_bridge_arm64.sh` 的 `out/wukong100` → `$OH_PRODUCT_NAME`（构建配置，非源码）。
- [ ] 逐库对 D200 侧平台库做 dynsym + build-id + 关键 struct/vtable(尤其 RS/window) parity，比对 D600 与 §4 GN 宏一致性。
- [ ] 把 libmali soname/namespace、gralloc usage/DMA-BUF fence 改为板无关运行期探测。
- [ ] `BASE_VERSIONS.md` 增 D200 per-device build profile 块；CI 加两板 strict-link + 冷启 ×2 门。
