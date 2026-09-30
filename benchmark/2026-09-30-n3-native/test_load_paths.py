"""Compile production ANL; fake only the OH namespace boundary."""
from pathlib import Path
import subprocess,tempfile
P=Path(__file__).resolve().parent
code=r'''
#include "app_native_loader.c"
#include <assert.h>
static int creates,opens;
static char seen_search[16384],seen_permitted[16384];
static int ready(void* p){return 1;}
static int create(Dl_namespace*b,const char*bn,const char*bs,const char*bp,const char*ss,const char*boot,const WlpbHostOpsV1*ops,void**h,Dl_namespace*a,const char*an,const char*as,const char*ap){
 creates++; snprintf(a->name,sizeof(a->name),"%s",an);if(b)snprintf(b->name,sizeof(b->name),"%s",bn);
 snprintf(seen_search,sizeof(seen_search),"%s",as);snprintf(seen_permitted,sizeof(seen_permitted),"%s",ap);return 0;
}
static void* open_ns(Dl_namespace*n,const char*p,int flags){assert(!(flags&RTLD_GLOBAL));opens++;return (void*)1;}
int main(int argc,char**argv){
 AnlRuntimeGateV1 gate={0};gate.abi_version=ANL_RUNTIME_GATE_ABI_VERSION;gate.struct_size=sizeof(gate);gate.verify_current_thread_ready=ready;
 gate.namespace_host_ops=(AnlNamespaceHostOpsV1){.abi_version=ANL_NAMESPACE_HOST_OPS_ABI_VERSION,.struct_size=sizeof(AnlNamespaceHostOpsV1),.runtime_generation=1,.create_configured_namespaces=create,.open_namespace=open_ns};
 assert(ANL_InstallRuntimeGate(&gate)==0);
 for(int i=0;i<4;i++){
  char file[4096],permitted[4096];
  const char* pkg=i==0?"org.localsend.localsend_app":i==1?"org.mozilla.firefox":i==2?"evil.org.mozilla.firefox":"com.DefaultCompany.ZigZag";
  snprintf(file,sizeof(file),"%s/%s/%s",argv[1],pkg,i==0?"libflutter.so":"libnative.so");
  /* Only load-path carries identity in these cases, as in JNA's generic CL. */
  snprintf(permitted,sizeof(permitted),"%s",argv[1]);
  AnlDomainConfig cfg={.app_search_paths=argv[1],.app_permitted_paths=permitted,.bridge_search_paths=argv[1],.bridge_permitted_paths=argv[1],.bridge_shared_sonames="liblog.so"};
  AnlDomain*d=NULL;int old=creates;assert(ANL_CreateDomain(&cfg,&d)==0);assert(creates==old+1);
  assert(ANL_Dlopen(d,file,RTLD_NOW));
  assert(creates==old+(i<2?2:1));
  if(i<2){assert(strstr(seen_search,pkg));assert(strstr(seen_search,i==0?"westlake_flutter":"westlake_native"));assert(!strstr(seen_search,"::"));}
  int first=creates;assert(ANL_Dlopen(d,file,RTLD_NOW));assert(creates==first);
  assert(!ANL_Dlopen(d,file,RTLD_NOW|RTLD_GLOBAL));
  assert(!ANL_Dlopen(d,"/outside/no-file.so",RTLD_NOW));
  ANL_ReleaseDomainHandle(d);
 }
 puts("PASS actual ANL: load-only identities, two lazy kinds, non-target/lookalike, reuse, admission negatives");
}
'''
with tempfile.TemporaryDirectory() as td:
 t=Path(td)
 for pkg in ['org.localsend.localsend_app','org.mozilla.firefox','evil.org.mozilla.firefox','com.DefaultCompany.ZigZag']:
  d=t/pkg;d.mkdir();(d/('libflutter.so' if pkg.startswith('org.localsend') else 'libnative.so')).touch()
 (t/'probe.c').write_text(code)
 for src,success in [(P/'flutter',True),(P.parent/'2026-09-30-n1-native/flutter',False)]:
  subprocess.run(['cc','-std=c11','-D_GNU_SOURCE','-Wno-unused-parameter','-I'+str(P.parents[1]/'bms/src/adapter/framework/app-native-loader/tests/host/include'),'-I'+str(src),'-I'+str(src/'include'),str(t/'probe.c'),'-o',str(t/'probe')],check=True)
  x=subprocess.run([str(t/'probe'),str(t)],text=True,capture_output=True)
  assert (x.returncode==0)==success,(str(src),x.stderr)
  print(src.name, 'candidate passed' if success else 'N1 negative rejected', x.stdout.strip())
