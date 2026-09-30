import subprocess,tempfile
from pathlib import Path
r=Path(__file__).resolve().parent;repo=r.parents[1];a=repo/'bms/src/adapter/framework/app-native-loader'
preamble=r'''
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <assert.h>
#include "oh_dlns_abi.h"
#include "westlake_bionic_pthread_bridge.h"
#define WLASC_NOINLINE
static int get_calls, inherits, failure;
static char owners[4][256], libs[4][4096];
void dlns_init(Dl_namespace *n,const char *s){snprintf(n->name,sizeof(n->name),"%s",s);}
int dlns_get(const char *s,Dl_namespace *n){get_calls++;if(failure)return EPERM;dlns_init(n,s);return 0;}
int dlns_create2(Dl_namespace*n,const char*p,int f){return 0;}
int dlns_set_namespace_separated(const char*n,bool s){return 0;}
int dlns_set_namespace_permitted_paths(const char*n,const char*p){return 0;}
int dlns_set_namespace_allowed_libs(const char*n,const char*p){return 0;}
int dlns_inherit(Dl_namespace*n,Dl_namespace*p,const char*l){assert(inherits<4);strcpy(owners[inherits],p->name);strcpy(libs[inherits++],l);return 0;}
void* dlopen_ns(Dl_namespace*n,const char*f,int m){return NULL;}
'''
main=r'''
int main(void){
 Dl_namespace b,a;void *h=NULL;char bn[128],an[128];
 snprintf(bn,sizeof(bn),"westlake.anl.bridge.%ld.1",(long)getpid());
 snprintf(an,sizeof(an),"westlake.anl.app.%ld.1",(long)getpid());
 const char* paths[]={"/system/android/lib64/westlake_flutter:/data/app/org.localsend.localsend_app/lib", "/data/app/org.localsend.localsend_app/lib", "/system/android/lib64/westlake_flutter:/data/app/evil.org.localsend.localsend_app/lib", "/system/android/lib64/westlake_flutter:/data/app/com.DefaultCompany.ZigZag/lib"};
 for(int i=0;i<4;i++) {
  get_calls=inherits=0;
  int rc=StockCreateConfiguredNamespaces(&b,bn,"/runtime","/runtime","liblog.so",NULL,NULL,&h,&a,an,paths[i],"/app");
  assert(rc==0);
  if(i==0){assert(get_calls==2);assert(inherits==3);assert(strcmp(owners[0],"default")==0);assert(strstr(libs[0],"libsurface.z.so"));assert(strcmp(owners[1],"westlake.sealed.child")==0);assert(strstr(libs[1],"liboh_android_runtime.so"));}
  else {assert(get_calls==0);assert(inherits==1);}
 }
 failure=1;inherits=0;
 int rc=StockCreateConfiguredNamespaces(&b,bn,"/runtime","/runtime","liblog.so",NULL,NULL,&h,&a,an,paths[0],"/app");
 assert(rc==EPERM);assert(inherits==0);
 failure=0;
 rc=StockCreateConfiguredNamespaces(&b,bn,"/runtime","/runtime","liblog.so",NULL,NULL,&h,&a,"foreign.app",paths[0],"/app");
 assert(rc==EINVAL);puts("PASS Flutter real owner edges; non-Flutter unchanged; lookup/foreign negatives");
}
'''
with tempfile.TemporaryDirectory() as td:
 for name,expected in [('src/westlake_stock_host_main.c',True),('../2026-09-30-v3c-next4-namespace/westlake_stock_host_main.baseline.c',False)]:
  s=(r/name).read_text(); s=s[s.index('static int NamespaceNameOwned'):s.index('static WLASC_NOINLINE void *StockOpenNamespace')]
  c=Path(td)/'probe.c';c.write_text(preamble+s+main);bin=Path(td)/'probe'
  cmd=['cc','-std=c11','-D_GNU_SOURCE','-Wno-unused-function','-Wno-unused-parameter']
  cmd+=['-I'+str(p) for p in [a/'tests/host/include',a/'include',a/'src',repo/'bms/src/adapter/framework/native-compat/bionic-pthread-bridge/include']]
  subprocess.run(cmd+[str(c),'-o',str(bin)],check=True)
  x=subprocess.run([str(bin)],capture_output=True,text=True)
  assert (x.returncode==0)==expected,(name,x.returncode,x.stderr)
  print(name, 'PASS' if expected else 'negative rejected',x.stdout.strip())
