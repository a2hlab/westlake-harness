// bionic_compat/src/unity_libc_stubs.c
// [UNITY-LIBC-STUB] Wall-3 (Unity-on-OH) net libc gap fillers.
//
// Unity's libil2cpp / libunity / libc++_shared / libswappywrapper were built
// against the Android NDK (bionic). On OHOS/musl every UND libc symbol they
// carry already resolves against musl / liblog / the bundled libc++ EXCEPT the
// 7 bionic-only symbols implemented below. Each is a hard (GLOBAL, non-weak)
// UND in at least one of those .so; a single missing one makes dlopen() fail.
//
// All 7 are exported as plain GLOBAL/strong defs (unversioned). The consumers
// reference them as `name@LIBC`, but on this platform the musl loader binds a
// versioned-undef to an unversioned def (this is exactly how every other
// bionic @LIBC symbol already resolves against musl on OH).
//
// Compiled as C (build picks $CF for *.c: clang -std=c11, musl headers,
// NO -nostdinc++ / NO libcxx_compat.h) so musl <stdio.h>/<pthread.h> etc. are
// the plain musl declarations.

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <errno.h>
#include <locale.h>
#include <pthread.h>
#include <sys/select.h>

// ---------------------------------------------------------------------------
// 1) __errno  (il2cpp, unity, c++_shared, swappy)
//    bionic: int* __errno(void).  musl: int* __errno_location(void).
//    Forward to musl's thread-local errno slot.
// ---------------------------------------------------------------------------
extern int* __errno_location(void);

int* __errno(void) {
    return __errno_location();
}

// ---------------------------------------------------------------------------
// 2) strtoll_l / strtoull_l  (il2cpp, unity, c++_shared)
//    bionic locale-aware variants. We are C-locale-only on OH; drop locale_t.
// ---------------------------------------------------------------------------
long long strtoll_l(const char* nptr, char** endptr, int base, locale_t loc) {
    (void)loc;
    return strtoll(nptr, endptr, base);
}

unsigned long long strtoull_l(const char* nptr, char** endptr, int base, locale_t loc) {
    (void)loc;
    return strtoull(nptr, endptr, base);
}

// ---------------------------------------------------------------------------
// 3) __FD_SET_chk  (il2cpp, unity)
//    bionic _FORTIFY_SOURCE thunk: void __FD_SET_chk(int, fd_set*, size_t).
//    We skip the bounds check and do the plain FD_SET.
// ---------------------------------------------------------------------------
void __FD_SET_chk(int fd, fd_set* set, size_t set_size) {
    (void)set_size;
    FD_SET(fd, set);
}

// ---------------------------------------------------------------------------
// 3b) __FD_ISSET_chk  (unity)  [UNITY-LIBC-STUB] -- sister of __FD_SET_chk.
//     bionic FORTIFY thunk: int __FD_ISSET_chk(int, const fd_set*, size_t).
//     Drop the size check, do the plain FD_ISSET.
// ---------------------------------------------------------------------------
int __FD_ISSET_chk(int fd, const fd_set* set, size_t set_size) {
    (void)set_size;
    return FD_ISSET(fd, (fd_set*)set);
}

// ---------------------------------------------------------------------------
// 4) __open_2  (unity, c++_shared)
//    bionic _FORTIFY_SOURCE 2-arg open thunk: int __open_2(const char*, int).
//    No O_CREAT path is taken here (that is __open_2's whole contract), so a
//    plain 2-arg open() is the exact equivalent.
// ---------------------------------------------------------------------------
int __open_2(const char* pathname, int flags) {
    return open(pathname, flags);
}

// ---------------------------------------------------------------------------
// 5) __register_atfork  (swappy)
//    bionic: int __register_atfork(void(*prepare)(void), void(*parent)(void),
//                                  void(*child)(void), void* dso);
//    The 4th arg (dso handle, for unregister-on-dlclose) has no musl analogue;
//    ignore it and forward to pthread_atfork (musl does not export
//    __register_atfork, but pthread_atfork has identical prepare/parent/child).
// ---------------------------------------------------------------------------
int __register_atfork(void (*prepare)(void),
                      void (*parent)(void),
                      void (*child)(void),
                      void* dso) {
    (void)dso;
    return pthread_atfork(prepare, parent, child);
}

