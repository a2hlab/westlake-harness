#include <nativeloader/native_bridge_policy.h>
#include <nativeloader/native_loader.h>

#include "native_loader_registry.h"
#include "system_loader.h"

#include <dlfcn.h>

#include <cstdlib>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

namespace westlake::nativeloader {
namespace {

bool ReadJString(JNIEnv* env, jstring value, std::optional<std::string>* output,
                 std::string* error) {
  if (value == nullptr) {
    output->reset();
    return true;
  }
  const char* utf = env->GetStringUTFChars(value, nullptr);
  if (utf == nullptr) {
    *error = "GetStringUTFChars failed";
    return false;
  }
  *output = std::string(utf);
  env->ReleaseStringUTFChars(value, utf);
  return true;
}

bool SplitColonStrict(const std::optional<std::string>& input,
                      const char* field, std::vector<std::string>* output,
                      std::string* error) {
  output->clear();
  if (!input.has_value() || input->empty()) return true;
  size_t begin = 0;
  while (begin <= input->size()) {
    size_t end = input->find(':', begin);
    if (end == std::string::npos) end = input->size();
    if (end == begin) {
      *error = std::string(field) + " contains an empty segment";
      return false;
    }
    output->push_back(input->substr(begin, end - begin));
    if (end == input->size()) break;
    begin = end + 1;
  }
  return true;
}

template <size_t N>
std::vector<std::string> OwnPolicy(
    const std::array<std::string_view, N>& values) {
  std::vector<std::string> result;
  result.reserve(values.size());
  for (std::string_view value : values) result.emplace_back(value);
  return result;
}

bool BuildExplicitConfig(JNIEnv* env, int32_t target_sdk, bool is_shared,
                         jstring dex_path, jstring library_path,
                         jstring permitted_path, jstring uses_library_list,
                         Config* config, std::string* error) {
  std::optional<std::string> dex;
  std::optional<std::string> search;
  std::optional<std::string> permitted;
  std::optional<std::string> uses;
  if (!ReadJString(env, dex_path, &dex, error) ||
      !ReadJString(env, library_path, &search, error) ||
      !ReadJString(env, permitted_path, &permitted, error) ||
      !ReadJString(env, uses_library_list, &uses, error)) {
    return false;
  }
  if (is_shared) {
    *error = "shared ClassLoader namespaces are not implemented by the OH backend";
    return false;
  }

  config->target_sdk = target_sdk;
  config->is_shared = false;
  config->origin = Config::Origin::kExplicitCreate;
  config->dex_path = std::move(dex);
  config->uses_library_list = std::move(uses);
  if (!SplitColonStrict(search, "librarySearchPath", &config->app_search_paths,
                        error) ||
      !SplitColonStrict(permitted, "libraryPermittedPath",
                        &config->app_permitted_paths, error)) {
    return false;
  }
  if (config->app_search_paths.empty() || config->app_permitted_paths.empty()) {
    *error = "app ClassLoader namespace requires non-empty search and permitted paths";
    return false;
  }
  config->bridge_search_paths = OwnPolicy(policy::kBridgeSearchPaths);
  config->bridge_permitted_paths = OwnPolicy(policy::kBridgePermittedPaths);
  config->bridge_shared_sonames = OwnPolicy(policy::kBridgeSharedSonames);
  config->bridge_bootstrap_soname =
      std::string(policy::kBridgeBootstrapSoname);
  return true;
}

bool BuildImplicitConfig(JNIEnv* env, int32_t target_sdk, jstring library_path,
                         Config* config, std::string* error) {
  std::optional<std::string> search;
  if (!ReadJString(env, library_path, &search, error) ||
      !SplitColonStrict(search, "libraryPath", &config->app_search_paths,
                        error)) {
    return false;
  }
  if (config->app_search_paths.empty()) return false;
  config->target_sdk = target_sdk;
  config->is_shared = false;
  config->origin = Config::Origin::kImplicitCustomLoader;
  config->app_permitted_paths = config->app_search_paths;
  config->bridge_search_paths = OwnPolicy(policy::kBridgeSearchPaths);
  config->bridge_permitted_paths = OwnPolicy(policy::kBridgePermittedPaths);
  config->bridge_shared_sonames = OwnPolicy(policy::kBridgeSharedSonames);
  config->bridge_bootstrap_soname =
      std::string(policy::kBridgeBootstrapSoname);
  return true;
}

jstring ErrorString(JNIEnv* env, const std::string& error) {
  return env->NewStringUTF(error.empty() ? "NativeLoader operation failed"
                                         : error.c_str());
}

}  // namespace
}  // namespace westlake::nativeloader

