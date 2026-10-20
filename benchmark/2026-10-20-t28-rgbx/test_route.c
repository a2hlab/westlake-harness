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
static unsigned request_calls,map_calls,unmap_calls,flush_calls,abort_calls;
static unsigned char pixels[2048];
/* Only the typed adapter's proven 24-byte prefix is accessible. */
struct BufferHandle {int32_t fd,width,stride,height,size,format;};
static struct BufferHandle bh={-1,17,80,3,240,12};
static int native_obj,buffer_obj,expect_opaque;
static int wanted_format=12;
static void *alloc_fail(void *c,size_t n){(void)c;(void)n;return NULL;}
static const char *mode;
static char journal[128];static unsigned jp;
static void event(char x){assert(jp<127);journal[jp++]=x;journal[jp]=0;}
static int acquire(void *v){assert(v==&wrapper);acalls++;refs++;event('A');return 1;}
static void *get(void *v){assert(v==&wrapper && refs>=2);gcalls++;event('G');return &oh_obj;}
static int release(void *v){assert(v==&wrapper && refs>=2);rcalls++;event('R');if(release_error)return 0;refs--;return 1;}
static int32_t opt(void *v,int32_t code,...){assert(v==&oh_obj && refs>=3);ocalls++;va_list ap;va_start(ap,code);int rc=0;
 if(code==0){assert(va_arg(ap,int)==17);assert(va_arg(ap,int)==3);event('D');rc=geo_error;}
 else{assert(code==3 && va_arg(ap,int)==wanted_format);event('F');}va_end(ap);return rc;}
