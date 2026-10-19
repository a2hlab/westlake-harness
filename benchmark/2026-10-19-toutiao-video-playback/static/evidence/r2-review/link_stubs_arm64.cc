// link_stubs_arm64.cc - Stub implementations for OHOS ARM64 target.
// Based on A15's link_stubs.cc but with ARM64 DexCache atomics (ldxp/stxp)
// instead of x86-64 cmpxchg16b, and static-build OpenNativeLibrary.
// Android 15 ART version.

#include <cstdint>
#include <cstdlib>
#include <cstdio>
#include <cstring>
#include <dlfcn.h>
#include <pthread.h>
#include <stdarg.h>
#include <jni.h>
#include <string>
#include <fcntl.h>
#include <unistd.h>
#include <cerrno>
#include <sys/mman.h>
#include <sys/stat.h>
#include "verified_app_library.h"

extern "C" {

// === liblog ===
// Minimal implementation that routes all log output to stderr.

struct __android_log_message {
    size_t struct_size;
    int32_t buffer_id;
    int32_t priority;
    const char* tag;
    const char* file;
    uint32_t line;
    const char* message;
};

typedef void (*__android_logger_function)(const struct __android_log_message* log_message);
typedef void (*__android_aborter_function)(const char* abort_message);

static __android_logger_function g_logger = nullptr;
static __android_aborter_function g_aborter = nullptr;
static int g_min_priority = 0;
static const char* g_default_tag = "dalvikvm";

static void default_stderr_logger(const struct __android_log_message* msg) {
    fprintf(stderr, "%s: %s\n", msg->tag ? msg->tag : g_default_tag, msg->message ? msg->message : "");
    fflush(stderr);
}

static void default_aborter(const char* msg) {
    fprintf(stderr, "ABORT: %s\n", msg);
    fflush(stderr);
    abort();
}

int __android_log_buf_print(int, int priority, const char* tag, const char* fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    fprintf(stderr, "%s: ", tag ? tag : g_default_tag);
    vfprintf(stderr, fmt, ap);
    fprintf(stderr, "\n");
    va_end(ap);
    fflush(stderr);
    return 0;
}
int __android_log_print(int priority, const char* tag, const char* fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    fprintf(stderr, "%s: ", tag ? tag : g_default_tag);
    vfprintf(stderr, fmt, ap);
    fprintf(stderr, "\n");
    va_end(ap);
    fflush(stderr);
    return 0;
}
int __android_log_is_loggable(int priority, const char*, int) { return priority >= g_min_priority; }
void __android_log_set_logger(__android_logger_function logger) { g_logger = logger; }
void __android_log_write_log_message(struct __android_log_message* msg) {
    if (g_logger) g_logger(msg); else default_stderr_logger(msg);
}
void __android_log_logd_logger(const struct __android_log_message* msg) { default_stderr_logger(msg); }
void __android_log_stderr_logger(const struct __android_log_message* msg) { default_stderr_logger(msg); }
void __android_log_set_aborter(__android_aborter_function aborter) { g_aborter = aborter; }
void __android_log_call_aborter(const char* msg) {
    if (g_aborter) g_aborter(msg); else default_aborter(msg);
}
void __android_log_default_aborter(const char* msg) { default_aborter(msg); }
int __android_log_set_minimum_priority(int p) { int old = g_min_priority; g_min_priority = p; return old; }
int __android_log_get_minimum_priority() { return g_min_priority; }
void __android_log_set_default_tag(const char* tag) { if (tag) g_default_tag = tag; }
int __android_log_write(int priority, const char* tag, const char* text) {
    fprintf(stderr, "%s: %s\n", tag ? tag : "art", text ? text : "");
    fflush(stderr);
    return 0;
}
void __android_log_assert(const char* cond, const char* tag, const char* fmt, ...) {
    va_list ap;
    if (fmt) {
        va_start(ap, fmt);
        fprintf(stderr, "%s: ASSERT FAILED (%s): ", tag ? tag : "art", cond ? cond : "");
        vfprintf(stderr, fmt, ap);
        fprintf(stderr, "\n");
        va_end(ap);
    } else {
        fprintf(stderr, "%s: ASSERT FAILED: %s\n", tag ? tag : "art", cond ? cond : "");
    }
    fflush(stderr);
    abort();
}

// === LZ4 ===
int LZ4_compressBound(int inputSize) { return inputSize + inputSize / 255 + 16; }
int LZ4_compress_default(const char* src, char* dst, int srcSize, int dstCapacity) {
    if (srcSize > dstCapacity) return 0;
    memcpy(dst, src, srcSize);
    return srcSize;
}
int LZ4_compress_HC(const char* src, char* dst, int srcSize, int dstCapacity, int) {
    return LZ4_compress_default(src, dst, srcSize, dstCapacity);
}
int LZ4_decompress_safe(const char* src, char* dst, int compressedSize, int dstCapacity) {
    if (compressedSize > dstCapacity) return -1;
    memcpy(dst, src, compressedSize);
    return compressedSize;
}

// === ART palette (expanded for Android 15) ===
int PaletteTraceEnabled(bool* enabled) { if (enabled) *enabled = false; return 0; }
int PaletteTraceBegin(const char*) { return 0; }
int PaletteTraceEnd() { return 0; }
int PaletteTraceIntegerValue(const char*, int) { return 0; }
int PaletteSchedGetPriority(int, int* p) { if (p) *p = 0; return 0; }
int PaletteSchedSetPriority(int, int) { return 0; }
int PaletteWriteCrashThreadStacks(const char* stacks, unsigned long length) {
    if (stacks == nullptr && length != 0) return 2;  // INVALID_ARGUMENT
    // OHOS does not run Android's tombstoned service. Preserve ART's SIGQUIT
    // contract by writing the completed dump to the process log captured by
    // AppSpawnX; this executes only after an explicit SIGQUIT request.
    if (length != 0 && fwrite(stacks, 1, length, stderr) != length) return 4;
    fflush(stderr);
    return 0;
}
int PaletteAshmemCreateRegion(const char*, unsigned long, int*) { return 4; /* NOT_SUPPORTED */ }
int PaletteAshmemSetProtRegion(int, int) { return 4; }
int PaletteCreateOdrefreshStagingDirectory(const char**) { return 4; }
int PaletteShouldReportDex2oatCompilation(bool* v) { if (v) *v = false; return 0; }
int PaletteNotifyStartDex2oatCompilation(int, int, int, int) { return 0; }
int PaletteNotifyEndDex2oatCompilation(int, int, int, int) { return 0; }
int PaletteNotifyDexFileLoaded(const char*) { return 0; }
int PaletteNotifyOatFileLoaded(const char*) { return 0; }
int PaletteShouldReportJniInvocations(bool* v) { if (v) *v = false; return 0; }
int PaletteNotifyBeginJniInvocation(void*) { return 0; }
int PaletteNotifyEndJniInvocation(void*) { return 0; }
int PaletteReportLockContention(void*, int, const char*, int, const char*, const char*, int, const char*, const char*, const char*) { return 0; }
int PaletteSetTaskProfiles(int, const char* const*, unsigned long) { return 4; }
int PaletteDebugStoreGetString(char* result, unsigned long max_size) {
    if (!result || max_size == 0) return 3; /* INVALID_ARGUMENT */
    result[0] = '\0';
    return 0;
}

// === Native bridge (not used in dalvikvm) ===
int InitializeNativeBridge(void*, const char*) { return 0; }
int LoadNativeBridge(const char*, void*) { return 0; }
int NativeBridgeInitialized() { return 0; }
int NativeBridgeGetVersion() { return 0; }
void* NativeBridgeGetTrampoline(void*, const char*, const char*, int) { return nullptr; }
void* NativeBridgeGetSignalHandler(int) { return nullptr; }
void PreInitializeNativeBridge(const char*, const char*) {}
void PreZygoteForkNativeBridge() {}
void UnloadNativeBridge() {}

// === Native loader (static build — NO dlopen on musl) ===
int InitializeNativeLoader() { return 0; }
int ResetNativeLoader() { return 0; }

// Legacy static-build class-library dispatch. The shared OH runtime uses the
// real dynamic loader below regardless of whether compatibility code remains
// enabled elsewhere in ART.
#if !defined(WESTLAKE_DYNAMIC_NATIVE_LOADER)
extern int JNI_OnLoad_icu(void* vm, void* reserved);
extern int JNI_OnLoad_javacore(void* vm, void* reserved);
extern int JNI_OnLoad_openjdk(void* vm, void* reserved);

static char g_fake_icu, g_fake_javacore, g_fake_openjdk, g_fake_ohbridge;
static void* g_saved_vm = nullptr;

void* OpenNativeLibrary(void* env, int target_sdk, const char* path, void* class_loader,
                        const char* caller_location, void* library_path,
                        bool* needs_native_bridge, char** error_msg) {
    if (needs_native_bridge) *needs_native_bridge = false;
    if (error_msg) *error_msg = NULL;

    // Get JavaVM from JNIEnv (index 219 in function table)
    if (env && !g_saved_vm) {
        typedef int (*GetJavaVM_fn)(void* env, void** vm);
        void** funcs = *(void***)env;
        GetJavaVM_fn getVM = (GetJavaVM_fn)funcs[219];
        if (getVM) getVM(env, &g_saved_vm);
    }

    // Static build: call JNI_OnLoad directly, return fake handle.
    // NO dlopen — it deadlocks on static musl.
    if (path && strstr(path, "libicu_jni")) {
        if (g_saved_vm) JNI_OnLoad_icu(g_saved_vm, NULL);
        return &g_fake_icu;
    }
    if (path && strstr(path, "libjavacore")) {
        if (g_saved_vm) JNI_OnLoad_javacore(g_saved_vm, NULL);
        return &g_fake_javacore;
    }
    if (path && strstr(path, "libopenjdk")) {
        if (g_saved_vm) JNI_OnLoad_openjdk(g_saved_vm, NULL);
        return &g_fake_openjdk;
    }
    extern int JNI_OnLoad_ohbridge(void*, void*) __attribute__((weak));
    if (path && strstr(path, "liboh_bridge")) {
        if (JNI_OnLoad_ohbridge && g_saved_vm) JNI_OnLoad_ohbridge(g_saved_vm, NULL);
        return &g_fake_ohbridge;
    }

    if (error_msg) *error_msg = strdup("Dynamic loading not supported (static build)");
    return NULL;
}
int CloseNativeLibrary(void*, void*, void*) { return 0; }
void NativeLoaderFreeErrorMessage(char*) {}
#else

/*
 * Generic OH native-loader boundary for Android-built DSOs that need an
 * isolated musl namespace.  Selection is launcher policy expressed as
 * basename lists; ART and the class library contain no package knowledge.
 * JavaVMExt still owns the SharedLibrary/ClassLoader association and JNI
 * symbol lookup around the handle returned here.
 */
typedef void (*WestlakeDlnsInitFn)(Dl_namespace*, const char*);
typedef int (*WestlakeDlnsGetFn)(const char*, Dl_namespace*);
typedef int (*WestlakeDlnsCreate2Fn)(Dl_namespace*, const char*, int);
typedef int (*WestlakeDlnsInheritFn)(Dl_namespace*, Dl_namespace*, const char*);
typedef void* (*WestlakeDlopenNsFn)(Dl_namespace*, const char*, int);

static pthread_mutex_t g_android_ns_mutex = PTHREAD_MUTEX_INITIALIZER;
static Dl_namespace g_android_ns;
static WestlakeDlopenNsFn g_dlopen_ns;
static int g_android_ns_state;
static void* g_android_ns_preload;

static bool BasenameInList(const char* path, const char* list) {
    if (path == nullptr || list == nullptr || list[0] == '\0') return false;
    const char* basename = strrchr(path, '/');
    basename = basename != nullptr ? basename + 1 : path;
    const size_t basename_length = strlen(basename);
    for (const char* item = list; *item != '\0';) {
        const char* end = strchr(item, ':');
        const size_t item_length = end != nullptr
                ? static_cast<size_t>(end - item) : strlen(item);
        if (item_length == basename_length &&
            memcmp(item, basename, basename_length) == 0) {
            return true;
        }
        if (end == nullptr) break;
        item = end + 1;
    }
    return false;
}

static void* OpenInAndroidNamespace(const char* path, bool use_anchor) {
    const char* search_path = getenv("WESTLAKE_ANDROID_NATIVE_SEARCH_PATH");
    const char* inherit_list = getenv("WESTLAKE_ANDROID_NATIVE_INHERIT");
    const char* open_path = use_anchor
            ? getenv("WESTLAKE_ANDROID_NATIVE_ANCHOR") : path;
    if (open_path == nullptr || open_path[0] == '\0' ||
        search_path == nullptr || search_path[0] == '\0') {
        return nullptr;
    }
    if (inherit_list == nullptr || inherit_list[0] == '\0') {
        inherit_list =
                "libc.so:libdl.so:libm.so:libz.so:libbionic_abi_shim.so";
    }

    pthread_mutex_lock(&g_android_ns_mutex);
    if (g_android_ns_state == 0) {
        auto init_fn = reinterpret_cast<WestlakeDlnsInitFn>(
                dlsym(RTLD_DEFAULT, "dlns_init"));
        auto get_fn = reinterpret_cast<WestlakeDlnsGetFn>(
                dlsym(RTLD_DEFAULT, "dlns_get"));
        auto create_fn = reinterpret_cast<WestlakeDlnsCreate2Fn>(
                dlsym(RTLD_DEFAULT, "dlns_create2"));
        auto inherit_fn = reinterpret_cast<WestlakeDlnsInheritFn>(
                dlsym(RTLD_DEFAULT, "dlns_inherit"));
        g_dlopen_ns = reinterpret_cast<WestlakeDlopenNsFn>(
                dlsym(RTLD_DEFAULT, "dlopen_ns"));

        Dl_namespace parent{};
        memset(&g_android_ns, 0, sizeof(g_android_ns));
        const int get_result = get_fn != nullptr ? get_fn(nullptr, &parent) : -1;
        if (init_fn == nullptr || create_fn == nullptr || inherit_fn == nullptr ||
            g_dlopen_ns == nullptr || get_result != 0) {
            g_android_ns_state = -1;
        } else {
            init_fn(&g_android_ns, "westlake_android_app");
            const int create_result = create_fn(&g_android_ns, search_path, 0);
            const int inherit_result = create_result == 0
                    ? inherit_fn(&g_android_ns, &parent, inherit_list) : -1;
            g_android_ns_state =
                    create_result == 0 && inherit_result == 0 ? 1 : -1;

            const char* preload = getenv("WESTLAKE_ANDROID_NATIVE_PRELOAD");
            if (g_android_ns_state == 1 && preload != nullptr &&
                preload[0] != '\0') {
                g_android_ns_preload = g_dlopen_ns(
                        &g_android_ns, preload, RTLD_NOW | RTLD_GLOBAL);
                if (g_android_ns_preload == nullptr) {
                    g_android_ns_state = -1;
                }
            }
        }
    }
    WestlakeDlopenNsFn open_fn = g_dlopen_ns;
    const bool ready = g_android_ns_state == 1;
    pthread_mutex_unlock(&g_android_ns_mutex);
    return ready && open_fn != nullptr
            ? open_fn(&g_android_ns, open_path, RTLD_NOW | RTLD_GLOBAL)
            : nullptr;
}

/*
 * bionic's soinfo::call_array() skips init/fini entries that are null or -1:
 *
 *     if (function == nullptr || reinterpret_cast<uintptr_t>(function) == -1) continue;
 *
 * musl's do_init_fini() has no such guard and calls every slot, so an Android
 * DSO that leaves a null in DT_INIT_ARRAY -- which several shipping obfuscators
 * do once their initialiser has run -- loads fine on Android and jumps to
 * address 0 here. Toutiao's libEncryptor.so has exactly one INIT_ARRAY entry and
 * it is null, so loading it killed the process in do_init_fini+444.
 *
 * Drop those slots before musl sees them, which reproduces bionic's behaviour
 * exactly: the entries bionic would have skipped are the entries removed. The
 * rewrite goes to an anonymous memfd, so the app's own file is never touched and
 * nothing is left behind on disk. Returns a /proc/self/fd path to dlopen, or an
 * empty string when the DSO needs no adjustment.
 */
static std::string SanitizeInitArray(const char* path) {
    if (path == nullptr || strchr(path, '/') == nullptr) return std::string();
    int fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) return std::string();
    struct stat info{};
    if (fstat(fd, &info) != 0 || info.st_size < 64 || info.st_size > (256 << 20)) {
        close(fd);
        return std::string();
    }
    std::string image(static_cast<size_t>(info.st_size), '\0');
    const bool read_ok = read(fd, &image[0], image.size()) == static_cast<ssize_t>(image.size());
    close(fd);
    if (!read_ok || memcmp(image.data(), "\177ELF\2\1", 6) != 0) return std::string();

    const auto word = [&image](size_t offset) -> uint64_t {
        uint64_t value = 0;
        if (offset + sizeof(value) > image.size()) return 0;
        memcpy(&value, image.data() + offset, sizeof(value));
        return value;
    };
    const auto half = [&image](size_t offset) -> uint16_t {
        uint16_t value = 0;
        if (offset + sizeof(value) > image.size()) return 0;
        memcpy(&value, image.data() + offset, sizeof(value));
        return value;
    };
    const uint64_t phoff = word(0x20);
    const uint16_t phentsize = half(0x36), phnum = half(0x38);
    if (phentsize < 56 || phnum == 0) return std::string();

    // Map a virtual address to its file offset through the PT_LOAD segments.
    const auto file_offset = [&](uint64_t vaddr, uint64_t* out) -> bool {
        for (uint16_t i = 0; i < phnum; ++i) {
            const size_t ph = static_cast<size_t>(phoff) + static_cast<size_t>(i) * phentsize;
            if ((word(ph) & 0xffffffffu) != 1 /* PT_LOAD */) continue;   // p_type is the low word
            const uint64_t offset = word(ph + 0x08), va = word(ph + 0x10), filesz = word(ph + 0x20);
            if (vaddr >= va && vaddr < va + filesz) { *out = offset + (vaddr - va); return true; }
        }
        return false;
    };

    uint64_t dynamic_offset = 0, dynamic_size = 0;
    for (uint16_t i = 0; i < phnum; ++i) {
        const size_t ph = static_cast<size_t>(phoff) + static_cast<size_t>(i) * phentsize;
        if ((word(ph) & 0xffffffffu) != 2 /* PT_DYNAMIC */) continue;
        dynamic_offset = word(ph + 0x08);
        dynamic_size = word(ph + 0x20);
        break;
    }
    if (dynamic_size == 0 || dynamic_offset + dynamic_size > image.size()) return std::string();

    uint64_t array_vaddr = 0, array_size = 0, array_size_entry = 0;
    uint64_t rela = 0, rela_size = 0, jmprel = 0, jmprel_size = 0, plt_type = 0;
    bool undecodable_relocs = false;
    for (uint64_t d = dynamic_offset; d + 16 <= dynamic_offset + dynamic_size; d += 16) {
        const uint64_t tag = word(d), value = word(d + 8);
        if (tag == 0 /* DT_NULL */) break;
        switch (tag) {
            case 25: array_vaddr = value; break;                       // DT_INIT_ARRAY
            case 27: array_size = value; array_size_entry = d + 8; break;  // DT_INIT_ARRAYSZ
            case 7:  rela = value; break;                              // DT_RELA
            case 8:  rela_size = value; break;                         // DT_RELASZ
            case 23: jmprel = value; break;                            // DT_JMPREL
            case 2:  jmprel_size = value; break;                       // DT_PLTRELSZ
            case 20: plt_type = value; break;                          // DT_PLTREL
            case 35: case 36:                                          // DT_RELR / DT_RELRSZ
            case 0x6000000d: case 0x6000000e:                          // DT_ANDROID_REL(SZ)
            case 0x6000000f: case 0x60000010:                          // DT_ANDROID_RELA(SZ)
                undecodable_relocs = true; break;
            default: break;
        }
    }
    // Relative and packed formats this code does not decode would make a slot look null
    // when it is in fact relocated at load time. Leave such a DSO exactly as it is.
    if (undecodable_relocs) return std::string();
    uint64_t array_offset = 0;
    if (array_vaddr == 0 || array_size < 8 || array_size % 8 != 0 ||
        !file_offset(array_vaddr, &array_offset) ||
        array_offset + array_size > image.size()) {
        return std::string();
    }

    /*
     * A slot that reads as zero in the file is usually NOT null at run time: lld emits the
     * link-time value plus an R_AARCH64_RELATIVE relocation, so the loader fills in
     * load_base + addend. Resolve each slot the way the loader will before deciding, or
     * this drops real constructors -- our own liboh_account_state.so stores 0 in the file
     * and is relocated to +0x1c0c. Only a slot with no relocation at all is really null,
     * which is the libEncryptor.so case.
     */
    const auto relocated_value = [&](uint64_t slot_vaddr, uint64_t stored) -> uint64_t {
        const uint64_t tables[2][2] = {{rela, rela_size},
                                       {plt_type == 7 ? jmprel : 0, jmprel_size}};
        for (const auto& table : tables) {
            if (table[0] == 0 || table[1] < 24) continue;
            uint64_t table_offset = 0;
            if (!file_offset(table[0], &table_offset)) continue;
            if (table_offset + table[1] > image.size()) continue;
            for (uint64_t r = 0; r + 24 <= table[1]; r += 24) {
                if (word(table_offset + r) != slot_vaddr) continue;
                const uint64_t type = word(table_offset + r + 8) & 0xffffffffu;
                // R_AARCH64_RELATIVE resolves to load_base + addend; any other relocation
                // means a symbol lands here, so treat the slot as live either way.
                return type == 1027 ? word(table_offset + r + 16) : 1;
            }
        }
        return stored;
    };

    // Keep the slots bionic would have called, in order.
    uint64_t kept = 0;
    for (uint64_t i = 0; i < array_size / 8; ++i) {
        const uint64_t slot = array_offset + i * 8;
        const uint64_t effective = relocated_value(array_vaddr + i * 8, word(slot));
        if (effective == 0 || effective == ~uint64_t(0)) continue;
        memcpy(&image[array_offset + kept * 8], image.data() + slot, 8);
        ++kept;
    }
    if (kept == array_size / 8) return std::string();   // nothing bionic would skip
    memset(&image[array_offset + kept * 8], 0, static_cast<size_t>(array_size - kept * 8));
    const uint64_t kept_bytes = kept * 8;
    memcpy(&image[array_size_entry], &kept_bytes, sizeof(kept_bytes));

    const uint64_t dropped = array_size / 8 - kept;

    /*
     * Where the rewritten image can live is constrained by SELinux: mapping
     * PROT_EXEC out of an anonymous memfd is denied to the app domain, so
     * dlopen("/proc/self/fd/N") comes back "Permission denied". Writing beside
     * the original instead inherits that directory's label, which is by
     * definition a place this process already loads libraries from. The file is
     * unlinked as soon as dlopen has mapped it, so nothing is left behind.
     */
    std::string sibling(path);
    const size_t slash = sibling.rfind('/');
    static int sequence;
    char suffix[64];
    snprintf(suffix, sizeof(suffix), ".westlake-init.%d.%d", (int)getpid(),
             __atomic_fetch_add(&sequence, 1, __ATOMIC_RELAXED));
    sibling.insert(slash + 1, ".");
    sibling += suffix;
    int out = open(sibling.c_str(), O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0600);
    if (out >= 0) {
        const bool written = write(out, image.data(), image.size()) ==
                             static_cast<ssize_t>(image.size());
        close(out);
        if (written) {
            fprintf(stderr, "[SOURCE-NATIVE-INITARRAY] %s: dropped %llu null init entr%s "
                    "(bionic skips them)\n", path, (unsigned long long)dropped,
                    dropped == 1 ? "y" : "ies");
            fflush(stderr);
            return sibling;
        }
        unlink(sibling.c_str());
    }

    // No writable sibling (read-only staging, say). memfd still works wherever
    // the domain is allowed to execute from it.
    const int memory = memfd_create(path + slash + 1, MFD_CLOEXEC);
    if (memory < 0) return std::string();
    if (write(memory, image.data(), image.size()) != static_cast<ssize_t>(image.size())) {
        close(memory);
        return std::string();
    }
    char resolved[64];
    snprintf(resolved, sizeof(resolved), "/proc/self/fd/%d", memory);
    fprintf(stderr, "[SOURCE-NATIVE-INITARRAY] %s: dropped %llu null init entr%s via memfd\n",
            path, (unsigned long long)dropped, dropped == 1 ? "y" : "ies");
    fflush(stderr);
    return std::string(resolved);   // fd deliberately stays open; dlopen needs it
}

