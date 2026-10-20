#define _GNU_SOURCE 1
#include "egl_import.h"
#include "observation.h"
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
/* Populated only from exact a11c consumer evidence; no guessed object layout. */
static const char *leaf(const char*);
#include "exact_binding.h"
static uintptr_t hwui_base;
static void *hwui_handle;
static void *surface_base;
static const char *leaf(const char*s){const char*p=s?strrchr(s,'/'):NULL;return p?p+1:(s?s:"");}
static int caller(void*pc){Dl_info i={0};return pc && dladdr(pc,&i) && (!hwui_base || (uintptr_t)i.dli_fbase==hwui_base) && i.dli_fname && !strcmp(i.dli_fname,"/data/local/tmp/asx/libhwui.so");}
static void *external(void *handle,const char*name,int extension){
 void *p=dlsym(handle,name);
 if(!p && extension){void *(*proc)(const char*)=(void*(*)(const char*))dlsym(handle,"eglGetProcAddress");if(proc)p=proc(name);}
 Dl_info self={0},found={0};if(!p || !dladdr((void*)&external,&self) || !dladdr(p,&found) || self.dli_fbase==found.dli_fbase)return NULL;return p;
}
static void *implementation_entry(void *h,void *base,const char *name){
 void *f=dlsym(h,name);Dl_info found={0};
 if(f && dladdr(f,&found) && found.dli_fbase==base)return f;
 void *(*proc)(const char*)=(void*(*)(const char*))dlsym(h,"eglGetProcAddress");
 Dl_info own={0};if(!proc || !dladdr((void*)proc,&own) || own.dli_fbase!=base)return NULL;
 f=proc(name);Dl_info self={0};if(!f || !dladdr(f,&found) || !dladdr((void*)&external,&self) || found.dli_fbase==self.dli_fbase)return NULL;
 fprintf(stderr,"[WL-R23-BIND] extension=%s impl_base=%p resolver=%p result=%p result_base=%p\n",name,base,(void*)proc,f,found.dli_fbase);return f;
}
static void add(struct r23_platform*p,void*h,void*expected_current){
 if(!h || p->count==R23_IMPLEMENTATIONS)return;
 void *current=external(h,"eglGetCurrentDisplay",0);if(!current || (expected_current && current!=expected_current))return;
 for(unsigned i=0;i<p->count;i++)if((void*)p->impl[i].current_display==current)return;
 Dl_info owner={0};if(!dladdr(current,&owner) || !owner.dli_fbase)return;
 struct r23_implementation *e=&p->impl[p->count];e->current_display=(void*(*)(void))current;
 e->create_image=(void*(*)(void*,void*,unsigned,void*,const int32_t*))implementation_entry(h,owner.dli_fbase,"eglCreateImageKHR");
 e->destroy_image=(unsigned(*)(void*,void*))implementation_entry(h,owner.dli_fbase,"eglDestroyImageKHR");
 e->dup_fence=(int(*)(void*,void*))implementation_entry(h,owner.dli_fbase,"eglDupNativeFenceFDANDROID");
 if(!e->create_image || !e->destroy_image){memset(e,0,sizeof(*e));return;}
 p->count++;
 Dl_info i={0};dladdr(current,&i);fprintf(stderr,"[WL-R23-BIND] egl_index=%u current=%p base=%p file=%s\n",p->count-1,current,i.dli_fbase,i.dli_fname?i.dli_fname:"?");
}
static int native_member(void*f,uintptr_t offset){Dl_info i={0};return f && dladdr(f,&i) && i.dli_fbase==surface_base && !strcmp(leaf(i.dli_fname),"libsurface.z.so") && (uintptr_t)f-(uintptr_t)i.dli_fbase==offset;}
int r23_platform_init(struct r23_platform*p){
 p->trusted_caller=caller;
 p->next_client=(void*(*)(const void*))external(RTLD_NEXT,"eglGetNativeClientBufferANDROID",0);
 p->next_create=(void*(*)(void*,void*,unsigned,void*,const int32_t*))external(RTLD_NEXT,"eglCreateImageKHR",0);
 p->next_destroy=(unsigned(*)(void*,void*))external(RTLD_NEXT,"eglDestroyImageKHR",0);
 p->next_fence=(int(*)(void*,void*))external(RTLD_NEXT,"eglDupNativeFenceFDANDROID",0);
 Dl_info current={0};void *first=dlsym(RTLD_DEFAULT,"eglGetCurrentDisplay");
 if(first && dladdr(first,&current) && current.dli_fname)add(p,dlopen(current.dli_fname,RTLD_NOW|RTLD_NOLOAD),first);
 add(p,dlopen("libGLES_mali.z.so",RTLD_NOW|RTLD_NOLOAD),NULL);
 add(p,dlopen("libEGL.so",RTLD_NOW|RTLD_NOLOAD),NULL);
 hwui_handle=dlopen("/data/local/tmp/asx/libhwui.so",RTLD_NOW|RTLD_NOLOAD|RTLD_LOCAL);
 /* Exact binding fills the HWUI instance even on a provider refusal, so a trusted
  * HWUI caller cannot escape into foreign forwarding after a native proof fails. */
 if(!r23_exact_consumer(hwui_handle,&hwui_base,&surface_base))return -1;
 void *h=hwui_handle; /* Existing consumer dependency scope, then exact instance checks. */
 if(!h)return -1;
 void *create=external(h,"OH_NativeWindow_CreateNativeWindowBufferFromNativeBuffer",0);
 void *destroy=external(h,"OH_NativeWindow_DestroyNativeWindowBuffer",0);
 if(!native_member(create,0x6702c) || !native_member(destroy,0x66e18))return -1;
 wl_r27_bind_import(h,surface_base);
 p->create_buffer=(void*(*)(void*))create;p->destroy_buffer=(void(*)(void*))destroy;
 fprintf(stderr,"[WL-R23-BIND] hwui_base=%p surface_base=%p create=%p destroy=%p\n",(void*)hwui_base,surface_base,create,destroy);return 0;
}
