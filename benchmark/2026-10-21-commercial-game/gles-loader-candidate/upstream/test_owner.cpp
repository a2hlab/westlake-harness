#include <cassert>
#include <cstdlib>
#include <cstring>
#include <dlfcn.h>
#include <string>
#include "system_loader.h"

namespace westlake::nativeloader {
char* CopyError(const std::string& message) { return strdup(message.c_str()); }
}

class FakeOps : public westlake::nativeloader::SystemLoaderOps {
 public:
  mutable int flags = 0;
  mutable std::string path;
  bool resident = true;
  bool ResolvePath(const char* input, std::string* output, std::string*) const override {
    *output = input;
    return true;
  }
  void* OpenExact(const char* input, int input_flags) const override {
    flags = input_flags;
    path = input;
    if ((flags & RTLD_NOLOAD) && !resident) return nullptr;
    return reinterpret_cast<void*>(0x1234);
  }
  int CloseExact(void*) const override { return 0; }
  const char* LastError() const override { return "resident owner unavailable"; }
};

int main() {
  FakeOps ops;
  westlake::nativeloader::SystemLoader loader(&ops);
  char* error = nullptr;
  void* handle = loader.Open("libmedia_jni.so", nullptr, false, &error);
  assert(handle && !error && (ops.flags & RTLD_NOLOAD));
  assert(ops.path == "/system/android/lib64/liboh_android_runtime.so");
  assert(loader.Close(handle, &error));
  ops.resident = false;
  assert(!loader.Open("libmedia_jni.so", nullptr, false, &error));
  assert(error && (ops.flags & RTLD_NOLOAD));
  free(error);
  handle = loader.Open("libmediandk.so", nullptr, false, &error);
  assert(handle && !error && !(ops.flags & RTLD_NOLOAD));
  assert(loader.Close(handle, &error));
  assert(!loader.Open("libunapproved.so", nullptr, false, &error));
  assert(error);
  free(error);
}
