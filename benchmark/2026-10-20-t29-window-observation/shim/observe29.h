#ifndef WL_OBSERVE29_H
#define WL_OBSERVE29_H
#include <stddef.h>
#include <stdint.h>
#define R29_HIDDEN __attribute__((visibility("hidden")))
enum r29_phase { R29_CACHE, R29_ENTRY, R29_OUTPUT, R29_RETURN, R29_FLUSH, R29_GEOMETRY, R29_PHASES };
enum r29_valid {
 R29_OH=1u, R29_REQUEST=2u, R29_LAYOUT=4u, R29_HISTORY=8u,
 R29_PROVIDER=16u, R29_REPORT=32u, R29_REFS=64u
};
/* Values only. Address-valued fields are NEVER dereferenced by this module. */
struct r29_record {
 unsigned phase,valid,invalid,transition;
 uint64_t call;
 uintptr_t self,caller,wrapper,oh,buffer,native,bits,provider;
 int raw_rc,raw_valid,rc,called,stage,failure_stage;
 int w,h,fmt,width,height,stride,format,history_known,history_format;
 int request_called,request_rc,map_called,map_rc,unmap_called,unmap_rc;
 int flush_called,flush_rc,abort_called,abort_rc,retained;
 int handle_called,handle_rc,native_convert_called,native_convert_rc;
 int fence_called,fence_rc,close_called,close_rc,prepare_called,prepare_rc;
 int conversion_called,conversion_rc_valid,conversion_rc;
 int acquire_called,acquire_rc,release_called,release_rc;
};
struct r29_stats {
 uint64_t eligible,formatted,timed,writes,bytes,losses,skipped;
 unsigned invalids,first_limit,final_exhaustion,identities,sink_state;
};
R29_HIDDEN uint64_t r29_call_id(void);
R29_HIDDEN void r29_emit(const struct r29_record *);
R29_HIDDEN void r29_stats_read(struct r29_stats *);
#endif
