#include "launcher_activity.h"
#include <cassert>
#include <iostream>
int main(int argc,char**argv) {
 assert(argc > 1);
 for(int i=1;i<argc;++i) {
  oh_adapter::ApkManifestParser::ManifestData m;
  assert(oh_adapter::ApkManifestParser::Parse(argv[i],m));
  const auto* chosen=oh_adapter::SelectLauncherActivity(m); assert(chosen);
  int count=0; for(const auto&a:m.activities) if(oh_adapter::IsAndroidLauncherActivity(a)) ++count;
  for(const auto&a:m.activities) if(oh_adapter::IsAndroidLauncherActivity(a)) std::cout << "candidate=" << a.name << "\n";
  if(m.packageName=="com.ichi2.anki") assert(chosen->name.rfind("com.ichi2.anki.",0)==0);
  std::cout << m.packageName << " launcher_count=" << count << " selected=" << chosen->name << " PASS\n";
 }
}
