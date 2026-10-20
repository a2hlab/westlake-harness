/* Reuse actual T26 cache concurrency fixtures; do not model its decisions. */
#define main t26_original_cases
#include "test_yv12.c"
#undef main
int main(void){
 assert(t26_original_cases()==0);
 unsigned char buf[256],before[256];for(unsigned i=0;i<sizeof(buf);i++)buf[i]=(unsigned char)i;memcpy(before,buf,sizeof(buf));
 struct r14_handle h={17,3,80,240,12};
 for(unsigned i=0;i<9;i++){
  struct r14_handle bad=h;
  switch(i){case 0:bad.format=11;break;case 1:bad.width=0;break;case 2:bad.height=-1;break;case 3:bad.width=INT64_MAX;break;case 4:bad.stride_bytes=67;break;case 5:bad.stride_bytes=68;bad.size_bytes=203;break;case 6:bad.size_bytes=239;break;case 7:bad.stride_bytes=INT64_MAX;break;case 8:bad.height=INT64_MAX;break;}
  assert(r28_opaque(&bad,buf)!=0 && !memcmp(buf,before,sizeof(buf)));
 }
 assert(r28_opaque(&h,NULL)!=0);assert(r28_opaque(&h,buf)==0);
 for(unsigned i=0;i<sizeof(buf);i++)assert(buf[i]==((i<240 && i%80<68 && i%4==3)?255:before[i]));
 puts("PASS 10 invalid layouts/no writes and nonuniform RGB/padding canaries");
 int oh;struct wrapper w={1,&oh},alias={1,&oh};create();geometry(&w,2);geometry(&alias,2);
 struct race a={.w=&w},b={.w=&alias};pthread_t ta,tb;assert(!pthread_create(&ta,NULL,race_lock,&a));assert(!pthread_create(&tb,NULL,race_lock,&b));pthread_join(ta,NULL);pthread_join(tb,NULL);
 assert((a.rc==0 && b.rc==-EBUSY)||(b.rc==0 && a.rc==-EBUSY));struct race *win=a.rc==0?&a:&b;
 /* Re-establish winner's known request only after releasing the raced token. */
 assert(r26_finish(current,win->t,0)==0);geometry(win->w,2);
 struct r26_token t;assert(r26_lock_begin(current,win->w,&oh,&t)==0);struct r14_buffer out={17,3,20,1,buf,{0}};
 assert(r26_prepare(current,t,&h,&out)==0 && out.format==2 && r26_reserved(current)==0);
 assert(r26_prepare(current,t,&h,&out)==-EBUSY);assert(r26_before_unmap(current,t)==0);assert(r26_before_unmap(current,t)==-EBUSY);assert(r26_finish(current,t,0)==0);
 geometry(win->w,1);assert(r26_lock_begin(current,win->w,&oh,&t)==0);memcpy(buf,before,sizeof(buf));out=(struct r14_buffer){17,3,20,1,buf,{0}};
 assert(r26_prepare(current,t,&h,&out)==0 && out.format==1);assert(r26_before_unmap(current,t)==0 && !memcmp(buf,before,sizeof(buf)));assert(r26_finish(current,t,0)==0);
 clean();assert(w.refs==1 && alias.refs==1);puts("PASS actual alias race and RGBX to RGBA state reuse");return 0;
}
