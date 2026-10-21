#include <nativeloader/native_loader.h>

#include "native_loader_registry.h"
#include "system_loader.h"

#include <algorithm>
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <dlfcn.h>
#include <functional>
#include <memory>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

using westlake::nativeloader::Config;
using westlake::nativeloader::Registry;
using westlake::nativeloader::Status;
using westlake::nativeloader::SystemLoader;
using westlake::nativeloader::SystemLoaderOps;

namespace fakejni {
namespace {

enum class RefKind { kLocal, kWeak, kString };

struct Object {
  uint64_t id = 0;
  bool collected = false;
  std::string text;
};

struct Ref {
  Object* object = nullptr;
  RefKind kind = RefKind::kLocal;
  bool live = true;
};

std::mutex g_mutex;
std::vector<std::unique_ptr<Object>> g_objects;
std::vector<std::unique_ptr<Ref>> g_refs;
uint64_t g_next_object = 1;
size_t g_deleted_weaks = 0;
bool g_pending_exception = false;
bool g_vm_alive = true;
size_t g_vm_api_calls = 0;

JNINativeInterface g_jni = {};
JNIInvokeInterface g_vm_functions = {};
JavaVM g_vm = {&g_vm_functions};
std::once_flag g_tables_once;
thread_local JNIEnv g_env = {&g_jni};

Ref* AsRef(jobject value) { return reinterpret_cast<Ref*>(value); }

Object* Resolve(jobject value) {
  if (value == nullptr) return nullptr;
  Ref* ref = AsRef(value);
  if (!ref->live || ref->object == nullptr) return nullptr;
  if (ref->kind == RefKind::kWeak && ref->object->collected) return nullptr;
  return ref->object;
}

jobject NewRef(Object* object, RefKind kind) {
  auto ref = std::make_unique<Ref>();
  ref->object = object;
  ref->kind = kind;
  Ref* raw = ref.get();
  g_refs.push_back(std::move(ref));
  return reinterpret_cast<jobject>(raw);
}

jboolean IsSameObject(JNIEnv*, jobject lhs, jobject rhs) {
  std::lock_guard<std::mutex> lock(g_mutex);
  return Resolve(lhs) == Resolve(rhs) ? JNI_TRUE : JNI_FALSE;
}

jweak NewWeakGlobalRef(JNIEnv*, jobject value) {
  std::lock_guard<std::mutex> lock(g_mutex);
  Object* object = Resolve(value);
  return reinterpret_cast<jweak>(object == nullptr
      ? nullptr : NewRef(object, RefKind::kWeak));
}

void DeleteWeakGlobalRef(JNIEnv*, jweak value) {
  std::lock_guard<std::mutex> lock(g_mutex);
  if (value == nullptr) return;
  Ref* ref = AsRef(value);
  if (ref->live) {
    ref->live = false;
    ref->object = nullptr;
    ++g_deleted_weaks;
  }
}

jobject NewLocalRef(JNIEnv*, jobject value) {
  std::lock_guard<std::mutex> lock(g_mutex);
  Object* object = Resolve(value);
  return object == nullptr ? nullptr : NewRef(object, RefKind::kLocal);
}

void DeleteLocalRef(JNIEnv*, jobject value) {
  std::lock_guard<std::mutex> lock(g_mutex);
  if (value == nullptr) return;
  Ref* ref = AsRef(value);
  if (ref->live && ref->kind != RefKind::kWeak) {
    ref->live = false;
    ref->object = nullptr;
  }
}

jboolean ExceptionCheck(JNIEnv*) {
  std::lock_guard<std::mutex> lock(g_mutex);
  return g_pending_exception ? JNI_TRUE : JNI_FALSE;
}

jstring NewStringUTF(JNIEnv*, const char* text) {
  std::lock_guard<std::mutex> lock(g_mutex);
  auto object = std::make_unique<Object>();
  object->id = g_next_object++;
  object->text = text == nullptr ? "" : text;
  Object* raw = object.get();
  g_objects.push_back(std::move(object));
  return reinterpret_cast<jstring>(NewRef(raw, RefKind::kString));
}

const char* GetStringUTFChars(JNIEnv*, jstring value, jboolean* is_copy) {
  std::lock_guard<std::mutex> lock(g_mutex);
  if (is_copy != nullptr) *is_copy = JNI_FALSE;
  Object* object = Resolve(value);
  return object == nullptr ? nullptr : object->text.c_str();
}

void ReleaseStringUTFChars(JNIEnv*, jstring, const char*) {}

jint GetJavaVM(JNIEnv*, JavaVM** vm) {
  if (vm == nullptr) return JNI_ERR;
  *vm = &g_vm;
  return JNI_OK;
}

jint AttachCurrentThread(JavaVM*, JNIEnv** env, void*) {
  std::lock_guard<std::mutex> lock(g_mutex);
  ++g_vm_api_calls;
  if (!g_vm_alive) return JNI_ERR;
  if (env == nullptr) return JNI_ERR;
  *env = &g_env;
  return JNI_OK;
}

jint DetachCurrentThread(JavaVM*) {
  std::lock_guard<std::mutex> lock(g_mutex);
  ++g_vm_api_calls;
  return g_vm_alive ? JNI_OK : JNI_ERR;
}

jint GetEnv(JavaVM*, void** env, jint version) {
  std::lock_guard<std::mutex> lock(g_mutex);
  ++g_vm_api_calls;
  if (!g_vm_alive) return JNI_ERR;
  if (env == nullptr || version != JNI_VERSION_1_6) return JNI_ERR;
  *env = &g_env;
  return JNI_OK;
}

void InitTables() {
  g_jni.IsSameObject = IsSameObject;
  g_jni.NewWeakGlobalRef = NewWeakGlobalRef;
  g_jni.DeleteWeakGlobalRef = DeleteWeakGlobalRef;
  g_jni.NewLocalRef = NewLocalRef;
  g_jni.DeleteLocalRef = DeleteLocalRef;
  g_jni.ExceptionCheck = ExceptionCheck;
  g_jni.NewStringUTF = NewStringUTF;
  g_jni.GetStringUTFChars = GetStringUTFChars;
  g_jni.ReleaseStringUTFChars = ReleaseStringUTFChars;
  g_jni.GetJavaVM = GetJavaVM;
  g_vm_functions.AttachCurrentThread = AttachCurrentThread;
  g_vm_functions.DetachCurrentThread = DetachCurrentThread;
  g_vm_functions.GetEnv = GetEnv;
}

}  // namespace

JNIEnv* Env() {
  std::call_once(g_tables_once, InitTables);
  return &g_env;
}

jobject NewObject() {
  std::lock_guard<std::mutex> lock(g_mutex);
  auto object = std::make_unique<Object>();
  object->id = g_next_object++;
  Object* raw = object.get();
  g_objects.push_back(std::move(object));
  return NewRef(raw, RefKind::kLocal);
}

jobject Alias(jobject value) {
  std::lock_guard<std::mutex> lock(g_mutex);
  return NewRef(Resolve(value), RefKind::kLocal);
}

void Collect(jobject value) {
  std::lock_guard<std::mutex> lock(g_mutex);
  Object* object = Resolve(value);
  if (object != nullptr) object->collected = true;
}

size_t DeletedWeakCount() {
  std::lock_guard<std::mutex> lock(g_mutex);
  return g_deleted_weaks;
}

void MarkVmDead() {
  std::lock_guard<std::mutex> lock(g_mutex);
  g_vm_alive = false;
}

size_t VmApiCallCount() {
  std::lock_guard<std::mutex> lock(g_mutex);
  return g_vm_api_calls;
}

void ResetModel() {
  std::lock_guard<std::mutex> lock(g_mutex);
  g_refs.clear();
  g_objects.clear();
  g_next_object = 1;
  g_deleted_weaks = 0;
  g_pending_exception = false;
  g_vm_alive = true;
  g_vm_api_calls = 0;
}

}  // namespace fakejni