void* OpenNativeLibrary(void* raw_env, int, const char* path, void*, const char*, void* raw_library_path,
                        bool* needs_native_bridge, char** error_msg) {
    if (needs_native_bridge != nullptr) *needs_native_bridge = false;
    if (error_msg != nullptr) *error_msg = nullptr;
    if (getenv("WESTLAKE_TRACE_NATIVE_LOADER")) {
        auto* env = static_cast<JNIEnv*>(raw_env);
        auto library_path = static_cast<jstring>(raw_library_path);
        const char* search = library_path ? env->GetStringUTFChars(library_path, nullptr) : nullptr;
        fprintf(stderr, "[SOURCE-NATIVE-LOADER] path=%s class_paths=%s\n",
                path ? path : "<null>", search ? search : "<none>");
        void* errno_symbol = dlsym(RTLD_DEFAULT, "__errno");
        Dl_info errno_provider{};
        bool errno_known = errno_symbol && dladdr(errno_symbol, &errno_provider);
        fprintf(stderr, "[SOURCE-NATIVE-ABI] errno=%p provider=%s\n", errno_symbol,
                errno_known ? errno_provider.dli_fname : "<none>");
        if (search && path && !strchr(path, '/')) {
            for (const char* first = search; *first;) {
                const char* end = strchr(first, ':');
                std::string directory(first, end ? size_t(end - first) : strlen(first));
                if (!directory.empty() && directory[0] == '/' && directory.find('!') == std::string::npos) {
                    std::string candidate = directory + "/" + path;
                    int fd = open(candidate.c_str(), O_RDONLY | O_CLOEXEC);
                    int error = fd < 0 ? errno : 0;
                    if (fd >= 0) close(fd);
                    fprintf(stderr, "[SOURCE-NATIVE-CANDIDATE] path=%s open_errno=%d\n", candidate.c_str(), error);
                }
                if (!end) break;
                first = end + 1;
            }
        }
        if (search) env->ReleaseStringUTFChars(library_path, search);
        if (env->ExceptionCheck()) return nullptr;
    }
    dlerror();
    const bool use_anchor = BasenameInList(
            path, getenv("WESTLAKE_ANDROID_NATIVE_ANCHOR_TARGET"));
    const bool use_namespace = use_anchor || BasenameInList(
            path, getenv("WESTLAKE_ANDROID_NATIVE_TARGETS"));
    // Android DSOs may carry init slots bionic skips; hand musl a copy without
    // them rather than let it jump to a null function pointer.
    const std::string adjusted = SanitizeInitArray(path);
    const char* open_path = adjusted.empty() ? path : adjusted.c_str();
    void* handle = use_namespace
            ? OpenInAndroidNamespace(open_path, use_anchor)
            : dlopen(open_path, RTLD_NOW | RTLD_LOCAL);
    // Preserve the first error before cleanup/JNI calls can overwrite dlerror.
    const char* raw_error = handle == nullptr ? dlerror() : nullptr;
    std::string load_error = raw_error ? raw_error : "dlopen failed";
    if (!adjusted.empty() && adjusted.compare(0, 6, "/proc/") != 0) unlink(adjusted.c_str());
    // OH may deny executable mappings of an app-private data copy. Reuse only
    // an identical image already supplied in this ClassLoader's APK library
    // directory. This neither changes its bytes nor relaxes mapping policy.
    if (handle == nullptr && path != nullptr &&
        load_error.find("failed to map library") != std::string::npos &&
        load_error.find("errno=13") != std::string::npos) {
        auto* env = static_cast<JNIEnv*>(raw_env);
        auto library_path = static_cast<jstring>(raw_library_path);
        const char* search = library_path ? env->GetStringUTFChars(library_path, nullptr) : nullptr;
        std::string digest;
        std::string packaged = westlake_app_library::FindPackagedCopy(path, search, &digest);
        if (search) env->ReleaseStringUTFChars(library_path, search);
        if (!env->ExceptionCheck() && !packaged.empty()) {
            fprintf(stderr, "[SOURCE-NATIVE-IDENTICAL-COPY] from=%s to=%s sha256=%s\n",
                    path, packaged.c_str(), digest.c_str());
            const char* retry_path = packaged.c_str();
            dlerror();
            handle = use_namespace ? OpenInAndroidNamespace(retry_path, use_anchor)
                                   : dlopen(retry_path, RTLD_NOW | RTLD_LOCAL);
            const char* retry_error = handle == nullptr ? dlerror() : nullptr;
            if (retry_error) load_error = retry_error;

        }
    }
    if (handle == nullptr && error_msg != nullptr) {
        fprintf(stderr, "[SOURCE-NATIVE-LOAD-FAIL] path=%s namespace=%d error=%s\n",
                path ? path : "<null>", use_namespace, load_error.c_str());
        *error_msg = strdup(load_error.c_str());
    }
    return handle;
}
int CloseNativeLibrary(void* handle, void*, void*) {
    return handle == nullptr ? 0 : dlclose(handle);
}
void NativeLoaderFreeErrorMessage(char* message) { free(message); }
#endif

