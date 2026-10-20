#define _GNU_SOURCE 1
#include <dlfcn.h>
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
static void *mock_open(const char*,int);
static void *mock_symbol(void*,const char*);
static int mock_address(const void*,Dl_info*);
#define dlopen mock_open
#define dlsym mock_symbol
#define dladdr mock_address
#include "platform.c"
static unsigned char *H,*S,*S2;
static int drift,bad_offset,unreadable,mixed,missing_destroy,wrong_path,mixed_egl,foreign_proc,opens;
static void *E=(void*)0x1110;
static void *cur(void){return(void*)0x2000;}
static void *cre(void*a,void*b,unsigned c,void*d,const int32_t*e){(void)a;(void)b;(void)c;(void)d;(void)e;return(void*)3;}
static unsigned des(void*a,void*b){(void)a;(void)b;return 1;}
static int dupfn(void*a,void*b){(void)a;(void)b;return 42;}
static void *getproc(const char*n){return !strcmp(n,"eglDupNativeFenceFDANDROID")?(void*)dupfn:NULL;}
static void *mock_open(const char*name,int flags){assert(flags&RTLD_NOLOAD);opens++;if(!strcmp(name,"/data/local/tmp/asx/libhwui.so"))return H;if(!strcmp(name,"/system/lib64/libEGL.so") || !strcmp(name,"libEGL.so"))return E;return NULL;}
static void *mock_symbol(void*h,const char*n){
 if(h==H){
  if(!strncmp(n,"_ZN7android29ASurfaceTexture_dequeueBuffer",40))return H+0x80a9c0+(bad_offset?4:0);
  if(!strcmp(n,"OH_NativeBuffer_FromNativeWindowBuffer"))return S+0x64be0+(drift?4:0);
  if(!strcmp(n,"OH_NativeWindow_CreateNativeWindowBufferFromNativeBuffer"))return (mixed?S2:S)+0x6702c;
  if(!strcmp(n,"OH_NativeWindow_DestroyNativeWindowBuffer"))return S+0x66e18;
 }
 if(h==RTLD_DEFAULT || h==E || h==RTLD_NEXT){
  if(!strcmp(n,"eglGetCurrentDisplay"))return(void*)cur;
  if(!strcmp(n,"eglCreateImageKHR"))return(void*)cre;
  if(!strcmp(n,"eglDestroyImageKHR"))return missing_destroy?NULL:(void*)des;
  if(!strcmp(n,"eglGetProcAddress"))return(void*)getproc;
 }
 return NULL;
}
static int mock_address(const void*p,Dl_info*i){memset(i,0,sizeof(*i));uintptr_t v=(uintptr_t)p;
 if(v>=(uintptr_t)H && v<(uintptr_t)H+0x850000){i->dli_fbase=H;i->dli_fname=wrong_path?"/foreign/libhwui.so":"/data/local/tmp/asx/libhwui.so";return 1;}
 if(v>=(uintptr_t)S && v<(uintptr_t)S+0x80000){i->dli_fbase=S;i->dli_fname="/system/lib64/chipset-sdk-sp/libsurface.z.so";return 1;}
 if(v>=(uintptr_t)S2 && v<(uintptr_t)S2+0x80000){i->dli_fbase=S2;i->dli_fname="/system/lib64/chipset-sdk-sp/libsurface.z.so";return 1;}
 if(p==(void*)external){i->dli_fbase=(void*)0x7770;i->dli_fname="libwebview_bionic_shim.so";return 1;}
 if((mixed_egl && p==(void*)cre) || (foreign_proc && p==(void*)getproc)){i->dli_fbase=(void*)0x9990;i->dli_fname="/other/libEGL.so";return 1;}
 i->dli_fbase=E;i->dli_fname="/system/lib64/libEGL.so";return 1;
}
int main(int argc,char**argv){assert(argc==2);H=calloc(1,0x850000);S=calloc(1,0x80000);S2=calloc(1,0x80000);assert(H&&S&&S2);
 struct r23_ehdr*e=(void*)H;memcpy(e->ident,"\177ELF\2\1\1",7);e->type=3;e->machine=183;e->ehsize=64;e->phsize=56;e->phoff=64;e->phnum=1;
 struct r23_phdr*p=(void*)(H+64);p->type=1;p->flags=4;p->memsz=0x850000;*(void**)(H+0x841850)=S+0x64be0;
 const char*c=argv[1];drift=!strcmp(c,"scope_drift");bad_offset=!strcmp(c,"wrong_owner_offset");unreadable=!strcmp(c,"unreadable_slot");mixed=!strcmp(c,"mixed_provider");missing_destroy=!strcmp(c,"missing_destroy");wrong_path=!strcmp(c,"wrong_path");mixed_egl=!strcmp(c,"mixed_egl");foreign_proc=!strcmp(c,"foreign_proc");if(unreadable)p->memsz=0x841850;
 struct r23_platform platform={0};int rc=r23_platform_init(&platform);
 if(!strcmp(c,"success")){assert(rc==0 && platform.create_buffer==(void*)(S+0x6702c) && platform.destroy_buffer==(void*)(S+0x66e18) && platform.count==1 && platform.impl[0].dup_fence==dupfn);assert(platform.trusted_caller(H+0x1234));assert(!platform.trusted_caller(S+0x1234));}
 else if(foreign_proc){assert(rc==0 && platform.count==1 && platform.impl[0].dup_fence==NULL);}
 else if(missing_destroy || mixed_egl){assert(rc==0 && platform.count==0);}
 else {assert(rc!=0 && !platform.create_buffer && !platform.destroy_buffer);}
 assert(opens>0);free(H);free(S);free(S2);return 0;
}
