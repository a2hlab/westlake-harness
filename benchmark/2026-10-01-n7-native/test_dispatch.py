"""Compile the delivered facade and exercise real dispatch, including proc lookup."""
from pathlib import Path
import subprocess,tempfile
H=Path(__file__).resolve().parent
TEST=r'''
#include <assert.h>
#include <string.h>
#include <stdio.h>
#include "flutter_egl.c"
static int calls;
static Handle fake_create(Handle d,Handle c,void*w,const int*a){(void)d;(void)c;(void)a;assert(w==(void*)0x111);calls++;return (void*)0x222;}
static Boolean fake_pair(Handle d,Handle s){(void)d;assert(s==(void*)0x222);calls++;return 1;}
static Boolean fake_damage(Handle d,Handle s,const int*r,int n){(void)r;assert(n==2);return fake_pair(d,s);}
static void extension(void){}
static Proc fake_proc(const char*n){return !strcmp(n,"onlyExtension")?extension:NULL;}
static int fake_error(void){return 0x3003;}
static void *resolve(const char*n){
 if(!strcmp(n,"eglCreateWindowSurface"))return (void*)fake_create;
 if(!strcmp(n,"eglDestroySurface")||!strcmp(n,"eglSwapBuffers"))return (void*)fake_pair;
 if(!strcmp(n,"eglSwapBuffersWithDamageKHR"))return (void*)fake_damage;
 if(!strcmp(n,"eglGetProcAddress"))return (void*)fake_proc;
 if(!strcmp(n,"eglGetError"))return (void*)fake_error;
 return NULL;
}
int main(void){
 assert(!eglCreateWindowSurface(0,0,0,0));assert(!eglGetProcAddress("eglCreateWindowSurface"));
 assert(westlake_flutter_egl_bind(NULL)==-1);assert(westlake_flutter_egl_bind(resolve)==0);
 assert(eglCreateWindowSurface(0,0,(void*)0x111,0)==(void*)0x222);
 assert(eglGetProcAddress("eglCreateWindowSurface")== (Proc)&eglCreateWindowSurface);
 assert(eglGetProcAddress("eglSwapBuffers")== (Proc)&eglSwapBuffers);
 assert(eglGetProcAddress("eglSwapBuffersWithDamageEXT")== (Proc)&eglSwapBuffersWithDamageKHR);
 assert(eglSwapBuffers(0,(void*)0x222));assert(eglDestroySurface(0,(void*)0x222));
 int rect[8]={0};assert(eglSwapBuffersWithDamageKHR(0,(void*)0x222,rect,2));
 assert(eglGetProcAddress("onlyExtension")==extension);assert(!eglGetProcAddress("absent"));
 assert(eglGetError()==0x3003);assert(westlake_flutter_egl_bind(resolve)==-1);assert(calls==4);
 puts("dispatch PASS: direct/proc window routing, raw result/error, extension fallback, bind rejection");
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'test.c').write_text(TEST)
 subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-I'+str(H/'src'),str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
s=(H/'src/host.c').read_text();assert 'if (flutter_private) {' in s and 'RTLD_NOW | RTLD_NOLOAD' in s
assert 'flutter_private ?' in s
print('scope source checks PASS; device loader behavior remains unverified')