static int32_t request(OHNativeWindow *v,OHNativeWindowBuffer **out,int *fd){assert(v==(void*)&oh_obj && refs>=2);request_calls++;event('Q');*out=(void*)&buffer_obj;*fd=-1;return 0;}
static BufferHandle *handle(OHNativeWindowBuffer *v){assert(v==(void*)&buffer_obj);event('H');return &bh;}
static int32_t convert(OHNativeWindowBuffer *v,OH_NativeBuffer **out){assert(v==(void*)&buffer_obj);event('C');*out=(void*)&native_obj;return 0;}
static int32_t map(OH_NativeBuffer *v,void **out){assert(v==(void*)&native_obj);map_calls++;event('M');*out=pixels;return 0;}
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
 if(!strcmp(mode,"wrong_lock"))*(void**)(player_image+0x472490)=surface_image+4;
 if(!strcmp(mode,"wrong_unlock"))*(void**)(player_image+0x472760)=surface_image+4;
 if(!strcmp(mode,"wrong_geometry"))*(void**)(player_image+0x472048)=surface_image+4;
 if(!strncmp(mode,"wrong_",6)){
  struct r14_buffer b;assert(ANativeWindow_setBuffersGeometry(&wrapper,17,3,R26_YV12)!=0);assert(ANativeWindow_lock(&wrapper,&b,NULL)!=0);assert(ANativeWindow_unlockAndPost(&wrapper)!=0);
  assert(acalls==0 && gcalls==0 && rcalls==0 && ocalls==0 && request_calls==0);puts("PASS real exported dispatch refuses with zero owner/OH calls");return 0;
 }
 if(!strcmp(mode,"rgb") || !strcmp(mode,"unknown")){
  const int af[]={1,2,3,4,5,22,43},hf[]={12,11,13,3,20,39,34},bytes[]={4,4,3,2,4,8,4},mapf[]={12,12,13,3,5,22,43};
  for(unsigned i=0;i<7;i++){
   wanted_format=mapf[i];if(!strcmp(mode,"rgb"))assert(ANativeWindow_setBuffersGeometry(&wrapper,17,3,af[i])==0);
   bh=(struct BufferHandle){-1,17,20*bytes[i],3,60*bytes[i],(!strcmp(mode,"rgb") && i==1)?12:hf[i]};memset(pixels,0x65,sizeof(pixels));jp=0;journal[0]=0;
   struct r14_buffer b;assert(ANativeWindow_lock(&wrapper,&b,NULL)==0);assert(b.width==17 && b.height==3 && b.stride==20 && b.format==af[i] && b.bits==pixels);assert(r26_reserved(cache)==0);
   assert(ANativeWindow_unlockAndPost(&wrapper)==0);assert(!strcmp(journal,"AGQHCMUPR"));for(unsigned n=0;n<sizeof(pixels);n++){int alpha=!strcmp(mode,"rgb") && i==1 && n<240 && n%80<68 && n%4==3;assert(pixels[n]==(alpha?255:0x65));}
  }
  assert(r20_destroy(context)==0);assert(r26_destroy(cache)==0);assert(refs==1);puts("PASS seven old RGB formats through exports/pair/R15/R14 unchanged");return 0;
 }
 if(!strncmp(mode,"rgbx",4)){
  assert(ANativeWindow_setBuffersGeometry(&wrapper,17,3,2)==0);assert(refs==2);
  if(!strcmp(mode,"rgbx_format0"))assert(ANativeWindow_setBuffersGeometry(&wrapper,17,3,0)==0);
  if(!strcmp(mode,"rgbx_geometry_failure")){geo_error=-19;assert(ANativeWindow_setBuffersGeometry(&wrapper,17,3,R26_YV12)==-19);geo_error=0;}
  if(!strcmp(mode,"rgbx_bad_format"))bh.format=11;
  memset(pixels,0x39,sizeof(pixels));jp=0;journal[0]=0;
  struct r14_buffer b;int rc=ANativeWindow_lock(&wrapper,&b,NULL);
  if(!strcmp(mode,"rgbx_bad_format")){assert(rc==-EINVAL && !b.bits && !b.format);assert(unmap_calls==1 && abort_calls==1 && !flush_calls);for(unsigned i=0;i<sizeof(pixels);i++)assert(pixels[i]==0x39);puts("PASS RGBX bad native format refuses publication");return 0;}
  assert(!rc && b.format==2 && b.width==17 && b.height==3 && b.stride==20 && b.bits==pixels && r26_reserved(cache)==0);
  for(unsigned i=0;i<sizeof(pixels);i++)assert(pixels[i]==0x39);
  if(!strcmp(mode,"rgbx_precheck"))cache->entries[0].packed.size_bytes=1;
  else expect_opaque=1;
  if(!strcmp(mode,"rgbx_unmap"))unmap_error=-5;
  if(!strcmp(mode,"rgbx_flush"))flush_error=-7;
  rc=ANativeWindow_unlockAndPost(&wrapper);
  int precheck=!strcmp(mode,"rgbx_precheck");assert(rc==(precheck?-EINVAL:(unmap_error?unmap_error:flush_error)));
  for(unsigned i=0;i<sizeof(pixels);i++){int alpha=!precheck && i<240 && i%80<68 && i%4==3;assert(pixels[i]==(alpha?255:0x39));}
  assert(unmap_calls==1 && flush_calls==(!precheck && !unmap_error) && abort_calls==(unsigned)precheck);
  if(!rc)assert(!strcmp(journal,"AGQHCMUPR"));
#ifdef WL_T27_OBSERVER
  wl_t27_record rec[8];size_t n=wl_t27_snapshot(rec,8);assert(n==2 && rec[1].scratch_format==2 && rec[1].scratch_pix_stride==20);
#endif
  unsigned u=unmap_calls,f=flush_calls;assert(ANativeWindow_unlockAndPost(&wrapper)!=0 && u==unmap_calls && f==flush_calls);
  if(!rc){assert(refs==2);assert(r20_destroy(context)==0);assert(r26_destroy(cache)==0);assert(refs==1);}else assert(r20_destroy(context)==-EBUSY);
  printf("PASS actual RGBX2 route %s rc=%d\n",mode,rc);return 0;
 }
 assert(ANativeWindow_setBuffersGeometry(&wrapper,17,3,R26_YV12)==0);assert(refs==2 && wanted_format==12);
 if(!strcmp(mode,"geometry_failure")){geo_error=-19;assert(ANativeWindow_setBuffersGeometry(&wrapper,17,3,2)==-19);geo_error=0;}
 if(!strcmp(mode,"unmap_failure"))unmap_error=-5;if(!strcmp(mode,"flush_failure"))flush_error=-7;
 if(!strcmp(mode,"alloc_failure"))cache->allocator.zero=alloc_fail;
 if(!strcmp(mode,"format_refuse"))bh.format=11;
 if(!strcmp(mode,"alloc_failure") || !strcmp(mode,"format_refuse")){
  struct r14_buffer out={0};int bad=ANativeWindow_lock(&wrapper,&out,NULL);
  assert(bad==(!strcmp(mode,"alloc_failure")?-ENOMEM:-EINVAL));assert(out.bits==NULL && out.format==0);
  assert(unmap_calls==1 && abort_calls==1 && flush_calls==0 && refs==3 && r26_reserved(cache)==0);
  assert(ANativeWindow_unlockAndPost(&wrapper)!=0);assert(unmap_calls==1 && abort_calls==1);puts("PASS actual prepare failure publishes nothing; cleanup once and retained");return 0;
 }
 struct r14_buffer b;struct r14_rect rect;assert(ANativeWindow_lock(&wrapper,&b,&rect)==0);assert(refs==3 && b.format==R26_YV12 && b.width==17 && b.height==3 && b.stride==32 && b.bits!=pixels && rect.right==17 && rect.bottom==3);
 struct r26_layout l;assert(r26_layout(17,3,&l)==0);memset(b.bits,81,l.v);memset((char*)b.bits+l.v,240,l.cs*l.ch);memset((char*)b.bits+l.u,90,l.cs*l.ch);
 memset(pixels,0xcc,sizeof(pixels));
 if(!strcmp(mode,"precheck_failure") || !strcmp(mode,"abort_failure")){
  cache->entries[0].packed.size_bytes=1;if(!strcmp(mode,"abort_failure"))abort_error=-11;
  assert(ANativeWindow_unlockAndPost(&wrapper)==-EINVAL);for(unsigned n=0;n<sizeof(pixels);n++)assert(pixels[n]==0xcc);
  assert(unmap_calls==1 && abort_calls==1 && flush_calls==0);struct r14_report r;assert(r20_report(context,&wrapper,&r)==0 && r.primary==-EINVAL && r.abort_rc==abort_error && r.retained);
  assert(ANativeWindow_unlockAndPost(&wrapper)!=0 && unmap_calls==1 && abort_calls==1);puts("PASS actual before-Unmap precheck: untouched destination, no Flush, original error and abort result retained");return 0;
 }
 if(!strcmp(mode,"owner_release_failure"))release_error=1;
 int rc=ANativeWindow_unlockAndPost(&wrapper);
