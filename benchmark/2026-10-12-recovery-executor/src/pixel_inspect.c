#define STB_IMAGE_IMPLEMENTATION
#define STBI_ONLY_JPEG
#define STBI_ONLY_PNG
#include "stb_image.h"
#include <stdio.h>
int main(int n,char**v){int w,h,c;unsigned char*p=stbi_load(v[1],&w,&h,&c,3);if(!p)return 2;int xy[][2]={{20,30},{600,30},{1190,140},{500,75},{900,145},{1100,280},{100,1800},{150,1840},{150,1860},{55,248},{120,1840},{1050,1850}};for(int i=0;i<12;i++){int k=3*(xy[i][1]*w+xy[i][0]);printf("%d,%d=%d,%d,%d\n",xy[i][0],xy[i][1],p[k],p[k+1],p[k+2]);}stbi_image_free(p);}