// === LZMA ===
void Lzma2EncProps_Init(void*) {}
void Lzma2EncProps_Normalize(void*) {}
int Xz_Encode(void*, void*, void*, void*) { return -1; }
void XzProps_Init(void*) {}
void XzUnpacker_Construct(void*, void*) {}
void XzUnpacker_Free(void*) {}
int XzUnpacker_Code(void*, void*, void*, void*, void*, int, void*) { return -1; }
int XzUnpacker_IsStreamWasFinished(void*) { return 1; }
void CrcGenerateTable() {}
void Crc64GenerateTable() {}

// === SHA1 ===
void SHA1_Init(void*) {}
void SHA1_Update(void* ctx, const void* data, unsigned long len) {}
void SHA1_Final(unsigned char* md, void* ctx) { if (md) memset(md, 0, 20); }

// === Remaining stub entrypoints ===
#define STUB_ENTRYPOINT(name) void name() { fprintf(stderr, "FATAL: stub entrypoint " #name " called\n"); abort(); }

// Interpreter stubs (mterp/nterp not in ARM64 quick_entrypoints)
STUB_ENTRYPOINT(ExecuteMterpImpl)

// artMterpAsmInstructionStart/End must be spaced exactly 256*128 = 32768 bytes apart
__attribute__((aligned(128))) char artMterpAsmInstructionStart[32768] = {};
char artMterpAsmInstructionEnd[1] = {};

