#define _GNU_SOURCE 1
#include <dlfcn.h>
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "entry.h"
static void *fake_dlopen(const char *,int);
static void *fake_dlsym(void *,const char *);
static int fake_dladdr(const void *,Dl_info *);
#define dlopen fake_dlopen
#define dlsym fake_dlsym
#define dladdr fake_dladdr
#include "pair.c"
#undef dlopen
#undef dlsym
#undef dladdr
static int refs=1,requests,flushes,mixed_provider,map_error,mixed_slots,resolver_drift,bad_phdr,bad_offset;
static unsigned char owner_image[0x175000] __attribute__((aligned(16)));
static int owner_token,provider_token,other_provider_token,window_token,oh_token,buffer_token,native_token,player_token,other_player_token;
static int f_ref(void *p){(void)p;return 0;}
static int f_unref(void *p){(void)p;return 0;}
static int f_other(void *p){(void)p;return 0;}
static int handle_words[6]={0,2,8,2,16,12};
static unsigned char bits[16];
static OHNativeWindow *f_get(void *w){return w==&window_token?(OHNativeWindow*)&oh_token:NULL;}
static int f_acquire(void *w){if(w!=&window_token)return 0;refs++;return 1;}
static int f_release(void *w){assert(w==&window_token);refs--;return 1;}
static int32_t f_request(OHNativeWindow*w,OHNativeWindowBuffer **b,int*fd){assert(w==(void*)&oh_token);requests++;*b=(void*)&buffer_token;*fd=-1;return 0;}
static BufferHandle *f_handle(OHNativeWindowBuffer*b){assert(b==(void*)&buffer_token);return (void*)handle_words;}
static int32_t f_convert(OHNativeWindowBuffer*b,OH_NativeBuffer**n){assert(b==(void*)&buffer_token);*n=(void*)&native_token;return 0;}
static int32_t f_map(OH_NativeBuffer*n,void**p){assert(n==(void*)&native_token);if(map_error)return -EIO;*p=bits;return 0;}
static int32_t f_unmap(OH_NativeBuffer*n){assert(n==(void*)&native_token);return 0;}
static int32_t f_flush(OHNativeWindow*w,OHNativeWindowBuffer*b,int fd,Region r){assert(w==(void*)&oh_token && b==(void*)&buffer_token && fd==-1 && r.rectNumber==1);flushes++;return 0;}
static int32_t f_abort(OHNativeWindow*w,OHNativeWindowBuffer*b){assert(w==(void*)&oh_token && b==(void*)&buffer_token);return 0;}
static struct {const char *name;void *fn;int owner;} symbols[]={
 {"oh_anw_get_oh",f_get,1},{"oh_anw_try_acquire",f_acquire,1},{"oh_anw_try_release",f_release,1},
 {"OH_NativeWindow_NativeWindowRequestBuffer",f_request,0},{"OH_NativeWindow_GetBufferHandleFromNative",f_handle,0},
 {"OH_NativeBuffer_FromNativeWindowBuffer",f_convert,0},{"OH_NativeBuffer_Map",f_map,0},{"OH_NativeBuffer_Unmap",f_unmap,0},
 {"OH_NativeWindow_NativeWindowFlushBuffer",f_flush,0},{"OH_NativeWindow_NativeWindowAbortBuffer",f_abort,0}};
