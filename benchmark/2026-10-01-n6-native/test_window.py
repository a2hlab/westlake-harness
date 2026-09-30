#!/usr/bin/env python3
"""Execute copied EGL functions with deterministic driver/bridge callbacks."""
import subprocess, tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
main=r'''
#include <cassert>
static int swaps=0, notices=0;
static bool swap_ok=true, destroy_ok=true, create_ok=true;
static void* received;
static void* shim=(void*)0x1100;
static void* native=(void*)0x2200;
static void* surf=(void*)0x3300;
extern "C" int HiLogPrint(int,int,unsigned,const char*,const char*,...){return 0;}
static void* unwrap(void* p){return p==shim?native:nullptr;}
static int notify(void* p){assert(p==shim);notices++;return 0;}
static void* create(void*,void*,void* win,const int*){received=win;return create_ok?surf:nullptr;}
static unsigned destroy(void*,void*){return destroy_ok;}
static unsigned swap(void*,void*){swaps++;return swap_ok;}
static unsigned damage(void*,void*,const int*,int){return swap(nullptr,nullptr);}
int main(){
 g_oh_anw_get_oh_fn=unwrap;g_oh_anw_notify_presented_fn=notify;
 g_real_eglCreateWindowSurface_fn=create;g_real_eglDestroySurface_fn=destroy;
 g_real_eglSwapBuffers_fn=swap;g_real_eglSwapBuffersWithDamageKHR_fn=damage;
 assert(eglCreateWindowSurface(nullptr,nullptr,shim,nullptr)==surf);assert(received==native);
 assert(eglSwapBuffers(nullptr,surf));assert(notices==1);
 swap_ok=false;assert(!eglSwapBuffers(nullptr,surf));assert(notices==1);
 swap_ok=true;assert(eglSwapBuffersWithDamageKHR(nullptr,surf,nullptr,0));assert(notices==2);
 destroy_ok=false;assert(!eglDestroySurface(nullptr,surf));assert(g_egl_surface_owner.count(surf)==1);
 destroy_ok=true;assert(eglDestroySurface(nullptr,surf));assert(g_egl_surface_owner.empty());
 assert(eglSwapBuffers(nullptr,surf));assert(notices==2);
 assert(eglCreateWindowSurface(nullptr,nullptr,native,nullptr)==surf);assert(received==native);assert(g_egl_surface_owner.empty());
 create_ok=false;assert(!eglCreateWindowSurface(nullptr,nullptr,shim,nullptr));assert(g_egl_surface_owner.empty());
 assert(notices==2&&swaps==4);
}
'''
with tempfile.TemporaryDirectory() as td:
 p=Path(td);(p/'test.cpp').write_text((HERE/'src/flutter_egl.cpp').read_text()+main)
 subprocess.run(['c++','-std=c++17',str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('PASS: shim/raw/create failure/successful swap/failed swap/damage/failed destroy/successful destroy')