namespace fakeanl {
namespace {

struct FakeDomain { uint64_t id; };

std::mutex g_mutex;
std::condition_variable g_changed;
int g_create_calls = 0;
int g_open_calls = 0;
int g_close_calls = 0;
int g_live_domains = 0;
int g_active_creates = 0;
int g_max_active_creates = 0;
int g_fail_create = 0;
int g_fail_create_with_domain = 0;
int g_fail_open = 0;
int g_fail_close = 0;
bool g_block_create = false;
bool g_release_create = false;
bool g_block_release = false;
bool g_release_release = false;
int g_active_releases = 0;
bool g_same_handle = false;
bool g_open_hook_armed = false;
std::function<void()> g_open_hook;
std::vector<std::string> g_last_bridge_sonames;
thread_local std::string g_error;
std::atomic<uintptr_t> g_next_handle{0x10000};

std::vector<std::string> Split(const char* value) {
  std::vector<std::string> result;
  if (value == nullptr || value[0] == '\0') return result;
  std::string input(value);
  size_t begin = 0;
  while (begin <= input.size()) {
    size_t end = input.find(':', begin);
    if (end == std::string::npos) end = input.size();
    result.push_back(input.substr(begin, end - begin));
    if (end == input.size()) break;
    begin = end + 1;
  }
  return result;
}

}  // namespace

void Reset() {
  std::lock_guard<std::mutex> lock(g_mutex);
  g_create_calls = g_open_calls = g_close_calls = 0;
  g_live_domains = g_active_creates = g_max_active_creates = 0;
  g_active_releases = 0;
  g_fail_create = g_fail_create_with_domain = g_fail_open = g_fail_close = 0;
  g_block_create = g_release_create = g_same_handle = false;
  g_block_release = g_release_release = false;
  g_open_hook_armed = false;
  g_open_hook = nullptr;
  g_last_bridge_sonames.clear();
  g_error.clear();
}

void BlockCreates(bool block) {
  std::lock_guard<std::mutex> lock(g_mutex);
  g_block_create = block;
  g_release_create = !block;
}

void ReleaseCreates() {
  std::lock_guard<std::mutex> lock(g_mutex);
  g_release_create = true;
  g_changed.notify_all();
}

bool WaitForActiveCreates(int count) {
  std::unique_lock<std::mutex> lock(g_mutex);
  return g_changed.wait_for(lock, std::chrono::seconds(2),
                            [&] { return g_active_creates >= count; });
}

void FailNextCreate() { std::lock_guard<std::mutex> lock(g_mutex); ++g_fail_create; }
void FailNextCreateWithDomain() {
  std::lock_guard<std::mutex> lock(g_mutex);
  ++g_fail_create_with_domain;
}
void FailNextOpen() { std::lock_guard<std::mutex> lock(g_mutex); ++g_fail_open; }
void FailNextClose() { std::lock_guard<std::mutex> lock(g_mutex); ++g_fail_close; }
void ReturnSameHandle(bool value) { std::lock_guard<std::mutex> lock(g_mutex); g_same_handle = value; }
void SetOpenHook(std::function<void()> hook) {
  std::lock_guard<std::mutex> lock(g_mutex);
  g_open_hook = std::move(hook);
  g_open_hook_armed = true;
}

void BlockReleases(bool block) {
  std::lock_guard<std::mutex> lock(g_mutex);
  g_block_release = block;
  g_release_release = !block;
}

void ReleaseReleases() {
  std::lock_guard<std::mutex> lock(g_mutex);
  g_release_release = true;
  g_changed.notify_all();
}

bool WaitForActiveReleases(int count) {
  std::unique_lock<std::mutex> lock(g_mutex);
  return g_changed.wait_for(lock, std::chrono::seconds(2),
                            [&] { return g_active_releases >= count; });
}

int CreateCalls() { std::lock_guard<std::mutex> lock(g_mutex); return g_create_calls; }
int OpenCalls() { std::lock_guard<std::mutex> lock(g_mutex); return g_open_calls; }
int CloseCalls() { std::lock_guard<std::mutex> lock(g_mutex); return g_close_calls; }
int MaxActiveCreates() { std::lock_guard<std::mutex> lock(g_mutex); return g_max_active_creates; }
std::vector<std::string> LastBridgeSonames() {
  std::lock_guard<std::mutex> lock(g_mutex);
  return g_last_bridge_sonames;
}

}  // namespace fakeanl

