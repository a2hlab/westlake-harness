"""Exercise the actual callback body with a recorded namespace transport."""
from pathlib import Path
import shutil,subprocess,tempfile,unittest
H=Path(__file__).resolve().parent
class Callback(unittest.TestCase):
 def test_routes_and_typed_failures(self):
  source=(H/'src/sealed_child_provider_loader.c').read_text()
  callback=source[source.index('static Dl_namespace closure_namespace;'):source.index('\nstatic void *RealOpenLocalNow')]
  harness=r'''
#define WLSCPL_TESTING
#include "sealed_child_provider_loader.c"
#include <assert.h>
typedef struct {int token;} Dl_namespace;
static int opens, logs, fail;
static void *last_namespace;
static const char *last_path;
static int last_flags;
static int logger(int a,int b,unsigned int c,const char*d,const char*e,...) {(void)a;(void)b;(void)c;(void)d;(void)e;logs++;return 0;}
static void *lookup(void *h,const char *s) {(void)h;assert(!strcmp(s,"HiLogPrint"));return (void*)logger;}
static void *open_ns(Dl_namespace*n,const char*p,int f) {opens++;last_namespace=n;last_path=p;last_flags=f;return fail?NULL:(void*)33;}
#define dlsym lookup
#define dlopen_ns open_ns
'''+callback+r'''
int main(void) {
 namespace_prepared=1; g_owner_handles[0]=(void*)11;g_owner_handles[1]=(void*)22;
 int flags=RTLD_NOW|RTLD_LOCAL;
 assert(WLSCPL_OpenPreparedNamespace(g_owner_paths[0],flags)==(void*)11 && opens==0);
 assert(WLSCPL_OpenPreparedNamespace(g_owner_paths[1],flags)==(void*)22 && opens==0);
 const char *path="/system/android/lib64/libandroid.so";
 assert(WLSCPL_OpenPreparedNamespace(path,flags)==(void*)33 && opens==1);
 assert(last_namespace==&closure_namespace && last_path==path && last_flags==flags);
 g_owner_handles[0]=NULL;N11eReset();
 assert(!WLSCPL_OpenPreparedNamespace(g_owner_paths[0],flags));
 assert(g_n11e_failure.branch==WLSCPL_FAILB_OWNER_PUBLISH_LATE && g_n11e_failure.index==0 && opens==1);
 fail=1;N11eReset();assert(!WLSCPL_OpenPreparedNamespace(path,flags));
 assert(g_n11e_failure.branch==WLSCPL_FAILB_ARTIFACT_DLOPEN && opens==2);
 assert(!WLSCPL_OpenPreparedNamespace("/system/android/lib64/../libart.so",flags));
 assert(!WLSCPL_OpenPreparedNamespace(path,RTLD_NOW|RTLD_GLOBAL));
 assert(!WLSCPL_OpenPreparedNamespace(NULL,flags));
 namespace_prepared=0;assert(!WLSCPL_OpenPreparedNamespace(path,flags));
 assert(opens==2 && logs==9);
 return 0;
}
'''
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);(p/'test.c').write_text(harness)
   subprocess.run([shutil.which('clang'),'-std=c11','-D_GNU_SOURCE','-I'+str(H/'src'),'-I'+str(H/'include'),str(p/'test.c'),'-o',str(p/'test')],check=True)
   subprocess.run([str(p/'test')],check=True)
if __name__=='__main__':unittest.main()
