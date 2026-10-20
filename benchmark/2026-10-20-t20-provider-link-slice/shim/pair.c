#define _GNU_SOURCE 1
#include "entry.h"
#include <dlfcn.h>
#include <errno.h>
#include <pthread.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include <stdint.h>
/* Only the accepted player caller uses the new path. Other callers keep -ENODEV.
 * The caller must hold a VALID ANativeWindow reference on entry. This is not an
 * arbitrary-pointer validator. The selected exact owner consumes compatible
 * bridge windows only; a rejected unwrap never falls back to raw OH pointers. */
static pthread_once_t once=PTHREAD_ONCE_INIT;
static struct r20_context *context;
static OHNativeWindow *(*owner_get)(void *);
static int (*owner_acquire)(void *),(*owner_release)(void *);
static void *owner_handle;
static uintptr_t player_base;
static int bind_error=-ENODEV;
static unsigned log_count;
static void pair_log(const char *format,...){int saved=errno;va_list args;va_start(args,format);vfprintf(stderr,format,args);va_end(args);errno=saved;}
static int fail(int rc){errno=rc<0?-rc:EIO;return rc<0?rc:-EIO;}
static const char *leaf(const char *s){const char *p=s?strrchr(s,'/'):NULL;return p?p+1:(s?s:"");}
static int player_caller(void *pc){
 Dl_info i={0};if(!pc || !dladdr(pc,&i) || !i.dli_fbase || !i.dli_fname || strcmp(i.dli_fname,"/data/local/tmp/asx/lib/arm64-v8a/libttmplayer.so"))return 0;
 uintptr_t want=(uintptr_t)i.dli_fbase,empty=0;
 (void)__atomic_compare_exchange_n(&player_base,&empty,want,0,__ATOMIC_RELAXED,__ATOMIC_RELAXED);
 return __atomic_load_n(&player_base,__ATOMIC_RELAXED)==want;
}
static int original_lock_refusal(void){
 static int logged;
 if(!__atomic_exchange_n(&logged,1,__ATOMIC_RELAXED)){
  fprintf(stderr,"[WESTLAKE-ANW] ANativeWindow_lock: CPU rendering path not implemented; callers with a GPU path are unaffected\n");fflush(stderr);
 }
 return fail(-ENODEV);
}
static int member(void *fn,void **base,const char *kind){
 Dl_info i={0};if(!fn || !dladdr(fn,&i) || !i.dli_fbase)return 0;
 const char *file=leaf(i.dli_fname);
 if(!strcmp(kind,"owner_get") || !strcmp(kind,"owner_acquire") || !strcmp(kind,"owner_release")){if(strcmp(file,"liboh_adapter_bridge.so"))return 0;}
 else if(strcmp(file,"libsurface.z.so"))return 0;
 if(*base && *base!=i.dli_fbase)return 0;*base=i.dli_fbase;
 pair_log("[WL-R20-BIND] kind=%s fn=%p base=%p file=%s\n",kind,fn,i.dli_fbase,i.dli_fname?i.dli_fname:"?");return 1;
}
static int unwrap(void *ignored,const void *wrapper,OHNativeWindow **out){
 (void)ignored;*out=owner_get((void*)wrapper);
 unsigned n=__atomic_fetch_add(&log_count,1,__ATOMIC_RELAXED);
 if(n<64)pair_log("[WL-R20-UNWRAP] seq=%u wrapper=%p oh=%p rc=%d\n",n,wrapper,(void*)*out,*out?0:-ENODEV);
 return *out?0:-ENODEV;
}
/* These are exact dca530 ELF module locations, never window-object offsets.
 * The outer admission must hash this loaded owner. Also require all three public
 * owner offsets and a readable PT_LOAD for each GOT read before accessing it. */
