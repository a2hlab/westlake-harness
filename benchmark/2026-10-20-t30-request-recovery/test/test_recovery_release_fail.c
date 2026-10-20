#define _GNU_SOURCE 1
#include <dlfcn.h>
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
static void *fake_dlopen(const char *,int);
static void *fake_dlsym(void *,const char *);
static int fake_dladdr(const void *,Dl_info *);
static void *test_pc;
#define dlopen fake_dlopen
#define dlsym fake_dlsym
#define dladdr fake_dladdr
#define __builtin_return_address(level) test_pc
#include "derived/geometry.c"
#ifdef WL_T27_OBSERVER
#include "observer.h"
#endif
#define once pair_once
#define bind_once pair_bind_once
#define player_base pair_player_base
#define bind_error pair_bind_error
#define log_count pair_log_count
#define leaf pair_leaf
#define readable_slot pair_readable_slot
#define owner_handle pair_owner_handle
#define diagnostic pair_diagnostic
#include "derived/pair.c"
#undef once
#undef bind_once
#undef player_base
#undef bind_error
#undef log_count
#undef leaf
#undef readable_slot
#undef owner_handle
#undef diagnostic
#include "derived/shim_exports.c"
#include "yv12.c"
#undef __builtin_return_address
#undef dlopen
#undef dlsym
#undef dladdr
static unsigned char owner_image[0x175000] __attribute__((aligned(16)));
static unsigned char surface_image[0x70000] __attribute__((aligned(16)));
static unsigned char player_image[0x473000] __attribute__((aligned(16)));
static int self_base,owner_token,self_token,oh_obj,wrapper;
static int refs=1,acalls,gcalls,rcalls,ocalls,geo_error,unmap_error,flush_error,abort_error,release_error;
static int pressure_wrappers[8],pressure_oh[8],request_error,map_error,errno_route,handle_null,convert_error;
static int request_null;   /* T30: first Request returns no resource (buf NULL, fd -1, rc 40601000) */
static int wrapper_ok(void *v){if(v==&wrapper)return 1;for(unsigned i=0;i<8;i++)if(v==pressure_wrappers+i)return 1;return 0;}
static unsigned request_calls,map_calls,unmap_calls,flush_calls,abort_calls;
static unsigned char pixels[2048];
/* Only the typed adapter's proven 24-byte prefix is accessible. */
struct BufferHandle {int32_t fd,width,stride,height,size,format;};
static struct BufferHandle bh={-1,17,80,3,240,12};
static int native_obj,buffer_obj,expect_opaque;
static int wanted_format=12;
static const char *mode;
static char journal[128];static unsigned jp;
static void event(char x){assert(jp<127);journal[jp++]=x;journal[jp]=0;}
static int acquire(void *v){assert(wrapper_ok(v));acalls++;refs++;event('A');return 1;}
static void *get(void *v){assert(wrapper_ok(v) && refs>=2);gcalls++;event('G');for(unsigned i=0;i<8;i++)if(v==pressure_wrappers+i)return pressure_oh+i;return &oh_obj;}
static int release(void *v){assert(wrapper_ok(v) && refs>=2);rcalls++;event('R');if(release_error)return 0;refs--;if(errno_route)errno=ENOTTY;return 1;}
static int32_t opt(void *v,int32_t code,...){assert(v==&oh_obj && refs>=3);ocalls++;va_list ap;va_start(ap,code);int rc=0;
 if(code==0){assert(va_arg(ap,int)==17);assert(va_arg(ap,int)==3);event('D');rc=geo_error;}
 else{assert(code==3 && va_arg(ap,int)==wanted_format);event('F');}va_end(ap);return rc;}