// art_quick_invoke_stub_internal is ARM32-only
STUB_ENTRYPOINT(art_quick_invoke_stub_internal)

// A15 JNI lock/unlock entry points (not in A11 assembly)
void art_jni_lock_object(void*) {}
void art_jni_lock_object_no_inline(void*) {}
void art_jni_unlock_object(void*) {}
void art_jni_unlock_object_no_inline(void*) {}

// A15 JNI entry point stubs
void art_jni_monitored_method_start(void*) {}
void art_jni_monitored_method_end(void*) {}
void art_jni_method_start(void*) {}
void art_jni_method_end(void*) {}
void art_jni_method_entry_hook(void*) {}
void art_jni_read_barrier(void*) {}

// A15-only art_quick_* entry points not in A11 assembly
STUB_ENTRYPOINT(art_quick_invoke_polymorphic_with_hidden_receiver)

// NativeBridge stub (A15)
void* NativeBridgeGetTrampoline2(void*, const char*, const char*, uint32_t) { return nullptr; }

// OHBridge JNI_OnLoad stub used only by the legacy static runtime.
#if !defined(WESTLAKE_CLEAN_RUNTIME)
extern int JNI_OnLoad_ohbridge_real(void* vm, void* reserved) __attribute__((weak));
int JNI_OnLoad_ohbridge(void* vm, void* reserved) {
    if (JNI_OnLoad_ohbridge_real) {
        return JNI_OnLoad_ohbridge_real(vm, reserved);
    }
    fprintf(stderr, "[STUB] JNI_OnLoad_ohbridge called (fallback no-op)\n");
    fflush(stderr);
    return 0x00010006;  // JNI_VERSION_1_6
}
#endif

}  // extern "C"

