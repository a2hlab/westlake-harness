# #46③ 头条 WebView RenderThread SIGSEGV@0 符号化与根因

范围:cold-a4 的 `libwebviewchromium.so+0x3e026f0`(板 5ea34a45,#38),以及外环补充的 aot42 verify-1 的 `+0x26016f0`(板 5cd1e3dd,#42)。只读离线分析,没有上板。原始输出见同目录 `webview-renderthread-raw.txt`,文中 §A–§O 指该文件的小节。

## 结论(一句话)

两个偏移是**同一条指令,同一个根因**。westlake 的 `libwebview_bionic_shim.so` 在 dlopen 改道里有顺序 bug,导致 §734 的 GLES 改道从未生效。Chromium 因此拿到 OH 的 NDK 门面 `/system/lib64/ndk/libGLESv2.so`,`glGetString`/`glGetIntegerv` 失效,GrContext 创建静默失败。Chromium 109 的 `~SkiaOutputSurfaceImplOnGpu` 在 `gr_context()==NULL` 时仍调用 `gr_context()->flush()`,于是在文章页 WebView 画第一帧时 SIGSEGV@0。

## 1. 符号化

**二进制核对(verified)**:板上 `libwebviewchromium.so` 的 sha256 是 `27c34ff4…`,与 cold-a4 和 verify-1 两轮的 device-report 一致,也等于 VM `out-sp20/webview-candidate/webview-t-lib/libwebviewchromium.so`,build-id 为 `cf585aca…`。libhwui 是 `a11c9154…`,等于 `out-all0925/native-runtime/libhwui.so`。plat_support 是 `aef81ea2…`。见 §D、§E。

**偏移换算(verified,并修正 memory 中的规则)**:该库 PT_LOAD[0] 为 offset 0、vaddr 0、R E。真实 vaddr 应按 `绝对 pc − 首个 r-xp(offset 0)映射基址` 计算:
- cold-a4:0x7e113806f0 − 0x7e0f580000 = **0x1e006f0**,cppcrash 给出的 rel-pc 比它多 0x2002000。
- verify-1:0x7dd38806f0 − 0x7dd1a80000 = **0x1e006f0**,rel-pc 比它多 **0x801000**。

两轮 22 个 libwebviewchromium 帧逐帧相差恒定的 0x1801000。可见 faultloggerd 的 rel-pc 基址每轮不同,memory 里"一律减 0x2002000"只适用于 cold-a4,不是通用规则。

**库无 .symtab/.debug_info**(Chromium 109 官方引擎,已剥离符号)。识别方法:用 `paciasp` 定函数边界,解析 adrp+add 引用的字符串,再与 Chromium 109.0.5414.123 源码逐指令对照。源码取自 chromium.googlesource.com 同 tag 的 `skia_output_surface_impl_on_gpu.cc` 和 `output_surface_provider_webview.cc`。见 §G–§L。

| 帧 | cold-a4 rel-pc | vaddr | 函数 | 依据 |
|---|---|---|---|---|
| #00 | 0x3e026f0 | 0x1e006f0 | `GrDirectContext::flush(const GrFlushInfo&)`,入口第 4 条 `ldr x8,[x0]`(x0=NULL) | 相对 vtable 调 slot 8 即 `abandoned()`;为真时依次调 info[16](info[24]) 和 info[32](info[40],0),与 Skia 源码一致;0x1e00690 = `flushAndSubmit` 先调它再调 `submit`(0x1e1741c)§H |
| #01 | 0x6528fd0 | 0x4526fd0 | `SkiaOutputSurfaceImplOnGpu::~SkiaOutputSurfaceImplOnGpu()` 中的 `gr_context()->flush(flush_info)` | 开头写回自身 vtable(析构特征);`[this+472]`=context_state_ → `RemoveContextLostObserver(this+8)`;`MakeCurrent(false)`;`[this+40]` slot7=`GetGrShaderCache` + ScopedCacheUse;`[cs+208]`=vk_context_provider → `AddVulkanCleanupTaskForSkiaFlush`(0x1e0faf4,首条 `cbz x0`);`[cs+240]`=**gr_context_ = NULL** → flush。§I、§L |
| #02 | 0x6529354 | 0x4527354 | 同一类的 deleting destructor(调完整析构后尾跳 operator delete) | §J |
| #03 | 0x3e01f50 | 0x1dfff50 | `SkiaOutputSurfaceImplOnGpu::Create`:`if (!impl_on_gpu->Initialize()) return nullptr;` → 经 vtable 调 deleting dtor | 引用字符串 "SkiaOutputSurfaceImplOnGpu::Create" 与 "Failed to make current during initialization.";0x1dfff34 调 `Initialize()`(0x4526690),失败后在 0x1dfff50 调 `blr`。§K |
| #04 | 0x3e01d6c | 0x1dffd6c | Create 的调用方(应为 `SkiaOutputSurfaceImpl::InitializeOnGpuThread`,未由字符串坐实) | — |
| #05–#09 | … | 0x275aed0 / 0x452526c… | base::BindOnce invoker 与 GPU 任务转发 | — |
| #10/#14 | 0x2d37a40 | 0xd35a40 | OnceCallback 运行蹦床 | — |
| #11–#13 | 0x425d5fc… | 0x225b5fc… | `TaskForwardingSequence::RunTask`(WaitSyncToken) | 引用字符串 |
| #15 | 0x425de78 | 0x225be78 | `TaskQueueWebView::ScheduleOnVizAndBlock` / RunTasks | 引用 "../../android_webview/browser/gfx/task_queue_webview.cc" |
| #16–#20 | … | … | HardwareRendererViz / RenderThreadManager 绘制入口(函数名未坐实) | — |
| #21 | 0x42414a8 | 0x223f4a8 | `DrawFn_DrawGL`(AwDrawFnImpl) | 引用 trace 字符串 "DrawFn_DrawGL" 和 "android_webview,toplevel" |
| #22 | plat_support 0x3ad0 | — | `android::draw_gl(...)`(draw_functor.cpp,westlake 源码构建,带 DWARF) | llvm-symbolizer |
| #23–#89 | libhwui | — | `WebViewFunctor::drawGl` ← `GLFunctorDrawable::onDraw` ← `SkDrawable::draw` ← `ganesh::Device::drawDrawable` ← `DisplayListData::draw` ← `RenderNodeDrawable::drawContent/forceDraw`(多层递归) | llvm-symbolizer §F |

两轮寄存器同构:x0=0,x6=0x76,x9=0x5ea38c,x3=x4=−1,esr=0x92000007(数据异常,EL0 读)。§A、§C。

## 2. 根因链(每一步的证据)

1. **Chromium 拿到的是 NDK 门面 libGLESv2**
   - 进程 maps 中映射了 `/system/lib64/ndk/libGLESv2.so`(4 段);hwui 用的是 `platformsdk/libGLESv3.so` 和 `platformsdk/libEGL.so`。§B
   - Chromium 按裸名 `libGLESv2.so` 加载 GL(`.rodata` 中的字符串)。它的 dlopen 确实经过 shim:cold-a4 有 2 次 "library resolved libandroid.so … for the WebView caller"。
   - 但 §734 的改道日志 "GLES library translated … for libwebviewchromium.so" 在全部 **50/50** 份 child.stderr 中出现 **0 次**。§N
   - 原因在 shim 的代码顺序(`westlake-ability38/framework/webview-shim/webview_bionic_shim.c`):L969–976 的 `.z.so` 探测块先执行 `real_dlopen("libGLESv2.so")`,在 LD 路径(含 /system/lib64/ndk)里一打开就 `return plain;`。L991–1000 的 §734 改道 `→ /system/lib64/platformsdk/libGLESv3.so` 因此永远走不到,成了死代码。§O
   - 部署的 shim `ae6ac828…` 里有 §734 的字符串,说明代码编进去了,只是执行不到。
   - 同一文件 L925–941 的注释记录过同类 bug:"library resolved" 块曾因放在探测块后面而不可达,修法是把它挪到探测块之前。§734 块漏了这一步。
2. **NDK 门面在 OH 上让 GL 查询失效**:§734 注释(westlake 早先的实测)写明,门面依赖 Android EGL 线程 hook 表,而 OH 平台 EGL 不安装这张表,所以"即使有有效的当前上下文,glGetString 也返回 NULL,glGetIntegerv 不写 GL_MAX_VERTEX_ATTRIBS"。本次日志与此逐字吻合,cold-a4 child.stderr:69857–69865 和 verify-1:433545–433552 各有一组:
   - `SharedContextState::InitializeGL failure max_vertex_attribs : 0 is less that minimum required : 8`
   - `[INFO:GrGLUtil.cpp(66)] nullptr GL version string.`
   - `[ERROR:create_gr_gl_interface.cc(290)] Failed to initialize extensions`
   - `[ERROR:shared_context_state.cc(305)] OOP raster support disabled: GrGLInterface creation failed.`
3. **WebView 109 不检查初始化失败**:`OutputSurfaceProviderWebView::InitializeContext()` 忽略 `InitializeGL`/`InitializeGrContext` 的返回值,于是 `gr_context_` 保持 NULL。
4. **Chromium 的潜在 bug 把它变成崩溃**:`SkiaOutputSurfaceImplOnGpu::Initialize()` 先执行 `context_state_ = …`,再在 `!gr_context()` 时返回 false;`Create` 随即销毁对象。析构里 `MakeCurrent(false)` 成功(上下文并未标记丢失),`has_context` 为真,接着无条件调用 `gr_context()->flush(flush_info)`,对 NULL 解引用,在 #00 触发 SIGSEGV@0。

## 3. 出现频率

- 系统 cppcrash 只收回 2 份:cold-a4 与 verify-1。两份都是 RenderThread,栈完全相同(见上)。
- stderr 里的四行签名出现在 **12/50** 轮:ability38 的 cold-a4、cold-a5、cold-a7、cpu-detail-1、warm-b8、warm-b10;aot42 的 formal-base-r1、formal-base-r2、formal-base-r3、formal-speed-r2、formal-speed-r3、verify-1。
  - 每轮签名后 stderr 只剩 10–153 行就结束,说明进程随即死亡。其余 10 轮没有抓 faultlog。
- **与打开文章页一一对应**:共有 13 轮出现 `[B47-SLA] ENTRY … NewDetailActivity`,其中 12 轮带签名。第 13 轮 trace-1 在 ENTRY 后只剩 2769 行、没有任何 Chromium GL 日志,是日志在首帧前截止。
- 其余 37 轮没有打开文章页(只做同意、空闲、a6 跳 TikTok、提前退出),**完全没有** WebView GL 初始化。
- 各轮里 WebView 的 GL functor 首次绘制失败率是 12/12:文章页就是进程里第一个走 GL functor 的 WebView,一画首帧就崩。

## 4. 修复方案

**A. 能立刻修(westlake 源码,单个 .so 增量重编)**
- 在 `webview_bionic_shim.c` 的 `dlopen()` 里,把 §734 的 GLES 改道挪到 `.z.so` 探测块**之前**,紧跟在 "library resolved" 块后面。条件不变:basename 为 `libGLESv2.so`,且 `caller_is_webview`。
- 或者让探测块在 `actual_filename != filename` 时直接 `real_dlopen(actual_filename)`。
- 建议同时审一遍 `libEGL.so` 的路径一致性。Chromium 用 `/system/lib64/libEGL.so` 全路径;本进程实际映射的是 `platformsdk/libEGL.so`,和 hwui 相同,暂未见问题。
- 只重编 `libwebview_bionic_shim.so`(#36 增量)。**注意 memory [#27]:WebView 打包器会丢掉 shim 修复,除非手动 overlay**,所以要覆盖到 `webview-t-lib/` 的 payload,并核对部署后的 sha256。

**B. 纵深防御(需要实验)**:Chromium 引擎是固定的 109 预编译,无法改析构里的 NULL 检查。A 修好之后如果 GrContext 仍失败,再评估以下两条:
- `WESTLAKE_WEBVIEW_GPU_MODE=software`(`--disable-gpu-compositing`)能否在 functor 模式下出图,不能假设可行。
- 在 plat_support 的 `draw_gl` 里先探测 `glGetString(GL_VERSION)` 是否为 NULL,为 NULL 就跳过这一帧,避免崩溃。

## 5. 验证方法(可 grep 的断言)

板上跑头条,点条目打开文章页,至少 3 次:
1. `grep -c 'GLES library translated libGLESv2.so -> /system/lib64/platformsdk/libGLESv3.so for libwebviewchromium.so' child.stderr` == 1
2. `grep -c 'InitializeGL failure max_vertex_attribs' child.stderr` == 0,并且 `grep -c 'GrGLInterface creation failed' child.stderr` == 0
3. 点击后 60s 内,`/data/log/faultlog/temp/cppcrash-<pid>-*` 里没有 `Name:RenderThread` 且含 `libwebviewchromium.so` 的记录;进程 60s 后仍存活(`pidof`)。
4. 进程 maps:`grep -c 'ndk/libGLESv2.so' /proc/<pid>/maps` == 0(Chromium 不再加载门面库;若有其他库也加载它,要逐库说明)。
5. 文章页截图有正文内容,不是空白或信息流。

离线预检(不占板):对新 shim 执行 `strings`,确认改道字符串仍在;再用 `llvm-objdump` 确认 `dlopen` 中对 "libGLESv2.so" 的 strcmp 分支位于第一次 `real_dlopen` 调用之前。

## 6. R2 分级

- 符号化(#00–#03 与 #21 的函数身份、NULL 来自 `SharedContextState::gr_context_`):**verified**。依据是二进制哈希一致、源码与反汇编逐条对应、字符串交叉引用,并且两轮栈与寄存器同构。
- 两个偏移是同一根因:**verified**。22 帧逐帧相差恒定的 0x1801000,vaddr 相同(0x1e006f0),二进制相同,两轮 stderr 签名相同。
- 触发条件是 GrContext 创建失败(四行日志)、且紧接着进程终止:**verified**(12/12,两份 cppcrash)。
- "失败源于 shim 顺序 bug 让 Chromium 用上了 NDK 门面 libGLESv2":**partially**。代码顺序、0/50 改道日志、maps 中的 ndk/libGLESv2.so 都已核实;但"门面导致 glGetString 为 NULL"这一机理引自 §734 注释,本次没有独立复现。
- 修复 A 能消除崩溃并让文章 WebView 出图:**unverified**,需要上板。
- 类别:**能立刻修**(A);B 需要实验。