extern "C" {

int ANL_CreateDomain(const AnlDomainConfig* config, AnlDomain** output) {
  bool fail = false;
  bool fail_with_domain = false;
  {
    std::unique_lock<std::mutex> lock(fakeanl::g_mutex);
    ++fakeanl::g_create_calls;
    ++fakeanl::g_active_creates;
    fakeanl::g_max_active_creates =
        std::max(fakeanl::g_max_active_creates, fakeanl::g_active_creates);
    fakeanl::g_last_bridge_sonames =
        fakeanl::Split(config == nullptr ? nullptr : config->bridge_shared_sonames);
    fakeanl::g_changed.notify_all();
    if (fakeanl::g_block_create) {
      fakeanl::g_changed.wait(lock, [] { return fakeanl::g_release_create; });
    }
    if (fakeanl::g_fail_create > 0) {
      --fakeanl::g_fail_create;
      fail = true;
    }
    if (fakeanl::g_fail_create_with_domain > 0) {
      --fakeanl::g_fail_create_with_domain;
      fail = true;
      fail_with_domain = true;
    }
    --fakeanl::g_active_creates;
    fakeanl::g_changed.notify_all();
  }
  if (output == nullptr) return -1;
  *output = nullptr;
  if (fail && !fail_with_domain) {
    fakeanl::g_error = "injected create failure";
    return -1;
  }
  auto* domain = new fakeanl::FakeDomain();
  {
    std::lock_guard<std::mutex> lock(fakeanl::g_mutex);
    domain->id = static_cast<uint64_t>(++fakeanl::g_live_domains);
  }
  *output = reinterpret_cast<AnlDomain*>(domain);
  if (fail_with_domain) {
    fakeanl::g_error = "injected create failure with domain";
    return -1;
  }
  fakeanl::g_error.clear();
  return 0;
}

void* ANL_Dlopen(AnlDomain* domain, const char*, int) {
  bool fail = false;
  bool same = false;
  std::function<void()> hook;
  {
    std::lock_guard<std::mutex> lock(fakeanl::g_mutex);
    ++fakeanl::g_open_calls;
    if (fakeanl::g_fail_open > 0) {
      --fakeanl::g_fail_open;
      fail = true;
    }
    same = fakeanl::g_same_handle;
    if (fakeanl::g_open_hook_armed) {
      fakeanl::g_open_hook_armed = false;
      hook = fakeanl::g_open_hook;
    }
  }
  if (hook) hook();
  if (domain == nullptr || fail) {
    fakeanl::g_error = "injected open failure";
    return nullptr;
  }
  fakeanl::g_error.clear();
  return reinterpret_cast<void*>(same ? 0x70000
      : fakeanl::g_next_handle.fetch_add(0x10));
}

void* ANL_Dlsym(void*, const char*) { return nullptr; }

int ANL_Dlclose(void* handle) {
  bool fail = false;
  {
    std::lock_guard<std::mutex> lock(fakeanl::g_mutex);
    ++fakeanl::g_close_calls;
    if (fakeanl::g_fail_close > 0) {
      --fakeanl::g_fail_close;
      fail = true;
    }
  }
  if (handle == nullptr || fail) {
    fakeanl::g_error = "injected close failure";
    return -1;
  }
  fakeanl::g_error.clear();
  return 0;
}

const char* ANL_Dlerror(void) {
  return fakeanl::g_error.empty() ? nullptr : fakeanl::g_error.c_str();
}

const char* ANL_GetNamespaceName(const AnlDomain*) { return "fake.namespace"; }

void ANL_ReleaseDomainHandle(AnlDomain* domain) {
  if (domain == nullptr) return;
  {
    std::unique_lock<std::mutex> lock(fakeanl::g_mutex);
    ++fakeanl::g_active_releases;
    fakeanl::g_changed.notify_all();
    if (fakeanl::g_block_release) {
      fakeanl::g_changed.wait(lock, [] { return fakeanl::g_release_release; });
    }
    --fakeanl::g_live_domains;
    --fakeanl::g_active_releases;
    fakeanl::g_changed.notify_all();
  }
  delete reinterpret_cast<fakeanl::FakeDomain*>(domain);
}

}  // extern "C"

