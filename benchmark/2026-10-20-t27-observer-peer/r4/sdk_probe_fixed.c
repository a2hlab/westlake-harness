#define _GNU_SOURCE
#include <stdbool.h>
#include <native_buffer/native_buffer.h>
#include <stdio.h>
#include <assert.h>
#include <string.h>
#include "observer.c"
#define EQ(a,b) _Static_assert(offsetof(wl_t27_cfg,a)==offsetof(OH_NativeBuffer_Config,b),"SDK offset")
EQ(width,width);EQ(height,height);EQ(format,format);EQ(usage_low32,usage);EQ(stride,stride);
_Static_assert(sizeof(wl_t27_cfg)==sizeof(OH_NativeBuffer_Config),"SDK size");
static void real_layout(void *b,wl_t27_cfg *out){(void)b;OH_NativeBuffer_Config sdk={.width=576,.height=1024,.format=2,.usage=0x12345678,.stride=2304};memcpy(out,&sdk,sizeof sdk);}
int main(void){wl_t27_getters g={real_layout,0};wl_t27_cpu_native(1,2,0,0,(void*)1,&g,(void*)1);wl_t27_record r;assert(wl_t27_snapshot(&r,1)==1);assert(r.cfg.width==576&&r.cfg.height==1024&&r.cfg.format==2&&r.cfg.usage_low32==0x12345678&&r.cfg.stride==2304);printf("SDK size=%zu usage@%zu stride@%zu parsed usage=%d stride=%d\n",sizeof(OH_NativeBuffer_Config),offsetof(OH_NativeBuffer_Config,usage),offsetof(OH_NativeBuffer_Config,stride),r.cfg.usage_low32,r.cfg.stride);return 0;}
