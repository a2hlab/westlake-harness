/*
 * Copyright (C) 2015 The Android Open Source Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#ifndef WESTLAKE_NATIVE_LOADER_OH_INCLUDE_NATIVELOADER_NATIVE_LOADER_H_
#define WESTLAKE_NATIVE_LOADER_OH_INCLUDE_NATIVELOADER_NATIVE_LOADER_H_

#include <stdbool.h>
#include <stdint.h>

#include "jni.h"

#ifdef __cplusplus
namespace android {
extern "C" {
#endif

__attribute__((visibility("default"))) void InitializeNativeLoader(void);

__attribute__((visibility("default"))) jstring CreateClassLoaderNamespace(
    JNIEnv* env, int32_t target_sdk_version, jobject class_loader,
    bool is_shared, jstring dex_path, jstring library_path,
    jstring permitted_path, jstring uses_library_list);

__attribute__((visibility("default"))) void* OpenNativeLibrary(
    JNIEnv* env, int32_t target_sdk_version, const char* path,
    jobject class_loader, const char* caller_location, jstring library_path,
    bool* needs_native_bridge, char** error_msg);

__attribute__((visibility("default"))) bool CloseNativeLibrary(
    void* handle, bool needs_native_bridge, char** error_msg);

__attribute__((visibility("default"))) void NativeLoaderFreeErrorMessage(
    char* msg);

__attribute__((visibility("default"))) void ResetNativeLoader(void);

typedef void* (*WestlakeSealedOpenFnV1)(const char* absolute_path, int flags);

__attribute__((visibility("default"))) int WLNL_InstallSealedOpenV1(
    WestlakeSealedOpenFnV1 open_fn);

#ifdef __cplusplus
}  // extern "C"
}  // namespace android
#endif

#endif  // WESTLAKE_NATIVE_LOADER_OH_INCLUDE_NATIVELOADER_NATIVE_LOADER_H_