namespace {

int g_checks = 0;
int g_failures = 0;

#define CHECK(condition, message)                                            \
  do {                                                                       \
    ++g_checks;                                                              \
    if (!(condition)) {                                                      \
      ++g_failures;                                                          \
      std::fprintf(stderr, "FAIL: %s (%s:%d)\n", message, __FILE__, __LINE__); \
    }                                                                        \
  } while (0)

Config TestConfig(const char* root = "/data/app/test/lib/arm64") {
  Config config;
  config.target_sdk = 34;
  config.app_search_paths = {root};
  config.app_permitted_paths = {root};
  config.bridge_search_paths = {"/system/android/lib64", "/system/lib64"};
  config.bridge_permitted_paths = config.bridge_search_paths;
  config.bridge_shared_sonames = {"libc.so", "liblog.so"};
  return config;
}

void ResetModels() {
  fakeanl::Reset();
  fakejni::ResetModel();
}

void TestIdentityAndSingleFlight() {
  ResetModels();
  Registry registry;
  registry.Initialize(nullptr);
  jobject loader = fakejni::NewObject();
  jobject alias = fakejni::Alias(loader);
  std::atomic<int> successes{0};
  std::vector<std::thread> threads;
  for (int i = 0; i < 24; ++i) {
    threads.emplace_back([&, i] {
      std::string error;
      jobject ref = (i % 2 == 0) ? loader : alias;
      if (registry.GetOrCreate(fakejni::Env(), ref, TestConfig(), &error) ==
          Status::kOk) {
        ++successes;
      }
    });
  }
  for (auto& thread : threads) thread.join();
  CHECK(successes == 24, "all same-loader waiters succeed");
  CHECK(fakeanl::CreateCalls() == 1, "same-loader create is single-flight");
  CHECK(registry.LiveEntryCountForTests() == 1, "one identity entry");
  CHECK(registry.Reset() == Status::kOk, "identity test reset");
}

void TestDifferentLoadersCreateConcurrently() {
  ResetModels();
  Registry registry;
  registry.Initialize(nullptr);
  jobject first = fakejni::NewObject();
  jobject second = fakejni::NewObject();
  fakeanl::BlockCreates(true);
  std::atomic<int> successes{0};
  std::thread a([&] {
    std::string error;
    if (registry.GetOrCreate(fakejni::Env(), first, TestConfig("/data/app/a/lib"),
                             &error) == Status::kOk) ++successes;
  });
  std::thread b([&] {
    std::string error;
    if (registry.GetOrCreate(fakejni::Env(), second, TestConfig("/data/app/b/lib"),
                             &error) == Status::kOk) ++successes;
  });
  CHECK(fakeanl::WaitForActiveCreates(2), "two loaders reach backend concurrently");
  fakeanl::ReleaseCreates();
  a.join();
  b.join();
  CHECK(successes == 2, "both different loaders succeed");
  CHECK(fakeanl::MaxActiveCreates() >= 2, "backend create concurrency observed");
  CHECK(registry.Reset() == Status::kOk, "different-loader reset");
}

void TestOpenWaitsForCreate() {
  ResetModels();
  Registry registry;
  registry.Initialize(nullptr);
  jobject loader = fakejni::NewObject();
  fakeanl::BlockCreates(true);
  Status create_status = Status::kBackendError;
  std::thread creator([&] {
    std::string error;
    create_status = registry.GetOrCreate(fakejni::Env(), loader, TestConfig(), &error);
  });
  CHECK(fakeanl::WaitForActiveCreates(1), "create entered backend");
  void* handle = nullptr;
  char* open_error = nullptr;
  std::thread opener([&] {
    handle = registry.Open(fakejni::Env(), loader, nullptr,
                           "/data/app/test/lib/arm64/libmain.so", RTLD_NOW,
                           &open_error);
  });
  std::this_thread::sleep_for(std::chrono::milliseconds(10));
  fakeanl::ReleaseCreates();
  creator.join();
  opener.join();
  CHECK(create_status == Status::kOk, "blocked create succeeds");
  CHECK(handle != nullptr, "open waits and succeeds after create");
  CHECK(open_error == nullptr, "waited open has no error");
  CHECK(registry.Close(handle, nullptr) == Status::kOk, "close waited open");
  CHECK(registry.Reset() == Status::kOk, "open-wait reset");
}

void TestCollectedDuringCreateIsNeverPublished() {
  ResetModels();
  Registry registry;
  registry.Initialize(nullptr);
  jobject loader = fakejni::NewObject();
  fakeanl::BlockCreates(true);
  Status create_status = Status::kOk;
  std::thread creator([&] {
    std::string error;
    create_status = registry.GetOrCreate(fakejni::Env(), loader, TestConfig(), &error);
  });
  CHECK(fakeanl::WaitForActiveCreates(1), "GC race create entered backend");
  fakejni::Collect(loader);
  jobject other = fakejni::NewObject();
  char* sweep_error = nullptr;
  registry.Open(fakejni::Env(), other, nullptr, "/data/app/other/lib/x.so",
                RTLD_NOW, &sweep_error);
  std::free(sweep_error);
  fakeanl::ReleaseCreates();
  creator.join();
  CHECK(create_status != Status::kOk, "collected creating identity is not published");
  CHECK(registry.LiveEntryCountForTests() == 0, "collected entry retired");
  CHECK(fakejni::DeletedWeakCount() == 1, "collected weak deleted once");
  CHECK(registry.Reset() == Status::kOk, "GC-race reset releases quarantine");
}

void TestNestedOpenAndHandleAccounting() {
  ResetModels();
  Registry registry;
  registry.Initialize(nullptr);
  jobject loader = fakejni::NewObject();
  std::string error;
  CHECK(registry.GetOrCreate(fakejni::Env(), loader, TestConfig(), &error) ==
            Status::kOk,
        "nested-open create");
  void* nested = nullptr;
  fakeanl::SetOpenHook([&] {
    nested = registry.Open(fakejni::Env(), loader, nullptr,
                           "/data/app/test/lib/arm64/libnested.so", RTLD_NOW,
                           nullptr);
  });
  void* outer = registry.Open(fakejni::Env(), loader, nullptr,
                              "/data/app/test/lib/arm64/libouter.so", RTLD_NOW,
                              nullptr);
  CHECK(outer != nullptr && nested != nullptr, "nested backend open does not deadlock");
  CHECK(fakeanl::OpenCalls() == 2, "both nested opens reach backend");
  CHECK(registry.Reset() != Status::kOk, "reset refuses open handles");
  CHECK(registry.Close(outer, nullptr) == Status::kOk, "close outer");
  CHECK(registry.Close(nested, nullptr) == Status::kOk, "close nested");
  CHECK(registry.Reset() == Status::kOk, "reset succeeds after close drain");
}

void TestCloseFailureAndSameHandleRefs() {
  ResetModels();
  Registry registry;
  registry.Initialize(nullptr);
  jobject loader = fakejni::NewObject();
  std::string error;
  registry.GetOrCreate(fakejni::Env(), loader, TestConfig(), &error);
  fakeanl::ReturnSameHandle(true);
  void* first = registry.Open(fakejni::Env(), loader, nullptr,
                              "/data/app/test/lib/arm64/a.so", RTLD_NOW, nullptr);
  void* second = registry.Open(fakejni::Env(), loader, nullptr,
                               "/data/app/test/lib/arm64/b.so", RTLD_NOW, nullptr);
  CHECK(first == second && first != nullptr, "same backend handle is refcounted");
  fakeanl::FailNextClose();
  char* close_error = nullptr;
  CHECK(registry.Close(first, &close_error) == Status::kBackendError,
        "failed close retains ownership");
  CHECK(close_error != nullptr, "failed close returns owned error");
  std::free(close_error);
  CHECK(registry.Close(first, nullptr) == Status::kOk, "failed close can retry");
  CHECK(registry.Close(second, nullptr) == Status::kOk, "second open ref closes");
  CHECK(registry.Close(second, nullptr) == Status::kUnknownHandle,
        "extra close fails without backend call");
  CHECK(fakeanl::CloseCalls() == 3, "unknown close never reaches backend");
  CHECK(registry.Reset() == Status::kOk, "same-handle reset");
}

void TestErrorsAndConfigMismatch() {
  ResetModels();
  Registry registry;
  registry.Initialize(nullptr);
  jobject loader = fakejni::NewObject();
  std::string error;
  fakeanl::FailNextCreate();
  CHECK(registry.GetOrCreate(fakejni::Env(), loader, TestConfig(), &error) ==
            Status::kBackendError,
        "create failure surfaces");
  CHECK(error == "injected create failure", "create error copied immediately");
  CHECK(registry.GetOrCreate(fakejni::Env(), loader, TestConfig(), &error) ==
            Status::kBackendError,
        "failed create is sticky");
  CHECK(fakeanl::CreateCalls() == 1, "sticky failure does not retry");
  Config changed = TestConfig();
  changed.target_sdk = 33;
  CHECK(registry.GetOrCreate(fakejni::Env(), loader, changed, &error) ==
            Status::kConfigMismatch,
        "same identity different policy rejected");
  CHECK(registry.Reset() == Status::kOk, "error test reset");
}

void TestResetAfterVmDeathDoesNotCallVm() {
  ResetModels();
  Registry registry;
  registry.Initialize(nullptr);
  jobject loader = fakejni::NewObject();
  std::string error;
  CHECK(registry.GetOrCreate(fakejni::Env(), loader, TestConfig(), &error) ==
            Status::kOk,
        "VM teardown fixture creates one live namespace");
  const size_t vm_calls_before = fakejni::VmApiCallCount();
  fakejni::MarkVmDead();
  CHECK(registry.Reset(&error) == Status::kOk,
        "post-VM Reset succeeds without JNI teardown");
  CHECK(fakejni::VmApiCallCount() == vm_calls_before,
        "post-VM Reset performs zero JavaVM callbacks");
  CHECK(fakejni::DeletedWeakCount() == 0,
        "post-VM Reset forgets invalid weak token without JNI delete");
}

void TestResetWaitsForFailedCreateRelease() {
  ResetModels();
  Registry registry;
  registry.Initialize(nullptr);
  jobject loader = fakejni::NewObject();
  fakeanl::BlockReleases(true);
  fakeanl::FailNextCreateWithDomain();
  Status create_status = Status::kOk;
  std::thread creator([&] {
    std::string error;
    create_status = registry.GetOrCreate(fakejni::Env(), loader, TestConfig(), &error);
  });
  const bool release_started = fakeanl::WaitForActiveReleases(1);
  CHECK(release_started, "failed create enters backend release");
  std::atomic<bool> reset_done{false};
  Status reset_status = Status::kBackendError;
  std::thread resetter([&] {
    std::string error;
    reset_status = registry.Reset(&error);
    reset_done.store(true);
  });
  bool saw_resetting = false;
  const auto reset_deadline = std::chrono::steady_clock::now() +
                              std::chrono::seconds(2);
  while (std::chrono::steady_clock::now() < reset_deadline) {
    std::string probe_error;
    if (registry.Initialize(nullptr, &probe_error) == Status::kResetting) {
      saw_resetting = true;
      break;
    }
    std::this_thread::yield();
  }
  CHECK(saw_resetting, "test observes Reset inside the release barrier");
  CHECK(!reset_done.load(), "Reset remains behind failed-create release barrier");
  fakeanl::ReleaseReleases();
  creator.join();
  resetter.join();
  CHECK(create_status == Status::kBackendError,
        "failed create still reports backend error");
  CHECK(reset_status == Status::kOk,
        "Reset completes after old-generation release drains");
}

class FakeSystemOps final : public SystemLoaderOps {
 public:
  bool ResolvePath(const char* path, std::string* resolved,
                   std::string*) const override {
    ++resolve_calls;
    const bool is_provider = std::string_view(path).find("/lib64/") !=
                             std::string_view::npos;
    const std::string& override = is_provider ? provider_resolved_override
                                               : caller_resolved_override;
    *resolved = override.empty() ? path : override;
    return true;
  }

