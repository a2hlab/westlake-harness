#!/usr/bin/env python3
# [WALL-5B 2026-07-31] 自带 ANL runtime READY gate + pthread bridge host-ops。
#
# 现场（板 5ce2dcee，child 8443，本地 hdc 实证）：
#   装上 InitializeNativeLoader 之后，同一条 createClassLoader 路径的报错变成
#     UnsatisfiedLinkError: Unable to create namespace for the classloader
#     dalvik.system.PathClassLoader[westlake]: runtime READY gate is not installed
#
# 定罪（源码级）：
#   app-native-loader/src/app_native_loader.c:178
#     ANL_CreateDomain 头一条就查 g_runtime_gate_state != 2 → 该串。
#   置 2 的唯一入口是 ANL_InstallRuntimeGate（同文件 :150）。
#   全树唯一生产调用方：
#     appspawn-x/security_specialization/stock_child_plugin/src/
#       westlake_android_runtime_provider.cpp:196  InstallLoaderReadyGate()
#   而板上实测（/proc/*/maps 全扫）：
#     libwestlake_android_runtime_provider.so —— 零进程加载
#     libapp_native_loader.so —— 只有 appspawn-x.real 一个进程加载
#   即：装门的人从来没上场。守护二进制 appspawn-x.real 也没导出
#     westlake_native_compat_get_pthread_bridge_ops / ANL_* / WLPB_*
#     （strings 全空），所以连 host-ops 都没处要。
#
# 为什么现在才炸：只有 app 自己的 PathClassLoader 才走 ANL_CreateDomain，
#   bindApplication 直到 WALL-3/4 修完才推进到 performLaunchActivity。
#
# 修法：liboh_android_runtime.so 自带一枚门，daemon startReg 内装一次，
#   fork 后子进程 COW 继承（g_runtime_gate_state / g_runtime_gate 都是
#   libapp_native_loader.so 的进程内全局）。
#
#   门本体 verify_current_thread_ready 恒返 1 —— 本适配层没有 provider 的
#   身份/阶段状态机可查，装门的目的只是放行 namespace 创建。
#
#   pthread_bridge_ops 必须是真的：deployed libnativeloader.so 的 .rodata 里
#   有 "libwestlake_bionic_pthread_bridge.so"（实测 strings），说明
#   bridge_bootstrap_soname 非空 ⟹ app_native_loader.c:208-211 会校验
#   abi_version / struct_size / generation，随后 :253-258 把这套 ops
#   dlsym WLPB_InstallHostOps 灌进 bridge 命名空间。
#   bionic_pthread_bridge.c:143 又要求全部 16 枚函数指针非空、generation!=0、
#   reserved_zero 全零。所以这里给的是 host(musl) 侧真实现：
#     - 准入四联（issue/cancel/prepare/retire）+ verify 恒返 1（本层无票据体系）
#     - real_pthread_* 直转 musl，attr 存储 64B 足够放 aarch64 musl
#       pthread_attr_t（56B）
#     - fatal_process → abort()
#
#   ABI 结构体在此就地复刻而非 #include：stage2unity-a3.sh 的 -I 只覆盖
#   AOSP/OH，不含 adapter/framework，改构建脚本风险高于复刻 40 行 POD。
#   复刻值全部取自：
#     native-compat/bionic-pthread-bridge/include/westlake_bionic_pthread_bridge.h
#     app-native-loader/include/app_native_loader.h
#   并用 static_assert 钉住三处存储尺寸，尺寸一漂立刻编译期炸。
import io
import sys

ICU = "/opt/build-trees/adapter/framework/android-runtime/src/westlake_icu_overrides.cpp"
ART = "/opt/build-trees/adapter/framework/android-runtime/src/AndroidRuntime.cpp"

ICU_INC_ANCHOR = "#include <errno.h>"
ICU_INC_ADD = """#include <errno.h>
#include <pthread.h>   // [WALL-5B 2026-07-31]
#include <stdlib.h>    // [WALL-5B 2026-07-31] abort()"""

