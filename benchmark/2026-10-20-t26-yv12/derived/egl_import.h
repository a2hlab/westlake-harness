#ifndef WL_R23_EGL_IMPORT_H
#define WL_R23_EGL_IMPORT_H
#include <stdint.h>
#define R23_IMPLEMENTATIONS 3
struct r23_implementation {
 void *(*current_display)(void);
 void *(*create_image)(void *,void *,unsigned,void *,const int32_t *);
 unsigned (*destroy_image)(void *,void *);
 int (*dup_fence)(void *,void *);
};
struct r23_platform {
 void *(*create_buffer)(void *);
 void (*destroy_buffer)(void *);
 int (*trusted_caller)(void *);
 unsigned count;
 struct r23_implementation impl[R23_IMPLEMENTATIONS];
 void *(*next_client)(const void *);
 void *(*next_create)(void *,void *,unsigned,void *,const int32_t *);
 unsigned (*next_destroy)(void *,void *);
 int (*next_fence)(void *,void *);
};
/* Resolver must fill foreign forwards even if native-provider proof fails.
 * A failure disables native import; it never enables raw-pointer fallback. */
int r23_platform_init(struct r23_platform *);
#endif
