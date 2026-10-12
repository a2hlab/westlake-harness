/* Recovery format revision: the deployed capture emits JPEG.
 * Pixel predicates below are retained from screen_gate.c; decoding is local
 * stb_image 2.27 JPEG/PNG, independent of platform libpng/libjpeg ABI. */
#define STB_IMAGE_IMPLEMENTATION
#define STBI_ONLY_JPEG
#define STBI_ONLY_PNG
#define STBI_NO_HDR
#define STBI_NO_LINEAR
#define STBI_MAX_DIMENSIONS 4096
#include "stb_image.h"
#include <stdio.h>
#include <stdlib.h>
static unsigned char *rgb;
static int white(int x,int y){unsigned char*p=rgb+3*(y*1200+x);return p[0]>240&&p[1]>240&&p[2]>240;}
static int light(int x,int y){unsigned char*p=rgb+3*(y*1200+x);return p[0]>210&&p[1]>210&&p[2]>210;}
static int red(int x,int y){unsigned char*p=rgb+3*(y*1200+x);return p[0]>230&&p[1]>25&&p[1]<130&&p[2]>20&&p[2]<130;}
static int blue(int x,int y){unsigned char*p=rgb+3*(y*1200+x);return p[0]>85&&p[0]<160&&p[1]>140&&p[1]<210&&p[2]>225&&p[2]-p[0]>65;}
/* t11: bounded chrome regions measured on r3 feed captures. Pixel colour
 * predicates remain unchanged. Every region must match; article content is
 * still required. A red point or arbitrary picture alone cannot qualify. */
static int fraction(int (*test)(int,int),int x0,int x1,int y0,int y1,int step,unsigned percent){
 unsigned matches=0,total=0;
 for(int y=y0;y<y1;y+=step)for(int x=x0;x<x1;x+=step){matches+=test(x,y)!=0;total++;}
 return matches*100>=total*percent;
}
static int observed_feed_regions(void){
 if(!fraction(red,5,55,20,60,2,80) || !fraction(red,1160,1190,110,150,2,75)
    || !fraction(white,350,950,70,80,3,60)
    || !fraction(red,45,85,245,251,1,25)
    || !fraction(red,95,170,1830,1875,2,25)
    || !fraction(white,950,1040,1830,1880,3,85))return 0;
 unsigned dark=0;
 for(int y=275;y<660;y+=3)for(int x=35;x<750;x+=3){
  unsigned char*p=rgb+3*(y*1200+x);
  if(p[0]<100&&p[1]<100&&p[2]<100)dark++;
 }
 return dark>180;
}
int main(int argc,char**argv){
 if(argc!=2)return 2;
 int width,height,channels;
 if(!stbi_info(argv[1],&width,&height,&channels))return 5;
 if(width!=1200||height!=1920){puts("unknown");return 0;}
 rgb=stbi_load(argv[1],&width,&height,&channels,3);
 if(!rgb)return 7;
 const char*label="unknown";
 if(red(340,1250)&&red(400,1250)&&red(800,1295)&&red(850,1295)&&white(320,850)&&white(880,1150)&&white(320,800)&&white(880,800)&&blue(580,720)&&blue(610,705))label="privacy";
 /* Full-screen red login page: observed white X and red surroundings; no feed bar. */
 else if(red(25,100)&&red(85,100)&&red(55,125)&&light(55,92)&&light(43,80)&&light(67,104)&&light(43,104)&&light(67,80)&&!red(120,1840))label="login";
 else if(white(1100,280)&&white(100,1800)&&white(1050,1850)&&(red(120,1840)||red(150,1840))){
  unsigned dark=0;for(int y=275;y<660;y+=3)for(int x=35;x<750;x+=3){unsigned char*p=rgb+3*(y*1200+x);if(p[0]<100&&p[1]<100&&p[2]<100)dark++;}
  if(dark>180)label="feed";
 }
 /* Today's observed feed has the selected-home icon centered at x150,
  * rather than legacy x120, and author text at (100,1800). Require the
  * red header + white search pill + selected recommendation underline +
  * selected-home red icon + white nav background + actual dark article text.
  * Privacy/login keep precedence. No unknown-to-input action is introduced. */
 if(!strcmp(label,"unknown") && red(20,30)&&red(600,30)&&red(1190,140)
    &&white(500,75)&&white(900,145)&&white(1100,280)
    &&red(150,1840)&&red(55,248)&&white(1050,1850)){
   unsigned dark=0;
   for(int y=275;y<660;y+=3)for(int x=35;x<750;x+=3){
     unsigned char*p=rgb+3*(y*1200+x);
     if(p[0]<100&&p[1]<100&&p[2]<100)dark++;
   }
   if(dark>180)label="feed";
 }
 if(!strcmp(label,"unknown") && observed_feed_regions())label="feed";
 puts(label);stbi_image_free(rgb);return 0;
}