  void* OpenExact(const char* path, int) const override {
    ++open_calls;
    last_path = path;
    return reinterpret_cast<void*>(0x88000);
  }

  int CloseExact(void*) const override {
    ++close_calls;
    return 0;
  }

  const char* LastError() const override { return "fake system-loader error"; }

  mutable int resolve_calls = 0;
  mutable int open_calls = 0;
  mutable int close_calls = 0;
  mutable std::string last_path;
  mutable std::string provider_resolved_override;
  mutable std::string caller_resolved_override;
};

void TestSystemLoaderRouteIsolation() {
  FakeSystemOps ops;
  SystemLoader loader(&ops);
  char* error = nullptr;
  void* handle = loader.Open("libicu_jni.so", "/system/framework/core-oj.jar",
                             false, &error);
  CHECK(handle != nullptr && error == nullptr, "trusted system manifest open");
  CHECK(ops.open_calls == 1 &&
            ops.last_path == "/system/android/lib64/libicu_jni.so",
        "system route opens only exact manifest path");
  CHECK(loader.Owns(handle), "system route records handle ownership");
  CHECK(loader.Close(handle, &error) && error == nullptr, "system handle closes");
  CHECK(ops.close_calls == 1, "system close reaches exact backend once");

  handle = loader.Open("liboh_adapter_bridge.so",
                       "/system/android/framework/framework.jar", false,
                       &error);
  CHECK(handle != nullptr && error == nullptr,
        "trusted adapter class can reacquire exact adapter bridge");
  CHECK(ops.last_path == "/system/android/lib64/liboh_adapter_bridge.so",
        "adapter bridge system route uses exact generation path");
  CHECK(loader.Close(handle, &error) && error == nullptr,
        "adapter bridge system handle closes");

  ops.provider_resolved_override = "/system/android/lib64/wrong-provider.so";
  handle = loader.Open("libicu_jni.so", "/system/framework/core-oj.jar",
                       false, &error);
  CHECK(handle == nullptr && error != nullptr,
        "same-directory realpath redirect is rejected");
  std::free(error);
  error = nullptr;
  ops.provider_resolved_override.clear();

  ops.caller_resolved_override = "/data/app/escaped/base.apk";
  handle = loader.Open("libicu_jni.so", "/system/framework/link.jar", false,
                       &error);
  CHECK(handle == nullptr && error != nullptr,
        "trusted-root symlink escape is rejected after caller realpath");
  std::free(error);
  error = nullptr;
  ops.caller_resolved_override.clear();

  handle = loader.Open("libicu_jni.so",
                       "/system/framework/core-oj.jar!classes2.dex", false,
                       &error);
  CHECK(handle != nullptr && error == nullptr,
        "archive suffix preserves trusted filesystem origin");
  CHECK(loader.Close(handle, &error) && error == nullptr,
        "archive-suffix system handle closes");

  handle = loader.Open("libicu_jni.so",
                       "/system/framework/../../data/app/base.apk", false,
                       &error);
  CHECK(handle == nullptr && error != nullptr,
        "system caller dot-dot traversal is rejected");
  std::free(error);
  error = nullptr;
  handle = loader.Open("libicu_jni.so",
                       "/apex/com.android.art/../../../data/app/base.apk", false,
                       &error);
  CHECK(handle == nullptr && error != nullptr,
        "APEX caller dot-dot traversal is rejected");
  std::free(error);
  error = nullptr;
  handle = loader.Open("libicu_jni.so", "/system//framework/core-oj.jar",
                       false, &error);
  CHECK(handle == nullptr && error != nullptr,
        "caller with empty path component is rejected");
  std::free(error);
  error = nullptr;

  handle = loader.Open("libmain.so", "/system/framework/core-oj.jar", false,
                       &error);
  CHECK(handle == nullptr && error != nullptr,
        "app library absent from system manifest");
  std::free(error);
  error = nullptr;
  handle = loader.Open("libjavacore.so", "/data/app/pkg/base.apk", false,
                       &error);
  CHECK(handle == nullptr && error != nullptr, "app caller cannot enter system route");
  std::free(error);
  error = nullptr;
  handle = loader.Open("libopenjdk.so", "/system/framework/core-oj.jar", true,
                       &error);
  CHECK(handle == nullptr && error != nullptr,
        "system route rejects supplied ClassLoader library path");
  std::free(error);
  CHECK(ops.open_calls == 3, "all denied system requests fail before loader call");
}

void TestPublicProfileBAbiAndPolicy() {
  ResetModels();
  android::ResetNativeLoader();
  android::InitializeNativeLoader();
  JNIEnv* env = fakejni::Env();
  jobject loader = fakejni::NewObject();
  jstring search = env->NewStringUTF("/data/app/test/lib/arm64");
  jstring permitted = env->NewStringUTF("/data/app/test/lib/arm64");
  jstring attacker_list = env->NewStringUTF("libevil.so");
  jstring result = android::CreateClassLoaderNamespace(
      env, 34, loader, false, nullptr, search, permitted, attacker_list);
  CHECK(result == nullptr, "Profile B Create success is null jstring");
  std::vector<std::string> bridge = fakeanl::LastBridgeSonames();
  CHECK(std::find(bridge.begin(), bridge.end(), "liblog.so") != bridge.end(),
        "adapter bridge policy reaches backend");
  CHECK(std::find(bridge.begin(), bridge.end(), "libevil.so") == bridge.end(),
        "app soname list cannot widen bridge policy");

  bool needs_bridge = true;
  char* open_error = nullptr;
  void* no_loader = android::OpenNativeLibrary(
      env, 34, "/data/app/test/lib/arm64/libmain.so", nullptr, "caller",
      search, &needs_bridge, &open_error);
  CHECK(no_loader == nullptr && open_error != nullptr,
        "null ClassLoader does not recover through app path");
  CHECK(needs_bridge == false, "needs_native_bridge output initialized");
  android::NativeLoaderFreeErrorMessage(open_error);
  android::ResetNativeLoader();

  android::InitializeNativeLoader();
  jstring invalid = env->NewStringUTF("/data/app/a::/data/app/b");
  jstring invalid_result = android::CreateClassLoaderNamespace(
      env, 34, fakejni::NewObject(), false, nullptr, invalid, permitted, nullptr);
  CHECK(invalid_result != nullptr, "empty path segment fails closed");
  android::ResetNativeLoader();
}

}  // namespace

int main() {
  TestIdentityAndSingleFlight();
  TestDifferentLoadersCreateConcurrently();
  TestOpenWaitsForCreate();
  TestCollectedDuringCreateIsNeverPublished();
  TestNestedOpenAndHandleAccounting();
  TestCloseFailureAndSameHandleRefs();
  TestErrorsAndConfigMismatch();
  TestResetAfterVmDeathDoesNotCallVm();
  TestResetWaitsForFailedCreateRelease();
  TestSystemLoaderRouteIsolation();
  TestPublicProfileBAbiAndPolicy();
  std::printf("NativeLoader Profile B registry: %d checks, %d failures\n",
              g_checks, g_failures);
  return g_failures == 0 ? 0 : 1;
}