struct r20_ehdr {unsigned char ident[16];uint16_t type,machine;uint32_t version;uint64_t entry,phoff,shoff;uint32_t flags;uint16_t ehsize,phsize,phnum,shsize,shnum,shstr;};
struct r20_phdr {uint32_t type,flags;uint64_t off,vaddr,paddr,filesz,memsz,align;};
_Static_assert(sizeof(struct r20_ehdr)==64,"ELF64 header");
_Static_assert(sizeof(struct r20_phdr)==56,"ELF64 program header");
static int readable_slot(void *base,uintptr_t offset){
 const struct r20_ehdr *e=base;
 if(memcmp(e->ident,"\177ELF\2\1\1",7) || e->machine!=183 || e->type!=3 || e->ehsize!=64 || e->phsize!=56 || !e->phnum || e->phnum>64 || e->phoff<64 || e->phoff>4096)return 0;
 const struct r20_phdr *p=(const void*)((const unsigned char*)base+e->phoff);
 for(unsigned i=0;i<e->phnum;i++)if(p[i].type==1 && (p[i].flags&4) && offset>=p[i].vaddr && p[i].memsz>=sizeof(void*) && offset-p[i].vaddr<=p[i].memsz-sizeof(void*))return 1;
 return 0;
}
static int owner_provider(void *base,void **provider_base){
 if((uintptr_t)owner_get-(uintptr_t)base!=0x125dc0 || (uintptr_t)owner_acquire-(uintptr_t)base!=0x125dfc || (uintptr_t)owner_release-(uintptr_t)base!=0x125e4c)return 0;
 if(!readable_slot(base,0x1740a0) || !readable_slot(base,0x173fc8))return 0;
 void *ref=__atomic_load_n((void**)((unsigned char*)base+0x1740a0),__ATOMIC_ACQUIRE);
 void *unref=__atomic_load_n((void**)((unsigned char*)base+0x173fc8),__ATOMIC_ACQUIRE);
 if(!member(ref,provider_base,"owner_bound_reference") || !member(unref,provider_base,"owner_bound_unreference"))return 0;
 /* Compare actual owner slots with dependency-scope resolutions, not just names. */
 return ref==dlsym(owner_handle,"OH_NativeWindow_NativeObjectReference") && unref==dlsym(owner_handle,"OH_NativeWindow_NativeObjectUnreference");
}
static void bind_once(void){
 owner_handle=dlopen("/data/local/tmp/asx/liboh_adapter_bridge.so",RTLD_NOW|RTLD_NOLOAD|RTLD_LOCAL);
 if(!owner_handle){pair_log("[WL-R20-BIND] refuse=existing_owner_missing\n");return;}
 void *base=NULL,*provider_base=NULL;
 owner_get=(OHNativeWindow*(*)(void*))dlsym(owner_handle,"oh_anw_get_oh");
 owner_acquire=(int(*)(void*))dlsym(owner_handle,"oh_anw_try_acquire");
 owner_release=(int(*)(void*))dlsym(owner_handle,"oh_anw_try_release");
 if(!member((void*)owner_get,&base,"owner_get") || !member((void*)owner_acquire,&base,"owner_acquire") || !member((void*)owner_release,&base,"owner_release")){bind_error=-ENOSYS;return;}
 if(!owner_provider(base,&provider_base)){bind_error=-EXDEV;pair_log("[WL-R20-BIND] refuse=owner_provider_instance_unproven\n");return;}
 struct r15_provider p;
#define RESOLVE(field,name) do { p.field=(__typeof__(p.field))dlsym(owner_handle,#name); if(!member((void*)p.field,&provider_base,#name)){bind_error=-EXDEV;pair_log("[WL-R20-BIND] refuse=provider_member name=%s\n",#name);return;} } while(0)
 RESOLVE(request,OH_NativeWindow_NativeWindowRequestBuffer);
 RESOLVE(handle,OH_NativeWindow_GetBufferHandleFromNative);
 RESOLVE(convert,OH_NativeBuffer_FromNativeWindowBuffer);
 RESOLVE(map,OH_NativeBuffer_Map);RESOLVE(unmap,OH_NativeBuffer_Unmap);
 RESOLVE(flush,OH_NativeWindow_NativeWindowFlushBuffer);
 RESOLVE(abort,OH_NativeWindow_NativeWindowAbortBuffer);
#undef RESOLVE
 const struct r20_owner own={NULL,unwrap};bind_error=r20_create(&p,&own,&context);
 pair_log("[WL-R20-BIND] result=%d context=%p owner_base=%p provider_base=%p\n",bind_error,(void*)context,base,provider_base);
}
static void diagnostic(const char *op,void *window,void *caller,int rc,const struct r14_report *r){
 unsigned n=__atomic_fetch_add(&log_count,1,__ATOMIC_RELAXED);if(n>=64)return;
 pair_log("[WL-R20-PAIR] seq=%u op=%s window=%p caller=%p rc=%d request=%u/%d handle=%u/%d convert=%u/%d map=%u/%d unmap=%u/%d flush=%u/%d abort=%u/%d retained=%u\n",n,op,window,caller,rc,r->request_called,r->request_rc,r->handle_called,r->handle_rc,r->convert_called,r->convert_rc,r->map_called,r->map_rc,r->unmap_called,r->unmap_rc,r->flush_called,r->flush_rc,r->abort_called,r->abort_rc,r->retained);
}
__attribute__((visibility("hidden"))) int wl_r20_pair_lock(void *window,void *out,void *dirty,void *caller){
 if(!player_caller(caller))return original_lock_refusal();
 if(!window || !out)return fail(-EINVAL);
 pthread_once(&once,bind_once);if(bind_error || !context)return fail(bind_error);
 int acquired=owner_acquire(window);
 if(acquired!=1){struct r14_report rejected={0};diagnostic("owner_refused",window,caller,-ENODEV,&rejected);return fail(-ENODEV);}
 struct r14_report report={0};int rc=r20_lock(context,window,out,dirty,&report);
 /* One additional wrapper reference remains through success or uncertain failure. */
 if(rc && !report.retained && owner_release(window)!=1)rc=-EPROTO;
 diagnostic("lock",window,caller,rc,&report);return rc?fail(rc):0;
}
__attribute__((visibility("hidden"))) int wl_r20_pair_unlock(void *window,void *caller){
 if(!player_caller(caller))return fail(-ENODEV);
 if(!window)return fail(-EINVAL);pthread_once(&once,bind_once);if(bind_error || !context)return fail(bind_error);
 struct r14_report report={0};int rc=r20_unlock(context,window,&report);
 if(!rc && owner_release(window)!=1)rc=-EPROTO;
 diagnostic("unlock",window,caller,rc,&report);return rc?fail(rc):0;
}
