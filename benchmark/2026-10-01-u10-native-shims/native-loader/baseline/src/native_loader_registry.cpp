#include "native_loader_registry.h"

#include <cstdlib>
#include <cstring>
#include <utility>

namespace westlake::nativeloader {
namespace {

thread_local uint32_t g_backend_depth = 0;

class BackendDepthGuard {
 public:
  BackendDepthGuard() { ++g_backend_depth; }
  ~BackendDepthGuard() { --g_backend_depth; }
};

std::string Join(const std::vector<std::string>& values) {
  std::string result;
  for (size_t i = 0; i < values.size(); ++i) {
    if (i != 0) result.push_back(':');
    result.append(values[i]);
  }
  return result;
}

void SetError(std::string* output, const char* message) {
  if (output != nullptr) *output = message;
}

}  // namespace

bool Config::operator==(const Config& other) const {
  return target_sdk == other.target_sdk && is_shared == other.is_shared &&
         origin == other.origin && dex_path == other.dex_path &&
         uses_library_list == other.uses_library_list &&
         app_search_paths == other.app_search_paths &&
         app_permitted_paths == other.app_permitted_paths &&
         bridge_search_paths == other.bridge_search_paths &&
         bridge_permitted_paths == other.bridge_permitted_paths &&
         bridge_shared_sonames == other.bridge_shared_sonames &&
         bridge_bootstrap_soname == other.bridge_bootstrap_soname;
}

void DomainDeleter::operator()(AnlDomain* domain) const {
  if (domain == nullptr) return;
  BackendDepthGuard backend_depth;
  ANL_ReleaseDomainHandle(domain);
}

char* CopyError(const std::string& message) {
  char* copy = static_cast<char*>(std::malloc(message.size() + 1));
  if (copy == nullptr) return nullptr;
  std::memcpy(copy, message.data(), message.size());
  copy[message.size()] = '\0';
  return copy;
}

Registry& GlobalRegistry() {
  static Registry* registry = new Registry();
  return *registry;
}

Status Registry::BindVmLocked(JavaVM* vm, std::string* error) {
  if (vm == nullptr) return Status::kOk;
  if (vm_ == nullptr) {
    vm_ = vm;
    return Status::kOk;
  }
  if (vm_ != vm) {
    SetError(error, "NativeLoader observed a different JavaVM");
    return Status::kWrongVm;
  }
  return Status::kOk;
}

Status Registry::Initialize(JavaVM* vm, std::string* error) {
  if (error != nullptr) error->clear();
  std::lock_guard<std::mutex> lock(mutex_);
  if (state_ == RegistryState::kResetting) {
    SetError(error, "NativeLoader reset is in progress");
    return Status::kResetting;
  }
  Status vm_status = BindVmLocked(vm, error);
  if (vm_status != Status::kOk) return vm_status;
  if (state_ == RegistryState::kUninitialized) {
    state_ = RegistryState::kRunning;
    ++epoch_;
  }
  return Status::kOk;
}

std::shared_ptr<Registry::Entry> Registry::FindSameLocked(
    JNIEnv* env, jobject class_loader) {
  for (const auto& entry : entries_) {
    if (entry->epoch != epoch_ || entry->state == EntryState::kRetired ||
        entry->loader_weak == nullptr) {
      continue;
    }
    if (env->IsSameObject(entry->loader_weak, class_loader) == JNI_TRUE) {
      return entry;
    }
  }
  return nullptr;
}

void Registry::SweepCollectedLocked(JNIEnv* env, jobject pinned_loader) {
  for (const auto& entry : entries_) {
    if (entry->loader_weak == nullptr || entry->state == EntryState::kRetired) {
      continue;
    }
    if (pinned_loader != nullptr &&
        env->IsSameObject(entry->loader_weak, pinned_loader) == JNI_TRUE) {
      continue;
    }

    jobject local = env->NewLocalRef(entry->loader_weak);
    if (local != nullptr) {
      env->DeleteLocalRef(local);
      continue;
    }
    if (env->ExceptionCheck() == JNI_TRUE) {
      continue;
    }

    env->DeleteWeakGlobalRef(entry->loader_weak);
    entry->loader_weak = nullptr;
    if (entry->state != EntryState::kCreating) {
      entry->state = EntryState::kRetired;
    }
  }
}

Status Registry::GetOrCreate(JNIEnv* env, jobject class_loader,
                             const Config& config, std::string* error) {
  if (error != nullptr) error->clear();
  if (env == nullptr || class_loader == nullptr) {
    SetError(error, "ClassLoader namespace requires non-null JNI arguments");
    return Status::kInvalidArgument;
  }
  if (config.app_search_paths.empty() || config.app_permitted_paths.empty()) {
    SetError(error, "ClassLoader namespace requires app search and permitted paths");
    return Status::kInvalidArgument;
  }
  if (g_backend_depth != 0) {
    SetError(error, "reentrant namespace creation from a loader backend is forbidden");
    return Status::kSelfReentry;
  }

  JavaVM* observed_vm = nullptr;
  if (env->GetJavaVM(&observed_vm) != JNI_OK || observed_vm == nullptr) {
    SetError(error, "GetJavaVM failed");
    return Status::kJniFailure;
  }

  std::unique_lock<std::mutex> lock(mutex_);
  if (state_ != RegistryState::kRunning) {
    SetError(error, state_ == RegistryState::kResetting
                        ? "NativeLoader reset is in progress"
                        : "NativeLoader is not initialized");
    return state_ == RegistryState::kResetting ? Status::kResetting
                                                : Status::kNotRunning;
  }
  Status vm_status = BindVmLocked(observed_vm, error);
  if (vm_status != Status::kOk) return vm_status;

  SweepCollectedLocked(env, class_loader);
  for (;;) {
    std::shared_ptr<Entry> existing = FindSameLocked(env, class_loader);
    if (existing == nullptr) break;
    if (existing->state == EntryState::kCreating) {
      const uint64_t wait_epoch = epoch_;
      changed_.wait(lock, [&] {
        return state_ != RegistryState::kRunning || epoch_ != wait_epoch ||
               existing->state != EntryState::kCreating;
      });
      if (state_ != RegistryState::kRunning || epoch_ != wait_epoch) {
        SetError(error, "NativeLoader reset interrupted namespace creation");
        return Status::kResetting;
      }
      continue;
    }
    if (existing->state == EntryState::kReady) {
      if (existing->config == config) return Status::kOk;
      SetError(error, "ClassLoader namespace configuration mismatch");
      return Status::kConfigMismatch;
    }
    if (existing->state == EntryState::kFailed) {
      if (existing->config == config) {
        if (error != nullptr) *error = existing->create_error;
        return Status::kBackendError;
      }
      SetError(error, "failed ClassLoader namespace has a different configuration");
      return Status::kConfigMismatch;
    }
  }

  jweak weak = env->NewWeakGlobalRef(class_loader);
  if (weak == nullptr) {
    SetError(error, env->ExceptionCheck() == JNI_TRUE
                        ? "NewWeakGlobalRef failed with a pending JNI exception"
                        : "NewWeakGlobalRef returned null");
    return Status::kJniFailure;
  }

  auto entry = std::make_shared<Entry>();
  entry->id = next_id_++;
  entry->epoch = epoch_;
  entry->loader_weak = weak;
  entry->config = config;
  entry->state = EntryState::kCreating;
  entry->active_calls = 1;
  entries_.push_back(entry);
  const uint64_t create_epoch = epoch_;
  ++backend_calls_;

  const std::string app_search = Join(config.app_search_paths);
  const std::string app_permitted = Join(config.app_permitted_paths);
  const std::string bridge_search = Join(config.bridge_search_paths);
  const std::string bridge_permitted = Join(config.bridge_permitted_paths);
  const std::string bridge_sonames = Join(config.bridge_shared_sonames);
  const bool has_bridge = !config.bridge_shared_sonames.empty();

  AnlDomainConfig backend_config = {};
  backend_config.app_search_paths = app_search.c_str();
  backend_config.app_permitted_paths = app_permitted.c_str();
  backend_config.bridge_search_paths = has_bridge ? bridge_search.c_str() : nullptr;
  backend_config.bridge_permitted_paths =
      has_bridge ? bridge_permitted.c_str() : nullptr;
  backend_config.bridge_shared_sonames =
      has_bridge ? bridge_sonames.c_str() : nullptr;
  backend_config.bridge_bootstrap_soname = has_bridge ?
      config.bridge_bootstrap_soname.c_str() : nullptr;

  lock.unlock();
  AnlDomain* raw_domain = nullptr;
  int backend_result = 0;
  {
    BackendDepthGuard backend_depth;
    backend_result = ANL_CreateDomain(&backend_config, &raw_domain);
  }
  std::string backend_error;
  if (backend_result != 0 || raw_domain == nullptr) {
    const char* borrowed = ANL_Dlerror();
    backend_error = borrowed != nullptr ? borrowed :
        (raw_domain == nullptr ? "ANL_CreateDomain returned a null domain"
                               : "ANL_CreateDomain failed");
    backend_result = -1;
  }

  DomainPtr release_after_unlock;
  lock.lock();
  entry->active_calls = 0;
  const bool stale = state_ != RegistryState::kRunning ||
                     epoch_ != create_epoch || entry->loader_weak == nullptr ||
                     env->IsSameObject(entry->loader_weak, class_loader) != JNI_TRUE;

  Status result = Status::kOk;
  if (backend_result != 0) {
    if (stale) {
      entry->state = EntryState::kRetired;
    } else {
      entry->state = EntryState::kFailed;
      entry->create_error = backend_error;
    }
    release_after_unlock.reset(raw_domain);
    if (error != nullptr) *error = backend_error;
    result = stale ? Status::kResetting : Status::kBackendError;
  } else if (stale) {
    entry->state = EntryState::kRetired;
    entry->domain.reset(raw_domain);
    SetError(error, "ClassLoader was collected or reset won the create race");
    result = Status::kResetting;
  } else {
    entry->domain.reset(raw_domain);
    entry->state = EntryState::kReady;
  }
  changed_.notify_all();
  lock.unlock();
  release_after_unlock.reset();
  {
    std::lock_guard<std::mutex> completed_lock(mutex_);
    if (backend_calls_ > 0) --backend_calls_;
    changed_.notify_all();
  }
  return result;
}

void* Registry::Open(JNIEnv* env, jobject class_loader,
                     const Config* implicit_config, const char* path, int flags,
                     char** error_msg) {
  if (error_msg != nullptr) *error_msg = nullptr;
  if (env == nullptr || class_loader == nullptr || path == nullptr || path[0] == '\0') {
    if (error_msg != nullptr) {
      *error_msg = CopyError(class_loader == nullptr
          ? "null ClassLoader is reserved for the owned system-loader path"
          : "invalid NativeLoader open arguments");
    }
    return nullptr;
  }

  JavaVM* observed_vm = nullptr;
  if (env->GetJavaVM(&observed_vm) != JNI_OK || observed_vm == nullptr) {
    if (error_msg != nullptr) *error_msg = CopyError("GetJavaVM failed during open");
    return nullptr;
  }

  bool attempted_implicit_create = false;
  std::shared_ptr<Entry> entry;
  AnlDomain* domain = nullptr;
  for (;;) {
    std::unique_lock<std::mutex> lock(mutex_);
    if (state_ != RegistryState::kRunning) {
      lock.unlock();
      if (error_msg != nullptr) {
        *error_msg = CopyError("NativeLoader is not running during open");
      }
      return nullptr;
    }
    std::string vm_error;
    if (BindVmLocked(observed_vm, &vm_error) != Status::kOk) {
      lock.unlock();
      if (error_msg != nullptr) *error_msg = CopyError(vm_error);
      return nullptr;
    }
    SweepCollectedLocked(env, class_loader);
    entry = FindSameLocked(env, class_loader);
    if (entry == nullptr) {
      lock.unlock();
      if (implicit_config == nullptr || attempted_implicit_create) {
        if (error_msg != nullptr) {
          *error_msg = CopyError("no native dependency domain for ClassLoader");
        }
        return nullptr;
      }
      attempted_implicit_create = true;
      std::string create_error;
      if (GetOrCreate(env, class_loader, *implicit_config, &create_error) !=
          Status::kOk) {
        if (error_msg != nullptr) *error_msg = CopyError(create_error);
        return nullptr;
      }
      continue;
    }
    if (entry->state == EntryState::kCreating) {
      const uint64_t wait_epoch = epoch_;
      changed_.wait(lock, [&] {
        return state_ != RegistryState::kRunning || epoch_ != wait_epoch ||
               entry->state != EntryState::kCreating;
      });
      continue;
    }
    if (entry->state == EntryState::kFailed) {
      std::string create_error = entry->create_error;
      lock.unlock();
      if (error_msg != nullptr) *error_msg = CopyError(create_error);
      return nullptr;
    }
    if (entry->state != EntryState::kReady || entry->domain == nullptr) {
      lock.unlock();
      if (error_msg != nullptr) *error_msg = CopyError("native dependency domain is not ready");
      return nullptr;
    }
    domain = entry->domain.get();
    ++entry->active_calls;
    ++backend_calls_;
    break;
  }

  void* handle = nullptr;
  {
    BackendDepthGuard backend_depth;
    handle = ANL_Dlopen(domain, path, flags);
  }
  std::string backend_error;
  if (handle == nullptr) {
    const char* borrowed = ANL_Dlerror();
    backend_error = borrowed != nullptr ? borrowed : "ANL_Dlopen failed";
  }

  {
    std::lock_guard<std::mutex> lock(mutex_);
    if (entry->active_calls > 0) --entry->active_calls;
    if (backend_calls_ > 0) --backend_calls_;
    if (handle != nullptr) ++handles_[handle].open_refs;
    changed_.notify_all();
  }
  if (handle == nullptr && error_msg != nullptr) {
    *error_msg = CopyError(backend_error);
  }
  return handle;
}

Status Registry::Close(void* handle, char** error_msg) {
  if (error_msg != nullptr) *error_msg = nullptr;
  bool unknown_handle = false;
  {
    std::lock_guard<std::mutex> lock(mutex_);
    auto slot = handles_.find(handle);
    if (handle == nullptr || slot == handles_.end() ||
        slot->second.open_refs <= slot->second.close_in_flight) {
      unknown_handle = true;
    } else {
      ++slot->second.close_in_flight;
      ++backend_calls_;
    }
  }
  if (unknown_handle) {
    if (error_msg != nullptr) {
      *error_msg = CopyError("unknown or already-closed NativeLoader handle");
    }
    return Status::kUnknownHandle;
  }

  int backend_result = 0;
  {
    BackendDepthGuard backend_depth;
    backend_result = ANL_Dlclose(handle);
  }
  std::string backend_error;
  if (backend_result != 0) {
    const char* borrowed = ANL_Dlerror();
    backend_error = borrowed != nullptr ? borrowed : "ANL_Dlclose failed";
  }

  {
    std::lock_guard<std::mutex> lock(mutex_);
    auto slot = handles_.find(handle);
    if (slot != handles_.end()) {
      if (backend_result == 0 && slot->second.open_refs > 0) {
        --slot->second.open_refs;
      }
      if (slot->second.close_in_flight > 0) --slot->second.close_in_flight;
      if (slot->second.open_refs == 0 && slot->second.close_in_flight == 0) {
        handles_.erase(slot);
      }
    }
    if (backend_calls_ > 0) --backend_calls_;
    changed_.notify_all();
  }
  if (backend_result != 0) {
    if (error_msg != nullptr) *error_msg = CopyError(backend_error);
    return Status::kBackendError;
  }
  return Status::kOk;
}

bool Registry::Owns(void* handle) {
  std::lock_guard<std::mutex> lock(mutex_);
  auto slot = handles_.find(handle);
  return slot != handles_.end() &&
         slot->second.open_refs > slot->second.close_in_flight;
}

Status Registry::Reset(std::string* error) {
  if (error != nullptr) error->clear();
  if (g_backend_depth != 0) {
    SetError(error, "reentrant NativeLoader reset from a loader backend is forbidden");
    return Status::kSelfReentry;
  }

  {
    std::unique_lock<std::mutex> lock(mutex_);
    if (state_ == RegistryState::kUninitialized) return Status::kOk;
    if (state_ == RegistryState::kRunning) {
      state_ = RegistryState::kResetting;
      ++epoch_;
      changed_.notify_all();
    }
    changed_.wait(lock, [&] { return !reset_teardown_active_; });
    if (state_ == RegistryState::kUninitialized) return Status::kOk;
    reset_teardown_active_ = true;
    changed_.wait(lock, [&] { return backend_calls_ == 0; });
    for (const auto& item : handles_) {
      if (item.second.open_refs != 0) {
        reset_teardown_active_ = false;
        changed_.notify_all();
        SetError(error, "NativeLoader reset refused while handles remain open");
        return Status::kBackendError;
      }
    }
  }

  std::vector<DomainPtr> domains;
  {
    std::lock_guard<std::mutex> lock(mutex_);
    for (const auto& entry : entries_) {
      // ART calls ResetNativeLoader only after destroying JavaVM. At that
      // point jweak values are invalid tokens owned by the dead VM and must
      // only be forgotten, never passed back through JNI.
      entry->loader_weak = nullptr;
      if (entry->domain != nullptr) domains.push_back(std::move(entry->domain));
    }
    entries_.clear();
    handles_.clear();
  }

  domains.clear();
  {
    std::lock_guard<std::mutex> lock(mutex_);
    vm_ = nullptr;
    state_ = RegistryState::kUninitialized;
    reset_teardown_active_ = false;
    changed_.notify_all();
  }
  return Status::kOk;
}

size_t Registry::LiveEntryCountForTests() {
  std::lock_guard<std::mutex> lock(mutex_);
  size_t count = 0;
  for (const auto& entry : entries_) {
    if (entry->state != EntryState::kRetired) ++count;
  }
  return count;
}

uint64_t Registry::EpochForTests() {
  std::lock_guard<std::mutex> lock(mutex_);
  return epoch_;
}

}  // namespace westlake::nativeloader
