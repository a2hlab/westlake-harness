#include "yv12.h"
#include <stdio.h>
#include <stdint.h>
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
 int destroyed=r26_destroy(c);printf("destroy_rc=%d\n",destroyed);
 return rc==-28 && destroyed==0?0:5;
}
