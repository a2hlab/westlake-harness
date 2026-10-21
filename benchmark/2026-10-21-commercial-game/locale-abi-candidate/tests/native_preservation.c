#define _GNU_SOURCE 1
#include <assert.h>
#include <errno.h>
#include <netdb.h>
#include <dlfcn.h>
#include <stdint.h>
#include <string.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/select.h>
static int atfork_calls, lookup_calls, mode;
static void (*seen[3])(void);
static void *queue;
static int fake_atfork(void(*a)(void),void(*b)(void),void(*c)(void)){atfork_calls++;seen[0]=a;seen[1]=b;seen[2]=c;return 17;}
static void *fake_dlsym(void *handle,const char *name){assert(handle==RTLD_DEFAULT);lookup_calls++;if(strcmp(name,"SL_IID_BUFFERQUEUE")==0)return mode?&queue:NULL;return NULL;}
int *__errno_location(void){return &errno;}
#define pthread_atfork fake_atfork
#define dlsym fake_dlsym
#include G30_SOURCE
#undef pthread_atfork
#undef dlsym
static void a(void){} static void b(void){} static void c(void){}
int main(void){
 assert(lookup_calls==1);assert(SL_IID_ANDROIDSIMPLEBUFFERQUEUE==&kAndroidSimpleBufferQueue);
 assert(__register_atfork(a,b,c,(void*)123)==17);assert(atfork_calls==1&&seen[0]==a&&seen[1]==b&&seen[2]==c);
 fd_set f;FD_ZERO(&f);__FD_SET_chk(7,&f,sizeof f);assert(__FD_ISSET_chk(7,&f,sizeof f));__FD_CLR_chk(7,&f,sizeof f);assert(!__FD_ISSET_chk(7,&f,sizeof f));
 assert(__errno()==&errno);assert(__get_h_errno()==&h_errno);
 mode=1;queue=NULL;westlake_map_simple_buffer_queue();assert(SL_IID_ANDROIDSIMPLEBUFFERQUEUE==&kAndroidSimpleBufferQueue);
 static SlInterfaceId iid;queue=&iid;westlake_map_simple_buffer_queue();assert(SL_IID_ANDROIDSIMPLEBUFFERQUEUE==&iid);
 assert(SL_IID_ANDROIDCONFIGURATION==&kAndroidConfiguration);
 puts("PASS native production body: atfork forwarding/rc, FD set/is/clear, errno pointers, constructor absent/null/present IID");return 0;
}
