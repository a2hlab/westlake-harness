#define _GNU_SOURCE 1
#include "geometry.h"
#include "wiring.h"
#include "observe29.h"
#include <dlfcn.h>
#include <errno.h>
#include <pthread.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

static int32_t mapped_format(int32_t f) {
 switch(f){case 1:return 12;case 2:return 12;case 3:return 13;case 4:return 3;case 0x32315659:return 12;default:return f;}
}
int32_t r25_apply(const struct r25_ops *o,void *w,int32_t width,int32_t height,int32_t format,struct r25_report *r) {
 if(!r)return -EINVAL;
 memset(r,0,sizeof(*r));r->wrapper=w;
 if(!w){r->result=-EINVAL;return r->result;}
 if(!o || !o->acquire || !o->get || !o->release || !o->handle_opt){r->result=-ENOSYS;return r->result;}
 r->acquire_called=1;r->acquire_rc=o->acquire(w);
 if(r->acquire_rc!=1){r->result=-ENODEV;return r->result;}
 r->unwrap_called=1;r->oh=o->get(w);r->unwrap_rc=r->oh?0:-ENODEV;
 int rc=r->unwrap_rc;
 if(!rc){
  r->geometry_called=1;r->geometry_rc=o->handle_opt(r->oh,0,width,height);rc=r->geometry_rc;
  if(!rc && format>0){r->format_called=1;r->format_rc=o->handle_opt(r->oh,3,mapped_format(format));rc=r->format_rc;}
 }
 r->release_called=1;r->release_rc=o->release(w);
 /* Preserve the first operation failure; cleanup failure never washes it out. */
 if(!rc && r->release_rc!=1)rc=-EPROTO;
 r->result=rc;return rc;
}

/* Adapted from exact T20 pair.c: loaded-owner-only dependency scope plus
 * actual owner Reference/Unreference GOT identities. No object-layout reads. */
