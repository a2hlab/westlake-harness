/* observer.h — T27 bounded buffer-metadata observer (API for cx; offline, host-testable).
 *
 * Contract (see t27-buffer-observation.spec.md):
 *  - The observer RECORDS only. It never loads a provider: no dlopen (incl. NOLOAD), no new
 *    C++ getter, no MapPlanes, no extra map/acquire/reference, no raw +0x18 / +14 tail read.
 *  - cx INJECTS already-retained getter pointers (resolved via the T20 owner / R23 HWUI handle).
 *    A NULL getter => zero getter calls for that record => the dependent fields stay UNKNOWN.
 *  - Original lifecycle / change-class provider calls are untouched; admitted getter calls are
 *    allowed and counted separately (wl_t27_getter_calls()).
 *  - Each record is emitted to the EXISTING stderr immediately (bounded to 256 lines; past that,
 *    counted only + one drop marker), so records survive a crash — not only the in-memory ring.
 *  - errno: the pure-observation entry points preserve the ENTRY errno (fully transparent). The
 *    create entry runs the real create_image with the caller's errno (not dladdr's) and preserves
 *    the PROVIDER's errno afterwards (real behavior unchanged); it never calls eglGetError.
 *  - Fixed WL_T27_SLOTS ring for host snapshot; on full, newest dropped and wl_t27_dropped()++.
 *    Output never waits for a consumer, holds no new provider lock, adds no unbounded alloc/thread.
 */
#ifndef WL_T27_OBSERVER_H
#define WL_T27_OBSERVER_H
#include <stdint.h>
#include <stddef.h>

#define WL_T27_SLOTS 256u
#define WL_T27_UNKNOWN_I32 ((int32_t)0x80000000) /* sentinel for an unread signed32 field */

typedef enum {
  WL_T27_CPU_NATIVE_CONFIG = 1, /* R15 provider_adapter.c:77-81, after CONVERTED publish, before R14/map */
  WL_T27_ANDROID_OUTPUT    = 2, /* after T26 prepare_output, before publish: returned YV12 scratch + native packed */
  WL_T27_IMPORT_CONFIG     = 3, /* R23 egl_import.c:56, create_buffer nonnull, new window-buffer retained */
  WL_T27_CREATE_CALL       = 4  /* R23 egl_import.c:73-75, around the selected create_image call */
} wl_t27_point;

/* Mirrors the real SDK OH_NativeBuffer_Config EXACTLY so OH_NativeBuffer_GetConfig writes the right
 * fields: order is width, height, format, usage, stride (usage@12 BEFORE stride@16; all 5 int32,
 * sizeof 20). usage is the low 32 bits only (upper 32 UNKNOWN). Do NOT reorder. */
typedef struct { int32_t width, height, format, usage_low32, stride; } wl_t27_cfg;
_Static_assert(sizeof(wl_t27_cfg) == 20, "OH_NativeBuffer_Config == 5x int32 == 20 bytes");
_Static_assert(offsetof(wl_t27_cfg, width)       == 0,  "width@0");
_Static_assert(offsetof(wl_t27_cfg, height)      == 4,  "height@4");
_Static_assert(offsetof(wl_t27_cfg, format)      == 8,  "format@8");
_Static_assert(offsetof(wl_t27_cfg, usage_low32) == 12, "usage@12 (SDK order: before stride)");
_Static_assert(offsetof(wl_t27_cfg, stride)      == 16, "stride@16 (SDK order: after usage)");

/* Getter pointers cx injects (already resolved via retained handles); either may be NULL. */
typedef void  (*wl_t27_getconfig_fn)(void *buffer, wl_t27_cfg *out);  /* OH_NativeBuffer_GetConfig: no rc */
typedef void *(*wl_t27_fromnwb_fn)(void *window_buffer);              /* public FromNativeWindowBuffer */
typedef struct { wl_t27_getconfig_fn get_config; wl_t27_fromnwb_fn from_nwb; } wl_t27_getters;

/* dladdr-derived identity of the actual create_image pointer (NOT the current-display base). */
typedef struct { void *addr, *base; const char *file; uint64_t rel_off; uint8_t resolved; } wl_t27_dl;

/* One retained record (snapshot-readable by host tests). Unused fields hold UNKNOWN/NULL. */
typedef struct {
  uint64_t op_id, txn_id;
  int32_t  pid, tid;
  uint8_t  point;         /* wl_t27_point */
  uint8_t  getter_called; /* 1 if an injected getter ran for this record, else 0 */
  void    *window, *window_buffer, *native, *converted, *input_native;
  int32_t  slot, generation;
  wl_t27_cfg cfg;                 /* GetConfig result or all-UNKNOWN */
  int32_t  scratch_w, scratch_h, scratch_pix_stride, scratch_format; /* ANDROID_OUTPUT: returned YV12 scratch */
  /* CREATE_CALL only: */
  wl_t27_dl create;               /* dladdr of the selected create_image fn ptr */
  void    *display, *context; uint32_t target; const void *attribs; /* attribs ptr recorded, never traversed */
  void    *create_ret;            /* the single create_image() return (cx must reuse this; no 2nd call) */
} wl_t27_record;

/* ---- four thin entry points cx calls at the existing insertion points ----
 * Each preserves errno. Each returns void except wl_t27_create_call, which performs the ONE
 * create_image invocation and returns its value so cx uses the same result (no double call). */

void wl_t27_cpu_native(uint64_t op_id, uint64_t txn_id, void *window, void *window_buffer,
                       void *native, const wl_t27_getters *g, void *cfg_buffer);

void wl_t27_android_output(uint64_t op_id, uint64_t txn_id,
                           int32_t scratch_w, int32_t scratch_h, int32_t scratch_pix_stride,
                           int32_t scratch_format, const wl_t27_getters *g, void *native_packed_buffer);

void wl_t27_import_config(uint64_t op_id, uint64_t txn_id, void *input_native, void *window_buffer,
                          int32_t slot, int32_t generation, const wl_t27_getters *g);

/* create_image_fn has eglCreateImageKHR shape: void*(void *dpy,void *ctx,uint32_t tgt,void *cbuf,const int32_t*attr). */
void *wl_t27_create_call(uint64_t op_id, uint64_t txn_id, void *create_image_fn,
                         void *display, void *context, uint32_t target,
                         void *window_buffer, const void *attribs);

/* ---- host-test / drain surface (no device) ---- */
uint32_t wl_t27_dropped(void);        /* records dropped from the host-snapshot ring when full */
uint32_t wl_t27_printed(void);        /* durable stderr lines emitted (<= 256) */
uint32_t wl_t27_print_suppressed(void); /* records past the stderr print cap (counted, one drop marker) */
uint64_t wl_t27_getter_calls(void);   /* admitted getter calls made (separate from provider op counts) */
size_t   wl_t27_count(void);          /* retained records (<= WL_T27_SLOTS) */
size_t   wl_t27_snapshot(wl_t27_record *out, size_t n); /* copy up to n records out; returns number copied */
void     wl_t27_reset(void);          /* host-test only: clear ring, counters */

#endif /* WL_T27_OBSERVER_H */