static int32_t request(OHNativeWindow *v,OHNativeWindowBuffer **out,int *fd){assert(v==(void*)&oh_obj && refs>=2);request_calls++;event('Q');if(request_null && request_calls==1){*out=NULL;*fd=-1;return 40601000;}*out=(void*)&buffer_obj;*fd=-1;return request_error;}
static BufferHandle *handle(OHNativeWindowBuffer *v){assert(v==(void*)&buffer_obj);event('H');return handle_null?NULL:&bh;}
static int32_t convert(OHNativeWindowBuffer *v,OH_NativeBuffer **out){assert(v==(void*)&buffer_obj);event('C');*out=(void*)&native_obj;return convert_error;}
static int32_t map(OH_NativeBuffer *v,void **out){assert(v==(void*)&native_obj);map_calls++;event('M');*out=pixels;return map_error;}
static int32_t unmap(OH_NativeBuffer *v){assert(v==(void*)&native_obj);unmap_calls++;event('U');if(expect_opaque)for(int y=0;y<3;y++)for(int x=0;x<17;x++)assert(pixels[y*80+x*4+3]==255);return unmap_error;}
static int32_t flush(OHNativeWindow *v,OHNativeWindowBuffer *b,int fd,Region region){assert(v==(void*)&oh_obj && b==(void*)&buffer_obj && fd==-1);assert(region.rectNumber==1 && region.rects[0].w==17 && region.rects[0].h==3);flush_calls++;event('P');return flush_error;}
static int32_t abort_buffer(OHNativeWindow *v,OHNativeWindowBuffer *b){assert(v==(void*)&oh_obj && b==(void*)&buffer_obj);abort_calls++;event('B');return abort_error;}
static void *fake_dlopen(const char *p,int flags){assert(flags&RTLD_NOLOAD);return strstr(p,"bridge")?&owner_token:&self_token;}
static void *fake_dlsym(void *h,const char *n){
 if(h==&self_token){if(!strcmp(n,"ANativeWindow_lock"))return (void*)ANativeWindow_lock;if(!strcmp(n,"ANativeWindow_unlockAndPost"))return (void*)ANativeWindow_unlockAndPost;if(!strcmp(n,"ANativeWindow_setBuffersGeometry"))return (void*)ANativeWindow_setBuffersGeometry;return NULL;}
 assert(h==&owner_token);
 const char *owners[]={"oh_anw_get_oh","oh_anw_try_acquire","oh_anw_try_release"};const size_t offsets[]={0x125dc0,0x125dfc,0x125e4c};
 for(unsigned i=0;i<3;i++)if(!strcmp(n,owners[i]))return owner_image+offsets[i];
 if(!strcmp(n,"OH_NativeWindow_NativeObjectReference"))return surface_image+0x100;
 if(!strcmp(n,"OH_NativeWindow_NativeObjectUnreference"))return surface_image+0x200;
 if(!strcmp(n,"OH_NativeWindow_NativeWindowHandleOpt"))return surface_image+0x68c10;
 const char *names[]={"OH_NativeWindow_NativeWindowRequestBuffer","OH_NativeWindow_GetBufferHandleFromNative","OH_NativeBuffer_FromNativeWindowBuffer","OH_NativeBuffer_Map","OH_NativeBuffer_Unmap","OH_NativeWindow_NativeWindowFlushBuffer","OH_NativeWindow_NativeWindowAbortBuffer"};
 for(unsigned i=0;i<7;i++)if(!strcmp(n,names[i]))return surface_image+0x300+i*16;
 return NULL;
}
static int fake_dladdr(const void *p,Dl_info *i){memset(i,0,sizeof(*i));uintptr_t a=(uintptr_t)p;
 if(p==(void*)bind_once || p==(void*)pair_bind_once || p==(void*)ANativeWindow_lock || p==(void*)ANativeWindow_unlockAndPost || p==(void*)ANativeWindow_setBuffersGeometry){i->dli_fbase=&self_base;i->dli_fname="/data/local/tmp/asx/webview-t-lib/libwebview_bionic_shim.so";return 1;}
 if(a>=(uintptr_t)owner_image && a<(uintptr_t)owner_image+sizeof(owner_image)){i->dli_fbase=owner_image;i->dli_fname="/data/local/tmp/asx/liboh_adapter_bridge.so";return 1;}
 if(a>=(uintptr_t)surface_image && a<(uintptr_t)surface_image+sizeof(surface_image)){i->dli_fbase=surface_image;i->dli_fname="/system/lib64/libsurface.z.so";return 1;}
 if(p==player_image+0x1000){i->dli_fbase=player_image;i->dli_fname=!strcmp(mode,"wrong_caller")?"/foreign/libttmplayer.so":"/data/local/tmp/asx/lib/arm64-v8a/libttmplayer.so";return 1;}return 0;
}
static void elf(void *v,size_t size){struct r25_ehdr *e=v;memcpy(e->ident,"\177ELF\2\1\1",7);e->type=3;e->machine=183;e->ehsize=64;e->phoff=64;e->phsize=56;e->phnum=1;struct r25_phdr *p=(void*)((char*)v+64);p->type=1;p->flags=4;p->memsz=size;}
int main(int argc,char **argv){assert(argc==2);mode=argv[1];test_pc=player_image+0x1000;
 elf(owner_image,sizeof(owner_image));elf(player_image,sizeof(player_image));
 *(void**)(owner_image+0x1740a0)=surface_image+0x100;*(void**)(owner_image+0x173fc8)=surface_image+0x200;
 *(void**)(player_image+0x472490)=(void*)ANativeWindow_lock;*(void**)(player_image+0x472760)=(void*)ANativeWindow_unlockAndPost;*(void**)(player_image+0x472048)=(void*)ANativeWindow_setBuffersGeometry;
 pthread_once(&once,bind_once);assert(bind_error==0);pthread_once(&pair_once,pair_bind_once);assert(pair_bind_error==0);
 /* Resolver/gate ran on actual ELF projections. Replace only already-bound
  * capability addresses with executable counters, never the gate or dispatch. */
 assert(r20_destroy(context)==0);assert(r26_destroy(cache)==0);
 ops=(struct r25_ops){acquire,get,release,opt};struct r26_owner own={acquire,get,release};assert(r26_create(&own,NULL,&cache)==0);
 owner_acquire=acquire;owner_get=(OHNativeWindow*(*)(void*))get;owner_release=release;
 struct r15_provider p={request,handle,convert,map,unmap,flush,abort_buffer};const struct r20_owner cap={NULL,unwrap};assert(r20_create(&p,&cap,&context)==0);
 /* T30 scenario: recovery-path owner_release failure. A proven resource-free first Request fails
  * (buffer NULL, fd -1); the derived R14/R15 recover (report.retained==0), so the REAL pair.c runs
  * owner_release during the fail path. We inject that release returning != 1. Expect -EPROTO, the real
  * release actually attempted, the owner ref left UNBALANCED (not force-zeroed), and R14 RECOVERED
  * (freed, not FAILED) -- i.e. recovery is not faked and the failed release is not masked. */
 assert(!strcmp(mode,"recovery_release_fail"));
 assert(ANativeWindow_setBuffersGeometry(&wrapper,17,3,2)==0);assert(refs==2);
 int rel_before=rcalls,refs_before=refs;  /* geometry already balanced its own owner ref */
 request_null=1;release_error=1;
 struct r14_buffer b;int rc=ANativeWindow_lock(&wrapper,&b,NULL);
 struct r14_report report={0};int report_rc=r20_report(context,&wrapper,&report);
 printf("{\"mode\":\"recovery_release_fail\",\"rc\":%d,\"request_calls\":%u,\"map_calls\":%u,\"flush_calls\":%u,"
        "\"release_calls\":%d,\"release_delta\":%d,\"refs\":%d,\"report_rc\":%d,\"journal\":\"%s\"}\n",
        rc,request_calls,map_calls,flush_calls,rcalls,rcalls-rel_before,refs,report_rc,journal);
 assert(rc==-EPROTO);                     /* owner_release failed during recovery -> -EPROTO, not swallowed */
 assert(request_calls==1 && !map_calls && !flush_calls && !b.bits && !b.format);
 assert(rcalls==rel_before+1);            /* the lock's recovery attempted owner_release exactly once */
 assert(refs==refs_before+1);             /* ref NOT force-balanced: the failed release left it held (2 -> 3) */
 assert(report_rc==-ENOENT);              /* R14 slot RECOVERED (freed), never left FAILED/poisoned */
 puts("PASS real pair recovery + injected owner_release failure: -EPROTO, R14 freed (report -ENOENT), "
      "owner ref left unbalanced (no force-zero, failure not masked)");
 return 0;
}
