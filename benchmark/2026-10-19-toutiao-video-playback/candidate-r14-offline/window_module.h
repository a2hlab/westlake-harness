#ifndef R14_WINDOW_MODULE_H
#define R14_WINDOW_MODULE_H
#include <stdint.h>
#include <stddef.h>
/* OFFLINE_MODULE_ONLY_NOT_DEPLOYABLE. No provider resolver or production ABI. */
#define R14_STATUS "OFFLINE_MODULE_ONLY_NOT_DEPLOYABLE"
#define R14_FENCE_MS 3000
#define R14_SLOTS 8
struct r14_buffer { int32_t width,height,stride,format; void *bits; uint32_t reserved[6]; };
struct r14_rect { int32_t left,top,right,bottom; };
struct r14_handle { int64_t width,height,stride_bytes,size_bytes; int32_t format; };
/* All callbacks are trusted injected capabilities; wrapper is never dereferenced.
 * Exactly one module instance must cover an OH ownership domain; creating two
 * modules for the same OH window bypasses serialization and is forbidden.
 * ctx and capabilities are immutable and must outlive the module. Distinct OH
 * windows may execute callbacks concurrently. Callback implementations must not
 * cancel threads, longjmp, destroy the module, or mutate aliases during a call.
 * request owns any returned nonnegative fence, even on error. conversion borrows.
 * clock returns monotonic nanoseconds; poll returns rc and explicit saved errno.
 * flush receives a full returned-buffer rect and fence=-1. No ownership ref ops.
 */
struct r14_ops {
 void *ctx;
 int (*unwrap)(void *,const void *,void **);
 int (*request)(void *,void *,void **,int *);
 int (*handle)(void *,void *,struct r14_handle *);
 int (*convert)(void *,void *,void **);
 int (*map)(void *,void *,void **);
 int (*unmap)(void *,void *);
 int (*flush)(void *,void *,void *,int,const struct r14_rect *);
 int (*abort)(void *,void *,void *);
 int (*clock_ns)(void *,int64_t *);
 int (*poll_fd)(void *,int,int,short *,int *);
 int (*close_fd)(void *,int);
};
struct r14_report {
 int primary,request_rc,handle_rc,convert_rc,map_rc,unmap_rc,flush_rc,abort_rc,close_rc;
 unsigned request_called,handle_called,convert_called,map_called,unmap_called,flush_called,abort_called,close_called;
 unsigned retained;
};
struct r14_module;
int r14_create(const struct r14_ops *,struct r14_module **);
/* Lifetime precondition: caller must externally quiesce ALL API calls (including
 * unwrap) and prevent new calls before destroy. No concurrent destroy is allowed.
 * Returns -EBUSY if any reservation remains. No force-reset/drop-ownership API.
 * Every request error is conservatively retained, even with NULL buffer/-1 fd:
 * an error return alone does not prove a provider performed no state change. */
int r14_destroy(struct r14_module *);
int r14_lock(struct r14_module *,const void *,struct r14_buffer *,struct r14_rect *,struct r14_report *);
int r14_unlock(struct r14_module *,const void *,struct r14_report *);
/* Read diagnostic of an owned slot; never consumes it or invokes providers. */
int r14_report_for(struct r14_module *,const void *,struct r14_report *);
#endif