namespace android {
extern "C" {

void InitializeNativeLoader(void) {
  westlake::nativeloader::GlobalRegistry().Initialize(nullptr);
}

jstring CreateClassLoaderNamespace(
    JNIEnv* env, int32_t target_sdk_version, jobject class_loader,
    bool is_shared, jstring dex_path, jstring library_path,
    jstring permitted_path, jstring uses_library_list) {
  using namespace westlake::nativeloader;
  if (env == nullptr || class_loader == nullptr) {
    return env == nullptr ? nullptr
                          : ErrorString(env, "ClassLoader must not be null");
  }
  Config config;
  std::string error;
  if (!BuildExplicitConfig(env, target_sdk_version, is_shared, dex_path,
                           library_path, permitted_path, uses_library_list,
                           &config, &error)) {
    return ErrorString(env, error);
  }
  Status status = GlobalRegistry().GetOrCreate(env, class_loader, config, &error);
  return status == Status::kOk ? nullptr : ErrorString(env, error);
}

void* OpenNativeLibrary(JNIEnv* env, int32_t target_sdk_version,
                        const char* path, jobject class_loader,
                        const char* caller_location, jstring library_path,
                        bool* needs_native_bridge, char** error_msg) {
  using namespace westlake::nativeloader;
  (void)caller_location;
  if (needs_native_bridge != nullptr) *needs_native_bridge = false;
  if (error_msg != nullptr) *error_msg = nullptr;

  if (class_loader == nullptr) {
    return GlobalSystemLoader().Open(path, caller_location,
                                     library_path != nullptr, error_msg);
  }

  Config implicit_config;
  std::string config_error;
  const Config* implicit = nullptr;
  if (env != nullptr && class_loader != nullptr && library_path != nullptr) {
    if (!BuildImplicitConfig(env, target_sdk_version, library_path,
                             &implicit_config, &config_error)) {
      if (!config_error.empty() && error_msg != nullptr) {
        *error_msg = CopyError(config_error);
      }
      if (!config_error.empty()) return nullptr;
    } else {
      implicit = &implicit_config;
    }
  }
  return GlobalRegistry().Open(env, class_loader, implicit, path, RTLD_NOW,
                               error_msg);
}

bool CloseNativeLibrary(void* handle, bool needs_native_bridge,
                        char** error_msg) {
  using namespace westlake::nativeloader;
  (void)needs_native_bridge;
  if (GlobalRegistry().Owns(handle)) {
    return GlobalRegistry().Close(handle, error_msg) == Status::kOk;
  }
  if (GlobalSystemLoader().Owns(handle)) {
    return GlobalSystemLoader().Close(handle, error_msg);
  }
  if (error_msg != nullptr) {
    *error_msg = CopyError("NativeLoader handle has no registered owner");
  }
  return false;
}

void NativeLoaderFreeErrorMessage(char* msg) { std::free(msg); }

void ResetNativeLoader(void) {
  westlake::nativeloader::GlobalRegistry().Reset();
}

int WLNL_InstallSealedOpenV1(WestlakeSealedOpenFnV1 open_fn) {
  return westlake::nativeloader::InstallSealedOpen(open_fn);
}

}  // extern "C"
}  // namespace android
