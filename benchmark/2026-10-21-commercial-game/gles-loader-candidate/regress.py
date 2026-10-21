#!/usr/bin/env python3
"""Run preserved U13 policy/owner and native loader host regression plus bounded delta controls."""
import argparse, difflib, json, shutil
from pathlib import Path
from prepare_inputs import HERE, MAIN, AUTHOR, REL, sha, save, alias
from build_candidate import run

def stage_tests():
 up=HERE/'upstream';tests=HERE/'tests';tests.mkdir(exist_ok=True)
 support=MAIN/REL/'sources/build-support'
 if not (up/'build-support').exists():shutil.copytree(support,up/'build-support')
 original=AUTHOR/'bms/src/adapter/framework/native-loader-oh/tests/native_loader_registry_host_test.cpp'
 if not (up/original.name).exists():shutil.copyfile(original,up/original.name)
 text=(up/original.name).read_text();anchor='  std::vector<std::string> bridge = fakeanl::LastBridgeSonames();'
 assert text.count(anchor)==1
 extra='''
  std::vector<std::string> expected = {"libandroid.so", "libEGL.so", "liblog.so",
      "libmediandk.so", "libz.so", "libwestlake_bionic_pthread_bridge.so", "libstdc++.so"};
#ifdef EXPECT_GLES
  expected.push_back("libGLESv2.so");
#endif
  CHECK(bridge == expected, "exact ordered shared policy reaches explicit backend");
  bool implicit_bridge = true;
  char* implicit_error = nullptr;
  void* implicit_handle = android::OpenNativeLibrary(
      env, 34, "/data/app/test/lib/arm64/libprobe.so", fakejni::NewObject(),
      "caller", search, &implicit_bridge, &implicit_error);
  CHECK(implicit_handle != nullptr && implicit_error == nullptr, "implicit open succeeds");
  CHECK(fakeanl::LastBridgeSonames() == expected, "exact ordered shared policy reaches implicit backend");
  if (implicit_handle != nullptr) {
    CHECK(android::CloseNativeLibrary(implicit_handle, implicit_bridge, &implicit_error), "implicit handle closes");
  }
'''
 augmented=text.replace(anchor,anchor+extra);(tests/'registry_delta_test.cpp').write_text(augmented)
 owner=(up/'test_owner.cpp').read_text();owner=owner.replace('#include "system_loader.h"','#include "system_loader.h"\n#include <nativeloader/native_bridge_policy.h>')
 anchor='  char* error = nullptr;';assert owner.count(anchor)==1
 owner=owner.replace(anchor,anchor+'''
  static_assert(westlake::nativeloader::policy::kSystemLibraries.size() == 7);
  for (const auto& item : westlake::nativeloader::policy::kSystemLibraries) {
    void* each = loader.Open(std::string(item.soname).c_str(), nullptr, false, &error);
    assert(each && !error && ops.path == item.path);
    assert(bool(ops.flags & RTLD_NOLOAD) == (item.soname == "libmedia_jni.so"));
    assert(loader.Close(each, &error));
  }
''');(tests/'system7_test.cpp').write_text(owner)
 (tests/'registry-test.patch').write_text(''.join(difflib.unified_diff(text.splitlines(True),augmented.splitlines(True),fromfile='upstream/native_loader_registry_host_test.cpp',tofile='tests/registry_delta_test.cpp')))
 save(HERE/'test-source-pins.json',{'original_registry':{'path':alias(original),'sha256':sha(original)},'files':{str(p.relative_to(HERE)):sha(p) for root in [up/'build-support',tests] for p in sorted(root.rglob('*')) if p.is_file()},'original_owner_sha256':sha(up/'test_owner.cpp'),'preserved_registry_sha256':sha(up/original.name)})

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',default='regression-01');args=ap.parse_args();output=HERE/'.private'/args.out;output.mkdir(parents=True,exist_ok=False);stage_tests();up=HERE/'upstream';tests=HERE/'tests';records=[]
 for variant in ['baseline','candidate']:
  tree=HERE/'sources'/variant
  records.append(run(output,variant+'-policy',['python3',tree/'tests/verify_bridge_policy.py'],output))
  common=['clang++','-std=c++17','-O2','-Werror','-pthread','-include',up/'test_platform.h','-I'+str(tree/'include'),'-I'+str(tree/'src'),'-I'+str(up/'build-support/dependencies')]
  for kind,test in [('owner',up/'test_owner.cpp'),('system7',tests/'system7_test.cpp'),('registry',up/'native_loader_registry_host_test.cpp'),('registry-delta',tests/'registry_delta_test.cpp')]:
   binary=output/(variant+'-'+kind);sources=[tree/'src/system_loader.cpp']
   if kind.startswith('registry'):sources += [tree/'src/native_loader.cpp',tree/'src/native_loader_registry.cpp']
   flags=['-DEXPECT_GLES'] if variant=='candidate' else []
   records.append(run(output,variant+'-'+kind+'-compile',common+flags+[test]+sources+['-o',binary],output))
   records.append(run(output,variant+'-'+kind+'-run',[binary],output))
 for case,value,message in [('duplicate','libGLESv2.so','contains duplicates'),('invalid','/libbad.so','invalid bridge SONAME'),('reserved','libc.so','reserved-self')]:
  tree=output/('negative-'+case);shutil.copytree(HERE/'sources/candidate',tree)
  p=tree/'policy/native_bridge_policy.v1.json';d=json.loads(p.read_text());d['shared_sonames'].append(value);save(p,d)
  p=tree/'include/nativeloader/native_bridge_policy.h';s=p.read_text().replace('std::array<std::string_view, 8> kBridgeSharedSonames','std::array<std::string_view, 9> kBridgeSharedSonames').replace('    "libGLESv2.so",','    "libGLESv2.so",\n    "'+value+'",');p.write_text(s)
  records.append(run(output,'negative-'+case,['python3',tree/'tests/verify_bridge_policy.py'],output,allowed=(1,)))
  assert message in (output/'commands'/('negative-'+case)/'stderr').read_text()
 result={'status':'PASS','records':records,'production_delta_files':2,'system_entries':7,'shared_baseline':7,'shared_candidate':8,'negative_cases':3,'device_calls':0}
 save(output/'receipt.json',result);save(HERE/'regression.json',json.loads(json.dumps(result).replace(str(HERE),'$G18')))
 print('regressions complete: original tests + explicit/implicit policy + system7 + 3 negative cases')
if __name__=='__main__':main()
