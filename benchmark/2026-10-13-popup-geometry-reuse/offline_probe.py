"""Extract original functions; host mock boundary only, never an OH runtime build."""
import hashlib,json,subprocess
from pathlib import Path

BASE_SHA='e28f4bc3a7c863defd74bb173146ea89308a6bf952ea1d11c80b00dd87ecd658'
PORT_SHA='280a36f2000924cecc05feb60ca49d1c2a0fc72a660e02cd7488ad2dedfd2506'

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def function(text,signature):
    start=text.index(signature);brace=text.index('{',start);level=0
    # These exact functions have balanced comment/string braces. Source identity
    # and actual compiler acceptance gate this small extraction, not arbitrary C++.
    for n in range(brace,len(text)):
        if text[n]=='{':level+=1
        elif text[n]=='}':
            level-=1
            if level==0:return text[start:n+1]
    raise ValueError('unterminated original function')

HEADER=r'''
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cstdlib>
struct JNIEnv {}; using jclass=void*; using jlong=long long; using jint=int;
struct OHNativeWindow { int w=1200,h=1920; }; using ANativeWindow=OHNativeWindow;
static OHNativeWindow window;
static int writes=0;
int HiLogPrint(int,int,unsigned int,const char*,const char*,...){return 0;}
#define ALOGI(...) ((void)0)
#define ALOGW(...) ((void)0)
#define OH_OP_SET_BUFFER_GEOMETRY 0
int NativeWindowHandleOpt(OHNativeWindow* p,int,int w,int h){p->w=w;p->h=h;++writes;return 0;}
OHNativeWindow* anw_unwrap(ANativeWindow* p){return p;}
struct BBQ { int32_t width=0,height=0,format=0,sessionId=0; void* ohNativeWindow=nullptr; char name[128]; };
static BBQ bbq;
BBQ* as_bbq(jlong p){return p?&bbq:nullptr;}
int32_t oh_sc_get_session(jlong p){return p?42:0;}
void* oh_wm_get_native_window(int){return &window;}
void* oh_rs_get_child_surface_window(int,jlong,int32_t w,int32_t h){window.w=w;window.h=h;return &window;}
extern "C" void nwfs_seed_window_geometry(void*,const char*);
'''
MAIN=r'''
int main(int argc,char**argv){
 if(argc!=5)return 2;
 std::snprintf(bbq.name,sizeof(bbq.name),"%s",argv[1]);
 jlong w=std::strtoll(argv[2],nullptr,10),h=std::strtoll(argv[3],nullptr,10);
 BBQ_nativeUpdate(nullptr,nullptr,1,1,w,h,-2);
 int beforew=window.w,beforeh=window.h,updateWrites=writes;
 // The ADC handoff has a verified NOP at the setter. This is its
 // non-mutating instruction semantic model, not execution of an ARM ELF.
 if(std::strcmp(argv[4],"9cc-setter")==0)nwfs_seed_window_geometry(&window,"STAGE0-handoff");
 std::printf("{\"update\":[%d,%d],\"update_writes\":%d,\"handoff\":[%d,%d],\"all_writes\":%d}\n",beforew,beforeh,updateWrites,window.w,window.h,writes);
 return 0;
}
'''

def run_record(argv,directory,name,**kwargs):
    result=subprocess.run([str(x) for x in argv],capture_output=True,**kwargs)
    (directory/(name+'.stdout.txt')).write_bytes(result.stdout)
    (directory/(name+'.stderr.txt')).write_bytes(result.stderr)
    receipt=dict(argv=[str(x) for x in argv],rc=result.returncode,
                 stdout_sha256=hashlib.sha256(result.stdout).hexdigest(),stderr_sha256=hashlib.sha256(result.stderr).hexdigest())
    (directory/(name+'.receipt.json')).write_text(json.dumps(receipt,indent=2)+'\n')
    if result.returncode:raise ValueError('offline compile/probe failed: '+name)
    return result.stdout

def build_sources(original,patch_file,directory):
    directory.mkdir(parents=True,exist_ok=False)
    base=directory/'source187.cpp';base.write_bytes(original.read_bytes())
    if digest(base)!=BASE_SHA:raise ValueError('baseline source SHA drift')
    work=directory/'patch-work';work.mkdir();target=work/'android_graphics_compat_shim.cpp';target.write_bytes(base.read_bytes())
    run_record(['/usr/bin/patch','--fuzz=0','-p1','-i',patch_file.resolve()],directory,'existing947-source-patch',cwd=work)
    if digest(target)!=PORT_SHA:raise ValueError('original947 source transform differs')
    port=directory/'source947.cpp';port.write_bytes(target.read_bytes())
    return base,port

def probe(original,ported,directory,compiler=Path('/opt/homebrew/opt/llvm/bin/clang++')):
    if digest(original)!=BASE_SHA or digest(ported)!=PORT_SHA:raise ValueError('exact source pair required')
    directory.mkdir(parents=True,exist_ok=False)
    results={};pins={}
    for variant,source in [('187',original),('947',ported)]:
        text=source.read_text()
        pieces=[]
        if variant=='947':pieces.append('static void nwfs_apply_window_geometry(void*,const char*,int32_t,int32_t);')
        pieces.append(function(text,'void BBQ_nativeUpdate('))
        if variant=='947':pieces.append(function(text,'static void nwfs_apply_window_geometry(void* nw, const char* where, int32_t w, int32_t h) {'))
        pieces.append(function(text,'extern "C" void nwfs_seed_window_geometry(void* nw, const char* where) {'))
        cpp=directory/('isolated-'+variant+'.cpp');cpp.write_text(HEADER+'\n'+'\n'.join(pieces)+'\n'+MAIN)
        binary=directory/('isolated-'+variant)
        run_record([compiler,'-std=c++17','-O0','-Wall','-Wextra','-o',binary,cpp],directory,'compile-'+variant)
        pins[variant]=dict(full_source_sha256=digest(source),extracted_translation_unit_sha256=digest(cpp),host_binary_sha256=digest(binary))
        rows={}
        cases=[('StudyTracker','ViewRootImpl[popup]',864,657),('Seal','ViewRootImpl[popup]',864,1297),
               ('DropCount','ViewRootImpl[popup]',1223,1404),('BoatSurfaceView','SurfaceView[Boat]',1920,1200),
               ('Fullscreen','ViewRootImpl[main]',1200,1920)]
        for name,window,w,h in cases:
            for handoff in ['9cc-setter','adc-preserve']:
                out=run_record([binary,window,w,h,handoff],directory,variant+'-'+name+'-'+handoff)
                rows[name+'/'+handoff]=json.loads(out)
        results[variant]=rows
    receipt=dict(status='HOST_ISOLATED_FUNCTION_AB_NOT_OH_OR_BOAT_PASS',synthetic=True,device_calls=0,
                 production_runtime_builds=0,compiler=dict(path=str(compiler),sha256=digest(compiler)),source=pins,results=results,
                 boundary='Exact187/947 BBQ+seed functions with mocked JNI/window resolver/NativeWindowHandleOpt; ADC handoff is verified NOP semantic model. No real driver, renderer, OH compositor or gameplay executes.')
    (directory/'results.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt
