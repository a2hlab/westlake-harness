# wl_critfix — JNI 兼容层（LD_PRELOAD，appspawn-x）

给 OHOS 上跑 Android APK 补 ART 的三个洞。装法：加进 appspawn-x 的 `LD_PRELOAD`
（和 `wl_stackgrow.so` 一起，`wl_stackgrow` 要排在前面）。

## 它解决什么

1. **`FindCodeForNativeMethod` 的 GOT hook**（libart+0x1197fa0）
   ART 走到这里时会拿 `Java_*` 的 mangled 名去 dlsym 已注册的库。可是
   `liboh_android_runtime.so` 里的实现全是内部符号（`_ZN7androidL35android_..._nativeNextEl`），
   dlsym 永远找不到 —— 于是明明 `data_`、ClassLinker 边表、quick entry 全是对的，
   还是抛 `UnsatisfiedLinkError`。hook 里按（declaring class、dex method index）匹配，
   匹配不上就退回 `data_`（先用 `dladdr` 确认它确实落在某个已加载模块里）。

2. **@CriticalNative 调用约定适配**
   这个 ART 只对内部白名单里的方法用 critical 约定，其余的走 regular，
   于是被调用方把 `JNIEnv*` 当成自己的第一个参数。差别与签名无关（整型参数
   regular 从 x2 开始、critical 从 x0 开始；浮点参数两种都在 v0..v7），所以用一个
   40 字节 thunk 通用适配，凡 `acc & kAccCriticalNative` 就装。

3. **按 `.symtab` 解析实现地址**
   扫 `liboh_android_runtime.so` 的 `.symtab` 找 `"<类简名>_<方法名>E"`，
   替掉写死的偏移表 —— runtime 重编之后不用再跟着改。反向也能用：
   给个运行时地址反查 mangled 名（`dladdr` 只会给 `sym=?`）。

4. **JNI 接入准入闸门的诊断 + 临时放行**
   `ScopedJniAttachment`（`native-compat/jni-attach-admission`）在进 JVM 之前
   先问「线程守卫登记表」要 READY 凭证。可是 arm 登记表的那两个函数
   （`westlake_native_compat_prepare_parent_runtime` /
   `..._prepare_main_thread`）**全仓库没有调用点**，所以 app 进程一直是
   `WLTG_PROCESS_UNSEEDED`，每一次 attach 都被拒——包括 OH vsync 回调线程，
   于是 `onOhVsync` 永远进不了 Java，一帧都画不出来。

   这里做两件事：把登记表三个入口包一层打印真实 status/reason（普通符号插桩
   + 直接改 runtime 的 GOT 跳转槽，双保险，因为 runtime 的引用带 `WLTG_1.0`
   版本号）；以及**仅当登记表处于 UNSEEDED 时**伪造一张 READY MAIN 回执，
   让 attach 退化成普通 `AttachCurrentThread`。登记表一旦真 armed，这段
   代码一行都不走。

5. **补跑没跑过的 `<clinit>`**
   这个 substrate 会把 boot classpath 的类盖章成 kInitialized 却不跑
   `<clinit>`（libart 自己的日志：`Tolerating clinit failure for L<类>;`），
   静态字段留在 null。`probe == NULL` 表示无条件跑一次（字段名跨版本不稳定、
   且重新推导幂等时用这个模式）。

   名单分两张，**不要合并**：`kForce[]` 目前没有调用点（强跑
   Proxy/Settings 的 `<clinit>` 会在 `ExecuteSwitchImplCpp` 里 SIGSEGV）；
   `kSafeClinit[]` 在 `do_repair()` 开头跑一次，只放实测安全的。

   `kSafeClinit[]` 里这四个是一条自底向上的依赖链，顺序不能换：
   `Charset`（查找缓存为 null，全进程的字符集查找都是坏的）→
   `sun.nio.fs.Util`（用 `Charset.forName` 拿静态编码器）→
   `FileSystems$DefaultFileSystemHolder` → `VMClassLoader`（boot classpath
   的 URL handler 数组为 null）。这条链断了的表现是
   `String.format` 整个运行时不可用 —— `Choreographer.doFrame` 第一帧就死。

