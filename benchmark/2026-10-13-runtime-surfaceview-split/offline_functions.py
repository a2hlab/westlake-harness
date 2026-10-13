"""Compile exact candidate functions with distinct mocked main/child producers; zero OH/HDC."""
import hashlib,importlib.util,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'2026-10-13-popup-geometry-reuse/evidence/source-pair/source947.cpp'
HOST=Path('/opt/homebrew/opt/llvm/bin/clang++')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def tools():
    p=HERE.parent/'2026-10-13-popup-geometry-reuse/offline_probe.py';s=importlib.util.spec_from_file_location('extract_original_fn',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
HEADER=r'''
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <cstdarg>
struct JNIEnv {}; using jclass=void*; using jlong=long long; using jint=int;
struct OHNativeWindow { int w=640,h=480,fmt=1; }; using ANativeWindow=OHNativeWindow;
static OHNativeWindow mainWindow,childWindow;
static int mainWrites=0,childWrites=0,childCalls=0,mainCalls=0;
static bool childSuccess=true,mainSuccess=true;
int HiLogPrint(int,int,unsigned int,const char*,const char*,...){return 0;}
#define ALOGI(...) ((void)0)
#define ALOGW(...) ((void)0)
#define NWFS_INFO(...) ((void)0)
#define OH_OP_SET_BUFFER_GEOMETRY 0
#define OH_OP_SET_FORMAT 3
int NativeWindowHandleOpt(OHNativeWindow* p,int op,...){
 va_list a;va_start(a,op);
 if(op==0){p->w=va_arg(a,int);p->h=va_arg(a,int);if(p==&mainWindow)++mainWrites;else if(p==&childWindow)++childWrites;else std::abort();}
 else if(op==3)p->fmt=va_arg(a,int);else std::abort();
 va_end(a);return 0;
}
namespace oh_adapter {int androidToOHPixelFormat(int f){return f;}}
OHNativeWindow* anw_unwrap(ANativeWindow* p){return p;}
struct BBQ { int32_t width=0,height=0,format=0,sessionId=0;void* ohNativeWindow=nullptr;char name[128]; };
static BBQ bbq;
BBQ* as_bbq(jlong p){return p?&bbq:nullptr;}
int32_t oh_sc_get_session(jlong p){return p?42:0;}
void* oh_wm_get_native_window(int){++mainCalls;return mainSuccess?&mainWindow:nullptr;}
void* oh_rs_get_child_surface_window(int,jlong,int32_t,int32_t){++childCalls;return childSuccess?&childWindow:nullptr;}
extern "C" void nwfs_seed_window_geometry(void*,const char*);
static void nwfs_apply_window_geometry(void*,const char*,int32_t,int32_t);
'''
MAIN=r'''
int main(int argc,char**argv){
 if(argc!=7)return 2;
 std::snprintf(bbq.name,sizeof(bbq.name),"%s",argv[1]);
 int w=std::atoi(argv[2]),h=std::atoi(argv[3]);childSuccess=std::atoi(argv[4]);mainSuccess=std::atoi(argv[5]);
 BBQ_nativeUpdate(nullptr,nullptr,1,std::atoi(argv[6]),w,h,-2);
 auto* selected=reinterpret_cast<ANativeWindow*>(bbq.ohNativeWindow);
 int before=mainWrites+childWrites;
 nwfs_seed_window_geometry(selected,"BBQ.getSurface-lazy");
 nwfs_seed_window_geometry(selected,"STAGE0-handoff");
 int stage0=mainWrites+childWrites;
 ANativeWindow_setBuffersGeometry(selected,0,0,12);
 int zero=mainWrites+childWrites;
 std::printf("{\"main\":[%d,%d],\"child\":[%d,%d],\"main_writes\":%d,\"child_writes\":%d,\"main_calls\":%d,\"child_calls\":%d,\"selected\":\"%s\",\"update_writes\":%d,\"after_seed_writes\":%d,\"after_zero_writes\":%d}\n",mainWindow.w,mainWindow.h,childWindow.w,childWindow.h,mainWrites,childWrites,mainCalls,childCalls,selected==&childWindow?"child":selected==&mainWindow?"main":"none",before,stage0,zero);
 return 0;
}
'''
def run(out=None):
    out=out or HERE/'evidence/offline';out.mkdir(parents=True,exist_ok=False);t=tools();source=HERE/'source/android_graphics_compat_shim.cpp';old=BASE.read_text();new=source.read_text()
    if sha(BASE)!='280a36f2000924cecc05feb60ca49d1c2a0fc72a660e02cd7488ad2dedfd2506':raise ValueError('original947 TU drift')
    signature='void BBQ_nativeUpdate(';before=t.function(old,signature);after=t.function(new,signature)
    if old.replace(before,'BBQ_BODY')!=new.replace(after,'BBQ_BODY'):raise ValueError('change outside exactBBQ function')
    unchanged={}
    for sig in ['jobject BBQ_nativeGetSurface(', 'extern "C" void nwfs_seed_window_geometry(void* nw, const char* where) {', 'extern "C" ANativeWindow* ANativeWindow_fromSurface(', 'extern "C" int32_t ANativeWindow_setBuffersGeometry(']:
        if t.function(old,sig)!=t.function(new,sig):raise ValueError('preserved function changed: '+sig)
        unchanged[sig]=hashlib.sha256(t.function(new,sig).encode()).hexdigest()
    pieces=[after,t.function(new,'static void nwfs_apply_window_geometry(void* nw, const char* where, int32_t w, int32_t h) {'),t.function(new,'extern "C" void nwfs_seed_window_geometry(void* nw, const char* where) {'),t.function(new,'extern "C" int32_t ANativeWindow_setBuffersGeometry(')]
    cpp=out/'actual-functions.cpp';cpp.write_text(HEADER+'\n'+'\n'.join(pieces)+'\n'+MAIN);binary=out/'actual-functions'
    t.run_record([HOST,'-std=c++17','-O0','-Wall','-Wextra','-o',binary,cpp],out,'compile')
    cases=[('dedicated-child','SurfaceView[Boat]',1920,1200,1,1,42,'child',[1920,1200]),('popup-main','ViewRootImpl[popup]',864,657,1,1,42,'main',[1200,1920]),('named-child-fallback','SurfaceView[Boat]',1920,1200,0,1,42,'main',[1200,1920]),('boat-main-counterexample','ViewRootImpl[Boat]',1920,1200,1,1,42,'main',[1200,1920]),('child-and-main-unavailable','SurfaceView[Boat]',1920,1200,0,0,42,'none',None),('no-session','SurfaceView[Boat]',1920,1200,1,1,0,'none',None)]
    results={}
    for label,name,w,h,child,main,sc,selected,size in cases:
        raw=t.run_record([binary,name,w,h,child,main,sc],out,label);r=json.loads(raw)
        if r['selected']!=selected or size is not None and r[selected]!=size:raise ValueError('branch prediction differs: '+label)
        if r['update_writes']!=r['after_seed_writes'] or r['after_seed_writes']!=r['after_zero_writes']:raise ValueError('seed/width0 mutates geometry')
        if selected=='child' and (r['main_writes'] or r['child_writes']!=1):raise ValueError('wrong producer written')
        if selected=='main' and (r['child_writes'] or r['main_writes']!=1):raise ValueError('fallback/name-only regression')
        results[label]=r
    result={'status':'HOST_ACTUAL_FUNCTION_BRANCH_CHECKS_PASS_NOT_OH_OR_GAME_ACCEPTANCE','synthetic':True,'device_calls':0,'source_sha256':sha(source),'compiler':{'path':str(HOST),'sha256':sha(HOST)},'extracted_TU_sha256':sha(cpp),'host_binary_sha256':sha(binary),'unchanged_functions':unchanged,'cases':results,'boundary':'Exact production functions; mocked resolver/NativeWindowHandleOpt with distinct main/child windows. No OH compositor, renderer, input or game executes.'}
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':print(json.dumps(run()))
