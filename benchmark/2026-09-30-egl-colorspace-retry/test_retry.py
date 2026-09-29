#!/usr/bin/env python3
"""Execute the production retry block with deterministic EGL call outcomes."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[2]
s=(root/'bms/src/adapter/aosp_patches/libs/hwui/hwui_oh_abi_patch.cpp').read_text()
a=s.index('    EGLSurface surface = g_real_eglCreateWindowSurface_fn(')
b=s.index('    if (surface != EGL_NO_SURFACE && actualWindow != window',a)
block=s[a:b]
code=r'''
#include <vector>
#include <cassert>
#include <cstdio>
using EGLint=int; using EGLSurface=void*;
#define EGL_NONE 0x3038
#define EGL_NO_SURFACE nullptr
std::vector<std::vector<int>> calls;
std::vector<EGLSurface> results;
int errors=0, logs=0;
EGLSurface fake(void*,void*,void*,const int* a) {
 std::vector<int> v;
 if(a) { for(;*a!=EGL_NONE;a+=2){v.push_back(*a);v.push_back(a[1]);} v.push_back(EGL_NONE); }
 calls.push_back(v); assert(calls.size()<=results.size());return results[calls.size()-1];
}
auto g_real_eglCreateWindowSurface_fn=fake;
int eglGetError(){++errors;return 0x3003;}
int HiLogPrint(int,int,int,const char*,const char*,...){++logs;return 0;}
EGLSurface run(const int* attrib_list) { void *dpy=nullptr,*config=nullptr,*actualWindow=nullptr;
'''+block+r'''
return surface;
}
void reset(std::vector<EGLSurface> r){results=r;calls.clear();errors=0;logs=0;}
int main(){
 void* good=reinterpret_cast<void*>(1);
 int attrs[]={0x309D,0x3340,0x3341,10,0x334A,20,0x3360,30,0x3361,40,0x3086,5,0x3230,123,EGL_NONE};
 reset({good});assert(run(attrs)==good);assert(calls.size()==1&&errors==1&&logs==0);
 reset({nullptr,good});assert(run(attrs)==good);assert(calls.size()==2&&errors==2&&logs==2);
 assert((calls[1]==std::vector<int>{0x3086,5,0x3230,123,EGL_NONE}));
 reset({nullptr,nullptr});assert(run(attrs)==nullptr);assert(calls.size()==2&&errors==2);
 reset({nullptr});assert(run(nullptr)==nullptr);assert(calls.size()==1&&errors==1);
 int only[]={0x309D,0x3540,EGL_NONE};
 reset({nullptr,good});assert(run(only)==good);assert((calls[1]==std::vector<int>{EGL_NONE}));
 std::puts("PASS: success/no-retry, filtered retry, retry failure, null attributes, empty filtered list; unrelated attributes preserved");
}
'''
with tempfile.TemporaryDirectory(prefix='egl-retry-') as d:
 p=Path(d);(p/'test.cpp').write_text(code)
 subprocess.run(['clang++','-std=c++17','-Wall','-Wextra','-Werror',str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
