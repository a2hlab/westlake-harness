"""Compile actual registration fixes against JNI mock; no device assertions."""
import subprocess,tempfile,unittest
from pathlib import Path
H=Path(__file__).resolve().parent;WS=H.parents[2]
class RegistrationInit(unittest.TestCase):
 def test_vm_order_and_two_owner_caches(self):
  jni=WS/'westlake-harness-bms-deploy/bms/src/.work/b6-art14-recovery/aosp-restoration/libnativehelper/include_jni'
  main=r'''
#include <jni.h>
#include <dlfcn.h>
#include <cassert>
#include <cstring>
#include <string>
namespace android { struct assetmanager_offsets_t { jfieldID mObject; }; assetmanager_offsets_t gAssetManagerOffsets{}; int register_android_graphics_Typeface(JNIEnv*); }
extern "C" int initialize_n10b_asset_offsets(JNIEnv*);
static android::assetmanager_offsets_t ndk{};
static std::string mode; static int order=0,registered=0;
static JavaVM vm{}; static JavaVM* graphics_vm=nullptr;
static jfieldID field=reinterpret_cast<jfieldID>(0x5678);
static jint get_vm(JNIEnv*,JavaVM** out) { *out=mode=="vm"?nullptr:&vm;return JNI_OK; }
static void set_vm(JavaVM* p) {assert(order==0);graphics_vm=p;order=1;}
static int real_reg(JNIEnv*) {assert(order==1&&graphics_vm==&vm);order=2;++registered;return 0;}
static jclass find_class(JNIEnv*,const char* name) { assert(!strcmp(name,"android/content/res/AssetManager")); return reinterpret_cast<jclass>(1); }
static jfieldID get_field(JNIEnv*,jclass,const char* name,const char* sig) {assert(!strcmp(name,"mObject")&&!strcmp(sig,"J"));return mode=="field"?nullptr:field;}
static void delete_ref(JNIEnv*,jobject) {}
static jboolean exception(JNIEnv*) {return false;}
extern "C" void* dlopen(const char* name,int) { if(!strcmp(name,"libhwui.so"))return reinterpret_cast<void*>(1);assert(!strcmp(name,"libandroid.so"));return mode=="ndk"?nullptr:reinterpret_cast<void*>(2); }
extern "C" void* dlsym(void* handle,const char* name) {
 if(handle==reinterpret_cast<void*>(2)) {assert(!strcmp(name,"_ZN7android20gAssetManagerOffsetsE"));return mode=="cache"?nullptr:&ndk;}
 if(!strcmp(name,"_ZN11GraphicsJNI9setJavaVMEP7_JavaVM"))return mode=="setter"?nullptr:reinterpret_cast<void*>(&set_vm);
 if(!strcmp(name,"register_android_graphics_Typeface"))return reinterpret_cast<void*>(&real_reg);
 assert(false);return nullptr;
}
extern "C" char* dlerror() {return nullptr;}
int main(int argc,char** argv) {
 assert(argc==2);mode=argv[1];JNINativeInterface f{};f.GetJavaVM=get_vm;f.FindClass=find_class;f.GetFieldID=get_field;f.DeleteLocalRef=delete_ref;f.ExceptionCheck=exception;JNIEnv env{&f};
 int rc=android::register_android_graphics_Typeface(&env);
 if(mode=="vm"||mode=="setter") {assert(rc<0&&registered==0);return 0;}
 assert(rc==0&&registered==1);
 rc=initialize_n10b_asset_offsets(&env);
 if(mode=="field"||mode=="ndk"||mode=="cache") {assert(rc<0&&ndk.mObject==nullptr);return 0;}
 assert(rc==0&&ndk.mObject==field&&android::gAssetManagerOffsets.mObject==field);
 return 0;
}
'''
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);(p/'hilog').mkdir();(p/'hilog/log.h').write_text('#define LOG_CORE 0\n#define LOG_INFO 1\n#define LOG_WARN 2\n#define LOG_ERROR 3\ninline int HiLogPrint(int,int,unsigned,const char*,const char*,...){return 0;}\n');(p/'case.cpp').write_text(main)
   subprocess.run(['c++','-std=c++17','-Wno-writable-strings','-I'+str(jni),'-I'+str(p),str(p/'case.cpp'),str(H/'src/android_graphics_Typeface.cpp'),str(H/'src/asset-offsets-init.cpp'),'-o',str(p/'case')],check=True)
   for mode in ['ok','vm','setter','field','ndk','cache']:subprocess.run([str(p/'case'),mode],check=True)
if __name__=='__main__':unittest.main()
