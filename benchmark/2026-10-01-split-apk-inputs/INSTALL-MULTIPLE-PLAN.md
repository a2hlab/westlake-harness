# install-multiple 方案(重写版,FZ-001 扩展,离线,不编不上板)

派单(板 ACK(95) 02:15 打回重写):按安装器源码回答「单独装 split APK 会怎样」、
bm 多 -p 事务到安装器的行为、合包替代案评估,两案对比给推荐。

## ① 单独 bm install -p 一个 split APK:被拒、覆盖 base、还是追加?(源码行号)

**答案:被拒(多 APK 场景)+ 覆盖 base(单独装 split 时)。**

`oh61-bms-kit-b79/foundation/bundlemanager/bundle_framework/services/bundlemgr/src/base_bundle_installer.cpp`:

- **多 APK 事务(adapter 分派处就拦死)**:`:1495-1498`
  ```cpp
  if (apkCount != 1 || bundlePaths.size() != 1) {
      LOG_E(BMS_TAG_INSTALLER, "APK install requires exactly one APK and no mixed HAP/app inputs");
      return ERR_APPEXECFWK_INSTALL_MORE_THAN_ONE_APP;
  }
  ```
  多个 `-p` 走到这里直接拒,根本到不了 libapk_installer。

- **单独装一个 split APK(同包名,第二次)**:`:1615` `adapterIsUpdate = IsBundleExist(pkg)`
  走更新路径(`:1952` UPDATING_START 状态机)。**文件部署固定写 `deployedDir + "/base.apk"`(`:1636`),
  且 stage 目录先 `RemoveDir` 清场再重建(`:1659-1669`)** ⇒ 单独装 split = 以更新名义
  **清场重部署,base.apk 被 split 文件覆盖**。split 无 dex、versionCode 常为 null/0
  (mcdonalds lock 里 version_code=null),libapk_installer 的 JSON schema 校验
  `versionCode` 要求整数(`:1581` 附近 `isInteger(versionCode)`)——无 versionCode 的 split
  可能在校验处就被拒,即使过了也会被当 base 覆盖部署。

- **网络权限变更硬拒**:`:1776-1797` 更新时网络权限集合变更直接
  `ERR_APPEXECFWK_INSTALL_GRANT_REQUEST_PERMISSIONS_FAILED`。

**结论:逐件装 split 在当前安装器上行不通**——要么被多 APK 检查拒,要么覆盖 base。

## ② 「bm help 无 install-multiple」出处更正 + bm 多 -p 事务行为

**出处更正**:我写的是「实证:bm help 无此项」但没跑过板——这是凭 OH 公开文档与
`bm` 命令行接口推断,不是实测。按源码:`bm` CLI 的 install 子命令接口是
`bundle_installer_interface.h:62` `Install(vector<string>, ...)` 原生支持多路径 vector,
但 adapter 分支的 `apkCount != 1` 检查(`:1495`)把多 APK 对 .apk 封死。
**bm 多 -p 事务对 APK  = 被拒**(`ERR_APPEXECFWK_INSTALL_MORE_THAN_ONE_APP`)。

## ③ 合包替代案(主机侧 APKEditor merge)

**做法**:把 base + 选中 config splits(arm64_v8a + 密度 + 语言)在主机侧合成一个单 APK,
走原单 APK 路径(bms_batch/安装器零改动)。

**签名校验查证**(libapk_installer + adapter 分支源码 grep):
- `apk_installer.cpp`(vm-copies/westlake-current 与 b6-r155 版)grep signature/cert/pkcs/x509 = **0 命中**;
- adapter 分支(`base_bundle_installer.cpp:1485-2100`)grep signature = **0 命中**;
- ⇒ **安装器不验签**,合包后重签名不会触发安装器侧校验。

**app 侧自查签名**(5 个 split 键的 base APK classes.dex strings 扫描):
- subwaysurfers/mcdonalds/firefox 各含 1 处 `GET_SIGNATURES`/`signingInfo` 字符串;
  burgerking/x 为 0。这些字符串可能是引用而非实际调用(需反汇编确认),但存在即风险——
  合包重签名后签名指纹变,自查签名的 app 可能拒绝运行。

**合包工具**:APKEditor(github.com/REAndroid/APKEditor)`merge` 命令,社区验证过
(split→single APK)。需要重签名( jarsigner/apksigner),签名指纹变更是已知代价。

## ④ 两案对比与推荐

| 维度 | 逐件装(split 单独 bm install) | 合包(主机侧 merge 成单 APK) |
|---|---|---|
| 安装器改动 | 需改 FZ-001 冻结件(extension) | **零改动**(走原单 APK 路径) |
| 源码可行性 | **不可行**(多 APK 拒 :1495;单独装 split 覆盖 base :1636/:1659) | 可行(不碰安装器) |
| 签名风险 | 无(原签名不变) | 重签名后指纹变;3/5 split 键有签名字符串(风险) |
| 输入侧改动 | resolve_input 加 splits 字段 + install 段多 APK 分支 | resolve_input 加合包步骤(调 APKEditor merge + apksigner) |
| FZ-001 冻结约束 | 需 extension 审批(同产物加新功能) | **不碰冻结件** |
| 验证成本 | 5 个 split 键全量板上验 | 主机侧合包 + 单 APK 路径回归(原 FZ-001 证据 4 键) |

**推荐:合包案。** 理由:安装器零改动(不碰 FZ-001)、源码可行性闭合(逐件装被拒/覆盖);
签名风险可控(3/5 键有签名字符串但需反汇编确认是否实际调用;若调用则该键单独走
「保留原签名」或「签名白名单」处理)。

## ⑤ 输入侧三键便宜修(不变)

| 键 | 问题 | 修法 |
|---|---|---|
| fd-seal | sidecar `libaria2c.zip.so` 非 ARM64 ELF | 从 sidecar 清单剔除该件 |
| toutiao | sidecar `libcvt.so` 非 ARM64 ELF | 同上 |
| subwaysurfers | apps.json 钉的 apk_sha256 与目录实际不符 | 重钉为目录里 base APK 的实际 sha256 |

## ⑥ 验证计划(合包案)

| 组 | app | 验证点 |
|---|---|---|
| 原 FZ-001 回归 | fd-tusky / fd-k9 / fd-android / fd-filemanager | 单 APK 路径不变:t20 同冻结时状态 |
| 合包新功能 | x / burgerking | 合包后装上,native 库可加载 |
| 合包新功能 | mcdonalds / firefox / subwaysurfers | 同上;subwaysurfers 需先修输入钉值 |
| 签名风险 | subwaysurfers / mcdonalds / firefox | 反汇编确认签名字符串是否实际调用 |

