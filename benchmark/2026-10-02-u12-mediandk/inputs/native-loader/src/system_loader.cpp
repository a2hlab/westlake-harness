#include "system_loader.h"

#include <nativeloader/native_bridge_policy.h>

#include "native_loader_registry.h"

#include <dlfcn.h>
#include <limits.h>
#include <stdlib.h>

#include <atomic>
#include <string_view>

namespace westlake::nativeloader {
namespace {

std::atomic<SealedOpenFn> g_sealed_open{nullptr};

class RealSystemLoaderOps final : public SystemLoaderOps {
 public:
  bool ResolvePath(const char* path, std::string* resolved,
                   std::string* error) const override {
    char buffer[PATH_MAX];
    if (realpath(path, buffer) == nullptr) {
      *error = std::string("NativeLoader realpath failed: ") + path;
      return false;
    }
    *resolved = buffer;
    return true;
  }

  void* OpenExact(const char* path, int flags) const override {
    dlerror();
    SealedOpenFn open_fn = g_sealed_open.load(std::memory_order_acquire);
    return open_fn == nullptr ? nullptr : open_fn(path, flags);
  }

  int CloseExact(void* handle) const override {
    dlerror();
    return dlclose(handle);
  }

  const char* LastError() const override { return dlerror(); }
};

RealSystemLoaderOps g_real_ops;

bool StartsWith(std::string_view value, std::string_view prefix) {
  return value.size() >= prefix.size() && value.substr(0, prefix.size()) == prefix;
}

bool IsCanonicalAbsolutePath(std::string_view path) {
  if (path.size() < 2 || path.front() != '/' || path.back() == '/') return false;
  size_t begin = 1;
  while (begin < path.size()) {
    size_t end = path.find('/', begin);
    if (end == std::string_view::npos) end = path.size();
    std::string_view component = path.substr(begin, end - begin);
    if (component.empty() || component == "." || component == "..") return false;
    begin = end + 1;
  }
  return true;
}

bool IsWithinTrustedRoot(std::string_view path) {
  for (std::string_view root : policy::kSystemCallerRoots) {
    if (StartsWith(path, root) ||
        (root.back() == '/' && path == root.substr(0, root.size() - 1))) {
      return true;
    }
  }
  return false;
}

bool TrustedCaller(const SystemLoaderOps* ops, const char* caller_location,
                   std::string* error) {
  if (caller_location == nullptr) return true;
  std::string_view caller(caller_location);
  const size_t archive_separator = caller.find('!');
  if (archive_separator != std::string_view::npos &&
      caller.find('!', archive_separator + 1) != std::string_view::npos) {
    *error = "system NativeLoader caller has multiple archive separators";
    return false;
  }
  if (archive_separator != std::string_view::npos &&
      archive_separator + 1 == caller.size()) {
    *error = "system NativeLoader caller has an empty archive suffix";
    return false;
  }
  std::string_view filesystem_path = caller.substr(0, archive_separator);
  if (!IsCanonicalAbsolutePath(filesystem_path)) {
    *error = "system NativeLoader caller path is not canonical";
    return false;
  }

  std::string resolved;
  std::string filesystem_path_owned(filesystem_path);
  if (!ops->ResolvePath(filesystem_path_owned.c_str(), &resolved, error)) {
    return false;
  }
  if (!IsCanonicalAbsolutePath(resolved) || !IsWithinTrustedRoot(resolved)) {
    *error = "system NativeLoader caller resolved outside trusted roots";
    return false;
  }
  return true;
}

const policy::SystemLibrary* FindSystemLibrary(const char* path) {
  if (path == nullptr || path[0] == '\0') return nullptr;
  std::string_view requested(path);
  const bool absolute = requested.front() == '/';
  if (!absolute && requested.find('/') != std::string_view::npos) return nullptr;
  for (const auto& library : policy::kSystemLibraries) {
    if ((!absolute && requested == library.soname) ||
        (absolute && requested == library.path)) {
      return &library;
    }
  }
  return nullptr;
}

}  // namespace

int InstallSealedOpen(SealedOpenFn open_fn) {
  if (open_fn == nullptr) return -1;
  SealedOpenFn expected = nullptr;
  return g_sealed_open.compare_exchange_strong(
             expected, open_fn, std::memory_order_release,
             std::memory_order_relaxed)
      ? 0
      : -1;
}

SystemLoader& GlobalSystemLoader() {
  static SystemLoader* loader = new SystemLoader(&g_real_ops);
  return *loader;
}

void* SystemLoader::Open(const char* path, const char* caller_location,
                         bool library_path_was_supplied, char** error_msg) {
  if (error_msg != nullptr) *error_msg = nullptr;
  if (library_path_was_supplied) {
    if (error_msg != nullptr) {
      *error_msg = CopyError("system NativeLoader route rejects library_path");
    }
    return nullptr;
  }
  std::string caller_error;
  if (!TrustedCaller(ops_, caller_location, &caller_error)) {
    if (error_msg != nullptr) {
      *error_msg = CopyError(caller_error.empty()
          ? "system NativeLoader route rejected caller_location" : caller_error);
    }
    return nullptr;
  }
  const policy::SystemLibrary* library = FindSystemLibrary(path);
  if (library == nullptr) {
    if (error_msg != nullptr) {
      *error_msg = CopyError("system library is absent from the adapter manifest");
    }
    return nullptr;
  }

  std::string resolved;
  std::string resolve_error;
  if (!ops_->ResolvePath(library->path.data(), &resolved, &resolve_error) ||
      std::string_view(resolved) != library->path) {
    if (error_msg != nullptr) {
      *error_msg = CopyError(resolve_error.empty()
          ? "system library realpath does not match the adapter manifest"
          : resolve_error);
    }
    return nullptr;
  }

  void* handle = ops_->OpenExact(resolved.c_str(), RTLD_NOW | RTLD_LOCAL);
  std::string open_error;
  if (handle == nullptr) {
    const char* borrowed = ops_->LastError();
    open_error = borrowed == nullptr ? "system library open failed" : borrowed;
  }
  if (handle == nullptr) {
    if (error_msg != nullptr) *error_msg = CopyError(open_error);
    return nullptr;
  }
  {
    std::lock_guard<std::mutex> lock(mutex_);
    ++handles_[handle].open_refs;
  }
  return handle;
}

bool SystemLoader::Owns(void* handle) {
  std::lock_guard<std::mutex> lock(mutex_);
  auto slot = handles_.find(handle);
  return slot != handles_.end() &&
         slot->second.open_refs > slot->second.close_in_flight;
}

bool SystemLoader::Close(void* handle, char** error_msg) {
  if (error_msg != nullptr) *error_msg = nullptr;
  bool reserved = false;
  {
    std::lock_guard<std::mutex> lock(mutex_);
    auto slot = handles_.find(handle);
    if (handle != nullptr && slot != handles_.end() &&
        slot->second.open_refs > slot->second.close_in_flight) {
      ++slot->second.close_in_flight;
      reserved = true;
    }
  }
  if (!reserved) {
    if (error_msg != nullptr) {
      *error_msg = CopyError("unknown or already-closed system NativeLoader handle");
    }
    return false;
  }

  int result = ops_->CloseExact(handle);
  std::string close_error;
  if (result != 0) {
    const char* borrowed = ops_->LastError();
    close_error = borrowed == nullptr ? "system library close failed" : borrowed;
  }
  {
    std::lock_guard<std::mutex> lock(mutex_);
    auto slot = handles_.find(handle);
    if (slot != handles_.end()) {
      if (result == 0 && slot->second.open_refs > 0) --slot->second.open_refs;
      if (slot->second.close_in_flight > 0) --slot->second.close_in_flight;
      if (slot->second.open_refs == 0 && slot->second.close_in_flight == 0) {
        handles_.erase(slot);
      }
    }
  }
  if (result != 0) {
    if (error_msg != nullptr) *error_msg = CopyError(close_error);
    return false;
  }
  return true;
}

}  // namespace westlake::nativeloader
