#ifndef WESTLAKE_BIONIC_PTHREAD_BRIDGE_H
#define WESTLAKE_BIONIC_PTHREAD_BRIDGE_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#if defined(__GNUC__) || defined(__clang__)
#define WLPB_EXPORT __attribute__((visibility("default")))
#else
#define WLPB_EXPORT
#endif

#define WLPB_ABI_VERSION UINT32_C(1)
#define WLPB_TICKET_STORAGE_SIZE UINT32_C(80)
#define WLPB_RECEIPT_STORAGE_SIZE UINT32_C(112)
#define WLPB_MUSL_ATTR_STORAGE_SIZE UINT32_C(64)
#define WLPB_MAX_RECORDS UINT32_C(256)

typedef union WlpbTicketStorageV1 {
    uint64_t alignment;
    uint8_t bytes[WLPB_TICKET_STORAGE_SIZE];
} WlpbTicketStorageV1;

typedef union WlpbReceiptStorageV1 {
    uint64_t alignment;
    uint8_t bytes[WLPB_RECEIPT_STORAGE_SIZE];
} WlpbReceiptStorageV1;

typedef union WlpbMuslAttrStorageV1 {
    max_align_t alignment;
    uint8_t bytes[WLPB_MUSL_ATTR_STORAGE_SIZE];
} WlpbMuslAttrStorageV1;

typedef void *(*WlpbStartRoutine)(void *argument);

/* Every admission callback succeeds only when it returns exactly 1. */
typedef struct WlpbHostOpsV1 {
    uint32_t abi_version;
    uint32_t struct_size;
    void *context;
    int (*issue_thread_ticket)(void *context, WlpbTicketStorageV1 *ticket);
    int (*cancel_thread_ticket)(void *context,
                                const WlpbTicketStorageV1 *ticket);
    int (*prepare_current_thread)(void *context,
                                  const WlpbTicketStorageV1 *ticket,
                                  WlpbReceiptStorageV1 *receipt);
    int (*verify_current_thread_ready)(void *context,
                                       const WlpbReceiptStorageV1 *receipt);
    int (*retire_current_thread)(void *context,
                                 const WlpbReceiptStorageV1 *receipt);
    uint64_t (*get_current_thread_id)(void *context);
    int (*real_pthread_create)(void *context, uint64_t *thread,
                               const WlpbMuslAttrStorageV1 *attribute,
                               WlpbStartRoutine start, void *argument);
    void (*real_pthread_exit)(void *context, void *result);
    int (*real_pthread_attr_init)(void *context,
                                  WlpbMuslAttrStorageV1 *attribute);
    int (*real_pthread_attr_destroy)(void *context,
                                     WlpbMuslAttrStorageV1 *attribute);
    int (*real_pthread_attr_setdetachstate)(
        void *context, WlpbMuslAttrStorageV1 *attribute, int state);
    int (*real_pthread_attr_setstacksize)(
        void *context, WlpbMuslAttrStorageV1 *attribute, size_t size);
    int (*real_pthread_attr_getstack)(
        void *context, const WlpbMuslAttrStorageV1 *attribute,
        void **stack_base, size_t *stack_size);
    int (*real_pthread_getattr_np)(void *context, uint64_t thread,
                                   WlpbMuslAttrStorageV1 *attribute);
    void (*fatal_process)(void *context, uint32_t reason);
    uint64_t generation;
    uint32_t reserved_zero[4];
} WlpbHostOpsV1;

WLPB_EXPORT int WLPB_InstallHostOps(const WlpbHostOpsV1 *ops);
WLPB_EXPORT uint32_t WLPB_GetAbiVersion(void);

#ifdef __cplusplus
}
#endif

#endif
