#define _GNU_SOURCE

#include "westlake_thread_template_publisher.h"

#include <elf.h>
#include <link.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <sys/auxv.h>
#include <sys/mman.h>
#include <unistd.h>

#define WLTP_CONTRACT_MAGIC UINT32_C(0x574c5450)

#if defined(WLTP_MUTANT_WRONG_OFFSET)
#define WLTP_CONTRACT_PUBLISH_OFFSET UINT16_C(16)
#else
#define WLTP_CONTRACT_PUBLISH_OFFSET UINT16_C(24)
#endif

#if defined(WLTP_MUTANT_WRONG_IMAGE)
#define WLTP_CONTRACT_LOCATOR WLTP_CURRENT_THREAD_IMAGE_LOCATOR
#else
#define WLTP_CONTRACT_LOCATOR WLTP_MAIN_IMAGE_LOCATOR_AT_PHDR
#endif

#if defined(WLTP_MUTANT_UNPATCHED)
#define WLTP_CONTRACT_PATCH UINT8_C(0)
#else
#define WLTP_CONTRACT_PATCH UINT8_C(1)
#endif

#if defined(WLTP_MUTANT_NO_RESTORE)
#define WLTP_CONTRACT_RESTORE UINT8_C(0)
#else
#define WLTP_CONTRACT_RESTORE UINT8_C(1)
#endif

#if defined(WLTP_MUTANT_COMPETING_WRITER)
#define WLTP_CONTRACT_PUBLISHER_COUNT UINT8_C(2)
#elif defined(WLTP_MUTANT_NO_EXACT_ONCE)
#define WLTP_CONTRACT_PUBLISHER_COUNT UINT8_C(2)
#else
#define WLTP_CONTRACT_PUBLISHER_COUNT UINT8_C(1)
#endif

#if defined(WLTP_MUTANT_SKIP_CHILD_RESET)
#define WLTP_CONTRACT_CHILD_RESET UINT8_C(0)
#else
#define WLTP_CONTRACT_CHILD_RESET UINT8_C(1)
#endif

#if defined(WLTP_MUTANT_REUSE_PARENT_TEMPLATE)
#define WLTP_CONTRACT_CLEAR_INHERITED UINT8_C(0)
#else
#define WLTP_CONTRACT_CLEAR_INHERITED UINT8_C(1)
#endif

#if defined(WLTP_MUTANT_IGNORE_EPOCH_MODE)
#define WLTP_CONTRACT_EXPLICIT_MODE UINT8_C(0)
#else
#define WLTP_CONTRACT_EXPLICIT_MODE UINT8_C(1)
#endif

#if defined(WLTP_MUTANT_ALLOW_GENERATION_DRIFT)
#define WLTP_CONTRACT_SAME_GENERATION UINT8_C(0)
#else
#define WLTP_CONTRACT_SAME_GENERATION UINT8_C(1)
#endif

#if defined(WLTP_MUTANT_NO_FULL_IMAGE_COMPARE)
#define WLTP_CONTRACT_FULL_IMAGE UINT8_C(0)
#else
#define WLTP_CONTRACT_FULL_IMAGE UINT8_C(1)
#endif

_Static_assert(sizeof(WltpPublisherContractV1) == 24U,
               "WLTP publisher contract ABI drift");

WLTP_HIDDEN __attribute__((used, section(".rodata.wltp_contract")))
const WltpPublisherContractV1 wltp_publisher_contract_v1 = {
    .magic = WLTP_CONTRACT_MAGIC,
    .version = WLTP_ABI_VERSION,
    .reservation_size = WLTP_RESERVATION_SIZE,
    .publish_offset = WLTP_CONTRACT_PUBLISH_OFFSET,
    .guard_size = WLTP_GUARD_SIZE,
    .main_image_locator = WLTP_CONTRACT_LOCATOR,
    .template_patch = WLTP_CONTRACT_PATCH,
    .restore_protection = WLTP_CONTRACT_RESTORE,
    .requires_relro = UINT8_C(1),
    .publisher_count = WLTP_CONTRACT_PUBLISHER_COUNT,
    .explicit_epoch_mode = WLTP_CONTRACT_EXPLICIT_MODE,
    .child_reset_enabled = WLTP_CONTRACT_CHILD_RESET,
    .clear_inherited_template = WLTP_CONTRACT_CLEAR_INHERITED,
    .same_adapter_generation = WLTP_CONTRACT_SAME_GENERATION,
    .full_image_compare = WLTP_CONTRACT_FULL_IMAGE,
    .reserved_zero = {UINT8_C(0), UINT8_C(0)},
};