6. **`JNIEnv` 溯源探针（`[WLENV]`）**
   把 `JavaVM` 的 invoke 表复制一份，换掉 attach/detach/GetEnv，于是每个线程
   拿还 `JNIEnv` 都留痕：线程名、`env`、`env->functions`、`self_`、`vm_`，加上
   回环 `self->tlsPtr_.jni_env`（Thread+0xc8）。外加一个 50 µs 轮询的看门狗盯
   `vm_`。`functions` 按 env 逐个记——**主线程的函数表和别的线程不是同一张**
   （`liboh_android_runtime` 给主线程换过），拿一个全局「已知正确值」去比，会
   把其余所有 env 误判成不是 env。

   看门狗线程只在子进程里起（`getuid() != 0`），而且走 `dlsym(RTLD_NEXT,
   "pthread_create")`：本文件自己插桩了 `pthread_create`，且在 SELinux HAP
   转换之前多一个线程会让 `applySELinux` 返回 -7。

7. **`RegisterNatives` 那扇门上的 @CriticalNative 补装**
   第 2 条的 thunk **只在 `FindCodeForNativeMethod` 的 hook 里装**，也就是只
   覆盖「ART 主动来问代码在哪」的方法。凡是通过 `RegisterNatives` 成批注册的
   （`android.view.MotionEvent` 就是一整张表一次注册完），ART 手里已有代码
   指针，根本不会来问 —— 于是一个 thunk 都没装上，被调用方继续把 `JNIEnv*`
   当自己的 `long nativePtr` 往里写。

   所以直接盯这扇门：`wl_RegisterNatives` 换进 `JNINativeInterface` 表里。

   - **改表本身，不是改每个 env 的 `functions` 指针**：每个 attach 上来的线程
     都有自己的 env，而且有些 env 是 ART 直接发的、不经过我们任何 hook，追
     env 永远追不完。改表一次，共用这张表的 env 全覆盖。这里**有两张表**——
     主线程那张和别人不是同一张，两张都得打。
   - 槽位地址取 `&(*env)->RegisterNatives`，**从头到尾不写结构体名字**：它在
     有的头文件里叫 `JNINativeInterface`，有的叫 `JNINativeInterface_`。
   - 打表的动作放在 `wl_patch_vm_table()` 里,所以 root 的 spawner 也会打；
     libart 那页是 `MAP_PRIVATE`，子进程 fork 时连补丁一起继承，于是
     `AndroidRuntime::startReg` 那一大批注册也在覆盖范围内。

   **不能在注册现场就扫**：注册发生在 runtime 起来的过程中、在 ART 随手挑的
   线程上，而扫描要调 Java。所以 hook 只把类存成 global ref 排队，由主线程的
   修复点（`wl_drain_regnat`）来消费 —— 就是第 5 条那个已经验证安全的窗口。

   **用反射列方法，不要用 `GetMethodID`**：JNI 规定 `GetMethodID` 会初始化类，
   而强跑框架类的 `<clinit>` 在这个 substrate 上正是会在
   `ExecuteSwitchImplCpp` 里 SIGSEGV 的操作；`getDeclaredMethods` 不会。

   `kCritSweep[]` 那张固定类名表留着,只跑一次,兜住 hook 装上之前就已经绑好的。

   两个细节：
   - `is_thunk()` 现在是必须的。两条路都会装 thunk，而 `crit_thunk` 只按目标
     地址去重,给 thunk 再套一个 thunk 它会照做,结果参数搬两次。
   - 同一次 drain 周期内重复注册的类会合并(这个 runtime 一次启动能把
     `SurfaceControl` 注册 **107 次**),但**不做永久去重** —— 真的重新注册会
     把原始入口点写回来,那就得重新装。

