# split APK 合包结果(2026-10-01,oc-t4,离线)

## 合包(5 个 split key)

| key | 合包大小 | 签名 | so 数 | split 属性 | 资源 |
|---|---|---|---|---|---|
| mcdonalds | 128,037,904 | v3 | 10/10 ✓ | 无 split ✓ | en/es ✓ |
| subwaysurfers | 241,209,895 | v1+v2+v3 | 20/20 ✓ | 无 split ✓ | 多语言 ✓ |
| x | 178,542,028 | v3 | 33/33 ✓ | 无 split ✓ | en ✓ |
| burgerking | 70,781,182 | v2+v3 | 34/34 ✓ | 无 split ✓ | en 系列 ✓ |
| firefox | 248,670,382 | v2+v3 | 18/18 ✓ | 无 split ✓ | 多语言 ✓ |

**合包工具**:APKEditor 1.4.9(jar sha256 前 16: 7b458b43),merge 子命令,`-i <dir> -o <out.apk>`。
**签名**:apksigner + ohtest_nopass.jks(空密码),v1/v2/v3 按支持度自动选择。
**输出位置**:VM `/home/zhaoyue/a2hlab/ws/t4-split-merge/`(Mac `/Users/zhaoyue/OrbStack/a2hlab/...` 挂载可见)。

## 逐项核(badging)

- **native-code**:全部含 `arm64-v8a` ✓
- **split 属性**:全部无 split/isSplitRequired/requiredSplitTypes ✓
- **so 数量**:与原 ABI split 逐件对上(mcdonalds 10/10, subwaysurfers 20/20, x 33/33, burgerking 34/34, firefox 18/18)✓
- **资源**:全部含 en,密度含 160/240/320/480/640 ✓

## 三键便宜修

| 键 | 修法 | 结果 |
|---|---|---|
| fd-seal | 剔除 3 个 zip 压包 sidecar(libaria2c.zip.so/libffmpeg.zip.so/libpython.zip.so) | app-input.json 已改 |
| toutiao | 剔除 1 个 32 位 ARM ELF(libcvt.so) | app-input.json 已改 |
| subwaysurfers | apps.json 钉值重钉为目录实际 sha256 | apps.json 已改(5904cda2 → ffd32287) |

## 新钉值(合包后)

| key | 合包 sha256 前 16 |
|---|---|
| mcdonalds | 340c0d59f4bd0b85 |
| subwaysurfers | 4b06bd74a49f364b |
| x | eaed447b994a2d7d |
| burgerking | 76ff64914f0bc25e |
| firefox | a72db02671ceddfb |

**红线**:合包是商业 APK,只放 VM 输入目录,不进仓库;apps.json 只改 subwaysurfers 钉值(原 base 钉值不动)。
