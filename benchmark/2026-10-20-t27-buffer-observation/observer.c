/* observer.c — T27 bounded buffer-metadata observer (offline, host-testable).
 * See observer.h for the contract. Records only; no dlopen (dladdr only), no eglGetError,
 * no raw tail read. Getter/create calls run OUTSIDE the ring lock (no lock-order inversion,
 * no provider call under the observer lock). errno is preserved across every entry point. */
#include "observer.h"
#include <dlfcn.h>
#include <errno.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#if defined(__linux__)
#include <sys/syscall.h>
#endif

#define WL_T27_PRINT_CAP 256u   /* bounded stderr lines; beyond this, count only + one drop marker */

static wl_t27_record  g_ring[WL_T27_SLOTS];
static size_t         g_count;
static uint32_t       g_dropped;          /* ring (host-snapshot) overflow */
static uint32_t       g_emit_seq;         /* total emit attempts (drives the print budget) */
static uint32_t       g_print_suppressed; /* records past the print cap */
static uint64_t       g_getter_calls;
static pthread_mutex_t g_lock = PTHREAD_MUTEX_INITIALIZER;

static const wl_t27_cfg WL_CFG_UNKNOWN = {
  WL_T27_UNKNOWN_I32, WL_T27_UNKNOWN_I32, WL_T27_UNKNOWN_I32, WL_T27_UNKNOWN_I32, WL_T27_UNKNOWN_I32
};

static int32_t wl_pid(void) { return (int32_t) getpid(); }
#if defined(__linux__)
static int32_t wl_tid(void) { return (int32_t) syscall(SYS_gettid); }   /* real TID on OH/Linux */
#else
static int32_t wl_tid(void) { return (int32_t) (uintptr_t) pthread_self(); } /* host-test portability only */
#endif

/* store into the host-snapshot ring; drop-newest-on-full. Holds g_lock only for the copy. */
static void wl_t27_store(const wl_t27_record *r) {
  pthread_mutex_lock(&g_lock);
  if (g_count < WL_T27_SLOTS) g_ring[g_count++] = *r;
  else g_dropped++;
  pthread_mutex_unlock(&g_lock);
}

/* DURABLE sink: emit one bounded line to the existing stderr immediately, so records survive a
 * crash (not only the in-memory ring awaiting external drain). Budgeted to WL_T27_PRINT_CAP lines;
 * past the cap, count only and emit a single drop marker. errno-neutral (write(2) sets errno). */
static void wl_t27_emit(const wl_t27_record *r) {
  int saved = errno;
  uint32_t n = __atomic_fetch_add(&g_emit_seq, 1, __ATOMIC_RELAXED);
  if (n < WL_T27_PRINT_CAP) {
    char b[1024];
    const char *file = r->create.file ? r->create.file : "?";   /* the only unbounded field; placed last */
    int k = snprintf(b, sizeof b,
      "[WL-T27] p=%u op=%llu txn=%llu pid=%d tid=%d g=%u "
      "fmt=%d w=%d h=%d stride=%d usageL=%d scratch=%dx%d ps=%d sf=%d slot=%d gen=%d "
      "window=%p wbuf=%p native=%p conv=%p innat=%p "
      "create_addr=%p create_base=%p rel=0x%llx ret=%p disp=%p ctx=%p tgt=0x%x attribs=%p "
      "file=%s\n",
      (unsigned) r->point, (unsigned long long) r->op_id, (unsigned long long) r->txn_id, r->pid, r->tid,
      (unsigned) r->getter_called, r->cfg.format, r->cfg.width, r->cfg.height, r->cfg.stride, r->cfg.usage_low32,
      r->scratch_w, r->scratch_h, r->scratch_pix_stride, r->scratch_format, r->slot, r->generation,
      r->window, r->window_buffer, r->native, r->converted, r->input_native,
      r->create.addr, r->create.base, (unsigned long long) r->create.rel_off, r->create_ret,
      r->display, r->context, (unsigned) r->target, r->attribs, file);
    size_t len;
    if (k < 0) { b[0] = '\n'; len = 1; }                         /* encoding error: still emit a newline */
    else if ((size_t) k >= sizeof b) {                           /* truncated: force a <TRUNC> tag + newline */
      static const char t[] = " <TRUNC>\n";                      /* sizeof t includes the NUL */
      memcpy(b + sizeof b - sizeof t, t, sizeof t);              /* overwrite the tail; base/rel/ret precede file */
      len = sizeof b - 1;
    } else len = (size_t) k;
    (void) write(STDERR_FILENO, b, len);
  } else {
    if (__atomic_add_fetch(&g_print_suppressed, 1, __ATOMIC_RELAXED) == 1) {
      static const char m[] = "[WL-T27] print-cap=256 reached; further records counted only (dropped)\n";
      (void) write(STDERR_FILENO, m, sizeof m - 1);
    }
  }
  errno = saved;
}

/* emit to the durable stderr first (crash-survivable), then store for host snapshot. */
static void wl_t27_append(const wl_t27_record *r) { wl_t27_emit(r); wl_t27_store(r); }

static void wl_hdr(wl_t27_record *r, uint64_t op, uint64_t txn, uint8_t point) {
  memset(r, 0, sizeof *r);
  r->op_id = op; r->txn_id = txn; r->pid = wl_pid(); r->tid = wl_tid(); r->point = point;
  r->cfg = WL_CFG_UNKNOWN;
  r->scratch_w = r->scratch_h = r->scratch_pix_stride = r->scratch_format = WL_T27_UNKNOWN_I32;
  r->slot = r->generation = WL_T27_UNKNOWN_I32;
}

