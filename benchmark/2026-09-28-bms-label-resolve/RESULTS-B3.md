# B3 图标最高密度 + 自适应合成(#40,oc-t4,5cd)

接 `RESULTS-KIT-BUILD.md`(B2)。B3 库 = B2 基础上新增 `adaptive_icon.{h,cpp}`(AXML 遍历 + arsc 最高密度引用解析 + lodepng 双线性缩放合成)并接线 `apk_installer.cpp` 的 XML 分支(合成优先,失败回退原路径表)。

- build2:**Compiled: 31/31,Linking OK**,1.3M(raw `18b515da…`,patchelf 后 `675536e8…`)
- 部署 5cd 双路径 + foundation 3328 `/proc` root 四处哈希一致(`675536e8…`),根分区回 ro;B2 库已备份(`/data/local/tmp/b2-kit-backup/libapk_installer.b2kit.sys64.so`)
- 日志:`evidence/b3-build-20260929T0245.log`(build1 30/31,唯一 FAIL=引用了 arsc_resolver 匿名命名空间的 ReadZipEntry→本 TU 自带 minizip 读取器修复)、`evidence/b3-build-20260929T0300.log`(全绿)

## 场景 b3_icon_from_highest_density(verified)

安装后部署目录 `icon.png` 实测(hilog `ResolveResourceIdToFile` + `ReadIconByManifest` 原文行见 four-hilog.txt 等):

| app | manifest icon id | arsc 选中(候选数) | 部署 icon.png |
|---|---|---|---|
| wikipedia | 0x7f0f0000 | `res/ET.png`(6) | 48×48,1825B |
| termux | 0x7f0d0000 | `res/u3.png`(6) | 48×48,505B |
| aegis | 0x7f0f0000 | `res/9w.png`(7) | 48×48,2990B |
| markor | 0x7f0800d8 | `res/8X.png`(6) | 48×48,3127B |
| mcdonalds | 0x7f110004 | `res/mipmap-xxxhdpi-v4/mcd_launcher.png`(6) | 192×192,8641B |
| burgerking | 0x7f0f0000 | `res/mipmap-xxxhdpi-v4/ic_launcher.webp`(6) | 192×192,13146B |

混淆资源名(wikipedia/termux/aegis/markor/fd-seal)经 manifest→arsc 正确命中;这五个 APK 图标资源本身只有单密度桶(选中即最高);mcd/bk 在 6 个密度候选中选中 xxxhdpi 192×192。**位图路径覆盖,判据满足。**

## 场景 b3_adaptive_icon_composed(unverified-on-board)

- 实现已落地并编译进库(31/31);`apk_installer.cpp` XML 分支:读 XML → `ComposeAdaptiveIcon`(foreground/background TYPE_REFERENCE 各经 arsc 最高密度;背景支持 ARGB8 纯色;画布 max(层尺寸,108) 上限 512;src-over 合成)→ 成功则发布,失败回退。
- **板上无触发**:全部可装 app 的 manifest 图标都先解析到位图(spec 决策:位图优先,自适应 XML 仅当只解析到 XML 时合成)。带自适应 XML 的可装 app(mcd/bk)有 xxxhdpi 位图;唯一"仅 XML"的 x/toutiao 在图标段之前就失败(见下)。
- R2:代码 verified(编译+静态审查),运行时行为 unverified。

## 场景 b3_missing_icon_apps_install(FAIL,根因具名且在图标之外)

三 app 仍 9568260,但失败链前移、图标不再是墙(原始行见 fd-seal-hilog.txt / x-hilog.txt / toutiao-hilog.txt):

- **fd-seal**:图标链全成功(`0x7f0d0000 -> res/9w.png` 960B、normalize、label=Seal、entry.hap 写入 OK)→ 之后 `BMSInstalld installd_operator.cpp:3222 APK native extraction failed: CRC/ELF/owner/mode verification failed`(libaria2c.so 提取后)→ `ExtractFiles(APK_NATIVE_SO) failed ec=8519936` → 9568260。**墙=installd 原生库校验。**
- **x / toutiao**:`base_bundle_installer.cpp:1514 oh_adapter_install_apk_with_manifest failed: -2005`(`OH_ADAPTER_APK_VERIFY_MANIFEST_FAILED`,apk_verified_session_c_api.h:42)——发生在图标段之前,AdaptiveIcon 0 次执行。**墙=APK verify-manifest。**

即 spec"图标修复后三 app 可装"的前提被证伪(该前提源自旧 3de38f09 代的观察);两堵新墙(installd native 校验、-2005)需外环派新条目。

## 桌面截图

`desktop.jpeg` sha256 `f6fa2c03…`(与 B2 相同=新图标不在当前页;外环读图定桌面显示)。

## R2

编译/部署/哈希核验/位图桶判据 = **verified**;自适应合成运行时 = **unverified**(无板上触发,代码已编入);三 app 可装 = **FAIL**(具名根因在图标之外,证据在案)。
