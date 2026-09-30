# c-route-dex2oat-108(hw248 持久产物)

OC-T4 黑板 #91 tagsoup 启动镜像线,Option C 交叉编产物。2026-09-30。

## 位置与哈希

hw248 `/home/alvin/c-route-dex2oat-108/`(构建原样副本在 `/home/yao/c-route-dex2oat/`):

| 文件 | sha256(前 16) | 说明 |
|---|---|---|
| `dex2oat` | `fe05a1cb54fd90ce` | 静态 ARM aarch64 EXEC,23,797,648 B,debug_info 未 strip |
| `Makefile.ohos-arm64-108` | `8f74b50ec9d6cb3d` | wall5 线 Makefile 副本(c++17 + hw248 路径 + 修复) |
| `libz.a` | `9b3136ca503728a1` | 自造(aosp-android-11-full zlib,15 成员,119,328 B) |

其余:`art-108-e6af1cd8/`(源,= LineageOS android_art @ e6af1cd8,img108/oat230)、`patches/`(yao 树隔离副本 + 108 适配)、`stubs108/`(yao stubs 隔离副本 + 108 适配 + host userfaultfd.h)、`fmtlib-vm/`(VM fmtlib 60101,带 `operator""_format`)、`build108-r4.log`(链成轮日志)。

## 版本核验(同板上 libart 59e1bb45 代)

- 二进制内 `art\n108\0` ×2、`art\n118\0` ×0;源 `runtime/image.cc` kImageVersion=108、`runtime/oat.h` kOatVersion=230
- readelf:Machine AArch64,Type EXEC(静态)

## 复编命令(hw248)

```bash
cd /home/yao/westlake-local-build/art-latest && make -f /home/yao/c-route-dex2oat/Makefile.ohos-arm64-108 -j32 \
  ART=/home/yao/c-route-dex2oat/art-108-e6af1cd8 \
  ART11=/home/yao/westlake-local-build/aosp-android-11-full/art \
  AOSP=/home/yao/westlake-local-build/aosp-android-11-full \
  STUBS=/home/yao/c-route-dex2oat/stubs108 \
  OHOS_LLVM=/home/yao/ohos-sdk/native/llvm \
  OHOS_SYSROOT=/home/yao/ohos-sdk/native/sysroot \
  LNH_R9=/home/yao/westlake-local-build/libnativehelper-r9 \
  BUILDDIR=/home/yao/c-route-dex2oat/build108 link-dex2oat
```

注:patches/stubs 重定向为 c-route 绝对路径(yao 共享树零污染);工具链与环境(westlake-local-build、ohos-sdk)属 yao,复编依赖其在位。

## 用途

上 5cd(`scp` → `/data/local/tmp/oc-t4-boot/`),原 5 jar(core-oj/core-libart/core-icu4j/adapter-mainline-stubs/framework,payload=板上 md5 逐字节同)原样重编 9 段 → 拉回逐段比 checksum;通过后才做 tagsoup 1.2.1 替换版。等外环『5cd 放行 oc-t4』。
