# R155 ART 补丁序列来源(SOURCES.md)

底座: android-14.0.0 (art-r1 = b6-art14-recovery/art-r1, describe=android-platform-14.0.0_r19, commit 3c05e56adf; R155 同底 kImageVersion 108/kOatVersion 230)。
目标: 逐字节复现 B6 重建树 art-hanbin(b6-art14-recovery/art-hanbin)在 19 个差异文件上;#20 PRIMCLASS-GUARD 为反汇编补回(art-hanbin 未含)。
对账: 两版寒冰补丁 hanbin_adapter/aosp_patches(106)与 HanBingChen/adapter/aosp_patches(108),逐文件应用到 r1 验哪版命中 art-hanbin(43 处不同的逐文件裁决见下)。
验证: 全 20 补丁 plain `git apply` 到 fresh r1 = ok=20/fail=0,19 文件与 art-hanbin mismatches=0(见 tools/spec-checks d1_patch_series_applies_to_r1)。

| # | patch | 目标文件 | 来源 | sha256 |
|---|---|---|---|---|
| 01 | 01-compiler__optimizing__code_generator.cc.patch | compiler/optimizing/code_generator.cc | ~/workspace/hanbin_adapter/aosp_patches/art + ~/orca/HanBingChen/adapter/aosp_patches/art (两版一致) | 60a4aff7a46241b24fd38fef9633024484fdc27970689af06862b2d7ce2d5b11 |
| 02 | 02-compiler__optimizing__graph_visualizer.cc.patch | compiler/optimizing/graph_visualizer.cc | ~/workspace/hanbin_adapter/aosp_patches/art + ~/orca/HanBingChen/adapter/aosp_patches/art (两版一致) | 4dc1569c3b797f2918ba6cfb17dcca678d4e67ac3833c1f09c65be80af72dfeb |
| 03 | 03-compiler__optimizing__nodes.h.patch | compiler/optimizing/nodes.h | ~/workspace/hanbin_adapter/aosp_patches/art + ~/orca/HanBingChen/adapter/aosp_patches/art (两版一致) | f49cd8659853573b94628c5be557ced5bed8c85bf861e51e33e60f72c611f688 |
| 04 | 04-dexoptanalyzer__Android.bp.patch | dexoptanalyzer/Android.bp | ~/workspace/hanbin_adapter/aosp_patches/art (仅此版有;HanBingChen 缺) | 7cacb0fa756bfd66f3e2a1507985f739b99aecb961ffce9fdbc23a130d1ec3dc |
| 05 | 05-libartbase__base__metrics__metrics.h.patch | libartbase/base/metrics/metrics.h | ~/workspace/hanbin_adapter/aosp_patches/art + ~/orca/HanBingChen/adapter/aosp_patches/art (两版一致) | 5e0f5b8890e244dc0cf3c4739687f17f30508aa9e401c259795a2c8f2772c3a1 |
| 06 | 06-libartservice__service__Android.bp.patch | libartservice/service/Android.bp | B6 重建树 art-hanbin 直取(两版寒冰均无此补丁) | beed829d322ba798ecac6cab0bceade533e8e1c41edba843db77f0bf5efe8184 |
| 07 | 07-profman__Android.bp.patch | profman/Android.bp | ~/workspace/hanbin_adapter/aosp_patches/art (仅此版有;HanBingChen 缺) | 9f833e2afada287bd5a47ae688e5ea9755a1ff40a3a49b039e5ce1ee52ff9b29 |
| 08 | 08-runtime__class_linker.cc.patch | runtime/class_linker.cc | ~/workspace/hanbin_adapter/aosp_patches/art/~/orca/HanBingChen/adapter/aosp_patches/art 语义基线 + B6 art-hanbin 树的调试 fprintf 增补(寒冰补丁 applies 但 art-hanbin 另加了 [CLI_CP] 等诊断) | be96c5d367c4618c60fa66508c2aed34b0603d9fe329a1e51d8862d0aef1a2bb |
| 09 | 09-runtime__elf_file.cc.patch | runtime/elf_file.cc | ~/orca/HanBingChen/adapter/aosp_patches/art (仅此版命中;hanbin_adapter 版 applies-nomatch) | 6bf15eead30a18633ab04ee85f305a08b7a777396e1935a6fa7bdd00a6987610 |
| 10 | 10-runtime__gc__collector__mark_compact.cc.patch | runtime/gc/collector/mark_compact.cc | ~/workspace/hanbin_adapter/aosp_patches/art + ~/orca/HanBingChen/adapter/aosp_patches/art (两版一致) | 45fc8c81ae2bfdef0dcc363c4169c89e617d0e72ff9f62e3069c199dbf25bb20 |
| 11 | 11-runtime__gc__heap-inl.h.patch | runtime/gc/heap-inl.h | ~/workspace/hanbin_adapter/aosp_patches/art + ~/orca/HanBingChen/adapter/aosp_patches/art (两版一致) | 83c353ce14e56a1a15587317d7321e064f5836be8284a332cf38fed7f0d6b122 |
| 12 | 12-runtime__gc__heap.cc.patch | runtime/gc/heap.cc | ~/orca/HanBingChen/adapter/aosp_patches/art (仅此版命中) | a50b61adcd5e0cbc6808e75f97bd706950e74fe1d3395c3d459713d6dc83769f |
| 13 | 13-runtime__gc__space__image_space.cc.patch | runtime/gc/space/image_space.cc | ~/orca/HanBingChen/adapter/aosp_patches/art (仅此版命中) | 147a83db77bc80cf1867cc6aaf1819e73be181437c67ad38fc67aa9fe44dc65c |
| 14 | 14-runtime__jit__debugger_interface.cc.patch | runtime/jit/debugger_interface.cc | ~/orca/HanBingChen/adapter/aosp_patches/art (仅此版命中) | 17bb523d161f607da7504b0bdf075155aaeb294a6a1864dfdbc56656dde63aac |
| 15 | 15-runtime__jni__jni_id_manager.cc.patch | runtime/jni/jni_id_manager.cc | ~/orca/HanBingChen/adapter/aosp_patches/art (仅此版命中) | bfd91df56f222965204046940a0e5b0665d720be75936339012e1be91413406e |
| 16 | 16-runtime__oat_file.cc.patch | runtime/oat_file.cc | ~/orca/HanBingChen/adapter/aosp_patches/art (仅此版命中) | a2f155188365ddf67297425be804bfe28dfdff83b54a51e9195773bc4014166b |
| 17 | 17-runtime__runtime.cc.patch | runtime/runtime.cc | ~/workspace/hanbin_adapter/aosp_patches/art/~/orca/HanBingChen/adapter/aosp_patches/art 语义基线 + B6 art-hanbin 树的调试 fprintf 增补 | 74306d25355585464a89fab3425b5dd4e9791a1501229d0c0dc46e5523ac65fe |
| 18 | 18-runtime__thread.cc.patch | runtime/thread.cc | B6 重建树 art-hanbin 直取(两版寒冰均无此补丁) | 02a7dc13353fc55bbfef1323b7f159e7721156c2d6e949924b3b8956ef30083c |
| 19 | 19-runtime__thread.h.patch | runtime/thread.h | ~/workspace/hanbin_adapter/aosp_patches/art + ~/orca/HanBingChen/adapter/aosp_patches/art (两版一致) | b7f95cf832b62d8e0f5e7d3e026803beb97e8bed6b5b6ec845dbf9d4c1a44902 |
| 20 | 20-runtime__mirror__dex_cache-inl.h.patch | runtime/mirror/dex_cache-inl.h | R155 反汇编推回(DIGEST E.7 PRIMCLASS-GUARD;B6 art-hanbin 快照未含,须单列) | 31e8ecf25e786cf269fb23ef0b2f6aa939f0d661b07629773265d0bc15c4c2b2 |

## 无来源补丁数: 0(每条均标 寒冰目录 / B6 重建树 / 反汇编依据)