static void *fake_dlopen(const char *path,int mode){assert(mode&RTLD_NOLOAD);return strstr(path,"bridge")?&owner_token:&provider_token;}
static void *fake_dlsym(void *h,const char *name){assert(h==&owner_token);
 if(!strcmp(name,"oh_anw_get_oh"))return owner_image+0x125dc0+(bad_offset?4:0);
 if(!strcmp(name,"oh_anw_try_acquire"))return owner_image+0x125dfc;
 if(!strcmp(name,"oh_anw_try_release"))return owner_image+0x125e4c;
 if(!strcmp(name,"OH_NativeWindow_NativeObjectReference"))return resolver_drift?(void*)f_other:(void*)f_ref;
 if(!strcmp(name,"OH_NativeWindow_NativeObjectUnreference"))return mixed_slots?(void*)f_other:(void*)f_unref;
for(size_t i=0;i<sizeof(symbols)/sizeof(*symbols);i++)if(!strcmp(name,symbols[i].name))return symbols[i].fn;return NULL;}
static int fake_dladdr(const void *fn,Dl_info *i){
 memset(i,0,sizeof(*i));
 if(fn==(void*)1 || fn==(void*)2 || fn==(void*)3 || fn==(void*)4){i->dli_fbase=fn==(void*)4?&other_player_token:&player_token;i->dli_fname=(fn==(void*)1 || fn==(void*)4)?"/data/local/tmp/asx/lib/arm64-v8a/libttmplayer.so":fn==(void*)2?"/data/local/tmp/asx/lib/arm64-v8a/other.so":"/unrelated/libttmplayer.so";return 1;}
 if(fn==owner_image+0x125dc0 || fn==owner_image+0x125dc4 || fn==owner_image+0x125dfc || fn==owner_image+0x125e4c){i->dli_fbase=owner_image;i->dli_fname="/data/local/tmp/asx/liboh_adapter_bridge.so";return 1;}
 if(fn==(void*)f_ref || fn==(void*)f_unref || fn==(void*)f_other){i->dli_fbase=mixed_slots && fn==(void*)f_other?&other_provider_token:&provider_token;i->dli_fname="/system/lib64/libsurface.z.so";return 1;}
 for(size_t j=0;j<sizeof(symbols)/sizeof(*symbols);j++)if(fn==symbols[j].fn){i->dli_fbase=symbols[j].owner?&owner_token:(mixed_provider && fn==(void*)f_map?&other_provider_token:&provider_token);i->dli_fname=symbols[j].owner?"/data/local/tmp/asx/liboh_adapter_bridge.so":"/system/lib64/libsurface.z.so";return 1;}return 0;
}
int main(int argc,char**argv){
 assert(argc==2);struct r14_buffer out;struct r14_rect dirty;int rc;
 if(!strcmp(argv[1],"nonplayer") || !strcmp(argv[1],"foreign_same_basename")){
  void *caller=!strcmp(argv[1],"nonplayer")?(void*)2:(void*)3;
  rc=wl_r20_pair_lock(&window_token,&out,&dirty,caller);assert(rc==-ENODEV && errno==ENODEV && refs==1 && requests==0);
  assert(wl_r20_pair_lock(&window_token,&out,&dirty,caller)==-ENODEV && errno==ENODEV && refs==1 && requests==0);assert(wl_r20_pair_unlock(&window_token,caller)==-ENODEV && errno==ENODEV);puts("PASS nonplayer untouched");return 0;
 }
 mixed_provider=!strcmp(argv[1],"mixed_provider");map_error=!strcmp(argv[1],"failed_retained");mixed_slots=!strcmp(argv[1],"mixed_slots");resolver_drift=!strcmp(argv[1],"slot_resolver_drift");bad_phdr=!strcmp(argv[1],"unreadable_slot");bad_offset=!strcmp(argv[1],"wrong_owner_offset");
 struct r20_ehdr *elf=(void*)owner_image;memcpy(elf->ident,"\177ELF\2\1\1",7);elf->machine=183;elf->type=3;elf->ehsize=64;elf->phsize=56;elf->phoff=64;elf->phnum=1;
 struct r20_phdr *ph=(void*)(owner_image+64);ph->type=1;ph->flags=bad_phdr?2:4;ph->memsz=sizeof(owner_image);
 *(void**)(owner_image+0x1740a0)=(void*)f_ref;*(void**)(owner_image+0x173fc8)=mixed_slots?(void*)f_other:(void*)f_unref;
 /* Exercise the actual once binding and ELF/GOT gates. Owner callable methods
  * are counter seams after successful binding; fake ELF addresses are not code. */
 pthread_once(&once,bind_once);
 if(mixed_provider || mixed_slots || resolver_drift || bad_phdr || bad_offset){assert(bind_error==-EXDEV && !context && refs==1 && requests==0);puts("PASS owner/GOT/provider mismatch refused before context");return 0;}
 assert(bind_error==0 && context);owner_get=f_get;owner_acquire=f_acquire;owner_release=f_release;

 rc=wl_r20_pair_lock(&window_token,&out,&dirty,(void*)1);

 if(map_error){assert(rc==-EIO && errno==EIO && refs==2 && requests==1);assert(wl_r20_pair_lock(&window_token,&out,&dirty,(void*)1)==-EBUSY && errno==EBUSY && refs==2 && requests==1);assert(wl_r20_pair_unlock(&window_token,(void*)1)==-EBUSY && refs==2);puts("PASS failed slot retains one reference, repeated calls add none");return 0;}
 assert(rc==0 && refs==2 && requests==1);
 if(!strcmp(argv[1],"player_base_drift")){assert(wl_r20_pair_lock(&window_token,&out,&dirty,(void*)4)==-ENODEV && errno==ENODEV && refs==2 && requests==1);}
 assert(wl_r20_pair_lock(&window_token,&out,&dirty,(void*)1)==-EBUSY && errno==EBUSY && refs==2 && requests==1);
 assert(wl_r20_pair_unlock(&window_token,(void*)1)==0 && refs==1 && flushes==1);assert(wl_r20_pair_unlock(&window_token,(void*)1)==-EBUSY && errno==EBUSY && refs==1);
 puts("PASS paired success, duplicate lock/unlock reference conservation");return 0;
}