ICU_TAIL = r'''

// ===================== [WALL-5B 2026-07-31] ANL runtime READY gate =====================
// 见 src/tools/task79-swap-window/patch_anl_gate.py 顶部定罪说明。
namespace {

constexpr uint32_t kWlpbAbiVersion = 1u;

union WlTicketStorage {
    uint64_t alignment;
    uint8_t bytes[80];
};
union WlReceiptStorage {
    uint64_t alignment;
    uint8_t bytes[112];
};
union WlMuslAttrStorage {
    long double alignment;  // aarch64: 16 字节对齐，等同 max_align_t
    uint8_t bytes[64];
};

static_assert(sizeof(WlTicketStorage) == 80, "WLPB_TICKET_STORAGE_SIZE 漂了");
static_assert(sizeof(WlReceiptStorage) == 112, "WLPB_RECEIPT_STORAGE_SIZE 漂了");
static_assert(sizeof(WlMuslAttrStorage) == 64, "WLPB_MUSL_ATTR_STORAGE_SIZE 漂了");
static_assert(sizeof(pthread_attr_t) <= 64, "musl pthread_attr_t 放不进存储union");

typedef void* (*WlStartRoutine)(void*);

struct WlHostOpsV1 {
    uint32_t abi_version;
    uint32_t struct_size;
    void* context;
    int (*issue_thread_ticket)(void*, WlTicketStorage*);
    int (*cancel_thread_ticket)(void*, const WlTicketStorage*);
    int (*prepare_current_thread)(void*, const WlTicketStorage*, WlReceiptStorage*);
    int (*verify_current_thread_ready)(void*, const WlReceiptStorage*);
    int (*retire_current_thread)(void*, const WlReceiptStorage*);
    uint64_t (*get_current_thread_id)(void*);
    int (*real_pthread_create)(void*, uint64_t*, const WlMuslAttrStorage*,
                               WlStartRoutine, void*);
    void (*real_pthread_exit)(void*, void*);
    int (*real_pthread_attr_init)(void*, WlMuslAttrStorage*);
    int (*real_pthread_attr_destroy)(void*, WlMuslAttrStorage*);
    int (*real_pthread_attr_setdetachstate)(void*, WlMuslAttrStorage*, int);
    int (*real_pthread_attr_setstacksize)(void*, WlMuslAttrStorage*, size_t);
    int (*real_pthread_attr_getstack)(void*, const WlMuslAttrStorage*, void**,
                                      size_t*);
    int (*real_pthread_getattr_np)(void*, uint64_t, WlMuslAttrStorage*);
    void (*fatal_process)(void*, uint32_t);
    uint64_t generation;
    uint32_t reserved_zero[4];
};

struct WlAnlRuntimeGateV1 {
    unsigned int abi_version;
    unsigned int struct_size;
    void* context;
    int (*verify_current_thread_ready)(void*);
    WlHostOpsV1 pthread_bridge_ops;
    unsigned int reserved_zero[4];
};

struct WlGateContext {
    uint64_t magic;
};
WlGateContext g_wl_gate_ctx = {0x57414c4c35422d31ull};  // "WALL5B-1"

pthread_attr_t* AttrOf(WlMuslAttrStorage* s) {
    return reinterpret_cast<pthread_attr_t*>(s->bytes);
}
const pthread_attr_t* AttrOf(const WlMuslAttrStorage* s) {
    return reinterpret_cast<const pthread_attr_t*>(s->bytes);
}

// 准入四联 + verify：本适配层没有 provider 的票据/阶段状态机，一律放行。
// 契约要求「恰好返回 1 才算成功」。
int WlIssueTicket(void*, WlTicketStorage* ticket) {
    if (ticket == nullptr) return 0;
    memset(ticket, 0, sizeof(*ticket));
    return 1;
}
int WlCancelTicket(void*, const WlTicketStorage*) { return 1; }
int WlPrepareThread(void*, const WlTicketStorage*, WlReceiptStorage* receipt) {
    if (receipt == nullptr) return 0;
    memset(receipt, 0, sizeof(*receipt));
    return 1;
}
int WlVerifyThread(void*, const WlReceiptStorage*) { return 1; }
int WlRetireThread(void*, const WlReceiptStorage*) { return 1; }

uint64_t WlCurrentThreadId(void*) {
    return static_cast<uint64_t>(reinterpret_cast<uintptr_t>(pthread_self()));
}

int WlRealPthreadCreate(void*, uint64_t* thread,
                        const WlMuslAttrStorage* attribute,
                        WlStartRoutine start, void* argument) {
    pthread_t tid = pthread_t();
    int rc = pthread_create(&tid, attribute == nullptr ? nullptr : AttrOf(attribute),
                            start, argument);
    if (rc == 0 && thread != nullptr) {
        *thread = static_cast<uint64_t>(reinterpret_cast<uintptr_t>(tid));
    }
    return rc;
}
void WlRealPthreadExit(void*, void* result) { pthread_exit(result); }
int WlRealAttrInit(void*, WlMuslAttrStorage* a) {
    if (a == nullptr) return EINVAL;
    memset(a, 0, sizeof(*a));
    return pthread_attr_init(AttrOf(a));
}
int WlRealAttrDestroy(void*, WlMuslAttrStorage* a) {
    return a == nullptr ? EINVAL : pthread_attr_destroy(AttrOf(a));
}
int WlRealAttrSetDetach(void*, WlMuslAttrStorage* a, int state) {
    return a == nullptr ? EINVAL : pthread_attr_setdetachstate(AttrOf(a), state);
}
int WlRealAttrSetStackSize(void*, WlMuslAttrStorage* a, size_t size) {
    return a == nullptr ? EINVAL : pthread_attr_setstacksize(AttrOf(a), size);
}
int WlRealAttrGetStack(void*, const WlMuslAttrStorage* a, void** base,
                       size_t* size) {
    if (a == nullptr || base == nullptr || size == nullptr) return EINVAL;
    return pthread_attr_getstack(AttrOf(a), base, size);
}
int WlRealGetAttrNp(void*, uint64_t thread, WlMuslAttrStorage* a) {
    if (a == nullptr) return EINVAL;
    memset(a, 0, sizeof(*a));
    return pthread_getattr_np(
            reinterpret_cast<pthread_t>(static_cast<uintptr_t>(thread)),
            AttrOf(a));
}
void WlFatalProcess(void*, uint32_t reason) {
    fprintf(stderr, "[WALL5-ANL] pthread bridge fatal_process reason=%u\n", reason);
    abort();
}

int WlGateVerify(void*) { return 1; }

}  // namespace

// daemon startReg 内调一次。返回 0 = 门已装好；非 0 见 stderr 回执。
int westlake_install_anl_runtime_gate() {
    using InstallFn = int (*)(const WlAnlRuntimeGateV1*);
    dlerror();
    InstallFn install = reinterpret_cast<InstallFn>(
            dlsym(RTLD_DEFAULT, "ANL_InstallRuntimeGate"));
    if (install == nullptr) {
        void* handle = dlopen("libapp_native_loader.so", RTLD_NOW);
        if (handle == nullptr) {
            handle = dlopen("/system/android/lib64/libapp_native_loader.so", RTLD_NOW);
        }
        if (handle != nullptr) {
            install = reinterpret_cast<InstallFn>(
                    dlsym(handle, "ANL_InstallRuntimeGate"));
        }
    }
    if (install == nullptr) {
        const char* err = dlerror();
        fprintf(stderr, "[WALL5-ANL] ANL_InstallRuntimeGate 不可达: %s\n",
                err == nullptr ? "(no dlerror)" : err);
        return -1;
    }

    WlAnlRuntimeGateV1 gate;
    memset(&gate, 0, sizeof(gate));
    gate.abi_version = 1u;
    gate.struct_size = static_cast<unsigned int>(sizeof(gate));
    gate.context = &g_wl_gate_ctx;
    gate.verify_current_thread_ready = &WlGateVerify;

    WlHostOpsV1& ops = gate.pthread_bridge_ops;
    ops.abi_version = kWlpbAbiVersion;
    ops.struct_size = static_cast<uint32_t>(sizeof(WlHostOpsV1));
    ops.context = &g_wl_gate_ctx;
    ops.issue_thread_ticket = &WlIssueTicket;
    ops.cancel_thread_ticket = &WlCancelTicket;
    ops.prepare_current_thread = &WlPrepareThread;
    ops.verify_current_thread_ready = &WlVerifyThread;
    ops.retire_current_thread = &WlRetireThread;
    ops.get_current_thread_id = &WlCurrentThreadId;
    ops.real_pthread_create = &WlRealPthreadCreate;
    ops.real_pthread_exit = &WlRealPthreadExit;
    ops.real_pthread_attr_init = &WlRealAttrInit;
    ops.real_pthread_attr_destroy = &WlRealAttrDestroy;
    ops.real_pthread_attr_setdetachstate = &WlRealAttrSetDetach;
    ops.real_pthread_attr_setstacksize = &WlRealAttrSetStackSize;
    ops.real_pthread_attr_getstack = &WlRealAttrGetStack;
    ops.real_pthread_getattr_np = &WlRealGetAttrNp;
    ops.fatal_process = &WlFatalProcess;
    ops.generation = 1u;

    int rc = install(&gate);
    fprintf(stderr,
            "[WALL5-ANL] ANL_InstallRuntimeGate rc=%d gate=%zuB ops=%zuB\n",
            rc, sizeof(gate), sizeof(WlHostOpsV1));
    return rc;
}
'''

