/* observe29c.h — T29 CONSUMER hidden logger (independent, per-DSO).
 *
 * This is a SELF-CONTAINED hidden logger for the consumer bridge DSO. It is NOT merged into the cpu
 * shim/observe29.c: each DSO keeps its OWN hidden logger with its OWN budget and OWN private sink,
 * matching the interface's per-DSO isolation. The concurrency / reserved-quota / sink core here is a
 * faithful copy of observe29.c's proven algorithm (mutex-guarded identities+stats+sink, atomic call
 * id, dev/ino sink re-verification before every eligible write, write-result accounting, disjoint
 * reserved quotas) — reused so the two loggers share one proven design, not two different bugs. Only
 * the RECORD fields, the six phase labels, and the emit branch are consumer-specific (SurfaceTexture
 * update/attach/detach, TextureView producer replace/destroy).
 *
 * Symbols carry a `r29c_` prefix so this logger stays an independent bridge implementation and can be
 * linked alongside the cpu observe29.c with no symbol clash and no shared state. Values only: no
 * address-valued field is ever dereferenced here. */
#ifndef WL_OBSERVE29C_H
#define WL_OBSERVE29C_H
#include <stddef.h>
#include <stdint.h>

#define R29_HIDDEN __attribute__((visibility("hidden")))

/* Six consumer phase slots (budget shape identical to the cpu side: 16 x 8 x 6 x (2+2) = 3072). */
enum r29c_phase {
  R29C_ATTACH = 0,            /* SurfaceTexture.attachToGLContext */
  R29C_DETACH = 1,            /* SurfaceTexture.detachFromGLContext */
  R29C_UPDATE = 2,            /* SurfaceTexture.updateTexImage */
  R29C_PRODUCER_REPLACE = 3,  /* TextureView.nCreateNativeWindow */
  R29C_PRODUCER_DESTROY = 4,  /* TextureView.nDestroyNativeWindow */
  R29C_PHASE_OTHER = 5,
  R29C_PHASES = 6
};

/* valid_mask bits — set means the value was safely obtained; clear means UNKNOWN (never a fabricated 0). */
enum r29c_valid {
  R29C_OH        = 1u << 0,
  R29C_STATE     = 1u << 1,
  R29C_IMAGE     = 1u << 2,
  R29C_OLDWIN    = 1u << 3,
  R29C_NEWWIN    = 1u << 4,
  R29C_TEX       = 1u << 5,
  R29C_RELEASED  = 1u << 6,
  R29C_DETACHED  = 1u << 7,
  R29C_RAWRC     = 1u << 8,
  R29C_PUBRC     = 1u << 9,
  R29C_PROVIDER  = 1u << 10,
  R29C_REFRC     = 1u << 11,
  R29C_UNREFRC   = 1u << 12
};

/* Values-only consumer record. Address-valued fields (self/caller/wrapper/oh/state/image/old_window/
 * new_window/provider) are opaque and NEVER dereferenced by the logger. */
struct r29c_record {
  /* common */
  unsigned  phase;       /* enum r29c_phase */
  unsigned  valid;       /* enum r29c_valid bitmask */
  unsigned  invalid;     /* 1 => invalid early-return (routes to the 30 invalid/overflow quota) */
  unsigned  transition;  /* 1 => an observed attach/detach/producer transition (may advance epoch) */
  uint64_t  call;        /* caller-supplied call ordinal (from r29c_call_id) */
  uintptr_t self, caller, wrapper, oh, state, image, provider;
  int       called;      /* call_executed: did the real provider op run (vs an early return)? */
  int       raw_rc;      /* provider raw rc (valid iff R29C_RAWRC) */
  int       rc;          /* normalized public rc (valid iff R29C_PUBRC; void methods leave it 0) */
  /* consumer */
  uintptr_t old_window, new_window;
  int       tex_name;                 /* valid iff R29C_TEX */
  int       released_valid, released; /* released flag read (valid bit vs value) */
  int       detached_valid, detached;
  int       existing_exception_branch;/* the method's PRE-EXISTING throw branch was taken */
  int       ref_called, ref_rc_valid, ref_rc;     /* producer reference; independent of raw/public rc */
  int       unref_called, unref_rc_valid, unref_rc;/* producer unreference; independent rc */
};

/* Mirrors observe29.c's stats so the same host-test assertions and cx's merge apply unchanged. */
struct r29c_stats {
  uint64_t eligible, formatted, timed, writes, bytes, losses, skipped;
  unsigned invalids, first_limit, final_exhaustion, identities, sink_state;
};

/* extern "C" so the C++ derived TUs reference the same unmangled symbols the C logger defines. */
#ifdef __cplusplus
extern "C" {
#endif
R29_HIDDEN uint64_t r29c_call_id(void);
R29_HIDDEN void     r29c_observe(const struct r29c_record *);
R29_HIDDEN void     r29c_stats_read(struct r29c_stats *);
#ifdef __cplusplus
}
#endif

#endif /* WL_OBSERVE29C_H */
