#include "system_loader.h"
#include <cassert>
#include <cstdlib>
#include <dlfcn.h>
#include <string>
#include <cstring>

namespace westlake::nativeloader {
char *CopyError(const std::string &message) {
    char *copy = static_cast<char *>(std::malloc(message.size() + 1));
    if (copy) std::memcpy(copy, message.c_str(), message.size() + 1);
    return copy;
}
}

using namespace westlake::nativeloader;
class Ops final : public SystemLoaderOps {
public:
    mutable std::string path;
    mutable int flags = 0;
    mutable unsigned opens = 0;
    bool redirect = false, fail_open = false;
    bool ResolvePath(const char *input, std::string *resolved, std::string *) const override {
        *resolved = redirect && std::string(input).find("/lib64/") != std::string::npos
            ? "/data/app/evil/libmedia_jni.so" : input;
        return true;
    }
    void *OpenExact(const char *input, int mode) const override {
        ++opens;
        path = input;
        flags = mode;
        return fail_open ? nullptr : reinterpret_cast<void *>(0x4000);
    }
    int CloseExact(void *) const override { return 0; }
    const char *LastError() const override { return "resident owner absent"; }
};

int main() {
    Ops ops;
    SystemLoader loader(&ops);
    char *error = nullptr;
    void *handle = loader.Open("libmedia_jni.so", "/system/android/framework/framework.jar", false, &error);
    assert(handle && !error && loader.Owns(handle));
    assert(ops.path == "/system/android/lib64/liboh_android_runtime.so");
    assert((ops.flags & RTLD_NOLOAD) && !(ops.flags & RTLD_GLOBAL));
    assert(loader.Close(handle, &error));
    unsigned previous = ops.opens;
    handle = loader.Open("libmedia_jni.so", "/data/app/package/base.apk", false, &error);
    assert(!handle && error && ops.opens == previous);
    std::free(error); error = nullptr;
    ops.redirect = true;
    handle = loader.Open("libmedia_jni.so", "/system/framework/framework.jar", false, &error);
    assert(!handle && error && ops.opens == previous);
    std::free(error); error = nullptr;
    ops.redirect = false;
    handle = loader.Open("libmediandk.so", "/system/framework/framework.jar", false, &error);
    assert(!handle && error && ops.opens == previous);
    std::free(error); error = nullptr;
    ops.fail_open = true;
    handle = loader.Open("libmedia_jni.so", "/system/framework/framework.jar", false, &error);
    assert(!handle && error && std::string(error) == "resident owner absent");
    std::free(error); error = nullptr;
    ops.fail_open = false;
    handle = loader.Open("libicu_jni.so", "/system/framework/core-oj.jar", false, &error);
    assert(handle && !error && !(ops.flags & RTLD_NOLOAD));
    assert(loader.Close(handle, &error));
    handle = loader.Open("libmedia_jni.so", "/system/framework/framework.jar", true, &error);
    assert(!handle && error);
    std::free(error);
    return 0;
}