## 编

```sh
bash build.sh      # 需要 OHOS SDK sysroot + aarch64-linux-ohos clang
```

## 验证过的效果（板子 5cd33a95，OHOS-6.1.0.31）

- `No implementation found`：从一堆 → **0**
- LRT 踩内存哨兵：**0 告警**（装 thunk 前 `RenderNode_setTranslationX` 会把
  `JNIEnv+0x28` 写成 `0x404`）
- app 从 10 秒内必崩 → **活满 60 秒**，OHOS 建出真 surface、vsync 在跑
- 放行 attach 之后 `onOhVsync` 不再失败，**`Choreographer.doFrame` 真的跑起来了**
- 补完 `<clinit>` 链之后：`relayout` 从**全程 0** → c.stderr 5 行 / hilog 2 行，
  带 `SURFACE_CHANGED (firstCreate=true)` 和 `frame=Rect(0,0-1200,1920)`；
  主线程抛异常次数 1 → **0**
- **App 画出了自己的界面**（G2 Minimal Tap 的 `onDraw` 三行字），截图与完整日志见
  `var/evidence/task70-android-golden/runs/20260804-d600-first-real-frame/`
- **App 自己响应了触摸**：注入 3 次点击，app 的计数从 `0` 跳到 `3`，`[WLENV]`
  看门狗 `CORRUPT`/`RECYCLED` **各 0 条**，整轮无 `cppcrash`。截图与完整日志见
  `var/evidence/task70-android-golden/runs/20260804-d600-first-input/`

## 输入是怎么修好的（第 7 条的来历）

点击能送进 app 进程，但工作线程 `OH_InputMotionWorker` 每次都崩。`[WLENV]`
探针把因果链钉死了：它的 `JNIEnv` **拿到手时是好的**（`vm_` 正确、`self` 回环
闭合、没 detach），几十微秒后 `vm_` 被一次**32 位写**改掉——高 4 字节原样、低
4 字节被换。四轮不同 ASLR 下坏值低 12 位恒为 `0x211`，是页内固定偏移，不是
随机垃圾。

反汇编把读取点也钉死了：`MarkClassInitialized+0xfc` 从 `self+0xc8` 取
`jni_env`、再从 `jni_env+0x10` 取 `vm_` 交给 `AddWeakGlobalRef`，后者
`this+0x138` 取条件变量、进 `WaitHoldingLocks` 时 `guard_` 为 NULL 当场炸。

这是第 2 条那个老毛病的第二次发作，只是这次走的是另一扇门（见第 7 条）。补装
之后计数器从 0 走到 3，`CORRUPT` 归零。

顺带两个佐证，都指向「一串野写」而不是「单个坏字段」：踩进去的字节有一轮是
ASCII（`"Display ID: 0, Name: UNKNOWN, RefreshRate: 60..."`，全仓库搜不到，来自
OH 系统库），另一轮是 IEEE-754 double 的 NaN `0x7fc0000000000000`——正好对上
`nativeSetCursorPosition "(JFF)V"`，AOSP 对非鼠标事件传的就是 `Float.NaN`。
只把 `vm_` 修回去时崩溃点会往后挪到 detach 时 free 这个 NaN。

装上 hook 之后实测(同一次启动)：固定表补 42 个，hook 的队列又扫出 23 个类、
再补 26 个（`XmlBlock` 16、`Typeface` 5、`SystemProperties` 3、`Trace` 1、
`ApkAssets` 1），合并掉 148 次重复注册。

## 还没解决

- 真正的根治在 ART 里：凡 `IsCriticalNative()` 就该用 critical 约定派发，
  而不是只认内部白名单。这条改下去，第 2、7 两条都能删。
- 窗口 `attach:1 / sessionState:0` 不匹配仍未解。
- 第 4 条那张伪造的 READY 回执是止血；根治要给 arm 登记表补上真正的调用点。
