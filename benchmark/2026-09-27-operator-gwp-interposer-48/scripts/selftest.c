#include <stdio.h>
#include <stdlib.h>
#include <string.h>
// self-test: `t normal|overflow|uaf`. Build native (cc), run under LD_PRELOAD=libwestlake_gwp.so.
// normal -> NORMAL_OK rc0 ; overflow/uaf -> SIGSEGV (rc139) AT the write when WGWP_SAMPLE=1.
int main(int argc,char**argv){const char*m=argc>1?argv[1]:"normal";
 if(!strcmp(m,"normal")){for(int i=0;i<2000;i++){char*p=malloc(64+i%128);memset(p,0xAB,64+i%128);if(i%3==0)free(p);}
  char*a=calloc(10,20);a[199]=1;free(a);char*b=malloc(100);b=realloc(b,300);memset(b,1,300);free(b);
  void*mm=0;posix_memalign(&mm,64,128);memset(mm,2,128);free(mm);printf("NORMAL_OK\n");return 0;}
 if(!strcmp(m,"overflow")){char*p=malloc(100);memset(p,0,100);for(int i=100;i<9000;i++)p[i]=0x41;printf("NO_FAULT\n");return 0;}
 if(!strcmp(m,"uaf")){char*p=malloc(100);free(p);p[0]=0x42;printf("NO_FAULT\n");return 0;}
 return 0;}
