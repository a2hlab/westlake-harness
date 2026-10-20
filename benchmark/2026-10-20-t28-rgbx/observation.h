#ifndef WL_T26_OBSERVATION_H
#define WL_T26_OBSERVATION_H
#include <stdint.h>
#include "window_module.h"
#define R27_LOCAL __attribute__((visibility("hidden")))
#ifdef WL_T27_OBSERVER
R27_LOCAL void wl_r27_bind_cpu(void *,void *);
R27_LOCAL void wl_r27_bind_import(void *,void *);
R27_LOCAL void wl_r27_cpu(uint64_t,void *,void *,void *);
R27_LOCAL void wl_r27_output(uint64_t,void *,const struct r14_buffer *);
R27_LOCAL void wl_r27_import(void *,void *,unsigned,uint64_t);
R27_LOCAL void *wl_r27_create(unsigned,uint64_t,void *,void *,void *,unsigned,void *,const int32_t *);
#else
static inline void wl_r27_bind_cpu(void *h,void *b){(void)h;(void)b;}
static inline void wl_r27_bind_import(void *h,void *b){(void)h;(void)b;}
static inline void wl_r27_cpu(uint64_t t,void *w,void *b,void *n){(void)t;(void)w;(void)b;(void)n;}
static inline void wl_r27_output(uint64_t t,void *n,const struct r14_buffer *b){(void)t;(void)n;(void)b;}
static inline void wl_r27_import(void *n,void *b,unsigned s,uint64_t g){(void)n;(void)b;(void)s;(void)g;}
static inline void *wl_r27_create(unsigned s,uint64_t g,void *f,void *d,void *c,unsigned t,void *b,const int32_t *a){(void)s;(void)g;return ((void *(*)(void *,void *,unsigned,void *,const int32_t *))f)(d,c,t,b,a);}
#endif
#endif
