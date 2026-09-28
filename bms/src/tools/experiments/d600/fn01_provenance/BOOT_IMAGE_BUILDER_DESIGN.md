# Fn01.A04 当前代 boot image 最小 builder 设计

## 目标与边界

此 builder 只接受同一份 hash-frozen generation 中的 host ART 工具、九个
runtime BCP dex jar 和五个 `DEX2OATBOOTCLASSPATH` dex jar，产出 ARM64
九组三件套 `art/oat/vdex`（共 27 文件）。首组是
`boot.{art,oat,vdex}`，后八组按 jar role 命名。它不得从历史部署目录、设备 readback、
archive 或硬编码旧路径补输入。

boot image 是 A04 部署代际的必需产物。只有 jar 文件哈希相同不够：
`oh-adapter-framework.jar` 中的新 `PackageInfo` Java 路径是否被 ART 实际使用，
取决于与它同代烘焙并部署的 boot image。

## 固定顺序

runtime `BOOTCLASSPATH`：

1. `core-oj`
2. `core-libart`
3. `core-icu4j`
4. `okhttp`
5. `bouncycastle`
6. `apache-xml`
7. `adapter-mainline-stubs`
8. `framework`
9. `oh-adapter-framework`

`DEX2OATBOOTCLASSPATH`：

1. `core-oj`
2. `core-libart`
3. `core-icu4j`
4. `adapter-mainline-stubs`
5. `framework`

顺序本身必须进入 receipt；不能只记录一个无序哈希集合。

## 五段最小流水线

1. **冻结源码与 builder**
   - 延续 `generation-r4` 的 source-before/source-after 门。
   - 把 AlexPC AOSP manifest、目标 repo dirty digest、host `dex2oat64`、
     `libart.so`、`libsigchain.so`、JDK/d8/r8 工具哈希写入 builder identity。
   - 所有输入复制到新的隔离 staging；不直接以默认 `out/` 路径作为最终真源。

2. **产生九个当前代 dex jar**
   - 可用模块统一在 `BUILD_BROKEN_DISABLE_BAZEL=true` 的隔离 `OUT_DIR` 重编。
   - `framework` 使用已验证的 `framework-minus-apex` producer。
   - `core-icu4j` 已证明可从本树 current combined source jar 经本树 current
     d8、JDK 17 和 current `core-oj`/`core-libart` javac jars 显式生成含
     `classes.dex` 的 jar；最终 builder 必须重放该 producer，而不是直接接纳
     `.work/` 下的临时候选。
   - `adapter-mainline-stubs` 必须从
     `src/adapter/framework/mainline-stubs/java` 建立当前 builder，不得复制旧 jar。

3. **输入门**
   - 对九个 jar 检查 SHA-256、字节数、至少一个 `classes*.dex`。
   - 对两个 classpath 检查角色全集、唯一性和固定顺序。
   - 对 host ART 工具检查 ELF 架构、SHA-256 和完整动态依赖闭包。
   - 任一输入未被新 generation identity 收录即拒绝调用 dex2oat。

4. **ARM64 烘焙**
   - 使用当前代 host `dex2oat64`，显式指定 `--instruction-set=arm64`、
     按 runtime BCP 顺序提供全部九个 `--dex-file/--dex-location`、输出位置和
     设备目标参数。五项 `DEX2OATBOOTCLASSPATH` 是另一份运行期契约。
   - 完整命令数组、环境、rc 和 stdout/stderr 原样写入 stage log。
   - 产出与九个 runtime BCP jar 对齐的九组三件套，共 27 文件，逐个复制进
     sealed artifacts。五项 `DEX2OATBOOTCLASSPATH` 不等于输出段数。

5. **闭包与部署**
   - 新 generation identity 同时列出 host tools、九个 jar、27 份 boot 输出、
     bridge、installer 和 `oh-adapter-framework.jar`。
   - 部署工具只从该 identity 导入 expected hashes；caller 自报
     `PATH=HASH` 无权成为 oracle。
   - 设备 read-only receipt 绑定 serial、boot_id、全部部署路径与实际哈希；
     provenance PASS 仍不等于 Action 行为 `device_verified`。

## 已证实的 `core-icu4j` producer

AlexPC 当前树已完成三次 falsifier：

1. 不带 `--lib` 失败；
2. 把 dex jar 误作 `--lib` 失败；
3. 改用本树 current `core-oj`/`core-libart` javac jars 后通过。

通过代使用 JDK 17 与 current d8
`b773a721be3d4988dea9660815a9e441b76100e5b0f5c72b5893cfadadc76c6f`，
输入 current combined source jar
`c90d7239acbf8480a2908a109a10ced85548b4246fb5eb5e2e677fdbe11c4fd9`，
临时输出为 `0e17cb399e195426ac17ecd567118a772c931cba26ea0851dd00e7467f879195`
（1 个 `classes.dex`，jar 1,168,986 bytes；dex 2,511,508 bytes）。

这只资格化了 producer 路线。最终通用 builder/receipt 仍必须记录 JDK identity、
source jar、d8、按序 javac libs、完整 argv/environment/rc/log 及输出
hash/bytes/dex count，然后把输出复制进新的 sealed generation。临时
`/opt/build-trees/.work/fn01-a04-current-bcp-r1/` 不能成为最终真源。

## 当前精确输入缺口

`check_fn01_a04_boot_inputs.py` 已证明候选字节中无哈希漂移；通用 builder
机制也已完成资格化，但最终部署代尚未 READY：

- `core-icu4j`：producer 已由通用 worker 从 frozen staging 重放并封存进
  qualification closure。
- `adapter-mainline-stubs`：current JDK 17 javac + current framework-minus-apex
  turbine classpath 编译 111 源文件为 189 classes，再经 current d8 与
  current core javac libs，producer 已通过。两项 missing-type warning 必须原样
  入 receipt，不得静默丢弃或误判为 PASS/FAIL。
- 其余 host src/tools/jar 已复制并纳入 qualification closure；该 closure 的父代 r4
  已被 supersede，因此不能转为最终部署 oracle。
- `framework-minus-apex` 路线已构建成功，候选 `framework.jar` 含五个 dex；
  仍需在最终 boot generation 中重编/封存，不能把当前默认 `out/` 当成收据。

资格化 generation `Fn01.boot-0bdfcec3166c2e61a46f` 已生成 27 文件和
hash-bound receipt/closure/identity，状态刻意保持
`qualification_only=true`、`eligible_for_deploy=false`。最终缺口不再是 boot
producer，而是把新 bridge 与真实 target trigger seam 证据合并成新的
cross-action coverage，再从全新 staging 重烤最终代。
