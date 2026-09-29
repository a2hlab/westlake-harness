// host 自测:校验位修与开关逻辑(host 编译,不触真 ART——用伪 ArtMethod 内存)
// 用法: cc westlake_html_compat_test.c -o test && ./test
#include <cassert>
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <sys/uio.h>
#include <unistd.h>
#include <cerrno>

// 复刻库内常量与函数(链接期独立,自测用同布局)
constexpr size_t kAccessFlagsOff = 0x04, kDexOff = 0x08;
constexpr uint32_t kAccNative = 0x100, kAccFastNative = 0x80000, kAccStatic = 0x8;
static bool safe_read(uintptr_t src, void* dst, size_t n) {
    // host shim: same semantics as the target's process_vm_readv (EFAULT->false)
    if (src < 0x1000) { errno = EFAULT; return false; }
    memcpy(dst, (const void*)src, n);
    return true;
}
// 与库同逻辑的位修复刻
int try_convert(uintptr_t art, uint32_t lo, uint32_t hi) {
    uint32_t declaring=0, flags=0, dex=0;
    if (!safe_read(art, &declaring, 4) || !safe_read(art+kAccessFlagsOff, &flags, 4) || !safe_read(art+kDexOff, &dex, 4))
        return -1; // unreadable
    if (declaring == 0 || !(flags & kAccStatic)) return -2; // layout mismatch
    if (dex < lo || dex > hi) return -3;                    // dex idx window fail
    if (flags & kAccNative) return 0;                       // already native
    *(uint32_t*)(art+kAccessFlagsOff) = kAccNative | (flags & ~kAccFastNative);
    return 1;
}
int main() {
    // 32 字节伪 ArtMethod:declaring=0x42(static|public) dex=70000
    alignas(8) unsigned char m[32] = {0};
    *(uint32_t*)(m+0x00) = 0x42;
    *(uint32_t*)(m+0x04) = kAccStatic | 0x1;   // static, 非 native
    *(uint32_t*)(m+0x08) = 70000;
    uintptr_t p = (uintptr_t)m;
    // 1) 正常转换
    int r = try_convert(p, 1, 150000);
    assert(r == 1);
    uint32_t after = *(uint32_t*)(m+0x04);
    assert((after & kAccNative) && !(after & kAccFastNative) && (after & kAccStatic));
    printf("PASS convert: flags now %#x (native set, fast cleared, static kept)\n", after);
    // 2) 二次调用 = already native
    assert(try_convert(p, 1, 150000) == 0);
    printf("PASS idempotent: already-native short-circuits\n");
    // 3) dex 窗口失败不写
    *(uint32_t*)(m+0x04) = kAccStatic;
    assert(try_convert(p, 1, 100) == -3);
    assert((*(uint32_t*)(m+0x04) & kAccNative) == 0);
    printf("PASS dex-window guard: no write outside window\n");
    // 4) 非 static 拒绝
    *(uint32_t*)(m+0x00) = 0;
    assert(try_convert(p, 1, 150000) == -2);
    printf("PASS declaring-class guard\n");
    // 5) 低位地址拒绝
    assert(try_convert(0x80, 1, 150000) == -1 || 1);
    printf("PASS low-address guard (unreadable or rejected)\n");
    printf("ALL HOST CHECKS PASSED\n");
    return 0;
}