enum WltpPublishState {
    WLTP_STATE_COLD = 0,
    WLTP_STATE_PUBLISHING = 1,
    WLTP_STATE_PUBLISHED = 2,
    WLTP_STATE_FAILED = 3,
    WLTP_STATE_RESETTING = 4,
};

/* Process-global and deliberately non-TLS; fork gives each child a COW copy. */
static _Atomic uint32_t g_publish_state = WLTP_STATE_COLD;
static _Atomic uint64_t g_owner_pid;
static _Atomic uint64_t g_reset_process_epoch;
static _Atomic uint64_t g_adapter_generation;

typedef struct WltpMainImage {
    uintptr_t expected_phdr;
    uint8_t *bytes;
    uintptr_t protect_begin;
    size_t protect_length;
    uint32_t match_count;
    bool valid;
} WltpMainImage;

static bool WltpRange(uintptr_t begin, size_t size, uintptr_t *end)
{
    if (end == NULL || size > UINTPTR_MAX - begin) return false;
    *end = begin + size;
    return true;
}

static bool WltpContains(uintptr_t outer_begin, uintptr_t outer_end,
                         uintptr_t inner_begin, uintptr_t inner_end)
{
    return outer_begin <= inner_begin && inner_begin < inner_end &&
           inner_end <= outer_end;
}

static bool WltpPageRange(uintptr_t begin, uintptr_t end,
                          uintptr_t page_size, uintptr_t *page_begin,
                          uintptr_t *page_end)
{
    if (begin >= end || page_begin == NULL || page_end == NULL ||
        page_size == (uintptr_t)0 ||
        (page_size & (page_size - (uintptr_t)1)) != (uintptr_t)0 ||
        end > UINTPTR_MAX - page_size + (uintptr_t)1) {
        return false;
    }
    *page_begin = begin & ~(page_size - (uintptr_t)1);
    *page_end =
        (end + page_size - (uintptr_t)1) & ~(page_size - (uintptr_t)1);
    return *page_begin < *page_end;
}

