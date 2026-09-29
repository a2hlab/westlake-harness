# r16 三堵没人接的 native 墙 —— 定因与垫片覆盖判定(30 分钟限时)

证据:r16 hilog 一手(路径见各节)+ 输入侧 APK/lib 检查(VM unzip/ls 一手)。

## ① fd-breezyweather `libnrb.so` —— **已被 #86 垫片覆盖,零新工作**

- hilog 原文(5cd,00:17:10.579):`relocating failed: symbol not found. dso=/data/app/.../org.breezyweather/android/lib/arm64-v8a/libnrb.so s=__errno use_vna_hash=1 van_hash=50d63…`
- 判定:**与 fd-netguard 完全同型**——版本化 `__errno@LIBC`(bionic 专有,musl 真身 `__errno_location`)。
- 覆盖:#86 `westlake-bionic` 的 `libc.so`(`bionic-abi.map` 的 LIBC version node + `bionic_assert_compat.c` L23-24 桥)正是为此构建。**并 v3c 即解,不需要任何新符号。**

## ② fd-organicmaps `liborganicmaps.so` —— **新缺:`libGLESv2.so` 垫片,Westlake 有路可抄**

- hilog 原文(61b,00:16:47.067):`Error loading shared library libGLESv2.so: (needed by /data/app/.../app.organicmaps/android/lib/arm64-v8a/liborganicmaps.so)`
- 判定:**DT_NEEDED 缺失**(不是符号,不是版本节点)——与 fd-app 缺 `libstdc++.so`、mindustry 缺 `libOpenSLES.so` 同型,但缺的是 **libGLESv2.so**(GLESv2 的 Android soname;板上只有 OH 的 `libGLESv3.so`,且在 ndk 域被拒——fitness 结论)。
- Westlake 现成实现:**没有"libGLESv2.so 垫片"文件**(bionic_compat 无此 soname),但有语义来源:`framework/hwui-shim/jni/oh_skia_ahb_shim.cpp` 头注释明言其链接面是 "libEGL.so, libGLESv3.so"(OH 真 GLES 入口);Westlake 从不缺它是因为 app 库经 default 域解析到系统真 GLES。
- 建议(r17-native 最小做法):在 `westlake-bionic/build.sh` 加一个 **`libGLESv2.so` 转发垫片**(`DT_NEEDED libGLESv3.so` + 逐符号转发,或最简:空 DSO 满足 soname,organicmaps 只查 soname 不导 GLES 符号时即可过 dlopen——需编后上板验证哪一档够用)。**注意**:fitness 结论显示 `/system/lib64/libGLESv3.so` 本身在 ndk 域被拒——垫片若 DT_NEEDED 它,须放进 default 域可达路径或与 #86 包同放 app 域。
- 诚实限界:未验证 organicmaps 是否在 dlopen 成功后还要真调 GLES 函数(若要,转发垫片才够,空壳不够)。

## ③ firefox JNA `libjnidispatch.so` —— **不是垫片问题,是输入装配问题(split 未合并)**

- hilog 原文(61b,00:28:45.765+):`Open uncompressed library: lib/armeabi-v7a/libjnidispatch.so was not found in …/android/base.apk` + `UnsatisfiedLinkError: Native library (com/sun/jna/android-aarch64/libjnidispatch.so) not found in resource path (.)`
- 一手定因(输入侧):firefox 输入是 **original-apk-with-splits**(`app-input.json` 原文),native 库在 **sidecar 目录** `app-inputs/firefox/lib/arm64-v8a/`(18 个 .so,含 `libjnidispatch.so`);APK 本体 `unzip -l` **零 lib/ 条目**。r16 装的是单 APK → 板上 `android/` 目录只有 base.apk+icon,**根本没有任何 native 库**。JNA 先查 APK(无)→ 再查自身 jar resource(无)→ 死。
- 判定:**不属于 bionic/垫片段**;是 **bms_batch/installer 对 split APK 的装配缺口**(record `split_hint: True`、`apk_candidates: 3` 已有信号)。改法(交 cx-t0/cc-t3 定):装配时把 sidecar lib/arm64-v8a 推到板上 APK 相邻目录并把 `ApplicationInfo.nativeLibraryDir` 指过去(PackageInfoBuilder L205-242 的探测序正好会吃 `apkParent/lib/<abi>`——`#82 段 6` 的现成语义),或合并 split 再装。
- Westlake 对照:它当年的 firefox 跑法就是 launcher 预铺 runtime root(`ASX_NATIVE_LIB_DIR` 指向自带 lib 目录),同一问题的解法在 #82 段 6 已写。

## 汇总(给 cx-t0 并 v3c 的净增量)

| 墙 | 净增量 | 动作 |
|---|---|---|
| libnrb.so | **零**(#86 已覆盖) | v3c 带上 #86 libc.so 即可 |
| libGLESv2.so | **一个新垫片** | westlake-bionic/build.sh 加 libGLESv2.so(先空壳验证,不够再转发) |
| firefox JNA | **非 native 段** | 装配修(split/sidecar lib 入板 + nativeLibraryDir),记 cc-t3 |
