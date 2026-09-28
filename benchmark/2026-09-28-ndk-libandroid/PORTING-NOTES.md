# ANativeWindow_* 簇移植核对(OH 6.1.0.31 sysroot)

来源(外环 2026-09-28 批注,黑板 #5/#8):
- `~/orca/00.Workspace` @ commit `72a2f0a52`
  - `src/adapter/framework/android-runtime/src/android_graphics_compat_shim.cpp`(L1093 起 "G2.14ad ANativeWindow NDK bridges";`ANativeWindow_fromSurface/acquire/release/getWidth/getHeight/getFormat/setBuffersGeometry/query`)
  - `src/adapter/framework/hwui-shim/jni/oh_native_window_shim.c`(OH NativeWindow 桥接,同族函数 + setBuffersDataSpace/tryAllocateBuffers/setFrameRate 等)

sysroot:`~/a2hlab/ws/toolchains/ohos-sdk/native/sysroot`(VM;`external_window.h` + `usr/lib/aarch64-linux-ohos/libnative_window.so` 存根)

## 符号逐个核对结论

| 00.Workspace 引用(裸名/inner API) | OH 6.1 头文件 | OH 6.1 存根 .so 导出 | 移植动作 |
|---|---|---|---|
| `NativeObjectReference` | ✗ 无声明 | `OH_NativeWindow_NativeObjectReference` ✓ | 改名 `OH_NativeWindow_NativeObjectReference` |
| `NativeObjectUnreference` | ✗ | `OH_NativeWindow_NativeObjectUnreference` ✓ | 同上改名 |
| `NativeWindowHandleOpt` | ✗ | `OH_NativeWindow_NativeWindowHandleOpt` ✓ | 同上改名 |
| `CreateNativeWindowFromSurface` | ✗ | ✗(仅 `OH_NativeWindow_CreateNativeWindowFromSurfaceId`) | 不需要:fromSurface 走读 `Surface.mNativeObject` 直返,不用它 |
| `CreateNativeWindowFromSurfaceId` | ✗ 裸名无 | `OH_NativeWindow_CreateNativeWindowFromSurfaceId` ✓ | 改前缀名 |
| `NativeWindowGetDefaultWidthAndHeight` | ✗ 头文件无 | ✗ 无导出 | 删除,改 `NativeWindowHandleOpt(oh, GET_BUFFER_GEOMETRY, &h, &w)` |
| `NativeWindowPreAllocBuffers` | ✗ | `OH_NativeWindow_PreAllocBuffers` ✓ | 改名 |
| `OH_NativeWindow_GetSurfaceId` | ✓ L738 | ✓ | 原样保留 |

词边界复核(nm -D + grep -E `(^|[^_A-Za-z])sym`):裸名在 6.1 头文件中零命中;存根库全部导出均为 `OH_NativeWindow_*` 前缀(35 个)。

## 语义差异(必须改的两处)

1. **GET_BUFFER_GEOMETRY varargs**:OH 6.1 文档(external_window.h L113-117)为 `[out] int32_t *height, [out] int32_t *width` 两参;00.Workspace 源码传 `(&height, &width, &format)` 三参(OH7 痕迹)。移植时去掉第三参;取 format 走单独的 `GET_FORMAT`(`[out] int32_t *format`,L118-123)。
2. **AdapterAnw 探针**(`oh_anw_try_acquire/oh_anw_try_release/oh_anw_get_oh`,来自 `liboh_adapter_bridge.so`):00.Workspace 的 G2.14ag 分代 shim 机制在本运行时不存在。T4 上下文里 `ANativeWindow_fromSurface` 返回的就是 `Surface.mNativeObject` 里的裸 OHNativeWindow*,无 shim 层——移植时删掉 `anw_unwrap`/探针,直通 OH 调用;`mNativeObject==0` 与 sentinel 判空保留(null → 上层重试,行为与 hwui 期望一致)。

## OH_OP_* 操作码映射(NativeWindowOperation 枚举顺序)

SET_BUFFER_GEOMETRY=0, GET_BUFFER_GEOMETRY=1, GET_FORMAT=2, SET_FORMAT=3, GET_USAGE=4, SET_USAGE=5, SET_COLOR_GAMUT=12, SET_TRANSFORM=15, GET_TRANSFORM=16(枚举顺序与 00.Workspace 手写 #define 一致,已对枚举原文核过)。

## 构建约定

`scripts/lab/dockbuild.sh cc`(锁 clang-15 + 同 sysroot)编译;独立源码目录,不改共享 libandroid 产物;旧导出 48 个名字与版本不变(见 t4 spec #8)。