// === C++ stubs in art namespace ===
#include <ostream>
#include <vector>

// === Nterp C++ stubs ===
namespace art {
template <typename T> class ArrayRef {
  const T* data_ = nullptr;
  size_t size_ = 0;
public:
  ArrayRef() = default;
  ArrayRef(const T* d, size_t s) : data_(d), size_(s) {}
};
namespace interpreter {
bool IsNterpSupported() { return false; }
const void* GetNterpEntryPoint() { return nullptr; }
const void* GetNterpWithClinitEntryPoint() { return nullptr; }
bool CanRuntimeUseNterp() { return false; }
ArrayRef<const uint8_t> NterpWithClinitImpl() { return ArrayRef<const uint8_t>(); }
ArrayRef<const uint8_t> NterpImpl() { return ArrayRef<const uint8_t>(); }
void CheckNterpAsmConstants() {}
}  // namespace interpreter
}  // namespace art

// === BacktraceMap ===
class BacktraceMap {
public:
    static BacktraceMap* Create(int, bool);
};
BacktraceMap* BacktraceMap::Create(int, bool) { return nullptr; }

namespace art {

// DumpNativeStack - needs libbacktrace/libunwindstack
class ArtMethod;
void DumpNativeStack(std::ostream&, int, BacktraceMap*, const char*, ArtMethod*, void*, bool) {}
// Android 15 version uses unwindstack::AndroidLocalUnwinder instead of BacktraceMap
}  // namespace art (temporarily close)
namespace unwindstack { class AndroidLocalUnwinder; }
namespace art {
void DumpNativeStack(std::ostream&, ::unwindstack::AndroidLocalUnwinder&, int, const char*, ArtMethod*, void*, bool) {}
// A15 simplified overload (no unwinder parameter)
void DumpNativeStack(std::ostream&, int, const char*, ArtMethod*, void*, bool) {}

// BacktraceCollector
class BacktraceCollector {
public:
    void Collect();
};
void BacktraceCollector::Collect() {}

// SafeCopy
size_t SafeCopy(void* dst, const void* src, size_t len) {
    memcpy(dst, src, len);
    return len;
}

// hprof
namespace hprof {
    void DumpHeap(const char*, int, bool) {}
}

}  // namespace art