static int WltpFindMainImage(struct dl_phdr_info *info, size_t size,
                             void *opaque)
{
    (void)size;
    WltpMainImage *result = (WltpMainImage *)opaque;
    if ((uintptr_t)info->dlpi_phdr != result->expected_phdr) return 0;
    ++result->match_count;

    const ElfW(Phdr) *program_headers = NULL;
    const ElfW(Phdr) *interpreter = NULL;
    const ElfW(Phdr) *tls = NULL;
    const ElfW(Phdr) *load = NULL;
    const ElfW(Phdr) *relro = NULL;
    for (ElfW(Half) index = 0; index < info->dlpi_phnum; ++index) {
        const ElfW(Phdr) *header = &info->dlpi_phdr[index];
        if (header->p_type == PT_PHDR) program_headers = header;
        if (header->p_type == PT_INTERP) interpreter = header;
        if (header->p_type == PT_TLS) tls = header;
        if (header->p_type == PT_GNU_RELRO) relro = header;
    }
    if (program_headers == NULL || interpreter == NULL || tls == NULL ||
        relro == NULL ||
        (uintptr_t)info->dlpi_addr + program_headers->p_vaddr !=
            result->expected_phdr ||
        tls->p_filesz != WLTP_RESERVATION_SIZE ||
        tls->p_memsz != WLTP_RESERVATION_SIZE ||
        tls->p_align != UINT32_C(16) || tls->p_flags != PF_R) {
        return 0;
    }

    const uintptr_t image_begin =
        (uintptr_t)info->dlpi_addr + (uintptr_t)tls->p_vaddr;
    uintptr_t image_end = (uintptr_t)0;
    if (!WltpRange(image_begin, WLTP_RESERVATION_SIZE, &image_end)) return 0;
    for (ElfW(Half) index = 0; index < info->dlpi_phnum; ++index) {
        const ElfW(Phdr) *header = &info->dlpi_phdr[index];
        if (header->p_type != PT_LOAD) continue;
        const uintptr_t load_begin =
            (uintptr_t)info->dlpi_addr + (uintptr_t)header->p_vaddr;
        uintptr_t load_end = (uintptr_t)0;
        if (WltpRange(load_begin, (size_t)header->p_filesz, &load_end) &&
            WltpContains(load_begin, load_end, image_begin, image_end)) {
            load = header;
            break;
        }
    }
    if (load == NULL ||
        (load->p_flags & (PF_R | PF_W | PF_X)) != (PF_R | PF_W)) {
        return 0;
    }

    const long page_size_value = sysconf(_SC_PAGESIZE);
    if (page_size_value <= 0) return 0;
    const uintptr_t page_size = (uintptr_t)page_size_value;
    uintptr_t protect_begin = (uintptr_t)0;
    uintptr_t protect_end = (uintptr_t)0;
    if (!WltpPageRange(image_begin, image_end, page_size,
                       &protect_begin, &protect_end)) {
        return 0;
    }

    const uintptr_t relro_begin =
        (uintptr_t)info->dlpi_addr + (uintptr_t)relro->p_vaddr;
    uintptr_t relro_end = (uintptr_t)0;
    uintptr_t relro_page_begin = (uintptr_t)0;
    uintptr_t relro_page_end = (uintptr_t)0;
    if (!WltpRange(relro_begin, (size_t)relro->p_memsz, &relro_end) ||
        !WltpPageRange(relro_begin, relro_end, page_size,
                       &relro_page_begin, &relro_page_end) ||
        !WltpContains(relro_page_begin, relro_page_end,
                      protect_begin, protect_end)) {
        return 0;
    }

    result->bytes = (uint8_t *)image_begin;
    result->protect_begin = protect_begin;
    result->protect_length = (size_t)(protect_end - protect_begin);
    result->valid = true;
    return 0;
}

static bool WltpTemplateUnowned(const uint8_t *image,
                                const uint8_t *current)
{
#if defined(WLTP_MUTANT_NO_FULL_IMAGE_COMPARE)
    (void)current;
    uint64_t image_guard = UINT64_C(0);
    memcpy(&image_guard, image + WLTP_GUARD_RELATIVE_OFFSET,
           sizeof(image_guard));
    return image_guard == UINT64_C(0);
#else
    for (size_t index = 0; index < WLTP_RESERVATION_SIZE; ++index) {
        const bool is_guard =
            index >= WLTP_GUARD_RELATIVE_OFFSET &&
            index < WLTP_GUARD_RELATIVE_OFFSET + WLTP_GUARD_SIZE;
        if ((is_guard && image[index] != UINT8_C(0)) ||
            (!is_guard && image[index] != current[index])) {
            return false;
        }
    }
    return true;
#endif
}

static bool WltpResolveMainImage(WltpMainImage *image)
{
    memset(image, 0, sizeof(*image));
    image->expected_phdr = (uintptr_t)getauxval(AT_PHDR);
    return image->expected_phdr != (uintptr_t)0 &&
           dl_iterate_phdr(WltpFindMainImage, image) == 0 &&
           image->match_count == UINT32_C(1) && image->valid &&
           image->bytes != NULL;
}

static uint64_t WltpReadGuard(const uint8_t *reservation)
{
    uint64_t guard = UINT64_C(0);
    memcpy(&guard, reservation + WLTP_GUARD_RELATIVE_OFFSET,
           sizeof(guard));
    return guard;
}

