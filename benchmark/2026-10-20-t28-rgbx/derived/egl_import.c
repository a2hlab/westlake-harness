/* Reused from native691 webview_bionic_shim EGL import/display logic.
 * Narrow changes: explicit slot ownership, failure retention and unique-display
 * selection without consuming EGL error state. See donor-index.json. */
#include "egl_import.h"
#include "observation.h"
#include <pthread.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <errno.h>
#include <stdarg.h>
#ifndef R23_SLOTS
#define R23_SLOTS 256
#endif
#define API __attribute__((visibility("default")))
#define ANDROID_BUFFER 0x3140u
#define OH_BUFFER 0x34e1u
enum slot_state { FREE, RESERVED, CLIENT, CREATING, IMAGE, DESTROYING };
struct slot { enum slot_state state; uint64_t generation; void *buffer,*image,*display; unsigned implementation; };
static struct slot slots[R23_SLOTS];
static pthread_mutex_t table_lock=PTHREAD_MUTEX_INITIALIZER;
/* The OH public create/destroy pair is documented non-thread-safe. */
static pthread_mutex_t provider_lock=PTHREAD_MUTEX_INITIALIZER;
static pthread_once_t once=PTHREAD_ONCE_INIT;
static struct r23_platform platform;
static int native_ready;
static unsigned logs;
static void diagnostic(const char *format,...){
 unsigned n=__atomic_fetch_add(&logs,1,__ATOMIC_RELAXED);if(n>=64)return;
 int saved=errno;va_list ap;va_start(ap,format);vfprintf(stderr,format,ap);va_end(ap);errno=saved;
}
static void init(void){native_ready=r23_platform_init(&platform)==0 && platform.create_buffer && platform.destroy_buffer && platform.trusted_caller;}
static int implementation(void *display){
 int match=-1;if(!display || platform.count>R23_IMPLEMENTATIONS)return -1;
 for(unsigned i=0;i<platform.count;i++)if(platform.impl[i].current_display && platform.impl[i].current_display()==display){if(match>=0)return -1;match=(int)i;}
 return match;
}
static void destroy_native(void *buffer){pthread_mutex_lock(&provider_lock);platform.destroy_buffer(buffer);pthread_mutex_unlock(&provider_lock);}
static void release_failed_create(unsigned index,uint64_t generation){
 void *buffer=NULL;pthread_mutex_lock(&table_lock);
 if(slots[index].state==CREATING && slots[index].generation==generation){buffer=slots[index].buffer;slots[index].state=DESTROYING;}
 pthread_mutex_unlock(&table_lock);if(!buffer)return;
 destroy_native(buffer);pthread_mutex_lock(&table_lock);
 if(slots[index].state==DESTROYING && slots[index].generation==generation){slots[index].state=FREE;slots[index].buffer=NULL;slots[index].image=NULL;slots[index].display=NULL;}
 pthread_mutex_unlock(&table_lock);
}
API void *eglGetNativeClientBufferANDROID(const void *buffer){
 pthread_once(&once,init);void *caller=__builtin_return_address(0);
 if(!platform.trusted_caller || !platform.trusted_caller(caller))return platform.next_client?platform.next_client(buffer):NULL;
 if(!native_ready || !buffer){diagnostic("[WL-R23-EGL] client refused provider_ready=%d\n",native_ready);return NULL;}
 unsigned index=R23_SLOTS;uint64_t generation=0;
 pthread_mutex_lock(&table_lock);
 for(unsigned i=0;i<R23_SLOTS;i++)if(slots[i].state==FREE){index=i;slots[i].state=RESERVED;generation=++slots[i].generation;break;}
 pthread_mutex_unlock(&table_lock);
 if(index==R23_SLOTS){diagnostic("[WL-R23-EGL] client refused table_full\n");return NULL;}
 pthread_mutex_lock(&provider_lock);void *window=platform.create_buffer((void*)buffer);pthread_mutex_unlock(&provider_lock);if(window)wl_r27_import((void*)buffer,window,index,generation);
 pthread_mutex_lock(&table_lock);
 if(slots[index].state!=RESERVED || slots[index].generation!=generation){pthread_mutex_unlock(&table_lock);if(window)destroy_native(window);return NULL;}
 slots[index].buffer=window;slots[index].state=window?CLIENT:FREE;
 pthread_mutex_unlock(&table_lock);
 diagnostic("[WL-R23-EGL] client native=%p window_buffer=%p slot=%u generation=%llu\n",buffer,window,index,(unsigned long long)generation);return window;
}
API void *eglCreateImageKHR(void *display,void *context,unsigned target,void *buffer,const int32_t *attribs){
 pthread_once(&once,init);unsigned index=R23_SLOTS;uint64_t generation=0;int refused=0;
 pthread_mutex_lock(&table_lock);
 for(unsigned i=0;i<R23_SLOTS;i++)if(buffer && slots[i].state!=FREE && slots[i].buffer==buffer){
  if(slots[i].state!=CLIENT || target!=ANDROID_BUFFER){refused=1;break;}
  index=i;generation=slots[i].generation;slots[i].state=CREATING;break;
 }
 pthread_mutex_unlock(&table_lock);
 if(refused){diagnostic("[WL-R23-EGL] create refused tracked_busy_or_target\n");return NULL;}
 if(index==R23_SLOTS)return platform.next_create?platform.next_create(display,context,target,buffer,attribs):NULL;
 int selected=implementation(display);void *image=NULL;
 if(selected>=0 && platform.impl[selected].create_image)image=wl_r27_create(index,generation,(void*)platform.impl[selected].create_image,display,context,OH_BUFFER,buffer,attribs);
 if(!image){diagnostic("[WL-R23-EGL] create failed display=%p selected=%d window_buffer=%p\n",display,selected,buffer);release_failed_create(index,generation);return NULL;}
 pthread_mutex_lock(&table_lock);
 /* No other operation can mutate CREATING. It remains owned across the driver call. */
 slots[index].image=image;slots[index].display=display;slots[index].implementation=(unsigned)selected;slots[index].state=IMAGE;
 pthread_mutex_unlock(&table_lock);
 diagnostic("[WL-R23-EGL] image display=%p image=%p window_buffer=%p implementation=%d\n",display,image,buffer,selected);return image;
}
API unsigned eglDestroyImageKHR(void *display,void *image){
 pthread_once(&once,init);unsigned index=R23_SLOTS,selected=0;uint64_t generation=0;void *buffer=NULL;int refused=0;
 pthread_mutex_lock(&table_lock);
 for(unsigned i=0;image && i<R23_SLOTS;i++)if(slots[i].state!=FREE && slots[i].image==image){
  if(slots[i].display!=display){refused=1;continue;}
  if(slots[i].state!=IMAGE){refused=1;break;}
  refused=0;
  index=i;selected=slots[i].implementation;generation=slots[i].generation;buffer=slots[i].buffer;slots[i].state=DESTROYING;break;
 }
 pthread_mutex_unlock(&table_lock);
 if(refused){diagnostic("[WL-R23-EGL] destroy refused display_or_busy\n");return 0;}
 if(index==R23_SLOTS)return platform.next_destroy?platform.next_destroy(display,image):0;
 unsigned result=platform.impl[selected].destroy_image?platform.impl[selected].destroy_image(display,image):0;
 if(result)destroy_native(buffer);
 pthread_mutex_lock(&table_lock);
 if(slots[index].state==DESTROYING && slots[index].generation==generation){
  if(result){slots[index].state=FREE;slots[index].buffer=NULL;slots[index].image=NULL;slots[index].display=NULL;}
  else slots[index].state=IMAGE;
 }
 pthread_mutex_unlock(&table_lock);
 diagnostic("[WL-R23-EGL] destroy display=%p image=%p result=%u retained=%u\n",display,image,result,!result);return result;
}
API int eglDupNativeFenceFDANDROID(void *display,void *sync){
 pthread_once(&once,init);int selected=implementation(display);
 if(selected>=0 && platform.impl[selected].dup_fence)return platform.impl[selected].dup_fence(display,sync);
 /* This fallback preserves the old path; it is not claimed as a corrected instance. */
 return platform.next_fence?platform.next_fence(display,sync):-1;
}
