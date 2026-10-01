import json,subprocess,tempfile,unittest
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1]
class OwnerTests(unittest.TestCase):
 def test_exact_owner_reuse_and_fail_closed(self):
  s=(H/'src/host.c').read_text();a=s[s.index('static int N11ShareJniOwners'):s.index('static WLASC_NOINLINE int StockCreateConfiguredNamespaces')];b=s[s.index('static WLASC_NOINLINE void *StockOpenNamespace'):s.index('static uint8_t HexNibble')]
  c=r'''
#include <string.h>
#include <stddef.h>
#include <stdio.h>
#include <assert.h>
#include <dlfcn.h>
#include <errno.h>
typedef struct { char name[128]; } Dl_namespace;
#define WLASC_NOINLINE
#define APPSPAWN_LOGI(...) ((void)0)
#define APPSPAWN_LOGE(...) ((void)0)
static int fail_get, fail_open, calls, shares;
static const char *seen_owner,*seen_path;static int seen_flags;
static int dlns_get(const char*n,Dl_namespace*p){if(fail_get)return EPERM;strcpy(p->name,n);return 0;}
static int dlns_inherit(Dl_namespace*t,Dl_namespace*o,const char*l){assert(!strcmp(o->name,"westlake.sealed.child"));assert(!strcmp(l,"liboh_adapter_bridge.so:liboh_android_runtime.so"));shares++;return 0;}
static void *dlopen_ns(Dl_namespace*n,const char*p,int f){calls++;seen_owner=!strcmp(n->name,"westlake.sealed.child")?"sealed":"app";seen_path=p;seen_flags=f;return fail_open?NULL:(void*)17;}
static int NamespaceNameOwnedByCurrentProcess(const char*n,const char*role){return !strcmp(n,"westlake.anl.app.mock");}
static void *NamespaceHandleFence(void *p){return p;}
'''+a+b+r'''
int main(void){Dl_namespace n;strcpy(n.name,"westlake.anl.app.mock");
 assert(N11ShareJniOwners(&n)==0 && shares==1);fail_get=1;assert(N11ShareJniOwners(&n)==EPERM);fail_get=0;
 const char*paths[]={"liboh_adapter_bridge.so","/system/android/lib64/liboh_adapter_bridge.so","liboh_android_runtime.so","/system/android/lib64/liboh_android_runtime.so"};
 for(int i=0;i<4;i++){calls=0;assert(StockOpenNamespace(&n,paths[i],RTLD_NOW)==(void*)17);assert(calls==1);assert(!strcmp(seen_owner,"sealed"));assert(seen_flags&RTLD_NOLOAD);assert(seen_path[0]=='/');}
 fail_open=1;calls=0;assert(!StockOpenNamespace(&n,paths[0],RTLD_NOW));assert(calls==1 && (seen_flags&RTLD_NOLOAD));fail_open=0;
 fail_get=1;calls=0;assert(!StockOpenNamespace(&n,paths[0],RTLD_NOW));assert(calls==0);fail_get=0;
 const char*ordinary[]={"libother.so","/data/app/evil/liboh_adapter_bridge.so","/system/android/lib64/../lib64/liboh_adapter_bridge.so"};
 for(int i=0;i<3;i++){calls=0;assert(StockOpenNamespace(&n,ordinary[i],RTLD_NOW)==(void*)17);assert(calls==1 && !strcmp(seen_owner,"app") && !(seen_flags&RTLD_NOLOAD));}
 calls=0;assert(!StockOpenNamespace(&n,paths[0],RTLD_GLOBAL));strcpy(n.name,"foreign");assert(!StockOpenNamespace(&n,paths[0],RTLD_NOW));assert(calls==0);puts("owner reuse + missing-owner/no-fresh fallback + path/namespace negatives PASS");}
'''
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'test.c';p.write_text(c);exe=Path(td)/'test';subprocess.run(['cc','-D_GNU_SOURCE','-std=c11',str(p),'-o',str(exe)],check=True);subprocess.run([str(exe)],check=True)
 def test_musl_semantics_are_pinned(self):
  s=(R/'benchmark/2026-10-01-n10b-child/evidence/oh61-dynlink-linux.c').read_text()
  self.assertIn('p = find_library_by_fstat(&st, namespace, check_inherited, 0);',s);self.assertIn('is_sharable(inherit, p->shortname)',s)
 def test_old_donor_does_not_match_provider(self):
  b=(R.parent/'westlake-generation-u8-j9-t7e/native/payload/android/lib64/libwestlake_android_runtime_provider.so').read_bytes()
  self.assertNotIn(b'INPUT-RT-CL-CHILD',b);self.assertIn(b'child_main_after_stock.cpp',b)
 def test_compat_never_loads_fresh(self):
  s=(H/'src/android_graphics_compat_shim.cpp').read_text();s=s[s.index('static void resolve_oh_wm_funcs()'):s.index('static void* oh_wm_get_native_window')]
  self.assertEqual(s.count('dlopen('),1);self.assertIn('RTLD_NOW | RTLD_NOLOAD',s);self.assertIn('[N11-WM-OWNER]',s)
if __name__=='__main__':unittest.main()
