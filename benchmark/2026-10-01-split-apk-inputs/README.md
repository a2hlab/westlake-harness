# split APK / 输入盲区取证(2026-10-01,oc-t4,离线,零板命令)

派单(板 ACK(95) 01:52):① fd-client null_producer 判③(SessionMixin 在 split APK,base.apk 取不到);
② EXCLUDE-input 3 个(fd-seal/subwaysurfers/toutiao)输入一直失败。查:66 键哪些是 split/xapk、
安装器与 bms_batch 对 split 实际怎么处理、3 个失败的日志原文;出分类表+修法方向。

## ① 66 键分类表(静态,输入目录 VM ~/a2hlab/app-inputs/ 实测)

**split 键(5 个)**——输入目录含多个 APK 且 app-input.json 标 `original-apk-with-splits`:

| key | APK 数 | splits 明细 | 备注 |
|---|---|---|---|
| burgerking | 4 | base + config splits | — |
| subwaysurfers | 2 | `subwaysurfers.apk` + `subwaysurfers.config.arm64_v8a.apk` | Unity IL2CPP,arm64 资源/库在 split |
| firefox | 3 | base + splits | — |
| mcdonalds | 4 | base + arm64_v8a/xxxhdpi/en 3 个 config split | extractNativeLibs=false,库在 ABI split |
| x | 4 | base + splits | — |

**mono 键(61 个)**:输入目录各 1 个 APK,`original-apk`。

**xapk 键(0 个)**:66 键输入目录里无 .xapk 文件(xapk 原料在 apks/xapk-extracted/,已解包)。

## ② 安装器与 bms_batch 对 split 的实际处理

`bms_batch.py resolve_input()`(benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py:114-151):

- 按 `apk_sha256` 从键目录里选**单个** APK(`sorted(matches)[0]`),**只取 base**;
- `split_hint` 仅作证据标记进 record,**不改变安装行为**;
- 安装落点 `code+'/base.apk'`,安装器(FZ-001 libbms/libapk_installer)只装这一个文件——
  **split APK 从不安装**。

⇒ 对 split 键:base 装上后缺 ABI split 里的 native 库/资源/密度资源,运行必炸。

## ③ 三个「输入失败」键的日志原文(record.json,j3-5ea 2026-09-30)

| key | status | error 原文 | 分类 |
|---|---|---|---|
| fd-seal | app_failed | `native sidecar is not an AArch64 shared ELF: libaria2c.zip.so` | **sidecar 架构错**,非 split |
| toutiao | app_failed | `native sidecar is not an AArch64 shared ELF: libcvt.so` | **sidecar 架构错**,非 split |
| subwaysurfers | app_failed | `pinned identity changed: apk_sha256` | **输入哈希漂移**,非 split |

三键都是**输入解析阶段**(resolve_input/native sidecar 校验)就拒,未进安装——与 split 只装 base 无关。
fd-seal/toutiao 的 sidecar 是 zip 压包或非 ARM64 ELF,被 `resolve_native_sidecars` 的 ELF 校验拦下;
subwaysurfers 是 apps.json 钉的 apk_sha256 与目录里实际 APK 不符(钉值过期或 APK 被换)。

## ④ fd-client「类在 split APK」更正

fd-client 输入目录 = 单件 `fd-client.apk`(kind=original-apk, splits=0),APK 内无 split entries;
但有 **7 个 DEX**(classes.dex … classes7.dex,multidex)。NULL-PRODUCERS 判③说的「类在 split APK」
实为**类在非主 DEX**(classesN.dex)——baksmali 离线只拆了 base 路径可见的部分。这是 multidex 取证盲区,
不是 split 安装问题;SessionMixin 在某一个 classesN.dex 里,bms 安装单 APK 时 multidex 全部可用,
运行时找类不受 split 影响——fd-client 的 null 根因仍是 DI 侧(accountManager 为 null),与 split 无关。

## ⑤ 修法方向

1. **安装器侧装 split(真 split 键的根治)**:5 个 split 键要亮,安装器需支持
   `pm install-multiple`(base + 选中 config splits:arm64_v8a + 密度 + 语言)。
   当前 libapk_installer 只吃单文件;改动量集中在安装器 + resolve_input 返回 splits 列表。
   优先级:subwaysurfers/x/firefox/mcdonalds/burgerking 都在 tail/controls,非当前点亮主线。
2. **输入侧修三键(便宜)**:
   - fd-seal/toutiao:从 sidecar 清单剔除 zip 压包/非 ARM64 件(libaria2c.zip.so、libcvt.so),
     或把 resolve_native_sidecars 的 ELF 校验放宽为「跳过+警告」而非拒装;
   - subwaysurfers:重钉 apps.json 的 apk_sha256 为目录里实际 base APK 的哈希。
3. **multidex 取证**:null_producer.py 的 baksmali 调用加 `-o out/` 后扫全部 classesN.dex,
   不只 base——fd-client 这类 7-dex app 的类归属判断才准。

## 证据位置

- 分类扫描:dockbuild 实跑 `~/a2hlab/app-inputs/` 113 目录逐键 APK 计数(本 README 数据行);
- 失败原文:`benchmark/2026-09-30-j3-u3-sweep/runs/j3-5ea/<serial>/{fd-seal,subwaysurfers,toutiao}/record.json`;
- fd-client multidex:dockbuild unzip -l 实证(0 split entries,7 dex);
- lock.json 对照:westlake-inputs/app-inputs.lock.json(25 条,mcdonalds/subwaysurfers splits 明细在)。
