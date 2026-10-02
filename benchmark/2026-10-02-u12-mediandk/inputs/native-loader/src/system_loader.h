#ifndef WESTLAKE_NATIVE_LOADER_OH_SYSTEM_LOADER_H_
#define WESTLAKE_NATIVE_LOADER_OH_SYSTEM_LOADER_H_

#include <cstdint>
#include <mutex>
#include <string>
#include <unordered_map>

namespace westlake::nativeloader {

using SealedOpenFn = void* (*)(const char* absolute_path, int flags);

int InstallSealedOpen(SealedOpenFn open_fn);

class SystemLoaderOps {
 public:
  virtual ~SystemLoaderOps() = default;
  virtual bool ResolvePath(const char* path, std::string* resolved,
                           std::string* error) const = 0;
  virtual void* OpenExact(const char* path, int flags) const = 0;
  virtual int CloseExact(void* handle) const = 0;
  virtual const char* LastError() const = 0;
};

class SystemLoader {
 public:
  explicit SystemLoader(const SystemLoaderOps* ops) : ops_(ops) {}

  void* Open(const char* path, const char* caller_location,
             bool library_path_was_supplied, char** error_msg);
  bool Owns(void* handle);
  bool Close(void* handle, char** error_msg);

 private:
  struct HandleSlot {
    uint64_t open_refs = 0;
    uint64_t close_in_flight = 0;
  };

  const SystemLoaderOps* ops_;
  std::mutex mutex_;
  std::unordered_map<void*, HandleSlot> handles_;
};

SystemLoader& GlobalSystemLoader();

}  // namespace westlake::nativeloader

#endif  // WESTLAKE_NATIVE_LOADER_OH_SYSTEM_LOADER_H_
