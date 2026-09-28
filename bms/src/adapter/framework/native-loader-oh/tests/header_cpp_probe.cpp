#include <nativeloader/native_loader.h>

void* westlake_native_loader_cpp_probe[] = {
    reinterpret_cast<void*>(&android::InitializeNativeLoader),
    reinterpret_cast<void*>(&android::ResetNativeLoader),
    reinterpret_cast<void*>(&android::CreateClassLoaderNamespace),
    reinterpret_cast<void*>(&android::OpenNativeLibrary),
    reinterpret_cast<void*>(&android::CloseNativeLibrary),
    reinterpret_cast<void*>(&android::NativeLoaderFreeErrorMessage),
};
