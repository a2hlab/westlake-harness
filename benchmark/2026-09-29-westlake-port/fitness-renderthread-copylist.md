# fd-fitness RenderThread SIGSEGV —— Westlake 照抄清单(#r16 限时项,交 cx-t0 并入 v3c)

证据:5ea run `20260930T000547-bbfaa0a6` fd-fitness(hilog+cppcrash-32667.txt 一手)。源:vm-copies/westlake-current @ `532633d`("Give Skia a font configuration that exists…")。

## 一、route-A 死亡链(r16 一手,时间序)

1. `09:09:45.863` `libhwui.so` 加载失败:`Error loading header libhwui.so: failed to map header → load libhwui.so failed, namespace=westlake.sealed.child, errno=2`
2. `09:09:47.844` mali 驱动起后 `libGLESv3.so` 被拒:`load absolute_path /system/lib64/libGLESv3.so: check ns accessible failed namespace=ndk` → `namespace=ndk no inherits` → `dlopen_impl load library header failed`
3. `09:09:48.194` RenderThread SIGSEGV:`SEGV_MAPERR@0x10000000f`,顶帧 `libskia_canvaskit.z.so sktext::gpu::TextBlobRedrawCoordinator::internalAdd+716`(drawGlyphRunList 之下)——**文字路径在无有效字体/字形缓存状态下崩**。

**关键甄别**:`namespace=ndk` 是 **OH 原生 dlns(musl loader)**,不是 route-A 的 ANL classloader 域(`westlake.sealed.child` 是另一套)。#91 的 ANL gate 放开救不了这两条——libhwui/GLESv3 的拒绝都发生在 OH 原生 loader 层。

## 二、Westlake 为什么活(四个部件,全部一手行号)

| # | 部件 | 文件:行 | 作用 |
|---|---|---|---|
| 1 | **真 libhwui 运行期注册** | `framework/android-runtime/src/AndroidRuntime.cpp` L3889-3920(Phase 2 r27) | `dlopen("/system/android/lib/libhwui.so", RTLD_NOW\|RTLD_GLOBAL)` 后调其 27 个 `register_X`——Paint/Canvas/RenderNode/HardwareRenderer 全是真 Skia 实现,无桩。hwui 的 DT_NEEDED(libskia_canvaskit/libEGL/libGLESv3/libutils)注释明言 "all available on device" |
| 2 | **hwui-shim 全家 = liboh_hwui_shim.so** | `framework/hwui-shim/jni/`(13 文件) | `oh_skia_ahb_shim.cpp`(GrAHardwareBufferUtils 三函数真实现:eglGetNativeClientBufferANDROID→eglCreateImageKHR→glGenTextures→GrBackendTextures::MakeGL);`oh_minikin_shim.cpp`(minikin::FontCollection/Layout/FontStyle 等,桥 OH_Drawing_Font/TextBlob——**正是 TextBlob 崩的这条文字路径**);`oh_display_shim/oh_native_window_shim/oh_hardwarebuffer_shim/oh_choreographer_shim/oh_graphicsstats_shim`;ashmem/atrace/sync compat;`wl_egl_trace/wl_gl_trace/wl_looper_trace` |
| 3 | **文件级字体初始化(不碰 IPC)** | `framework/hwui-shim/jni/oh_typeface_init.cpp`(G2.14n+ 重写)+ `framework/appspawn-x/src/child_main.cpp` L1204-1225 | `SkData::MakeFromFileName + SkTypeface::MakeFromStream`(纯 FreeType,无服务调用;明确避开 SkFontMgr_New_OHOS——它会生 OS_IPC 工作线程挂死 preFork)。child_main 在 fork 后 `dlopen liboh_hwui_shim.so(RTLD_LOCAL)` + `dlsym(oh_typeface_mark_child)` 标记"子进程可做真 Skia 工作" |
| 4 | **EGL 边界(可选 damage 回退)** | `framework/android-runtime/src/oh_egl_boundary.cpp` | 只删两个可选 damage 扩展的受控回退( WESTLAKE_EGL_TEST_NO_DAMAGE 注入开关),不伪造扩展、不全局软渲染 |
| (辅助) | **LD_LIBRARY_PATH 语义** | staged run.sh L5 | Westlake 子进程 env 含 `/system/lib64:/system/lib64/platformsdk:…`——`libGLESv3.so` 走 **default namespace** 的路径解析而非受限 ndk 域;这是"没有 ndk 域拒绝"的根因(route-A 的 OH 原生 ndk 域 no-inherits 才是拒绝方) |

## 三、照抄清单(给 cx-t0 → v3c)

1. **libhwui 真注册段**:AndroidRuntime.cpp L3889-3920 整段(route-A 侧对应 runtime 库启动处)——把 dlopen+27 register_X 抄入;route-A 当前 libhwui 在 `westlake.sealed.child` 域加载失败(errno=2),须同时把 `/system/android/lib/libhwui.so`(v3a payload 已含该路径)加入 sealed child 域的搜索/许可路径。
2. **hwui-shim 全家**:framework/hwui-shim/jni/ 13 文件原样(重点 oh_minikin_shim/oh_skia_ahb_shim/oh_typeface_init),链成 liboh_hwui_shim.so(构建注释在 oh_minikin_shim.cpp 头:`$CXX --target=arm-linux-ohos -shared -fPIC -std=c++17 … -lnative_drawing`)。
3. **child 标记**:child_main.cpp L1204-1225 的 mark_child dlopen/dlsym 段。
4. **GLESv3/EGL 可达**:两条任选其一——(a) 按照抄惯用法,把 `/system/lib64` 加入 OH 原生 default/ndk 域的 LD_LIBRARY_PATH 语义(route-A child env);(b) 在 ndk 域为 libGLESv3.so/libEGL.so 显式 `dlns_set_namespace_permitted_paths`(参照 stock_child_plugin/src/westlake_stock_host_main.c L151-167 的 dlns_create2/permitted/allowed_libs 用法)。**这是本条核心**:没有 GLES,shim 2 的 EGL import 路径照样死。
5. **EGL 边界文件**:oh_egl_boundary.cpp 原样(默认无害,留注入开关)。

## 四、诚实限界

- 未逐个验证 hwui-shim 13 文件的独立可编性(构建注释仅 minikin 一个;$W 无独立 build 脚本,原工程接线在 vm-copies 之外的构建树)——cx-t0 并入时按 2 的链接注释起步,失败文件逐个补;
- `libhwui.so` 在 5ea 板的 sealed 域 errno=2 具体是路径不存在还是权限,未在板上 stat 验证(下一步上板先 `ls /system/android/lib/libhwui.so`);
- TextBlob 崩的**直接触发者**(字体缺位 vs GlyphRunList 空列表)未做最小复现——照抄 2+3 后若仍崩,再挖 minikin shim 的 Layout 空输入路径;
- r16 全量目录(r16full-A-5cd / r16full-B-61b)未现,出现即 auto_triage 出表(第二批,另交)。
