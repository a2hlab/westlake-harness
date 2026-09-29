#include "launcher_activity.h"
#include <cstdio>
using oh_adapter::ApkManifestParser;
static ApkManifestParser::ActivityData MkLauncher(const char* name){
    ApkManifestParser::ActivityData a; a.name=name;
    ApkManifestParser::IntentFilterData f;
    f.actions.push_back("android.intent.action.MAIN");
    f.categories.push_back("android.intent.category.LAUNCHER");
    a.intentFilters.push_back(f);
    return a;
}
static int check(bool ok,const char*m,const char*got){std::printf("%s %s%s%s\n",ok?"PASS":"FAIL",m,got?" got=":"",got?got:"");return ok?0:1;}
int main(){
    int fail=0;
    {ApkManifestParser::ManifestData m; m.packageName="com.ichi2.anki";
     m.activities.push_back(MkLauncher("leakcanary.internal.activity.LeakLauncherActivity"));
     m.activities.push_back(MkLauncher("com.ichi2.anki.IntroductionActivity"));
     auto*c=oh_adapter::SelectLauncherActivity(m);
     fail+=check(c&&c->name=="com.ichi2.anki.IntroductionActivity","anki: own-pkg launcher chosen over leakcanary-first",c?c->name.c_str():"null");}
    {ApkManifestParser::ManifestData m; m.packageName="com.ichi2.anki";
     m.activities.push_back(MkLauncher("com.ichi2.anki.IntroductionActivity"));
     m.activities.push_back(MkLauncher("leakcanary.internal.activity.LeakLauncherActivity"));
     auto*c=oh_adapter::SelectLauncherActivity(m);
     fail+=check(c&&c->name=="com.ichi2.anki.IntroductionActivity","own-pkg launcher wins regardless of order",c?c->name.c_str():"null");}
    {ApkManifestParser::ManifestData m; m.packageName="com.example.app";
     m.activities.push_back(MkLauncher("some.other.LauncherActivity"));
     auto*c=oh_adapter::SelectLauncherActivity(m);
     fail+=check(c&&c->name=="some.other.LauncherActivity","foreign-only launcher falls back to first",c?c->name.c_str():"null");}
    {ApkManifestParser::ManifestData m; m.packageName="com.example.app";
     ApkManifestParser::ActivityData a; a.name="com.example.app.PlainActivity"; m.activities.push_back(a);
     auto*c=oh_adapter::SelectLauncherActivity(m);
     fail+=check(c==nullptr,"no launcher -> nullptr",c?c->name.c_str():"null");}
    std::printf(fail?"\n%d FAIL\n":"\nALL PASS\n",fail);
    return fail?1:0;
}