// =============================================================================
// === operator<< stubs for ART enums ===
// =============================================================================

#include <atomic>

namespace art {

// Forward declarations for enum types
enum class InstructionSet;
enum class InvokeType : uint32_t;
enum class LayoutType : uint8_t;
enum class ClassStatus : uint8_t;
enum class ThreadState : uint16_t;
enum class JdwpProvider;
enum class OatClassType : uint8_t;
enum class SuspendReason : uint32_t;
enum class IndirectRefKind;
enum class ReflectionSourceType;
enum VRegKind : int;
enum RootType : int;
enum class JniIdType;
enum class CompilationKind;  // New in A15

std::ostream& operator<<(std::ostream& os, InstructionSet rhs) {
  return os << "InstructionSet(" << static_cast<int>(rhs) << ")";
}
std::ostream& operator<<(std::ostream& os, InvokeType rhs) {
  return os << "InvokeType(" << static_cast<int>(rhs) << ")";
}
std::ostream& operator<<(std::ostream& os, LayoutType rhs) {
  return os << "LayoutType(" << static_cast<int>(rhs) << ")";
}
std::ostream& operator<<(std::ostream& os, ClassStatus rhs) {
  return os << "ClassStatus(" << static_cast<int>(rhs) << ")";
}
std::ostream& operator<<(std::ostream& os, ThreadState rhs) {
  return os << "ThreadState(" << static_cast<int>(rhs) << ")";
}
std::ostream& operator<<(std::ostream& os, JdwpProvider rhs) {
  return os << "JdwpProvider(" << static_cast<int>(rhs) << ")";
}
std::ostream& operator<<(std::ostream& os, OatClassType rhs) {
  return os << "OatClassType(" << static_cast<int>(rhs) << ")";
}
std::ostream& operator<<(std::ostream& os, SuspendReason rhs) {
  return os << "SuspendReason(" << static_cast<int>(rhs) << ")";
}
std::ostream& operator<<(std::ostream& os, IndirectRefKind rhs) {
  return os << "IndirectRefKind(" << static_cast<int>(rhs) << ")";
}
std::ostream& operator<<(std::ostream& os, ReflectionSourceType rhs) {
  return os << "ReflectionSourceType(" << static_cast<int>(rhs) << ")";
}
std::ostream& operator<<(std::ostream& os, VRegKind rhs) {
  return os << "VRegKind(" << static_cast<int>(rhs) << ")";
}
std::ostream& operator<<(std::ostream& os, RootType rhs) {
  return os << "RootType(" << static_cast<int>(rhs) << ")";
}
std::ostream& operator<<(std::ostream& os, JniIdType rhs) {
  return os << "JniIdType(" << static_cast<int>(rhs) << ")";
}
std::ostream& operator<<(std::ostream& os, CompilationKind rhs) {
  return os << "CompilationKind(" << static_cast<int>(rhs) << ")";
}

// MethodCompilationStat - in compiler/optimizing
enum class MethodCompilationStat;
std::ostream& operator<<(std::ostream& os, MethodCompilationStat rhs) {
  return os << "MethodCompilationStat(" << static_cast<int>(rhs) << ")";
}

// WriteBarrierKind - new in Android 15
enum class WriteBarrierKind;
std::ostream& operator<<(std::ostream& os, WriteBarrierKind rhs) {
  return os << "WriteBarrierKind(" << static_cast<int>(rhs) << ")";
}

// MemBarrierKind
enum class MemBarrierKind;
std::ostream& operator<<(std::ostream& os, MemBarrierKind rhs) {
  return os << "MemBarrierKind(" << static_cast<int>(rhs) << ")";
}

// MethodLoadKind
enum class MethodLoadKind;
std::ostream& operator<<(std::ostream& os, MethodLoadKind rhs) {
  return os << "MethodLoadKind(" << static_cast<int>(rhs) << ")";
}

// HLoadClass::LoadKind
class HLoadClass {
public:
  enum class LoadKind;
};
std::ostream& operator<<(std::ostream& os, HLoadClass::LoadKind rhs) {
  return os << "LoadKind(" << static_cast<int>(rhs) << ")";
}

// LockLevel
enum class LockLevel;
std::ostream& operator<<(std::ostream& os, LockLevel rhs) {
  return os << "LockLevel(" << static_cast<int>(rhs) << ")";
}

// GraphAnalysisResult
enum class GraphAnalysisResult;
std::ostream& operator<<(std::ostream& os, GraphAnalysisResult rhs) {
  return os << "GraphAnalysisResult(" << static_cast<int>(rhs) << ")";
}

// HLoadString::LoadKind
class HLoadString {
public:
  enum class LoadKind;
};
std::ostream& operator<<(std::ostream& os, HLoadString::LoadKind rhs) {
  return os << "LoadKind(" << static_cast<int>(rhs) << ")";
}

// --- ImageHeader nested enums ---
class ImageHeader {
public:
  enum ImageMethod : int;
  enum ImageSections : int;
  enum StorageMode : int;
};
std::ostream& operator<<(std::ostream& os, ImageHeader::ImageMethod rhs) {
  return os << "ImageMethod(" << static_cast<int>(rhs) << ")";
}
std::ostream& operator<<(std::ostream& os, ImageHeader::ImageSections rhs) {
  return os << "ImageSections(" << static_cast<int>(rhs) << ")";
}
std::ostream& operator<<(std::ostream& os, ImageHeader::StorageMode rhs) {
  return os << "StorageMode(" << static_cast<int>(rhs) << ")";
}

// --- EncodedArrayValueIterator nested enum ---
class EncodedArrayValueIterator {
public:
  enum class ValueType : uint8_t;
};
std::ostream& operator<<(std::ostream& os, EncodedArrayValueIterator::ValueType rhs) {
  return os << "ValueType(" << static_cast<int>(rhs) << ")";
}

// --- DexLayoutSections nested enum ---
class DexLayoutSections {
public:
  enum class SectionType : uint8_t;
};
std::ostream& operator<<(std::ostream& os, DexLayoutSections::SectionType rhs) {
  return os << "SectionType(" << static_cast<int>(rhs) << ")";
}

// --- Location nested enums ---
class Location {
public:
  enum class Kind : uint8_t;
  enum class Policy : uint8_t;
};
std::ostream& operator<<(std::ostream& os, Location::Kind rhs) {
  return os << "Location::Kind(" << static_cast<int>(rhs) << ")";
}
std::ostream& operator<<(std::ostream& os, Location::Policy rhs) {
  return os << "Location::Policy(" << static_cast<int>(rhs) << ")";
}

// --- LockWord nested enum ---
class LockWord {
public:
  enum LockState : int;
};
std::ostream& operator<<(std::ostream& os, LockWord::LockState rhs) {
  return os << "LockState(" << static_cast<int>(rhs) << ")";
}

}  // namespace art

