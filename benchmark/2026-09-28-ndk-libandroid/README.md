# T4 libandroid NDK 簇补口(离线段)— 已暂停

状态:**暂停于离线段**(2026-09-28 外环 #17 路线切换:改走 BMS/OH7.0 路线,Westlake 6.1 libandroid 补口停止)。

## 完成范围

1. **缺口口径与计算**(`scripts/compute_missing_symbols.py` → `results.json`):按 app 命名空间实际解析的 libandroid(framework-pinned,out.75d82d5,sha 核对通过)+ 全局 scope 内 DSO(libhwui/libwl_missing_natives/libwl_opengl_jni/libwebview_bionic_shim)建模,只保留强 UND 的 `A*` NDK 簇符号。结果:**STK 缺 16 个符号** —— AConfiguration×5、ASensorEventQueue×4、ASensorManager×4、ASensor×3;`AConfiguration_new`(原始报错符号)在集内 ✅。`ANativeWindow_*` 簇确认由 scope 内 libhwui.so 提供,不缺。
2. **ANativeWindow 簇移植**(外环 #5/#8 批注,黑板 #17 引用的"进行中的源码补丁"):`src/anativewindow_oh61.c` 从 `~/orca/00.Workspace`@`72a2f0a52` 两处源移植(非重写):`android_graphics_compat_shim.cpp` G2.14ad 段 + `oh_native_window_shim.c`。逐符号核对 OH 6.1.0.31 sysroot(`PORTING-NOTES.md`):裸名 `NativeObjectReference`/`NativeWindowHandleOpt`/`CreateNativeWindowFromSurface` 不存在 → 全改 `OH_NativeWindow_*` 前缀;`GET_BUFFER_GEOMETRY` varargs 确认两参 `(height,width)`,源码三参系 OH7 痕迹已改;AdapterAnw 探针层本运行时无 → 删并直通。`artifacts/anw_oh61_test.so` 经 `dockbuild.sh cc`(锁 clang-15 + OH 6.1 sysroot)编出,8 个导出齐(`BUILD-LOG.md` 有命令与 sha256)。

## 未完成(接手须知)

- STK 自身缺口的 AConfiguration×5 + ASensor×11 实现未写(ANativeWindow 簇服务于 26-app 横向覆盖,非 STK 立即需要);
- 功能测试程序(AConfiguration 尺寸密度 / AAsset 读写 seek EOF / 旧导出行为断言)未编;
- libandroid shim 未并入链接、未上板(等 T1 排序,已随路线切换作废);
- 横向扫描 66-app 结果在 VM `~/a2hlab/ws/out-t4-libandroid/`(apps66_scan/hist json),未拷回本仓。

## 材料

APK 提取的 `libSDL2.so`/`libmain.so` 未入库(`.gitignore` 排除,sha256 见 `apk-libs.SHA256`,可从 APK 重提)。GLESv1_CM stub 上游材料在 `../2026-09-27-app-breadth-sweep/glesv1cm-crux/`。
