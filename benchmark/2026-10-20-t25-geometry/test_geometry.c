#define _GNU_SOURCE 1
#include <dlfcn.h>
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <stdarg.h>
static void *fake_dlopen(const char *,int);
static void *fake_dlsym(void *,const char *);
static int fake_dladdr(const void *,Dl_info *);
#define dlopen fake_dlopen
#define dlsym fake_dlsym
#define dladdr fake_dladdr
#include "geometry.c"
#undef dlopen
#undef dlsym
#undef dladdr
static unsigned char owner[0x175000] __attribute__((aligned(16)));
static unsigned char surface[0x70000] __attribute__((aligned(16)));
static unsigned char player[0x473000] __attribute__((aligned(16)));
static unsigned char otherplayer[0x473000] __attribute__((aligned(16)));
static int selfbase,otherbase,owner_token,self_token,w,oh;
static int refs=1,acq_fail,get_fail,rel_fail,geo_rc,fmt_rc,expected_w,expected_h,expected_f,acalls,gcalls,rcalls,ocalls;
static char journal[20];static unsigned jp;
static const char *mode;
static void event(char c){assert(jp<sizeof(journal)-1);journal[jp++]=c;}
static int acquire(void *v){acalls++;event('A');assert(refs==1);if(v!=&w || acq_fail)return 0;refs++;return 1;}
static void *get(void *v){gcalls++;event('G');assert(v==&w && refs==2);return get_fail?NULL:&oh;}
static int release(void *v){rcalls++;event('R');assert(v==&w && refs==2);refs--;return rel_fail?0:1;}
static int32_t opt(void *v,int32_t code,...){assert(v==&oh && refs==2);ocalls++;va_list ap;va_start(ap,code);int rc;
 if(code==0){event('D');int wi=va_arg(ap,int),he=va_arg(ap,int);assert(wi==expected_w && he==expected_h);rc=geo_rc;}
 else{assert(code==3);event('F');assert(va_arg(ap,int)==expected_f);rc=fmt_rc;}
 va_end(ap);return rc;
}
static void *fake_dlopen(const char *path,int flags){assert(flags&RTLD_NOLOAD);if(!strcmp(mode,"missing_owner"))return NULL;return strstr(path,"bridge")?&owner_token:&self_token;}
static void *fake_dlsym(void *h,const char *n){
 if(h==&self_token){if(!strcmp(n,"ANativeWindow_lock"))return (char*)&selfbase+1;if(!strcmp(n,"ANativeWindow_unlockAndPost"))return (char*)&selfbase+2;if(!strcmp(n,"ANativeWindow_setBuffersGeometry"))return (char*)&selfbase+3;return NULL;}
 assert(h==&owner_token);
 if(!strcmp(n,"oh_anw_get_oh"))return owner+0x125dc0+(!strcmp(mode,"wrong_owner_offset")?4:0);
 if(!strcmp(n,"oh_anw_try_acquire"))return owner+0x125dfc;
 if(!strcmp(n,"oh_anw_try_release"))return owner+0x125e4c;
 if(!strcmp(n,"OH_NativeWindow_NativeObjectReference"))return surface+0x100+(!strcmp(mode,"slot_scope_drift")?8:0);
 if(!strcmp(n,"OH_NativeWindow_NativeObjectUnreference"))return surface+0x200;
 if(!strcmp(n,"OH_NativeWindow_NativeWindowHandleOpt"))return !strcmp(mode,"missing_opt")?NULL:surface+0x68c10+(!strcmp(mode,"wrong_opt_offset")?4:0);
 return NULL;
}
static int fake_dladdr(const void *f,Dl_info *i){memset(i,0,sizeof(*i));uintptr_t a=(uintptr_t)f;
 if(f==(void*)&bind_once || f==(char*)&selfbase+1 || f==(char*)&selfbase+2 || f==(char*)&selfbase+3){i->dli_fbase=&selfbase;i->dli_fname="/data/local/tmp/asx/webview-t-lib/libwebview_bionic_shim.so";return 1;}
 if(a>=(uintptr_t)owner && a<(uintptr_t)owner+sizeof(owner)){i->dli_fbase=owner;i->dli_fname="/data/local/tmp/asx/liboh_adapter_bridge.so";return 1;}
 if(a>=(uintptr_t)surface && a<(uintptr_t)surface+sizeof(surface)){i->dli_fbase=(!strcmp(mode,"mixed_provider") && f==surface+0x200)||(!strcmp(mode,"foreign_opt") && f==surface+0x68c10)?(void*)&otherbase:(void*)surface;i->dli_fname="/system/lib64/libsurface.z.so";return 1;}
 if(f==player+0x1000 || f==otherplayer+0x1000){i->dli_fbase=f==player+0x1000?(void*)player:(void*)otherplayer;i->dli_fname=!strcmp(mode,"foreign_caller")?"/other/libttmplayer.so":"/data/local/tmp/asx/lib/arm64-v8a/libttmplayer.so";return 1;}
 return 0;
}
static void elf(void *v,size_t size){struct r25_ehdr *e=v;memcpy(e->ident,"\177ELF\2\1\1",7);e->type=3;e->machine=183;e->ehsize=64;e->phoff=64;e->phsize=56;e->phnum=1;struct r25_phdr *p=(void*)((char*)v+64);p->type=1;p->flags=4;p->memsz=size;}
static void player_slots(unsigned char *v){*(void**)(v+0x472490)=(char*)&selfbase+1;*(void**)(v+0x472760)=(char*)&selfbase+2;*(void**)(v+0x472048)=(char*)&selfbase+3;}
int main(int argc,char **argv){assert(argc==2);mode=argv[1];struct r25_report report;
 if(!strncmp(mode,"core_",5)){
  struct r25_ops o={acquire,get,release,opt};expected_w=1080;expected_h=1920;expected_f=11;int f=2,want=0;void *input=&w;
  if(!strcmp(mode,"core_formats")){
   const int in[]={1,2,3,4,0x32315659,42},out[]={12,11,13,3,11,42};
   for(unsigned n=0;n<6;n++){jp=0;memset(journal,0,sizeof(journal));expected_f=out[n];expected_w=n?576:1080;expected_h=n?1024:1920;
    assert(r25_apply(&o,&w,expected_w,expected_h,in[n],&report)==0);assert(!strcmp(journal,"AGDFR") && refs==1 && report.format_called==1);}
   puts("PASS six exact formats and asymmetric dimensions");return 0;
  }
  if(!strcmp(mode,"core_zero")){expected_w=0;expected_h=0;f=0;}
  if(!strcmp(mode,"core_negative")){expected_w=-7;expected_h=-9;f=-1;}
  if(!strcmp(mode,"core_null")){input=NULL;want=-EINVAL;}
  if(!strcmp(mode,"core_foreign")){input=&oh;want=-ENODEV;}
  if(!strcmp(mode,"core_acquire")){acq_fail=1;want=-ENODEV;}
  if(!strcmp(mode,"core_unwrap")){get_fail=1;want=-ENODEV;}
  if(!strcmp(mode,"core_geometry_positive")){geo_rc=40001000;want=geo_rc;}
  if(!strcmp(mode,"core_geometry_negative")){geo_rc=-19;want=geo_rc;}
  if(!strcmp(mode,"core_format")){fmt_rc=40001000;want=fmt_rc;}
  if(!strcmp(mode,"core_release")){rel_fail=1;want=-EPROTO;}
  if(!strcmp(mode,"core_first_failure")){geo_rc=-22;rel_fail=1;want=-22;}
  if(!strcmp(mode,"core_missing")){o.handle_opt=NULL;want=-ENOSYS;}
  assert(r25_apply(&o,input,expected_w,expected_h,f,&report)==want);assert(report.result==want && refs==1);
  if(input==NULL || !o.handle_opt){assert(acalls==0 && ocalls==0 && rcalls==0);}
  else if(input!=&w || acq_fail){assert(!strcmp(journal,"A") && gcalls==0 && rcalls==0 && ocalls==0);}
  else if(get_fail){assert(!strcmp(journal,"AGR") && ocalls==0 && rcalls==1);}
  else if(geo_rc || f<=0){assert(!strcmp(journal,"AGDR") && ocalls==1 && report.format_called==0 && rcalls==1);}
  else{assert(!strcmp(journal,"AGDFR") && ocalls==2 && rcalls==1);}
  puts("PASS actual geometry core journal and return");return 0;
 }
 elf(owner,sizeof(owner));elf(player,sizeof(player));elf(otherplayer,sizeof(otherplayer));
 *(void**)(owner+0x1740a0)=surface+0x100;*(void**)(owner+0x173fc8)=surface+0x200;
 if(!strcmp(mode,"unreadable_owner"))((struct r25_phdr*)(owner+64))->flags=2;
 if(!strcmp(mode,"phdr_overflow"))((struct r25_ehdr*)owner)->phoff=4090;
 pthread_once(&once,bind_once);
 int rejected=!strcmp(mode,"missing_owner")||!strcmp(mode,"wrong_owner_offset")||!strcmp(mode,"slot_scope_drift")||!strcmp(mode,"missing_opt")||!strcmp(mode,"wrong_opt_offset")||!strcmp(mode,"mixed_provider")||!strcmp(mode,"foreign_opt")||!strcmp(mode,"unreadable_owner")||!strcmp(mode,"phdr_overflow");
 if(rejected){assert(dispatch(&w,1080,1920,2,player+0x1000)!=0);assert(bind_error!=0 && acalls==0 && ocalls==0);puts("PASS resolver refuses before wrapper/OH");return 0;}
 assert(bind_error==0);player_slots(player);player_slots(otherplayer);
 if(!strcmp(mode,"mixed_lock"))*(void**)(player+0x472490)=surface+4;
 if(!strcmp(mode,"mixed_unlock"))*(void**)(player+0x472760)=surface+4;
 if(!strcmp(mode,"wrong_geometry"))*(void**)(player+0x472048)=surface+4;
 if(!strcmp(mode,"unreadable_player"))((struct r25_phdr*)(player+64))->flags=2;
 int allowed=admitted_caller(player+0x1000);
 assert(allowed==(!strcmp(mode,"binding_success")||!strcmp(mode,"second_player")));
 if(!strcmp(mode,"second_player"))assert(admitted_caller(otherplayer+0x1000)==0);
 ops=(struct r25_ops){acquire,get,release,opt};expected_w=1080;expected_h=1920;expected_f=11;
 int result=dispatch(&w,1080,1920,2,player+0x1000);
 if(allowed){assert(result==0 && acalls==1 && gcalls==1 && ocalls==2 && rcalls==1 && refs==1 && !strcmp(journal,"AGDFR"));}
 else{assert(result!=0 && acalls==0 && gcalls==0 && ocalls==0 && rcalls==0);}
 puts("PASS actual dispatch provider/player route and owner/OH counts");return 0;
}
