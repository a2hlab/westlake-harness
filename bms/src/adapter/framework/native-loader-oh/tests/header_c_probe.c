#include <nativeloader/native_loader.h>

void* westlake_native_loader_c_probe[] = {
    (void*)&InitializeNativeLoader,
    (void*)&ResetNativeLoader,
    (void*)&CreateClassLoaderNamespace,
    (void*)&OpenNativeLibrary,
    (void*)&CloseNativeLibrary,
    (void*)&NativeLoaderFreeErrorMessage,
};
