#include "yv12.h"
#include <stdio.h>
#include <stdint.h>
#include <string.h>
static int acq(void *p){(void)p;return 1;}
static void *get(void *p){return p;}
static int rel(void *p){(void)p;return 1;}
int main(void){
 struct r26_owner o={acq,get,rel}; struct r26_context *c=0;
 int rc=r26_create(&o,0,&c); if(rc)return 2;
 for(uintptr_t i=1;i<=8;i++){struct r26_token t;rc=r26_geometry_begin(c,(void*)i,&t);if(rc)return 3;rc=r26_geometry_end(c,t,1,0,0);if(rc)return 4;}
 struct r26_token t;
 rc=r26_lock_begin(c,(void*)9,(void*)9,&t);
 printf("eight_idle_rgb_cache_entries new_rgb_lock_rc=%d reserved=%zu\n",rc,r26_reserved(c));
 unsigned char pixels[16]={1,2,3,4};
 struct r14_handle h={.width=2,.height=2,.stride_bytes=8,.size_bytes=16,.format=11};
 struct r14_buffer original={.width=2,.height=2,.stride=2,.format=2,.bits=pixels},answer=original;
 int prepare=rc?rc:r26_prepare(c,t,&h,&answer);
 int unchanged=!memcmp(&original,&answer,sizeof(answer));
 int before=prepare?prepare:r26_before_unmap(c,t);
 int finish=before?before:r26_finish(c,t,0);
 int destroyed=r26_destroy(c);printf("prepare_rc=%d unchanged=%d before_unmap_rc=%d finish_rc=%d destroy_rc=%d\n",prepare,unchanged,before,finish,destroyed);
 return rc==0 && prepare==0 && unchanged && before==0 && finish==0 && destroyed==0?0:5;
}
