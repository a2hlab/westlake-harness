"""Tests of the actual production sharing block and offline candidate boundary."""
import hashlib,json,subprocess,tempfile,unittest
from pathlib import Path
H=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text())
class Tests(unittest.TestCase):
 def test_identity(self):
  evidence=H.parent/'2026-10-01-n11-single-owner/offline-load-path'
  identities=read(evidence/'binary-identities.json')['inputs']
  self.assertTrue(identities['provider']['sha256'].startswith('0509fe23'))
  self.assertTrue(identities['bridge']['sha256'].startswith('84695d62'))
  self.assertIn('0xcf2c', (evidence/'provider-callsite-disassembly.txt').read_text())
  log=(evidence/'helloworld-load-order.txt').read_text()
  self.assertLess(log.index('[N10b-JNI-OWNER]'),log.index('ClassLoaderFactory::createClassloaderNamespace'))
  addresses=read(evidence/'address-derivation.json');self.assertNotEqual(addresses['bridge_java']['base'],addresses['bridge_compat']['base'])
 def test_owner(self):
  source=(H/'src/sealed_child_provider_loader.c').read_text()
  start=source.index('        /* N11b:');end=source.index('        /* HiLog ABI',start);block=source[start:end]
  harness='''#include <stddef.h>
#include <string.h>
#include <assert.h>
#define RTLD_NOW 2
#define RTLD_LOCAL 0
#define RTLD_NOLOAD 4
typedef struct {const char *name;} Dl_namespace;
static int scenario,lookups;
static void dlns_init(Dl_namespace *n,const char *s){n->name=s;}
static int dlns_inherit(Dl_namespace *a,Dl_namespace *b,const char *s){
 assert(!strcmp(a->name,"default"));(void)b;
 assert(!strcmp(s,"liboh_adapter_bridge.so:liboh_android_runtime.so"));
 return scenario==1 ? -1:0;
}
static int dlclose(void *h){(void)h;return 0;}
static void *dlopen_ns(Dl_namespace *n,const char *p,int flags){
 assert(!strcmp(n->name,"default"));assert(flags==(RTLD_NOW|RTLD_NOLOAD));
 int first=strstr(p,"adapter_bridge")!=NULL;lookups++;
 if((scenario==2&&first)||(scenario==4&&!first))return NULL;
 if(scenario==3&&first)return (void*)9;
 return first ? (void*)1:(void*)2;
}
static void *probe(void){
 void *handle=(void*)4;size_t owner;Dl_namespace closure_namespace={"westlake.sealed.child"};
 void *jni_owner_handles[2]={(void*)1,(void*)2};
 const char *owner_paths[2]={"/system/android/lib64/liboh_adapter_bridge.so","/system/android/lib64/liboh_android_runtime.so"};
'''+block+'''
 return handle;
}
int main(void){for(scenario=0;scenario<5;scenario++){lookups=0;assert((probe()!=NULL)==(scenario==0));if(scenario==1)assert(lookups==0);}return 0;}
'''
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'test.c').write_text(harness);subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',str(p/'test.c'),'-o',str(p/'test')],check=True);subprocess.run([str(p/'test')],check=True)
 def test_package(self):
  receipt=read(H/'build-receipt.json');self.assertTrue(receipt['baseline']['sha256'].startswith('dc73a28d'));self.assertEqual(receipt['candidate']['sha256'],receipt['repeat']['sha256'])
  d=read(H/'package.json');self.assertFalse(d['rollout_ready']);self.assertFalse(d['device_io']);self.assertEqual(d['identity_count'],312);self.assertEqual(set(d['changes']),{'/system/lib64/appspawn/libwestlake_android_child.z.so'})
  self.assertIn('0 violation(s)',(H/'frozen.txt').read_text())
  abi=read(H/'elf-compatibility.json');self.assertTrue(abi['needed_equal']);self.assertTrue(abi['soname_equal']);self.assertEqual(abi['removed_exports'],[]);self.assertEqual(abi['added_exports'],[])
if __name__=='__main__':unittest.main()
