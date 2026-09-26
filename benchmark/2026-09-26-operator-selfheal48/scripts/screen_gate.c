/* Fixed 1200x1920 board UI recognizer. Unknown images fail closed (no input).
 * Uses the platform PNG decoder; never modifies app/runtime libraries. */
#include <png.h>
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned char *rgb;
static int white(int x,int y){unsigned char*p=rgb+3*(y*1200+x);return p[0]>240&&p[1]>240&&p[2]>240;}
static int light(int x,int y){unsigned char*p=rgb+3*(y*1200+x);return p[0]>210&&p[1]>210&&p[2]>210;}
static int red(int x,int y){unsigned char*p=rgb+3*(y*1200+x);return p[0]>230&&p[1]>25&&p[1]<130&&p[2]>20&&p[2]<130;}
static int blue(int x,int y){unsigned char*p=rgb+3*(y*1200+x);return p[0]>85&&p[0]<160&&p[1]>140&&p[1]<210&&p[2]>225&&p[2]-p[0]>65;}
int main(int argc,char**argv){
 if(argc!=2)return 2;
 void*h=dlopen("/system/lib64/chipset-sdk/libpng.z.so",RTLD_NOW|RTLD_LOCAL);if(!h)return 3;
 int(*begin)(png_imagep,const char*)=dlsym(h,"png_image_begin_read_from_file");
 int(*finish)(png_imagep,png_const_colorp,void*,png_int_32,void*)=dlsym(h,"png_image_finish_read");
 void(*release)(png_imagep)=dlsym(h,"png_image_free");
 if(!begin||!finish||!release)return 4;
 png_image im;memset(&im,0,sizeof(im));im.version=PNG_IMAGE_VERSION;
 if(!begin(&im,argv[1]))return 5;
 if(im.width!=1200||im.height!=1920){release(&im);puts("unknown");return 0;}
 im.format=PNG_FORMAT_RGB;rgb=malloc(PNG_IMAGE_SIZE(im));if(!rgb){release(&im);return 6;}
 if(!finish(&im,NULL,rgb,0,NULL)){release(&im);free(rgb);return 7;}
 const char*label="unknown";
 if(red(340,1250)&&red(400,1250)&&red(800,1295)&&red(850,1295)&&white(320,850)&&white(880,1150)&&white(320,800)&&white(880,800)&&blue(580,720)&&blue(610,705))label="privacy";
 /* Full-screen red login page: observed white X and red surroundings; no feed bar. */
 else if(red(25,100)&&red(85,100)&&red(55,125)&&light(55,92)&&light(43,80)&&light(67,104)&&light(43,104)&&light(67,80)&&!red(120,1840))label="login";
 else if(white(1100,280)&&white(100,1900)&&white(1050,1850)&&(red(120,1840)||red(150,1840))){
  unsigned dark=0;for(int y=275;y<660;y+=3)for(int x=35;x<750;x+=3){unsigned char*p=rgb+3*(y*1200+x);if(p[0]<100&&p[1]<100&&p[2]<100)dark++;}
  if(dark>180)label="feed";
 }
 puts(label);release(&im);free(rgb);dlclose(h);return 0;
}