#ifdef WL_T27_OBSERVER
 wl_t27_record observed[8];size_t nobs=wl_t27_snapshot(observed,8);assert(nobs==2);assert(observed[0].point==WL_T27_CPU_NATIVE_CONFIG && observed[1].point==WL_T27_ANDROID_OUTPUT);assert(observed[0].txn_id==observed[1].txn_id && observed[1].scratch_format==R26_YV12 && observed[1].scratch_pix_stride==32 && observed[1].scratch_w==17 && observed[1].scratch_h==3);
#endif
 assert(rc==(unmap_error?unmap_error:(flush_error?flush_error:(release_error?-EPROTO:0))));
 for(unsigned row=0;row<3;row++){for(unsigned x=0;x<17;x++){unsigned char *v=pixels+row*80+x*4;assert(v[0]==255 && v[1]==0 && v[2]==0 && v[3]==255);}for(unsigned n=68;n<80;n++)assert(pixels[row*80+n]==0xcc);}
 unsigned u=unmap_calls,f=flush_calls;assert(ANativeWindow_unlockAndPost(&wrapper)!=0);assert(unmap_calls==u && flush_calls==f);
 if(release_error){assert(refs==3 && r26_destroy(cache)==-EBUSY);puts("PASS pair release failure poisons request cache");return 0;}
 if(rc){assert(refs==3 && r26_reserved(cache)>0 && r20_destroy(context)==-EBUSY);if(unmap_error)assert(flush_calls==0);}
 else{assert(refs==2 && r26_reserved(cache)==0);assert(r20_destroy(context)==0);assert(r26_destroy(cache)==0);assert(refs==1);}
 printf("PASS actual exported shim/pair/typed-provider/derived-R14/T26 chain; rc=%d\n",rc);return 0;
}