static int WltpRewriteTemplateGuard(
    WltpMainImage *image, uint64_t value)
{
    if (mprotect((void *)image->protect_begin, image->protect_length,
                 PROT_READ | PROT_WRITE) != 0) {
        return -1;
    }
    memcpy(image->bytes + WLTP_GUARD_RELATIVE_OFFSET,
           &value, sizeof(value));
    atomic_thread_fence(memory_order_release);
    if (mprotect((void *)image->protect_begin, image->protect_length,
                 PROT_READ) != 0) {
        return -1;
    }
    return WltpReadGuard(image->bytes) == value ? 0 : -1;
}

static bool WltpTemplateMatchesClearedGuard(
    const uint8_t *image, const uint8_t *current)
{
    for (size_t index = 0; index < WLTP_RESERVATION_SIZE; ++index) {
        const bool is_guard =
            index >= WLTP_GUARD_RELATIVE_OFFSET &&
            index < WLTP_GUARD_RELATIVE_OFFSET + WLTP_GUARD_SIZE;
        if ((is_guard && image[index] != UINT8_C(0)) ||
            (!is_guard && image[index] != current[index])) {
            return false;
        }
    }
    return true;
}

WLTP_HIDDEN int WLTP_BeginProcessEpoch(
    const WltpProcessEpochSeedV1 *seed,
    const uint8_t *current_reservation)
{
    if (seed == NULL || current_reservation == NULL ||
        seed->abi_version != WLTP_ABI_VERSION ||
        seed->struct_size != sizeof(*seed) ||
        seed->reserved_zero != UINT32_C(0) ||
        seed->adapter_generation == UINT64_C(0) ||
        seed->process_epoch == UINT64_C(0) ||
        (seed->mode != WLTP_PROCESS_EPOCH_PARENT_BOOTSTRAP &&
         seed->mode != WLTP_PROCESS_EPOCH_AFTER_FORK_CHILD)) {
        return WLTP_PROCESS_EPOCH_INVALID_ARGUMENT;
    }
    const pid_t pid_value = getpid();
    if (pid_value <= 0) return WLTP_PROCESS_EPOCH_INVALID_ARGUMENT;
    const uint64_t pid = (uint64_t)(uint32_t)pid_value;
#if defined(WLTP_MUTANT_IGNORE_EPOCH_MODE)
    const WltpProcessEpochMode mode =
        WLTP_PROCESS_EPOCH_PARENT_BOOTSTRAP;
#else
    const WltpProcessEpochMode mode = seed->mode;
#endif
    const uint32_t required_state =
        mode == WLTP_PROCESS_EPOCH_PARENT_BOOTSTRAP ?
            WLTP_STATE_COLD : WLTP_STATE_PUBLISHED;
    uint32_t expected = required_state;
    if (!atomic_compare_exchange_strong_explicit(
            &g_publish_state, &expected, WLTP_STATE_RESETTING,
            memory_order_acq_rel, memory_order_acquire)) {
        return WLTP_PROCESS_EPOCH_STATE_MISMATCH;
    }

    WltpMainImage image;
    if (!WltpResolveMainImage(&image)) {
        atomic_store_explicit(&g_publish_state, WLTP_STATE_FAILED,
                              memory_order_release);
        return WLTP_PROCESS_EPOCH_MAIN_TLS_NOT_EXACT;
    }
    const uint64_t current_guard = WltpReadGuard(current_reservation);
    const uint64_t template_guard = WltpReadGuard(image.bytes);
    const uint64_t inherited_pid = atomic_load_explicit(
        &g_owner_pid, memory_order_acquire);
    const uint64_t inherited_epoch = atomic_load_explicit(
        &g_reset_process_epoch, memory_order_acquire);
    const uint64_t inherited_generation = atomic_load_explicit(
        &g_adapter_generation, memory_order_acquire);

    if (mode == WLTP_PROCESS_EPOCH_PARENT_BOOTSTRAP) {
        if (inherited_pid != UINT64_C(0) ||
            inherited_epoch != UINT64_C(0) ||
            inherited_generation != UINT64_C(0) ||
            current_guard != UINT64_C(0) ||
            template_guard != UINT64_C(0) ||
            memcmp(image.bytes, current_reservation,
                   WLTP_RESERVATION_SIZE) != 0) {
            atomic_store_explicit(&g_publish_state, WLTP_STATE_FAILED,
                                  memory_order_release);
            return WLTP_PROCESS_EPOCH_INHERITED_IMAGE_MISMATCH;
        }
    } else {
        if (inherited_pid == UINT64_C(0) || inherited_pid == pid ||
            inherited_epoch == UINT64_C(0) ||
            inherited_epoch == seed->process_epoch ||
            inherited_generation == UINT64_C(0) ||
            current_guard == UINT64_C(0) ||
            template_guard != current_guard) {
            atomic_store_explicit(&g_publish_state, WLTP_STATE_FAILED,
                                  memory_order_release);
            return WLTP_PROCESS_EPOCH_STATE_MISMATCH;
        }
#if !defined(WLTP_MUTANT_ALLOW_GENERATION_DRIFT)
        if (inherited_generation != seed->adapter_generation) {
            atomic_store_explicit(&g_publish_state, WLTP_STATE_FAILED,
                                  memory_order_release);
            return WLTP_PROCESS_EPOCH_GENERATION_MISMATCH;
        }
#endif
#if !defined(WLTP_MUTANT_NO_FULL_IMAGE_COMPARE)
        if (memcmp(image.bytes, current_reservation,
                   WLTP_RESERVATION_SIZE) != 0) {
            atomic_store_explicit(&g_publish_state, WLTP_STATE_FAILED,
                                  memory_order_release);
            return WLTP_PROCESS_EPOCH_INHERITED_IMAGE_MISMATCH;
        }
#endif
#if defined(WLTP_MUTANT_SKIP_CHILD_RESET) || \
    defined(WLTP_MUTANT_REUSE_PARENT_TEMPLATE)
        const uint64_t reset_guard = template_guard;
#else
        const uint64_t reset_guard = UINT64_C(0);
#endif
        if (WltpRewriteTemplateGuard(&image, reset_guard) != 0 ||
            !WltpTemplateMatchesClearedGuard(
                image.bytes, current_reservation)) {
            atomic_store_explicit(&g_publish_state, WLTP_STATE_FAILED,
                                  memory_order_release);
            return WLTP_PROCESS_EPOCH_PROTECTION_FAILED;
        }
    }

    atomic_store_explicit(&g_owner_pid, pid, memory_order_release);
    atomic_store_explicit(&g_reset_process_epoch, seed->process_epoch,
                          memory_order_release);
    atomic_store_explicit(&g_adapter_generation, seed->adapter_generation,
                          memory_order_release);
    atomic_store_explicit(&g_publish_state, WLTP_STATE_COLD,
                          memory_order_release);
    return WLTP_PROCESS_EPOCH_OK;
}

