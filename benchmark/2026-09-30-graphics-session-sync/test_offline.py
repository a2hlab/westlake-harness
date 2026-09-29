import hashlib,json,re,subprocess,tempfile,unittest
from pathlib import Path
R=Path(__file__).resolve().parent
REPO=R.parents[1]
SRC=R/'src'

def compile_run(code):
    with tempfile.TemporaryDirectory(prefix='cx-t0-graphics-test-') as d:
        p=Path(d); (p/'t.cpp').write_text(code)
        subprocess.run(['c++','-std=c++17','-I'+str(SRC),str(p/'t.cpp'),'-o',str(p/'test')],check=True)
        subprocess.run([str(p/'test')],check=True)

def table(s):
    t=s[s.index('const JNINativeMethod kBlastBufferQueueMethods[]'):]
    return set(re.findall(r'\{ "(native\w+)",\s*"([^"]+)"',t[:t.index('\n};')]))

def blast_impl(s):
    return s[s.index('jboolean BBQ_nativeSyncNextTransaction('):s.index('// 2026-05-20 R5: BBQ.isSameSurfaceControl')]

class Graphics(unittest.TestCase):
    def test_owners(self):
        compile_run('''#include "surface_session_identity.h"
#include <cassert>
int main(){
 assert(oh_surface_session_identity("OH_Surface_297",298)==297);
 assert(oh_surface_session_identity("OH_Surface_298",297)==298);
 assert(oh_surface_session_identity("SurfaceView[child]",297)==297);
 assert(oh_surface_session_identity("SurfaceView[child]",298)==298);
 assert(oh_surface_session_identity("Background for SurfaceView",297)==297);
 assert(oh_surface_session_identity("OH_Surface_2147483647",0)==2147483647);
}''')
        s=(SRC/'android_view_SurfaceControl.cpp').read_text()
        self.assertIn('oh_surface_session_identity(nameC, parent ? parent->sessionId : 0)',s)
        self.assertIn('dst->sessionId = src->sessionId;',s)

    def test_invalid(self):
        compile_run('''#include "surface_session_identity.h"
#include <cassert>
int main(){
 for(const char* n:{"OH_Surface_", "OH_Surface_-1", "OH_Surface_297x", "OH_Surface_2147483648", "OH_Surface_999999999999999999", "OH_Surface_0"})
  assert(oh_surface_session_identity(n,298)==0);
 assert(oh_surface_session_identity(nullptr,0)==0);
 assert(oh_surface_session_identity("VRI[unknown]",0)==0);
 assert(oh_surface_session_identity("VRI[unknown]",-1)==0);
}'''.replace('#include <cassert>','#include <cassert>\n#include <initializer_list>'))
        for name in ['android_view_SurfaceControl.cpp','android_graphics_compat_shim.cpp']:
            self.assertNotIn('oh_wm_get_last_session',(SRC/name).read_text())
        s=(SRC/'android_graphics_compat_shim.cpp').read_text()
        self.assertNotIn('if (!nw) nw = oh_wm_get_native_window(sessionId);',s)
        self.assertIn('if (b->sessionId != sessionId) b->ohNativeWindow = nullptr;',s)

    def test_signatures(self):
        dex=(R/'source-evidence/BLASTBufferQueue.smali').read_text()
        methods=set(re.findall(r'^\.method private static native (native\w+)(\(.*)',dex,re.M))
        self.assertEqual(len(methods),13)
        s=(SRC/'android_graphics_compat_shim.cpp').read_text()
        self.assertEqual(table(s),methods)
        w=(R/'source-evidence/westlake-compat-shim.cpp').read_text()
        self.assertEqual(blast_impl(s),blast_impl(w))
        self.assertEqual(table(s),table(w))

    def test_exceptions(self):
        impl=blast_impl((SRC/'android_graphics_compat_shim.cpp').read_text())
        compile_run('''#include <cstdio>
#include <cassert>
using jboolean=bool; using jlong=long long; using jclass=void*; using jobject=void*;
using jmethodID=void*; constexpr bool JNI_FALSE=false;
struct JNIEnv {
 int fail=0; bool pending=false; int deleted=0; int constructed=0;
 jclass FindClass(const char*) {if(fail==1){pending=true;return nullptr;}return this;}
 bool ExceptionCheck(){return pending;}
 jmethodID GetMethodID(jclass,const char*,const char*){if(fail==2){pending=true;return nullptr;}return this;}
 void DeleteLocalRef(jclass){deleted++;}
 jobject NewObject(jclass,jmethodID){constructed++;if(fail==3){pending=true;return nullptr;}return this;}
};
'''+impl+'''
int main(){
 JNIEnv ok; assert(!BBQ_nativeSyncNextTransaction(&ok,nullptr,1,&ok,true));
 assert(BBQ_nativeGatherPendingTransactions(&ok,nullptr,1,1)==&ok);
 assert(ok.constructed==1 && ok.deleted==1 && !ok.pending);
 for(int f=1;f<=3;f++){JNIEnv e;e.fail=f;
 assert(BBQ_nativeGatherPendingTransactions(&e,nullptr,1,1)==nullptr);
 assert(e.pending);assert(e.deleted==(f==1?0:1));}
}''')

    def test_package(self):
        evidence=json.loads((R/'package-audit.json').read_text())
        self.assertEqual(evidence['changed_targets'],['/system/android/lib64/liboh_android_runtime.so'])
        self.assertTrue(evidence['baseline_runtime_sha256'].startswith('9e14bf20'))
        self.assertTrue(evidence['needed_equal'])
        self.assertEqual(evidence['removed_exports'],[])
        package=Path(evidence['package'])
        self.assertEqual(hashlib.sha256((package/'payload/android/lib64/liboh_android_runtime.so').read_bytes()).hexdigest(),evidence['runtime_sha256'])
        dry=json.loads((R/'dry-run.json').read_text())
        self.assertTrue(dry['passed'])
        self.assertFalse(dry['device_io'])

if __name__=='__main__':unittest.main()