struct r25_ehdr {unsigned char ident[16];uint16_t type,machine;uint32_t version;uint64_t entry,phoff,shoff;uint32_t flags;uint16_t ehsize,phsize,phnum,shsize,shnum,shstr;};
struct r25_phdr {uint32_t type,flags;uint64_t off,vaddr,paddr,filesz,memsz,align;};
_Static_assert(sizeof(struct r25_ehdr)==64,"ELF64 header");
_Static_assert(sizeof(struct r25_phdr)==56,"ELF64 program header");
static int readable_slot(void *base,uintptr_t offset) {
 const struct r25_ehdr *e=base;
 if(!e || memcmp(e->ident,"\177ELF\2\1\1",7) || e->machine!=183 || e->type!=3 || e->ehsize!=64 || e->phsize!=56 || !e->phnum || e->phnum>64 || e->phoff<64 || e->phoff+(uint64_t)e->phnum*56>4096)return 0;
 const struct r25_phdr *p=(const void*)((const unsigned char*)base+e->phoff);
 for(unsigned i=0;i<e->phnum;i++)if(p[i].type==1 && (p[i].flags&4) && offset>=p[i].vaddr && p[i].memsz>=sizeof(void*) && offset-p[i].vaddr<=p[i].memsz-sizeof(void*))return 1;
 return 0;
}
static const char *leaf(const char *s){const char *p=s?strrchr(s,'/'):NULL;return p?p+1:(s?s:"");}
static int at(void *fn,void *base,uintptr_t off,const char *name) {
 Dl_info i={0};return fn && dladdr(fn,&i) && i.dli_fbase==base && i.dli_fname && !strcmp(leaf(i.dli_fname),name) && (uintptr_t)fn-(uintptr_t)base==off;
}
static pthread_once_t once=PTHREAD_ONCE_INIT;
static struct r25_ops ops;
static struct r26_context *cache;
static void *owner_handle,*owner_base,*surface_base,*shim_base,*own_lock,*own_unlock,*own_geometry;
static uintptr_t player_base;
static int bind_error=-ENODEV;
static unsigned log_count;
static void diagnostic(const char *fmt,...) {
 unsigned old=__atomic_load_n(&log_count,__ATOMIC_RELAXED);
 do{if(old>=128)return;}while(!__atomic_compare_exchange_n(&log_count,&old,old+1,0,__ATOMIC_RELAXED,__ATOMIC_RELAXED));
 int saved=errno;va_list ap;va_start(ap,fmt);vfprintf(stderr,fmt,ap);va_end(ap);errno=saved;
}
static void bind_once(void) {
 owner_handle=dlopen("/data/local/tmp/asx/liboh_adapter_bridge.so",RTLD_NOW|RTLD_NOLOAD|RTLD_LOCAL);
 if(!owner_handle)return;
 void *get=dlsym(owner_handle,"oh_anw_get_oh"),*acquire=dlsym(owner_handle,"oh_anw_try_acquire"),*release=dlsym(owner_handle,"oh_anw_try_release");
 Dl_info i={0};if(!get || !dladdr(get,&i) || !i.dli_fbase)return;owner_base=i.dli_fbase;
 bind_error=-EXDEV;
 if(!at(get,owner_base,0x12670c,"liboh_adapter_bridge.so") || !at(acquire,owner_base,0x126748,"liboh_adapter_bridge.so") || !at(release,owner_base,0x126798,"liboh_adapter_bridge.so"))return;
 if(!readable_slot(owner_base,0x175520) || !readable_slot(owner_base,0x175448))return;
 void *ref=__atomic_load_n((void**)((unsigned char*)owner_base+0x175520),__ATOMIC_ACQUIRE);
 void *unref=__atomic_load_n((void**)((unsigned char*)owner_base+0x175448),__ATOMIC_ACQUIRE);
 Dl_info ri={0},ui={0};
 if(!ref || !unref || ref!=dlsym(owner_handle,"OH_NativeWindow_NativeObjectReference") || unref!=dlsym(owner_handle,"OH_NativeWindow_NativeObjectUnreference") || !dladdr(ref,&ri) || !dladdr(unref,&ui) || !ri.dli_fbase || ri.dli_fbase!=ui.dli_fbase || strcmp(leaf(ri.dli_fname),"libsurface.z.so") || strcmp(leaf(ui.dli_fname),"libsurface.z.so"))return;
 surface_base=ri.dli_fbase;
 void *opt=dlsym(owner_handle,"OH_NativeWindow_NativeWindowHandleOpt");
 if(!at(opt,surface_base,0x68c10,"libsurface.z.so"))return;
 Dl_info self={0};if(!dladdr((void*)&bind_once,&self) || !self.dli_fbase || !self.dli_fname)return;
 void *h=dlopen(self.dli_fname,RTLD_NOW|RTLD_NOLOAD|RTLD_LOCAL);if(!h)return;
 shim_base=self.dli_fbase;
 own_lock=dlsym(h,"ANativeWindow_lock");own_unlock=dlsym(h,"ANativeWindow_unlockAndPost");own_geometry=dlsym(h,"ANativeWindow_setBuffersGeometry");
 void *fns[]={own_lock,own_unlock,own_geometry};
 for(unsigned n=0;n<3;n++){Dl_info fi={0};if(!fns[n] || !dladdr(fns[n],&fi) || fi.dli_fbase!=shim_base)return;}
 ops=(struct r25_ops){(int(*)(void*))acquire,(void*(*)(void*))get,(int(*)(void*))release,(int32_t(*)(void*,int32_t,...))opt};
 struct r26_owner owner={ops.acquire,ops.get,ops.release};bind_error=r26_create(&owner,NULL,&cache);
 diagnostic("[WL-R25-BIND] owner=%p surface=%p HandleOpt=%p geometry=%p lock=%p unlock=%p owner_file=/data/local/tmp/asx/liboh_adapter_bridge.so surface_file=%s shim_file=%s\n",owner_base,surface_base,opt,own_geometry,own_lock,own_unlock,ri.dli_fname,self.dli_fname);
}
static int admitted_caller(void *pc) {
 Dl_info i={0};if(!pc || !dladdr(pc,&i) || !i.dli_fbase || !i.dli_fname || strcmp(i.dli_fname,"/data/local/tmp/asx/lib/arm64-v8a/libttmplayer.so"))return 0;
 /* Exact unchanged player relocation offsets, not wrapper offsets. Reject the
  * mixed765 ring-dependent lock path before acquiring or dereferencing wrapper. */
 const uintptr_t slots[]={0x472490,0x472760,0x472048};void *expected[]={own_lock,own_unlock,own_geometry};
 for(unsigned n=0;n<3;n++){
  if(!readable_slot(i.dli_fbase,slots[n]))return 0;
  void *actual=__atomic_load_n((void**)((unsigned char*)i.dli_fbase+slots[n]),__ATOMIC_ACQUIRE);
  if(actual!=expected[n])return 0;
 }
 uintptr_t empty=0,want=(uintptr_t)i.dli_fbase;
 (void)__atomic_compare_exchange_n(&player_base,&empty,want,0,__ATOMIC_RELAXED,__ATOMIC_RELAXED);
 return __atomic_load_n(&player_base,__ATOMIC_RELAXED)==want;
}
int wl_r26_gate(void *caller){pthread_once(&once,bind_once);return bind_error?bind_error:(admitted_caller(caller)?0:-EXDEV);}
struct r26_context *wl_r26_cache(void){return cache;}
static int32_t dispatch(void *w,int32_t width,int32_t height,int32_t format,void *caller) {
 struct r29_record d={.phase=R29_GEOMETRY,.valid=R29_REQUEST,.transition=1,.call=r29_call_id(),.self=(uintptr_t)ANativeWindow_setBuffersGeometry,.caller=(uintptr_t)caller,.wrapper=(uintptr_t)w,.w=width,.h=height,.fmt=format};
 if(!w){d.invalid=1;d.rc=-EINVAL;d.stage=d.failure_stage=1;r29_emit(&d);return -EINVAL;}
 pthread_once(&once,bind_once);
 if(bind_error || !admitted_caller(caller)){
  int rc=bind_error?bind_error:-EXDEV;diagnostic("[WL-R25-GEOMETRY] rejected caller=%p wrapper=%p rc=%d\n",caller,w,rc);d.invalid=1;d.rc=rc;d.stage=d.failure_stage=2;r29_emit(&d);return rc;
 }
 struct r26_token token;int rc=r26_geometry_begin(cache,w,&token);d.phase=R29_CACHE;d.rc=rc;d.raw_rc=rc;d.called=d.raw_valid=1;d.stage=3;d.failure_stage=rc?3:0;r29_emit(&d);if(rc)return rc;
 struct r25_report r;rc=r25_apply(&ops,w,width,height,format,&r);
 int cleanup=r26_geometry_end(cache,token,format,rc,r.release_called && r.release_rc!=1);if(!rc && cleanup)rc=cleanup;
 diagnostic("[WL-R25-GEOMETRY] caller=%p entry=%p wrapper=%p oh=%p wh=%dx%d fmt=%d acquire=%u/%d unwrap=%u/%d geometry=%u/%d format=%u/%d release=%u/%d result=%d\n",caller,own_geometry,w,r.oh,width,height,format,r.acquire_called,r.acquire_rc,r.unwrap_called,r.unwrap_rc,r.geometry_called,r.geometry_rc,r.format_called,r.format_rc,r.release_called,r.release_rc,rc);
 d.phase=R29_GEOMETRY;d.rc=rc;d.raw_rc=r.result;d.valid|=R29_REFS;d.oh=(uintptr_t)r.oh;if(r.oh)d.valid|=R29_OH;d.acquire_called=r.acquire_called;d.acquire_rc=r.acquire_rc;d.release_called=r.release_called;d.release_rc=r.release_rc;d.called=d.raw_valid=1;d.stage=4;d.failure_stage=rc?4:0;d.provider=(uintptr_t)r25_apply;d.valid|=R29_PROVIDER;r29_emit(&d);
 return rc;
}
int32_t ANativeWindow_setBuffersGeometry(void *w,int32_t width,int32_t height,int32_t format) {
 return dispatch(w,width,height,format,__builtin_extract_return_addr(__builtin_return_address(0)));
}
