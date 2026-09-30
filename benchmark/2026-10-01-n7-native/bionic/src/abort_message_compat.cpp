// AOSP-compatible process abort-message mapping for the Bionic/Musl boundary.
//
// This keeps the Android memory layout and first-message-wins semantics so
// crash tooling can locate the message by its 128-bit magic.  The storage is
// adapter-owned Musl memory; no Bionic or C++ object crosses the boundary.

#include <pthread.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <sys/mman.h>

#if defined(__linux__) || defined(__OHOS__)
#include <sys/prctl.h>
#endif

struct AbortMessage {
    size_t size;
    char message[0];
};

struct MagicAbortMessage {
    uint64_t magic1;
    uint64_t magic2;
    AbortMessage abort_message;
};

static_assert(offsetof(AbortMessage, message) == sizeof(size_t),
              "abort-message layout changed");
static_assert(offsetof(MagicAbortMessage, abort_message) == 2 * sizeof(uint64_t),
              "abort-message magic layout changed");

static pthread_mutex_t g_abort_message_lock = PTHREAD_MUTEX_INITIALIZER;
static AbortMessage* g_abort_message;

static void FillAbortMessageMagic(MagicAbortMessage* mapping)
{
    mapping->magic1 = UINT64_C(0xb18e40886ac388f0);
    mapping->magic2 = UINT64_C(0xc6dfba755a1de0b5);
}

extern "C" void android_set_abort_message(const char* message)
{
    if (pthread_mutex_lock(&g_abort_message_lock) != 0) return;

    if (__atomic_load_n(&g_abort_message, __ATOMIC_ACQUIRE) != nullptr) {
        (void)pthread_mutex_unlock(&g_abort_message_lock);
        return;
    }

    if (message == nullptr) message = "(null)";
    const size_t length = strlen(message);
    if (length > SIZE_MAX - sizeof(MagicAbortMessage) - 1) {
        (void)pthread_mutex_unlock(&g_abort_message_lock);
        return;
    }

    const size_t size = sizeof(MagicAbortMessage) + length + 1;
    void* memory = mmap(nullptr, size, PROT_READ | PROT_WRITE,
                        MAP_ANON | MAP_PRIVATE, -1, 0);
    if (memory == MAP_FAILED) {
        (void)pthread_mutex_unlock(&g_abort_message_lock);
        return;
    }

#if defined(PR_SET_VMA) && defined(PR_SET_VMA_ANON_NAME)
    // Naming is diagnostic only; unsupported kernels still retain the exact
    // magic/layout contract used by Android crash tooling.
    (void)prctl(PR_SET_VMA, PR_SET_VMA_ANON_NAME, memory, size,
                "abort message");
#endif

    auto* mapping = static_cast<MagicAbortMessage*>(memory);
    FillAbortMessageMagic(mapping);
    mapping->abort_message.size = size;
    memcpy(mapping->abort_message.message, message, length + 1);
    __atomic_store_n(&g_abort_message, &mapping->abort_message,
                     __ATOMIC_RELEASE);
    (void)pthread_mutex_unlock(&g_abort_message_lock);
}

extern "C" const char* android_get_abort_message(void)
{
    AbortMessage* current = __atomic_load_n(&g_abort_message, __ATOMIC_ACQUIRE);
    return current == nullptr ? nullptr : current->message;
}

