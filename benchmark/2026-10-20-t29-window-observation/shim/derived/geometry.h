#ifndef WL_T25_GEOMETRY_H
#define WL_T25_GEOMETRY_H
#include <stdint.h>
/* Accepted callers already own a live bridge ANativeWindow reference and
 * externally serialize geometry/lock/destroy. These capabilities are not an
 * arbitrary-pointer classifier. No raw-OH fallback or private765 format ring. */
struct r25_ops {
 int (*acquire)(void *);
 void *(*get)(void *);
 int (*release)(void *);
 int32_t (*handle_opt)(void *,int32_t,...);
};
struct r25_report {
 void *wrapper,*oh;
 unsigned acquire_called,unwrap_called,geometry_called,format_called,release_called;
 int acquire_rc,unwrap_rc,geometry_rc,format_rc,release_rc,result;
};
__attribute__((visibility("hidden"))) int32_t r25_apply(const struct r25_ops *,void *,int32_t,int32_t,int32_t,struct r25_report *);
__attribute__((visibility("default"))) int32_t ANativeWindow_setBuffersGeometry(void *,int32_t,int32_t,int32_t);
#endif
