#include "../overlay/android_dlext_abi.h"

#include <assert.h>
#include <dlfcn.h>

extern void* android_dlopen_ext(const char*, int, const android_dlextinfo*);

int main(int count, char** arguments) {
    assert(count == 2);
    android_dlextinfo info = {0};
    for (int iteration = 0; iteration < 2; ++iteration) {
        void* handle = android_dlopen_ext(arguments[1], RTLD_NOW, iteration == 0 ? NULL : &info);
        assert(handle != NULL);
        int (*function)(void) = (int (*)(void))dlsym(handle, "shim_fixture_value");
        assert(function != NULL && function() == 731);
        assert(dlclose(handle) == 0);
    }
    (void)dlerror();
    assert(android_dlopen_ext("/nonexistent-u10-fixture.so", RTLD_NOW, NULL) == NULL);
    assert(dlerror() != NULL);
    return 0;
}