WLTP_HIDDEN int WLTP_PublishMainThreadTemplate(
    const uint8_t *current_reservation)
{
    if (current_reservation == NULL) return WLTP_PUBLISH_INVALID_ARGUMENT;
    const pid_t pid_value = getpid();
    if (pid_value <= 0) return WLTP_PUBLISH_INVALID_ARGUMENT;
    const uint64_t pid = (uint64_t)(uint32_t)pid_value;
    if (atomic_load_explicit(&g_owner_pid, memory_order_acquire) != pid ||
        atomic_load_explicit(&g_reset_process_epoch,
                             memory_order_acquire) == UINT64_C(0)) {
        return WLTP_PUBLISH_INVALID_ARGUMENT;
    }
#if !defined(WLTP_MUTANT_NO_EXACT_ONCE)
    uint32_t expected_state = WLTP_STATE_COLD;
    if (!atomic_compare_exchange_strong_explicit(
            &g_publish_state, &expected_state, WLTP_STATE_PUBLISHING,
            memory_order_acq_rel, memory_order_acquire)) {
        return WLTP_PUBLISH_ALREADY_PUBLISHED;
    }
#endif
    uint64_t guard = WltpReadGuard(current_reservation);
    if (guard == UINT64_C(0)) {
        atomic_store_explicit(&g_publish_state, WLTP_STATE_FAILED,
                              memory_order_release);
        return WLTP_PUBLISH_INVALID_ARGUMENT;
    }

    WltpMainImage image;
    if (!WltpResolveMainImage(&image) ||
        !WltpTemplateUnowned(image.bytes, current_reservation)) {
#if defined(WLTP_MUTANT_REUSE_PARENT_TEMPLATE)
        if (image.bytes != NULL && WltpReadGuard(image.bytes) != UINT64_C(0)) {
            atomic_store_explicit(&g_publish_state, WLTP_STATE_PUBLISHED,
                                  memory_order_release);
            return WLTP_PUBLISH_OK;
        }
#endif
        const int result = image.bytes == NULL ?
            WLTP_PUBLISH_MAIN_TLS_NOT_EXACT : WLTP_PUBLISH_COMPETING_OWNER;
        atomic_store_explicit(&g_publish_state, WLTP_STATE_FAILED,
                              memory_order_release);
        return result;
    }

#if defined(WLTP_MUTANT_WRONG_IMAGE)
    const long page_size_value = sysconf(_SC_PAGESIZE);
    uintptr_t current_end = (uintptr_t)0;
    uintptr_t current_page_end = (uintptr_t)0;
    if (page_size_value <= 0 ||
        !WltpRange((uintptr_t)current_reservation, WLTP_RESERVATION_SIZE,
                   &current_end) ||
        !WltpPageRange((uintptr_t)current_reservation, current_end,
                       (uintptr_t)page_size_value, &image.protect_begin,
                       &current_page_end)) {
        atomic_store_explicit(&g_publish_state, WLTP_STATE_FAILED,
                              memory_order_release);
        return WLTP_PUBLISH_PROTECTION_FAILED;
    }
    image.bytes = (uint8_t *)(uintptr_t)current_reservation;
    image.protect_length = (size_t)(current_page_end - image.protect_begin);
#endif

    if (mprotect((void *)image.protect_begin, image.protect_length,
                 PROT_READ | PROT_WRITE) != 0) {
        atomic_store_explicit(&g_publish_state, WLTP_STATE_FAILED,
                              memory_order_release);
        return WLTP_PUBLISH_PROTECTION_FAILED;
    }

#if !defined(WLTP_MUTANT_UNPATCHED)
#if defined(WLTP_MUTANT_WRONG_OFFSET)
    const size_t publish_offset = UINT32_C(16);
#else
    const size_t publish_offset = WLTP_GUARD_RELATIVE_OFFSET;
#endif
    memcpy(image.bytes + publish_offset, &guard, sizeof(guard));
#if defined(WLTP_MUTANT_COMPETING_WRITER)
    const uint64_t competing_guard = ~guard;
    memcpy(image.bytes + WLTP_GUARD_RELATIVE_OFFSET,
           &competing_guard, sizeof(competing_guard));
#endif
#endif
    atomic_thread_fence(memory_order_release);

#if !defined(WLTP_MUTANT_NO_RESTORE)
#if defined(WLTP_MUTANT_WRONG_IMAGE)
    const int restore_protection = PROT_READ | PROT_WRITE;
#else
    const int restore_protection = PROT_READ;
#endif
    if (mprotect((void *)image.protect_begin, image.protect_length,
                 restore_protection) != 0) {
        atomic_store_explicit(&g_publish_state, WLTP_STATE_FAILED,
                              memory_order_release);
        return WLTP_PUBLISH_PROTECTION_FAILED;
    }
#endif

#if !defined(WLTP_MUTANT_UNPATCHED) && \
    !defined(WLTP_MUTANT_WRONG_OFFSET) && \
    !defined(WLTP_MUTANT_WRONG_IMAGE) && \
    !defined(WLTP_MUTANT_COMPETING_WRITER)
    if (memcmp(image.bytes, current_reservation,
               WLTP_RESERVATION_SIZE) != 0) {
        atomic_store_explicit(&g_publish_state, WLTP_STATE_FAILED,
                              memory_order_release);
        return WLTP_PUBLISH_VERIFY_FAILED;
    }
#endif
    atomic_store_explicit(&g_publish_state, WLTP_STATE_PUBLISHED,
                          memory_order_release);
    return WLTP_PUBLISH_OK;
}