// ---------------------------------------------------------------------------
// 8) _ctype_  (unity)  [UNITY-LIBC-STUB]  -- BSD ctype classification table.
//    DATA symbol, NOT a function. musl/OH libc.so does not export it.
//
//    ABI note (verified by disassembling PackageEscort libunity.so):
//      adrp x9,_ctype_GOT ; ldr x9,[x9]      ; x9 = &_ctype_   (the symbol addr)
//      ldr  x9,[x9]                          ; x9 = *_ctype_   <-- DEREFERENCE
//      add  x12,x9,char ; ldrb w12,[x12,#1]  ; class = base[char+1]
//    i.e. the consumer treats `_ctype_` as a POINTER (load value, then deref),
//    exactly like bionic's `const char *_ctype_ = _C_ctype_;`. A bare
//    `const char _ctype_[]` array would be loaded-then-WRONGLY-dereferenced
//    (first 8 table bytes used as a pointer) -> crash. So we replicate bionic:
//    a 257-byte table (_C_ctype_) + a `_ctype_` POINTER to it. base[0] is the
//    EOF slot; base[c+1] is char c's class. The verbatim table below is the
//    OpenBSD/bionic _C_ctype_ (bionic/libc/upstream-openbsd/.../gen/ctype_.c);
//    bytes 0x80..0xFF are 0 (ASCII-only classification, as bionic ships).
//
//    `_ctype_` shows in `llvm-nm -D` as `D _ctype_` (GLOBAL OBJECT in .data).
// ---------------------------------------------------------------------------
#define _CT_U 0x01  /* upper */
#define _CT_L 0x02  /* lower */
#define _CT_N 0x04  /* digit */
#define _CT_S 0x08  /* space */
#define _CT_P 0x10  /* punct */
#define _CT_C 0x20  /* control */
#define _CT_X 0x40  /* hex digit */
#define _CT_B 0x80  /* blank (printable space) */

const char _C_ctype_[1 + 256] = {
    0,
    _CT_C, _CT_C, _CT_C, _CT_C, _CT_C, _CT_C, _CT_C, _CT_C,
    _CT_C, _CT_C|_CT_S, _CT_C|_CT_S, _CT_C|_CT_S, _CT_C|_CT_S, _CT_C|_CT_S, _CT_C, _CT_C,
    _CT_C, _CT_C, _CT_C, _CT_C, _CT_C, _CT_C, _CT_C, _CT_C,
    _CT_C, _CT_C, _CT_C, _CT_C, _CT_C, _CT_C, _CT_C, _CT_C,
    _CT_S|(char)_CT_B, _CT_P, _CT_P, _CT_P, _CT_P, _CT_P, _CT_P, _CT_P,
    _CT_P, _CT_P, _CT_P, _CT_P, _CT_P, _CT_P, _CT_P, _CT_P,
    _CT_N, _CT_N, _CT_N, _CT_N, _CT_N, _CT_N, _CT_N, _CT_N,
    _CT_N, _CT_N, _CT_P, _CT_P, _CT_P, _CT_P, _CT_P, _CT_P,
    _CT_P, _CT_U|_CT_X, _CT_U|_CT_X, _CT_U|_CT_X, _CT_U|_CT_X, _CT_U|_CT_X, _CT_U|_CT_X, _CT_U,
    _CT_U, _CT_U, _CT_U, _CT_U, _CT_U, _CT_U, _CT_U, _CT_U,
    _CT_U, _CT_U, _CT_U, _CT_U, _CT_U, _CT_U, _CT_U, _CT_U,
    _CT_U, _CT_U, _CT_U, _CT_P, _CT_P, _CT_P, _CT_P, _CT_P,
    _CT_P, _CT_L|_CT_X, _CT_L|_CT_X, _CT_L|_CT_X, _CT_L|_CT_X, _CT_L|_CT_X, _CT_L|_CT_X, _CT_L,
    _CT_L, _CT_L, _CT_L, _CT_L, _CT_L, _CT_L, _CT_L, _CT_L,
    _CT_L, _CT_L, _CT_L, _CT_L, _CT_L, _CT_L, _CT_L, _CT_L,
    _CT_L, _CT_L, _CT_L, _CT_P, _CT_P, _CT_P, _CT_P, _CT_C,
    0, 0, 0, 0, 0, 0, 0, 0,  /* 0x80 */
    0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0,  /* 0x90 */
    0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0,  /* 0xA0 */
    0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0,  /* 0xB0 */
    0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0,  /* 0xC0 */
    0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0,  /* 0xD0 */
    0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0,  /* 0xE0 */
    0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0,  /* 0xF0 */
    0, 0, 0, 0, 0, 0, 0, 0
};

