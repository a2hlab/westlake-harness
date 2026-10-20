#include <assert.h>
#include <pthread.h>
#include <stdint.h>
#include <string.h>
#include "egl_import.c"
static int created,destroyed,images,image_destroys,foreigns,fail_destroy,fail_create,fail_native,provider_refused,trust=1,multiple,absent,block_create,entered,proceed;
static unsigned last_target;
static pthread_mutex_t seam_lock=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t seam_cond=PTHREAD_COND_INITIALIZER;
static void *D=(void*)0x1000,*I=(void*)0x2000;
static void *new_buffer(void *p){assert(p);if(fail_native)return NULL;created++;return(void*)(uintptr_t)(0x3000+created*16);}
static void free_buffer(void *p){assert(p);destroyed++;}
static int caller(void *p){(void)p;return trust;}
static void *current(void){return absent?NULL:D;}
static void *current2(void){return multiple?D:NULL;}
static void *new_image(void*d,void*c,unsigned t,void*b,const int32_t*a){assert(d==D && c==(void*)9 && b && a==(void*)7);last_target=t;images++;if(block_create){pthread_mutex_lock(&seam_lock);entered=1;pthread_cond_broadcast(&seam_cond);while(!proceed)pthread_cond_wait(&seam_cond,&seam_lock);pthread_mutex_unlock(&seam_lock);}return fail_create?NULL:I;}
static unsigned free_image(void*d,void*i){assert(d==D && i==I);image_destroys++;return !fail_destroy;}
static int fence(void*d,void*s){assert(d==D && s==(void*)8);return 41;}
static void *next_client(const void*b){assert(b==(void*)1);foreigns++;return(void*)0x9000;}
static void *next_create(void*d,void*c,unsigned t,void*b,const int32_t*a){assert(d==D && c==(void*)9 && t==ANDROID_BUFFER && b==(void*)0x9000 && a==(void*)7);foreigns++;return(void*)0x9001;}
static unsigned next_destroy(void*d,void*i){assert(d==D && i==(void*)0x9001);foreigns++;return 3;}
static int next_fence(void*d,void*s){assert(d==D && s==(void*)8);foreigns++;return 42;}
int r23_platform_init(struct r23_platform*p){*p=(struct r23_platform){.create_buffer=new_buffer,.destroy_buffer=free_buffer,.trusted_caller=caller,.count=2,.impl={{current,new_image,free_image,fence},{current2,new_image,free_image,fence}},.next_client=next_client,.next_create=next_create,.next_destroy=next_destroy,.next_fence=next_fence};return provider_refused?-1:0;}
static void *client(void){return eglGetNativeClientBufferANDROID((void*)1);}
static void *make(void*b){return eglCreateImageKHR(D,(void*)9,ANDROID_BUFFER,b,(void*)7);}
static void *thread_create(void*b){assert(make(b)==I);return NULL;}
int main(int argc,char**argv){assert(argc==2);const char*c=argv[1];
 if(!strcmp(c,"success")){void*b=client();assert(make(b)==I && last_target==OH_BUFFER);absent=1;assert(eglDestroyImageKHR(D,I)==1);assert(created==1 && destroyed==1 && image_destroys==1);}
 else if(!strcmp(c,"same_image_two_displays")){void*b=client();assert(make(b)==I);D=(void*)0x1100;void*c2=client();assert(make(c2)==I);assert(eglDestroyImageKHR(D,I)==1 && destroyed==1);D=(void*)0x1000;assert(eglDestroyImageKHR(D,I)==1 && destroyed==2);}
 else if(!strcmp(c,"full")){assert(client());assert(client());assert(!client());assert(created==2 && destroyed==0);}
 else if(!strcmp(c,"duplicate")){void*b=client();block_create=1;pthread_t t;assert(!pthread_create(&t,NULL,thread_create,b));pthread_mutex_lock(&seam_lock);while(!entered)pthread_cond_wait(&seam_cond,&seam_lock);pthread_mutex_unlock(&seam_lock);assert(!make(b));assert(!foreigns && images==1);pthread_mutex_lock(&seam_lock);proceed=1;pthread_cond_broadcast(&seam_cond);pthread_mutex_unlock(&seam_lock);pthread_join(t,NULL);assert(!make(b));assert(!foreigns);assert(eglDestroyImageKHR(D,I)==1 && destroyed==1);}
 else if(!strcmp(c,"wrong_display")){void*b=client();assert(make(b)==I);assert(!eglDestroyImageKHR((void*)5,I));assert(image_destroys==0 && destroyed==0 && foreigns==0);assert(eglDestroyImageKHR(D,I)==1);}
 else if(!strcmp(c,"destroy_retry")){void*b=client();assert(make(b)==I);fail_destroy=1;assert(!eglDestroyImageKHR(D,I));assert(!destroyed && !make(b) && !foreigns);fail_destroy=0;assert(eglDestroyImageKHR(D,I)==1 && destroyed==1 && image_destroys==2);}
 else if(!strcmp(c,"create_fail")){fail_create=1;void*b=client();assert(!make(b));assert(created==destroyed && !foreigns);}
 else if(!strcmp(c,"display_absent")){absent=1;void*b=client();assert(!make(b));assert(!images && created==destroyed);}
 else if(!strcmp(c,"display_multiple")){multiple=1;void*b=client();assert(!make(b));assert(!images && created==destroyed);}
 else if(!strcmp(c,"foreign")){trust=0;assert(client()==(void*)0x9000);assert(make((void*)0x9000)==(void*)0x9001);assert(eglDestroyImageKHR(D,(void*)0x9001)==3);assert(foreigns==3 && !created);}
 else if(!strcmp(c,"fence")){assert(eglDupNativeFenceFDANDROID(D,(void*)8)==41);absent=1;assert(eglDupNativeFenceFDANDROID(D,(void*)8)==42 && foreigns==1);}
 else if(!strcmp(c,"provider_refused")){provider_refused=1;assert(!client() && !created && !foreigns);}
 else if(!strcmp(c,"native_fail")){fail_native=1;assert(!client());assert(slots[0].state==FREE && !created);}
 else if(!strcmp(c,"target_refused")){void*b=client();assert(!eglCreateImageKHR(D,(void*)9,OH_BUFFER,b,(void*)7));assert(!images && !foreigns && !destroyed);assert(make(b)==I);assert(eglDestroyImageKHR(D,I)==1);}
 else assert(0);
 return 0;
}
