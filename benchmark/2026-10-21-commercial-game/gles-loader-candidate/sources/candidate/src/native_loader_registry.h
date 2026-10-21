#ifndef WESTLAKE_NATIVE_LOADER_OH_NATIVE_LOADER_REGISTRY_H_
#define WESTLAKE_NATIVE_LOADER_OH_NATIVE_LOADER_REGISTRY_H_

#include <jni.h>

#include <condition_variable>
#include <cstdint>
#include <list>
#include <memory>
#include <mutex>
#include <optional>
#include <string>
#include <unordered_map>
#include <vector>

#include "app_native_loader.h"

namespace westlake::nativeloader {

enum class Status {
  kOk = 0,
  kInvalidArgument,
  kConfigMismatch,
  kResetting,
  kJniFailure,
  kWrongVm,
  kBackendError,
  kUnknownHandle,
  kNoDomain,
  kNotRunning,
  kSelfReentry,
};

struct Config {
  enum class Origin { kExplicitCreate, kImplicitCustomLoader };

  int32_t target_sdk = 0;
  bool is_shared = false;
  Origin origin = Origin::kExplicitCreate;
  std::optional<std::string> dex_path;
  std::optional<std::string> uses_library_list;
  std::vector<std::string> app_search_paths;
  std::vector<std::string> app_permitted_paths;
  std::vector<std::string> bridge_search_paths;
  std::vector<std::string> bridge_permitted_paths;
  std::vector<std::string> bridge_shared_sonames;
  std::string bridge_bootstrap_soname;

  bool operator==(const Config& other) const;
  bool operator!=(const Config& other) const { return !(*this == other); }
};

struct DomainDeleter {
  void operator()(AnlDomain* domain) const;
};
using DomainPtr = std::unique_ptr<AnlDomain, DomainDeleter>;

class Registry {
 public:
  Status Initialize(JavaVM* vm, std::string* error = nullptr);

  Status GetOrCreate(JNIEnv* env, jobject class_loader, const Config& config,
                     std::string* error);

  void* Open(JNIEnv* env, jobject class_loader, const Config* implicit_config,
             const char* path, int flags, char** error_msg);

  Status Close(void* handle, char** error_msg);
  bool Owns(void* handle);

  Status Reset(std::string* error = nullptr);

  size_t LiveEntryCountForTests();
  uint64_t EpochForTests();

 private:
  enum class EntryState { kCreating, kReady, kFailed, kRetired };
  enum class RegistryState { kUninitialized, kRunning, kResetting };

  struct Entry {
    uint64_t id = 0;
    uint64_t epoch = 0;
    jweak loader_weak = nullptr;
    Config config;
    EntryState state = EntryState::kCreating;
    DomainPtr domain;
    std::string create_error;
    uint32_t active_calls = 0;
  };

  struct HandleSlot {
    uint64_t open_refs = 0;
    uint64_t close_in_flight = 0;
  };

  std::shared_ptr<Entry> FindSameLocked(JNIEnv* env, jobject class_loader);
  void SweepCollectedLocked(JNIEnv* env, jobject pinned_loader);
  Status BindVmLocked(JavaVM* vm, std::string* error);

  std::mutex mutex_;
  std::condition_variable changed_;
  RegistryState state_ = RegistryState::kUninitialized;
  JavaVM* vm_ = nullptr;
  uint64_t epoch_ = 0;
  uint64_t next_id_ = 1;
  uint32_t backend_calls_ = 0;
  bool reset_teardown_active_ = false;
  std::list<std::shared_ptr<Entry>> entries_;
  std::unordered_map<void*, HandleSlot> handles_;
};

Registry& GlobalRegistry();
char* CopyError(const std::string& message);

}  // namespace westlake::nativeloader

#endif  // WESTLAKE_NATIVE_LOADER_OH_NATIVE_LOADER_REGISTRY_H_
