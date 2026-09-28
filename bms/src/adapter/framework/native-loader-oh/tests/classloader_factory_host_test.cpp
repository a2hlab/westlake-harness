#include <jni.h>
#include <nativeloader/native_loader.h>

#include <cstdio>
#include <cstring>

namespace android {
int register_com_android_internal_os_ClassLoaderFactory(JNIEnv* env);
}

namespace {

void* g_registered_method;
jobject g_class_loader;
int32_t g_target_sdk;
bool g_is_shared;
jstring g_dex_path;
jstring g_library_path;
jstring g_permitted_path;
jstring g_uses_library_list;

jclass FindClass(JNIEnv*, const char*) {
  return reinterpret_cast<jclass>(0x1010);
}

jint RegisterNatives(JNIEnv*, jclass, const JNINativeMethod* methods,
                     jint count) {
  if (count != 1 ||
      std::strcmp(methods[0].name, "createClassloaderNamespace") != 0 ||
      std::strcmp(methods[0].signature,
                  "(Ljava/lang/ClassLoader;ILjava/lang/String;"
                  "Ljava/lang/String;ZLjava/lang/String;Ljava/lang/String;)"
                  "Ljava/lang/String;") != 0) {
    return JNI_ERR;
  }
  g_registered_method = methods[0].fnPtr;
  return JNI_OK;
}

void DeleteLocalRef(JNIEnv*, jobject) {}

}  // namespace

namespace android {

extern "C" jstring CreateClassLoaderNamespace(
    JNIEnv*, int32_t target_sdk_version, jobject class_loader,
    bool is_shared, jstring dex_path, jstring library_path,
    jstring permitted_path, jstring uses_library_list) {
  g_target_sdk = target_sdk_version;
  g_class_loader = class_loader;
  g_is_shared = is_shared;
  g_dex_path = dex_path;
  g_library_path = library_path;
  g_permitted_path = permitted_path;
  g_uses_library_list = uses_library_list;
  return reinterpret_cast<jstring>(0x9090);
}

}  // namespace android

int main() {
  JNINativeInterface table = {};
  table.FindClass = FindClass;
  table.RegisterNatives = RegisterNatives;
  table.DeleteLocalRef = DeleteLocalRef;
  JNIEnv env = {&table};

  if (android::register_com_android_internal_os_ClassLoaderFactory(&env) != 0 ||
      g_registered_method == nullptr) {
    std::fprintf(stderr, "registration failed\n");
    return 1;
  }

  using Method = jstring (*)(JNIEnv*, jclass, jobject, jint, jstring, jstring,
                             jboolean, jstring, jstring);
  auto method = reinterpret_cast<Method>(g_registered_method);
  jobject loader = reinterpret_cast<jobject>(0x1111);
  jstring library = reinterpret_cast<jstring>(0x2222);
  jstring permitted = reinterpret_cast<jstring>(0x3333);
  jstring dex = reinterpret_cast<jstring>(0x4444);
  jstring uses = reinterpret_cast<jstring>(0x5555);

  jstring result = method(&env, reinterpret_cast<jclass>(0x6666), loader, 34,
                          library, permitted, JNI_TRUE, dex, uses);
  if (result != reinterpret_cast<jstring>(0x9090) ||
      g_class_loader != loader || g_target_sdk != 34 || !g_is_shared ||
      g_dex_path != dex || g_library_path != library ||
      g_permitted_path != permitted || g_uses_library_list != uses) {
    std::fprintf(stderr, "seven-argument delegation order mismatch\n");
    return 2;
  }

  std::puts("ClassLoaderFactory seven-argument delegation: PASS");
  return 0;
}