// The exported symbol the consumer binds: a POINTER to the table base.
const char* _ctype_ = _C_ctype_;

// ---------------------------------------------------------------------------
// 6) __sF  (il2cpp, unity, c++_shared)  -- the fiddly one.
//
//    bionic <stdio.h> for NDK apps:  extern FILE __sF[];
//        #define stdin  (&__sF[0])
//        #define stdout (&__sF[1])
//        #define stderr (&__sF[2])
//    The consumer indexes this array with bionic's FROZEN sizeof(struct
//    __sFILE) == 152 bytes (LP64) and passes &__sF[k] straight into libc stdio
//    (fprintf/fwrite/...), which on OH are MUSL functions. So &__sF[k] must be
//    a usable *musl* FILE.
//
//    Impedance: musl's FILE (OHOS struct _IO_FILE) is 248 bytes > bionic's 152
//    stride, so the three slots necessarily overlap. We cannot change the
//    consumer's 152 stride (it's compiled in). Strategy:
//      - Back __sF with one buffer of 3*152 + tail padding (so a 248-byte musl
//        access on slot 2 at offset 304..552 stays in-bounds).
//      - At load time memcpy musl's live stdin/stdout/stderr FILE objects into
//        slots 0/1/2 (each 248 bytes). Copy order 0->1->2 means slot 2
//        (==stderr) lands last and is FULLY intact -> fprintf(stderr) works to
//        the byte. Slots 0/1 keep their first 152 bytes intact (flags, wpos,
//        wend, wbase, write fn, buf, buf_size, fd, lockcount) which is the
//        whole write path; only their control tail (mode/lock/lbf/locale, all
//        >=152) is overwritten by the next stream's leading bytes -- harmless
//        for output (those came from an adjacent static musl FILE: lock<0, etc).
//      - Force stdout/stderr slots unbuffered so writes flush straight to the
//        fd and never alias musl's own stdout buffer.
//
//    Net: the dlopen symbol gap is closed and stderr output is real. (Verified
//    by the self-test in wall3_build/sf_selftest.c on the OH/musl target.)
// ---------------------------------------------------------------------------
#define BIONIC_FILE_STRIDE 152u   // frozen bionic LP64 sizeof(struct __sFILE)
#define MUSL_FILE_SIZE     248u   // OHOS musl sizeof(struct _IO_FILE), LP64
#define SF_TAIL_PAD        256u   // headroom for the 248-byte access on slot 2

__attribute__((aligned(16)))
unsigned char __sF[BIONIC_FILE_STRIDE * 3u + SF_TAIL_PAD];

__attribute__((constructor))
static void __sF_init(void) {
    FILE* const musl_streams[3] = { stdin, stdout, stderr };
    for (unsigned k = 0; k < 3u; ++k) {
        unsigned char* slot = __sF + (size_t)k * BIONIC_FILE_STRIDE;
        memcpy(slot, (const void*)musl_streams[k], MUSL_FILE_SIZE);
    }
    // Make the two output slots unbuffered: guarantees fprintf/fwrite via
    // &__sF[1]/&__sF[2] emit immediately and never touch musl's own buffers.
    setvbuf((FILE*)(__sF + 1u * BIONIC_FILE_STRIDE), NULL, _IONBF, 0); // stdout
    setvbuf((FILE*)(__sF + 2u * BIONIC_FILE_STRIDE), NULL, _IONBF, 0); // stderr
}