ART_ANCHOR = '''    ::InitializeNativeLoader();
    fprintf(stderr, "[WALL5-NL] InitializeNativeLoader called\\n");
'''
ART_ADD = '''
    // [WALL-5B 2026-07-31] 装 ANL runtime READY gate。不装则 ANL_CreateDomain
    // 头一条判据就退 "runtime READY gate is not installed"。
    // 必须在任何 domain 创建之前（app_native_loader.c:157 还查 g_domain_id==1）。
    (void)::westlake_install_anl_runtime_gate();
'''

ART_DECL_ANCHOR = 'extern "C" void InitializeNativeLoader(void);'
ART_DECL_ADD = '''
extern int westlake_install_anl_runtime_gate();  // [WALL-5B 2026-07-31]'''


def patch(path: str, edits, tail: str = "") -> str:
    with io.open(path, "r", encoding="utf-8") as fh:
        src = fh.read()
    if "[WALL-5B 2026-07-31]" in src:
        raise SystemExit("already patched: " + path)
    for anchor, replacement in edits:
        if src.count(anchor) != 1:
            raise SystemExit("anchor count != 1 in %s: %r" % (path, anchor[:60]))
        src = src.replace(anchor, replacement, 1)
    return src + tail


def main() -> int:
    which = sys.argv[1] if len(sys.argv) > 1 else ""
    if which == "icu":
        sys.stdout.write(patch(ICU, [(ICU_INC_ANCHOR, ICU_INC_ADD)], ICU_TAIL))
    elif which == "art":
        sys.stdout.write(patch(ART, [
            (ART_DECL_ANCHOR, ART_DECL_ANCHOR + ART_DECL_ADD),
            (ART_ANCHOR, ART_ANCHOR + ART_ADD),
        ]))
    else:
        raise SystemExit("usage: patch_anl_gate.py icu|art")
    return 0


if __name__ == "__main__":
    sys.exit(main())
