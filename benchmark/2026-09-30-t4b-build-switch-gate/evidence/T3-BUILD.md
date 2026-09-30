# art-r155 构建记录(T3,2026-09-30 oc-t4)

树:hw248 `/home/alvin/aosp-14.0.0_r1-art`(T2 同步,钉版见 `../aosp-14.0.0_r1-pinned-manifest.xml`)。
补丁:art/ 上 21 件序列(#01-20 = T1 定版 R155 差异文件 patch;#21 = 构建层 `21-apex_available_platform.patch` 适配版,源自 cc-wiki `f880cd746`,sha16 `ce34ce8725307bf3`,490 行)。注:首轮逐字用 HanBingChen 原版 #21 与 #01-19 冲突(kati platform_availability_check 失败 03:01);逐字版 `git apply -R` 干净回退后换适配版,`--check` 过再打。

## 构建命令与结果

```sh
source build/envsetup.sh && lunch aosp_arm64-userdebug
m -j32 build-art-host libart   # r2: build completed successfully (19:58), FAILED=0
```

log:hw248 `/home/alvin/aosp-14.0.0_r1-art/t3-build2.log`(首轮败本 `t3-build.log`)。

## 产物(2026-09-30 20:33)

| 文件 | 大小 | sha256 前 16 |
|---|---|---|
| `out/host/linux-x86/bin/dex2oat64` | 211,517,928 | `8a125a256a743820` |
| `out/target/product/generic_arm64/apex/com.android.art/lib64/libart.so` | 10,304,888(ARM aarch64) | `65d8058f518cd22f` |

ldd(dex2oat64,仅 glibc 面 8 项):ld-linux-x86-64 / libc.so.6 / libdl.so.2 / libgcc_s.so.1 / libm.so.6 / libpthread.so.0 / librt.so.1 / linux-vdso.so.1 —— hw248 原生可跑。

源码版本(T2 已验):kImageVersion=108、kOatVersion=230(与板一致)。

## 下一步(T5)

用本 dex2oat64 对 9 jar(payload v3a-r8b)按板上 cmdline 原样(fn03 同形路径 + dex-location=/system/android/framework/*)生成 27 文件,对照 `boot-image-inputs.sha256`(L1/L2),kv 补 bootclasspath-checksums/compilation-reason。