void wl_t27_cpu_native(uint64_t op, uint64_t txn, void *window, void *window_buffer, void *native,
                       const wl_t27_getters *g, void *cfg_buffer) {
  int saved = errno;
  wl_t27_record r; wl_hdr(&r, op, txn, WL_T27_CPU_NATIVE_CONFIG);
  r.window = window; r.window_buffer = window_buffer; r.native = native;
  if (g && g->get_config && cfg_buffer) {            /* admitted getter only; NULL => UNKNOWN, no call */
    g->get_config(cfg_buffer, &r.cfg);
    r.getter_called = 1;
    __atomic_add_fetch(&g_getter_calls, 1, __ATOMIC_RELAXED);
  }
  wl_t27_append(&r);
  errno = saved;
}

void wl_t27_android_output(uint64_t op, uint64_t txn, int32_t sw, int32_t sh, int32_t sps, int32_t sf,
                           const wl_t27_getters *g, void *native_packed) {
  int saved = errno;
  wl_t27_record r; wl_hdr(&r, op, txn, WL_T27_ANDROID_OUTPUT);
  r.scratch_w = sw; r.scratch_h = sh; r.scratch_pix_stride = sps; r.scratch_format = sf; /* returned YV12 scratch */
  r.native = native_packed;
  if (g && g->get_config && native_packed) {         /* native packed descriptor, recorded separately */
    g->get_config(native_packed, &r.cfg);
    r.getter_called = 1;
    __atomic_add_fetch(&g_getter_calls, 1, __ATOMIC_RELAXED);
  }
  wl_t27_append(&r);
  errno = saved;
}

void wl_t27_import_config(uint64_t op, uint64_t txn, void *input_native, void *window_buffer,
                          int32_t slot, int32_t generation, const wl_t27_getters *g) {
  int saved = errno;
  wl_t27_record r; wl_hdr(&r, op, txn, WL_T27_IMPORT_CONFIG);
  r.input_native = input_native; r.window_buffer = window_buffer; r.slot = slot; r.generation = generation;
  if (g && g->from_nwb && window_buffer) {
    r.converted = g->from_nwb(window_buffer);
    r.getter_called = 1;
    __atomic_add_fetch(&g_getter_calls, 1, __ATOMIC_RELAXED);
    if (g->get_config && r.converted) {
      g->get_config(r.converted, &r.cfg);
      __atomic_add_fetch(&g_getter_calls, 1, __ATOMIC_RELAXED);
    }
  }
  wl_t27_append(&r);
  errno = saved;
}

void *wl_t27_create_call(uint64_t op, uint64_t txn, void *create_image_fn, void *display, void *context,
                         uint32_t target, void *window_buffer, const void *attribs) {
  int saved = errno;
  wl_t27_record r; wl_hdr(&r, op, txn, WL_T27_CREATE_CALL);
  r.display = display; r.context = context; r.target = target; r.window_buffer = window_buffer; r.attribs = attribs;
  Dl_info info; memset(&info, 0, sizeof info);
  if (create_image_fn && dladdr(create_image_fn, &info) != 0) {  /* owner of THIS fn, not current-display base */
    r.create.addr = create_image_fn; r.create.base = info.dli_fbase; r.create.file = info.dli_fname;
    r.create.rel_off = (uint64_t) ((const char *) create_image_fn - (const char *) info.dli_fbase);
    r.create.resolved = 1;
  }
  void *ret = NULL;
  int provider_errno = saved;                                    /* if no call is made, nothing changed */
  if (create_image_fn) {                                         /* single invocation; cx reuses the return */
    typedef void *(*cifn)(void *, void *, uint32_t, void *, const int32_t *);
    errno = saved;                                               /* real create runs with the caller's errno, not dladdr's */
    ret = ((cifn) create_image_fn)(display, context, target, window_buffer, (const int32_t *) attribs);
    provider_errno = errno;                                      /* capture the provider's errno immediately */
  }
  r.create_ret = ret;
  wl_t27_append(&r);                                             /* logging must not alter the provider's errno */
  errno = provider_errno;                                        /* restore the PROVIDER errno (real behavior), not entry */
  return ret;                                                    /* never calls eglGetError */
}

uint32_t wl_t27_dropped(void) {
  uint32_t v; pthread_mutex_lock(&g_lock); v = g_dropped; pthread_mutex_unlock(&g_lock); return v;
}
uint32_t wl_t27_printed(void) { uint32_t a = __atomic_load_n(&g_emit_seq, __ATOMIC_RELAXED); return a < WL_T27_PRINT_CAP ? a : WL_T27_PRINT_CAP; }
uint32_t wl_t27_print_suppressed(void) { return __atomic_load_n(&g_print_suppressed, __ATOMIC_RELAXED); }
uint64_t wl_t27_getter_calls(void) { return __atomic_load_n(&g_getter_calls, __ATOMIC_RELAXED); }
size_t wl_t27_count(void) {
  size_t v; pthread_mutex_lock(&g_lock); v = g_count; pthread_mutex_unlock(&g_lock); return v;
}
size_t wl_t27_snapshot(wl_t27_record *out, size_t n) {
  pthread_mutex_lock(&g_lock);
  size_t m = g_count < n ? g_count : n;
  if (out && m) memcpy(out, g_ring, m * sizeof *out);
  pthread_mutex_unlock(&g_lock);
  return m;
}
void wl_t27_reset(void) {
  pthread_mutex_lock(&g_lock); g_count = 0; g_dropped = 0; pthread_mutex_unlock(&g_lock);
  __atomic_store_n(&g_getter_calls, 0, __ATOMIC_RELAXED);
  __atomic_store_n(&g_emit_seq, 0, __ATOMIC_RELAXED);
  __atomic_store_n(&g_print_suppressed, 0, __ATOMIC_RELAXED);
}
