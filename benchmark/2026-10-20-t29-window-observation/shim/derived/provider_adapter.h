#ifndef R15_PROVIDER_ADAPTER_H
#define R15_PROVIDER_ADAPTER_H
#include "window_module.h"
#include <stdbool.h>
#ifdef R15_OH_SDK
#include <native_window/external_window.h>
#include <native_buffer/native_buffer.h>
#else
/* Host ABI projections only. OH compilation uses the actual SDK declarations. */
typedef struct NativeWindow OHNativeWindow;
typedef struct NativeWindowBuffer OHNativeWindowBuffer;
typedef struct OH_NativeBuffer OH_NativeBuffer;
typedef struct BufferHandle BufferHandle;
struct Rect { int32_t x,y; uint32_t w,h; };
typedef struct Region { struct Rect *rects; int32_t rectNumber; } Region;
#endif
#define R15_STATUS "OFFLINE_ADAPTER_ONLY_NOT_DEPLOYABLE"
#define R15_RECORDS 8
struct r15_provider {
 int32_t (*request)(OHNativeWindow *,OHNativeWindowBuffer **,int *);
 BufferHandle *(*handle)(OHNativeWindowBuffer *);
 int32_t (*convert)(OHNativeWindowBuffer *,OH_NativeBuffer **);
 int32_t (*map)(OH_NativeBuffer *,void **);
 int32_t (*unmap)(OH_NativeBuffer *);
 int32_t (*flush)(OHNativeWindow *,OHNativeWindowBuffer *,int,Region);
 int32_t (*abort)(OHNativeWindow *,OHNativeWindowBuffer *);
};
struct r15_capabilities {
 void *ctx;
 int (*unwrap)(void *,const void *,OHNativeWindow **);
 int (*clock_ns)(void *,int64_t *);
 int (*poll_fd)(void *,int,int,short *,int *);
 int (*close_fd)(void *,int);
};
enum r15_operation { R15_REQUEST,R15_HANDLE,R15_CONVERT,R15_MAP,R15_UNMAP,R15_FLUSH,R15_ABORT,R15_OPERATIONS };
struct r15_call { unsigned called,suppressed,raw_valid; int raw_rc,adapter_error; };
struct r15_record {
 OHNativeWindow *window; OHNativeWindowBuffer *buffer; OH_NativeBuffer *native;
 unsigned phase,uncertain,failed;
 struct r15_call calls[R15_OPERATIONS];
};
struct r15_adapter;
/* Exactly one adapter and one R14 module per OH ownership domain. Caller creates
 * that module from ops once. All capabilities immutable; borrowed objects and
 * stable 24-byte handle prefix remain valid through completion. Not arbitrary
 * pointer validation. Caller externally quiesces all calls before destroy;
 * destroy R14 first. Failed records never reset/reuse. No dynamic resolver. */
int r15_create(const struct r15_provider *,const struct r15_capabilities *,struct r15_adapter **,struct r14_ops *);
int r15_destroy(struct r15_adapter *);
int r15_record_for(struct r15_adapter *,OHNativeWindow *,struct r15_record *);
#endif