// --- art::gc:: namespace enums ---
namespace art {
namespace gc {

enum class AllocatorType;
enum class CollectorType;
enum class WeakRootState;

std::ostream& operator<<(std::ostream& os, AllocatorType rhs) {
  return os << "AllocatorType(" << static_cast<int>(rhs) << ")";
}
std::ostream& operator<<(std::ostream& os, CollectorType rhs) {
  return os << "CollectorType(" << static_cast<int>(rhs) << ")";
}
std::ostream& operator<<(std::ostream& os, WeakRootState rhs) {
  return os << "WeakRootState(" << static_cast<int>(rhs) << ")";
}

namespace space {

enum class GcRetentionPolicy;
enum class SpaceType;

std::ostream& operator<<(std::ostream& os, GcRetentionPolicy rhs) {
  return os << "GcRetentionPolicy(" << static_cast<int>(rhs) << ")";
}
std::ostream& operator<<(std::ostream& os, SpaceType rhs) {
  return os << "SpaceType(" << static_cast<int>(rhs) << ")";
}

class RegionSpace {
public:
  enum class RegionType : uint8_t;
  enum class RegionState : uint8_t;
};
std::ostream& operator<<(std::ostream& os, RegionSpace::RegionType rhs) {
  return os << "RegionType(" << static_cast<int>(rhs) << ")";
}
std::ostream& operator<<(std::ostream& os, RegionSpace::RegionState rhs) {
  return os << "RegionState(" << static_cast<int>(rhs) << ")";
}

}  // namespace space

namespace allocator {

class RosAlloc {
public:
  enum PageMapKind : uint8_t;
};
std::ostream& operator<<(std::ostream& os, RosAlloc::PageMapKind rhs) {
  return os << "PageMapKind(" << static_cast<int>(rhs) << ")";
}

}  // namespace allocator

namespace collector {

enum GcType : int;
std::ostream& operator<<(std::ostream& os, GcType rhs) {
  return os << "GcType(" << static_cast<int>(rhs) << ")";
}

}  // namespace collector

}  // namespace gc
}  // namespace art

