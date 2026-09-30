# native 层缺 bionic 符号簇(2026-10-01,oc-t4,离线)

派单(板 ACK(95) 03:34):① 66 key 全部 native 库的 UND 符号里 musl+libbionic_compat+westlake shim 都不提供的,聚类排序,先找已验证实现照抄;② 合包 4 键(x/mcdonalds/burgerking/subwaysurfers)在 61b 的首个致命点归簇。产出方案+补丁草稿交 cx-t0。

## ① 缺 bionic 符号簇(静态,static-facts.json 66 key 13 含 native 库的 app)

**真正缺的只剩 2 个符号**(`android_set_abort_message` 已被 libbionic_compat.so 导出,nm -D 命中 `T android_set_abort_message`):

| 符号 | 受影响 app 数 | 库 | 语义 | 照抄来源 |
|---|---|---|---|---|
| `__gnu_strerror_r` | 2(fd-fennec_fdroid/firefox 的 libmozglue.so) | libmozglue.so | GNU strerror_r 变体(返回 char* 而非 int) | **未找到**(Westlake/00.Workspace/real-work grep 0 命中) |
| `android_dlopen_ext` | 1(ppsspp 的 libppsspp_jni.so) | libppsspp_jni.so | dlopen 扩展(Android 特有,带 flag) | **未找到**(同) |

**`android_set_abort_message` 已提供**(13 apps 引用,但 libbionic_compat.so 已导出,不在缺失集)。

### 补丁草稿(shim,交 cx-t0 并进下一版 native)

**`__gnu_strerror_r`**(libbionic_compat.so 加导出):
```c
// bionic_compat 加:GNU strerror_r 变体(返回 char* 而非 int)
// 语义:strerror_r(errnum, buf, buflen) 的 GNU 版,返回 buf 或静态串
char *__gnu_strerror_r(int errnum, char *buf, size_t buflen) {
    // musl 的 strerror_r 是 POSIX 版(返回 int);GNU 版返回 char*
    // 简单实现:调 strerror(errnum) 拷进 buf,返回 buf
    const char *msg = strerror(errnum);  // musl strerror 线程安全(返回静态串)
    if (msg) {
        strncpy(buf, msg, buflen - 1);
        buf[buflen - 1] = '\0';
    } else {
        snprintf(buf, buflen, "Unknown error %d", errnum);
    }
    return buf;
}
```
出处:musl `strerror_r` 是 POSIX 版(返回 int);GNU 版在 glibc/bionic 返回 `char*`。bionic 的 `__gnu_strerror_r` 语义 = GNU 版。

**`android_dlopen_ext`**(libbionic_compat.so 加导出):
```c
// bionic_compat 加:Android dlopen 扩展(带 flag)
// 语义:dlopen 的 Android 扩展,支持 RTLD_* flag + Android 特有的 ANDROID_DLEXT_* flag
void *android_dlopen_ext(const char *filename, int flags, const void *extinfo) {
    // 简单实现:忽略 extinfo(Android 特有,如 ANDROID_DLEXT_USE_NAMESPACE),
    // 直接调 dlopen(filename, flags)。musl dlopen 支持 RTLD_* 标准 flag。
    (void)extinfo;  // 不处理 Android 特有 flag(命名空间等)
    return dlopen(filename, flags);
}
```
出处:Android `android_dlopen_ext` 是 `dlopen` 的扩展,额外支持 `android_dlextinfo`(命名空间、库路径等)。ppsspp 只用基础 flag,extinfo 可忽略。

## ② 合包 4 键首致命点(61b 20261001T030913 轮,hilog 栈)

| key | 首致命点(栈帧) | 归簇 |
|---|---|---|
| mcdonalds | `InputManagerGlobal.sService not found: NoSuchFieldException`(framework.jar classes2.dex)→ `System.load(libwestlake_html_compat.so) failed: path is outside app domain` → `attempted to close file descriptor 31`(DfxFaultLogger LastFatalMessage) | **framework 墙**(InputManagerGlobal.sService 缺字段)→ **native 域墙**(libwestlake_html_compat 不在 app 域)→ **fd 墙**(fd 31 误关) |
| burgerking | 同 mcdonalds 前两帧(InputManagerGlobal.sService + libwestlake_html_compat)→ `[VTLEN] klass=com.facebook.soloader.C super=UnsatisfiedLinkError`(class_linker.cc:8419) | **framework 墙**(同)→ **native 域墙**(同)→ **soloader 墙**(Facebook soloader 加载失败) |
| subwaysurfers | 同前两帧 → `[COROUTINE-FIX] primeCoroutineStart FAILED: ClassNotFoundException: kotlinx.coroutines.CoroutineStart` | **framework 墙**(同)→ **native 域墙**(同)→ **Kotlin coroutine 墙**(kotlinx.coroutines 类缺) |
| firefox | 同前两帧 → `[IFACE-BITS] kotlinx.coroutines.DispatchedTask.handleFatalException`(class_linker.cc:8653)→ 已知 `libmozglue.so __gnu_strerror_r` 缺符号(前一轮) | **framework 墙**(同)→ **native 域墙**(同)→ **Kotlin coroutine 墙**(同)→ **bionic 符号墙**(__gnu_strerror_r,簇①) |

**共簇**:4 键首两帧全同(InputManagerGlobal.sService + libwestlake_html_compat 域墙)——这是合包后新暴露的**公共 framework/native 域墙**,优先级高于各 app 特墙。

## ③ 交 cx-t0 建议

1. **libbionic_compat.so 加 2 个导出**(`__gnu_strerror_r`、`android_dlopen_ext`,补丁草稿见上)——`android_set_abort_message` 已提供,不动。
2. **公共 framework/native 域墙**(InputManagerGlobal.sService + libwestlake_html_compat 域墙)是 4 键共簇,优先于各 app 特墙——InputManagerGlobal.sService 是 framework.jar 缺字段(与 T7c 的 boot-api 桩同族);libwestlake_html_compat 域墙是 native 加载域问题(与 B7BindFixes 同族)。
3. **各 app 特墙**(burgerking soloader、subwaysurfers/firefox Kotlin coroutine)归已有簇,不新簇。

## 外环更正(2026-10-01 03:48,外环 claude)

②的「4 键首两帧全同 = 公共 framework/native 域墙,优先级高于各 app 特墙」不成立。这两行在 U5 全量里**已点亮的对照 app 同样各出现 1 次**(aegis、fd-droidify、helloworld、ooniprobe 的 hilog 都有 `InputManagerGlobal.sService` 与 `System.load(.../libwestlake_html_compat.so) failed: ... path is outside app domain`),是良性噪声,不是墙。4 个合包 key 的真正分叉点是后面那几条:mcdonalds 的 fd 31 被误关(fdsan)、burgerking 的 Facebook soloader、subwaysurfers/firefox 的 `kotlinx.coroutines.CoroutineStart` 找不到(与 fd-feeder、fd-gallery 同簇,cc-wiki 在查)、firefox 另有 `__gnu_strerror_r`。①的两个缺符号与补丁草稿不受影响。规则:最早出现的错误不等于致命点;先排除在已亮对照里也出现的日志行。
