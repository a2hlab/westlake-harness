"""Exercise actual production RealOpenLocalNow with a bounded mock loader ABI.
This proves namespace/order/failure handling, not device DSO uniqueness.
"""
import subprocess,tempfile,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
class OwnerOrder(unittest.TestCase):
 def test_route_owner_and_failures(self):
  s=(HERE/'src/sealed_child_provider_loader.c').read_text()
  fn=s[s.index('static void *RealOpenLocalNow'):s.index('static int RealCloseHandle')]
  prefix=r"""#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <limits.h>
#include <stdint.h>
#include <stdlib.h>
#define RTLD_NOW 2
#define RTLD_LOCAL 0
#define RTLD_NOLOAD 4
#define CREATE_INHERIT_CURRENT 2
typedef struct { char name[256]; } Dl_namespace;
static Dl_namespace closure_namespace;
static int namespace_prepared;
static int events, art_loaded, fail_art, fail_owner, owners, markers;
static int emit(int t,int l,unsigned d,const char *tag,const char *fmt,...) {assert(t==3&&l==4&&d==0xD000F00u);assert(!strcmp(tag,"N10bOwner"));assert(strstr(fmt,"preloaded in westlake.sealed.child"));assert(owners==2);++markers;return 1;}
static void *dlsym(void *handle,const char *name) {assert(handle);assert(!strcmp(name,"HiLogPrint"));return (void*)&emit;}
static int dlns_create2(Dl_namespace *n,const char *p,int f) { assert(!strcmp(n->name,"westlake.sealed.child"));assert(strstr(p,"route-a"));assert(f==CREATE_INHERIT_CURRENT); ++events; return 0; }
static void dlns_init(Dl_namespace *n,const char *p) { strcpy(n->name,p); }
static int dlclose(void *p) {assert(p);return 0;}
static const char *dlerror(void) { return "mock rejection"; }
static void *dlopen_ns(Dl_namespace *n,const char *p,int f) {
 assert(!strcmp(n->name,"westlake.sealed.child")); ++events;
 if (strstr(p,"libwestlake_android_runtime_provider.so")) {art_loaded=1;return (void*)1;}
 if (!strcmp(p,"libart.so")) {assert(f&RTLD_NOLOAD);return fail_art?NULL:(void*)2;}
 if (strstr(p,"liboh_")) {assert(art_loaded); ++owners; return fail_owner?NULL:(void*)3;}
 return (void*)4;
}
"""
  main=r"""
int main(int argc,char **argv) {
 fail_art=argc>1&&!strcmp(argv[1],"art");fail_owner=argc>1&&!strcmp(argv[1],"owner");
 assert(RealOpenLocalNow(NULL,"/route-a/g/libnativehelper.so",RTLD_NOW));
 assert(owners==0);void *p=RealOpenLocalNow(NULL,"/route-a/g/libwestlake_android_runtime_provider.so",RTLD_NOW);
 assert((p!=NULL)==(!fail_art&&!fail_owner));
 if (!fail_art&&!fail_owner) {assert(owners==2);assert(RealOpenLocalNow(NULL,"/route-a/g/libwestlake_android_runtime_provider.so",RTLD_NOW));assert(owners==2);assert(markers==2);}
 return 0;
}
"""
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'case.c').write_text(prefix+fn+main)
   subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',str(p/'case.c'),'-o',str(p/'case')],check=True)
   for mode in ['ok','art','owner']:subprocess.run([str(p/'case'),mode],check=True)
if __name__=='__main__':unittest.main()