// --- art::instrumentation:: ---
namespace art {
namespace instrumentation {

class Instrumentation {
public:
  enum InstrumentationEvent : uint32_t;
  enum class InstrumentationLevel;
};
std::ostream& operator<<(std::ostream& os, Instrumentation::InstrumentationEvent rhs) {
  return os << "InstrumentationEvent(0x" << std::hex << static_cast<unsigned>(rhs) << std::dec << ")";
}
std::ostream& operator<<(std::ostream& os, Instrumentation::InstrumentationLevel rhs) {
  return os << "InstrumentationLevel(" << static_cast<int>(rhs) << ")";
}

}  // namespace instrumentation
}  // namespace art

// --- art::linker:: ---
namespace art {
namespace linker {

class LinkerPatch {
public:
  enum class Type : uint8_t;
};
std::ostream& operator<<(std::ostream& os, LinkerPatch::Type rhs) {
  return os << "LinkerPatch::Type(" << static_cast<int>(rhs) << ")";
}

}  // namespace linker
}  // namespace art

// --- art::verifier:: ---
namespace art {
namespace verifier {

enum class MethodType : uint32_t;
enum class VerifyError : uint32_t;

std::ostream& operator<<(std::ostream& os, MethodType rhs) {
  return os << "MethodType(" << static_cast<int>(rhs) << ")";
}
std::ostream& operator<<(std::ostream& os, VerifyError rhs) {
  return os << "VerifyError(0x" << std::hex << static_cast<unsigned>(rhs) << std::dec << ")";
}

}  // namespace verifier
}  // namespace art

// =============================================================================
// === DexCache 128-bit atomic operations — ARM64 version ===
// Uses ldxp/stxp (load/store exclusive pair) instead of x86-64 cmpxchg16b.
// =============================================================================

namespace art {
namespace mirror {

class DexCache {
public:
  template <typename IntType>
  struct __attribute__((packed)) ConversionPair {
    IntType first;
    IntType second;
  };
  using ConversionPair64 = ConversionPair<uint64_t>;

  static ConversionPair64 AtomicLoadRelaxed16B(std::atomic<ConversionPair64>* target);
  static void AtomicStoreRelease16B(std::atomic<ConversionPair64>* target, ConversionPair64 value);
};

DexCache::ConversionPair64 DexCache::AtomicLoadRelaxed16B(
    std::atomic<ConversionPair64>* target) {
  // ARM64: use ldxp (load exclusive pair) for atomic 128-bit load.
  uint64_t lo, hi;
  unsigned int tmp;
  __asm__ __volatile__(
      "1: ldxp %[lo], %[hi], [%[ptr]]\n\t"
      "   stxp %w[tmp], %[lo], %[hi], [%[ptr]]\n\t"
      "   cbnz %w[tmp], 1b\n\t"
      : [lo] "=&r"(lo), [hi] "=&r"(hi), [tmp] "=&r"(tmp)
      : [ptr] "r"(target)
      : "memory");
  ConversionPair64 result;
  result.first = lo;
  result.second = hi;
  return result;
}

void DexCache::AtomicStoreRelease16B(
    std::atomic<ConversionPair64>* target, ConversionPair64 value) {
  // ARM64: use ldxp/stlxp (store-release exclusive pair) for atomic 128-bit store.
  uint64_t new_lo = value.first;
  uint64_t new_hi = value.second;
  uint64_t old_lo, old_hi;
  unsigned int tmp;
  __asm__ __volatile__(
      "1: ldxp %[old_lo], %[old_hi], [%[ptr]]\n\t"
      "   stlxp %w[tmp], %[new_lo], %[new_hi], [%[ptr]]\n\t"
      "   cbnz %w[tmp], 1b\n\t"
      : [old_lo] "=&r"(old_lo), [old_hi] "=&r"(old_hi), [tmp] "=&r"(tmp)
      : [ptr] "r"(target), [new_lo] "r"(new_lo), [new_hi] "r"(new_hi)
      : "memory");
}

}  // namespace mirror
}  // namespace art
