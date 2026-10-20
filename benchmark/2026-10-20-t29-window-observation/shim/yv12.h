#ifndef WL_T26_YV12_H
#define WL_T26_YV12_H
#include <stddef.h>
#include <stdint.h>
#include "window_module.h"
#define R26_YV12 INT32_C(0x32315659)
#define R26_LIMIT ((size_t)32*1024*1024)
#define R26_TOTAL ((size_t)64*1024*1024)
#define R26_SLOTS 8
#define R26_API __attribute__((visibility("hidden")))
struct r26_layout { size_t w,h,ys,cs,ch,v,u,total; };
struct r26_owner { int (*acquire)(void*); void *(*get)(void*); int (*release)(void*); };
struct r26_alloc { void *ctx; void *(*zero)(void*,size_t); void (*free)(void*,void*); };
struct r26_token { unsigned slot; uint64_t generation; };
struct r26_context;
/* External quiescence is mandatory for destroy, including threads in unwrap.
 * A cache reference is separate from the pair reference. No raw object reads. */
R26_API int r26_create(const struct r26_owner*,const struct r26_alloc*,struct r26_context**);
R26_API int r26_destroy(struct r26_context*);
R26_API int r26_layout(int64_t,int64_t,struct r26_layout*);
R26_API int r26_convert(const struct r26_layout*,const void*,size_t,const struct r14_handle*,void*);
R26_API int r26_geometry_begin(struct r26_context*,void*,struct r26_token*);
R26_API int r26_geometry_end(struct r26_context*,struct r26_token,int32_t,int,int);
R26_API int r26_lock_begin(struct r26_context*,const void*,void*,struct r26_token*);
R26_API int r26_prepare(struct r26_context*,struct r26_token,const struct r14_handle*,struct r14_buffer*);
R26_API int r26_before_unmap(struct r26_context*,struct r26_token);
R26_API int r26_finish(struct r26_context*,struct r26_token,int);
R26_API int r26_poison(struct r26_context*,const void*);
R26_API size_t r26_reserved(struct r26_context*);
#endif
