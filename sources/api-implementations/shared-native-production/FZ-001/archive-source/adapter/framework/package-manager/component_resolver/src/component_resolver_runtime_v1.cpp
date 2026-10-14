#include "component_resolver_runtime_v1.h"

#include "sha256.h"

#include <charconv>
#include <cerrno>
#include <cstring>
#include <fcntl.h>
#include <fstream>
#include <map>
#include <mutex>
#include <shared_mutex>
#include <sstream>
#include <sys/stat.h>
#include <unistd.h>
#include <utility>

namespace oh_adapter::component_resolver {
namespace {

constexpr size_t MAX_INDEX_BYTES = 32 * 1024 * 1024;
constexpr size_t MAX_SCOPE_BYTES = 256 * 1024;
constexpr int32_t ROOT_UID = 0;
constexpr int32_t SYSTEM_UID = 1000;
constexpr const char* PRODUCT_STORE_ROOT =
    "/data/service/el1/public/appspawnx/fn01/package-store-v1";
constexpr const char* PRODUCT_INDEX_PATH =
    "/data/service/el1/private/appspawnx/fn01/component-index-v1/catalog.bin";
constexpr const char* PRODUCT_SCOPE_ROOT =
    "/data/service/el1/private/appspawnx/fn01/caller-scope-v1";

std::shared_mutex runtimeMutex;
ComponentCatalogProviderV1* runtimeCatalog = nullptr;
PackageGuardReaderV1* runtimeGuard = nullptr;
CallerResolveContextProviderV1* runtimeCaller = nullptr;
ResolveFaultInjectorV1* runtimeFault = nullptr;

bool IsAbsolutePath(const std::string& path)
{
    return path.size() > 1 && path.front() == '/' &&
        path.find('\0') == std::string::npos &&
        path.find('\n') == std::string::npos &&
        path.find('\r') == std::string::npos &&
        path.find("/../") == std::string::npos &&
        path.rfind("/..", path.size() - 3) == std::string::npos;
}

bool ReadRegularFileNoFollow(const std::string& path, size_t maxBytes,
    std::vector<uint8_t>* bytes, bool* absent, std::string* error,
    struct stat* metadata = nullptr)
{
    if (bytes == nullptr || absent == nullptr) return false;
    *absent = false;
    const int descriptor =
        open(path.c_str(), O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (descriptor < 0) {
        *absent = errno == ENOENT;
        if (!*absent && error != nullptr) *error = std::strerror(errno);
        return false;
    }
    struct stat status {};
    if (fstat(descriptor, &status) != 0 || !S_ISREG(status.st_mode) ||
        status.st_size < 0 ||
        static_cast<uint64_t>(status.st_size) > maxBytes) {
        if (error != nullptr) *error = "file is not a bounded regular file";
        close(descriptor);
        return false;
    }
    if (metadata != nullptr) *metadata = status;
    std::vector<uint8_t> result(static_cast<size_t>(status.st_size));
    size_t offset = 0;
    while (offset < result.size()) {
        const ssize_t count =
            read(descriptor, result.data() + offset, result.size() - offset);
        if (count < 0 && errno == EINTR) continue;
        if (count <= 0) {
            if (error != nullptr) *error = "file short read";
            close(descriptor);
            return false;
        }
        offset += static_cast<size_t>(count);
    }
    close(descriptor);
    *bytes = std::move(result);
    if (error != nullptr) error->clear();
    return true;
}

std::string Sha256Hex(const std::vector<uint8_t>& bytes)
{
    uint8_t digest[32];
    sha256(bytes.data(), bytes.size(), digest);
    static constexpr char HEX[] = "0123456789abcdef";
    std::string result(64, '0');
    for (size_t index = 0; index < 32; ++index) {
        result[index * 2] = HEX[digest[index] >> 4];
        result[index * 2 + 1] = HEX[digest[index] & 15];
    }
    return result;
}

template <typename T>
bool ParseInteger(const std::string& value, T* parsed)
{
    if (parsed == nullptr || value.empty()) return false;
    T result = 0;
    const auto conversion =
        std::from_chars(value.data(), value.data() + value.size(), result);
    if (conversion.ec != std::errc() ||
        conversion.ptr != value.data() + value.size()) {
        return false;
    }
    *parsed = result;
    return true;
}

bool ScopeToken(const std::string& value, bool allowEmpty = false)
{
    return (allowEmpty || !value.empty()) && value.size() <= 4096 &&
        value.find('\0') == std::string::npos &&
        value.find('\n') == std::string::npos &&
        value.find('\r') == std::string::npos;
}

ComponentResolveResponseV1 ClosedResponse(
    const ComponentResolveRequestV1& request, const char* reason)
{
    ComponentResolveResponseV1 response;
    response.requestId = request.requestId;
    response.verdict = ComponentResolveVerdict::PACKAGE_NOT_READY;
    response.reason = reason;
    return response;
}

ComponentResolverRuntimeOwnerV1& ProductOwner()
{
    static ComponentResolverRuntimeOwnerV1 owner;
    return owner;
}

}  // namespace

FileComponentCatalogProviderV1::FileComponentCatalogProviderV1(
    std::string indexPath)
    : indexPath_(std::move(indexPath))
{
}

bool FileComponentCatalogProviderV1::Read(ComponentCatalogV1* catalog,
    std::string* indexDigest, std::string* error)
{
    if (catalog == nullptr || indexDigest == nullptr ||
        !IsAbsolutePath(indexPath_)) {
        if (error != nullptr) *error = "invalid component index path";
        return false;
    }
    std::vector<uint8_t> bytes;
    bool absent = false;
    if (!ReadRegularFileNoFollow(
            indexPath_, MAX_INDEX_BYTES, &bytes, &absent, error, nullptr)) {
        if (absent && error != nullptr) *error = "component index absent";
        return false;
    }
    if (!ParseComponentCatalogV1(bytes, catalog, error)) return false;
    *indexDigest = ComponentCatalogDigestV1(bytes);
    if (error != nullptr) error->clear();
    return true;
}

StorePackageGuardReaderV1::StorePackageGuardReaderV1(
    package_transaction::FilePackageStore* store)
    : store_(store)
{
}

bool StorePackageGuardReaderV1::Read(uint32_t userId,
    const std::string& packageName, PackageGuardV1* guard,
    std::string* error)
{
    if (store_ == nullptr || guard == nullptr || packageName.empty()) {
        if (error != nullptr) *error = "invalid package guard request";
        return false;
    }
    package_transaction::PackageManagementReadV1 read;
    if (!store_->ReadPackageManagementState(
            userId, packageName, &read, error)) {
        return false;
    }
    PackageGuardV1 result;
    result.catalogRevision = read.catalogRevision;
    result.removing = read.removing;
    if (read.canonical.has_value()) {
        result.hasCanonical = true;
        result.generation = read.canonical->generation;
        result.canonicalDigest = read.canonical->canonicalDigest;
    }
    if (read.projection.has_value()) {
        result.projectionActive =
            read.projection->state ==
                package_transaction::HostProjectionState::ACTIVE;
        result.projectionGeneration = read.projection->generation;
        result.projectionCanonicalDigest =
            read.projection->canonicalDigest;
    }
    if (read.publicationToken.has_value()) {
        result.tokenExternalReady =
            read.publicationToken->state ==
                package_transaction::PublicationState::EXTERNAL_READY;
        result.tokenGeneration = read.publicationToken->generation;
        result.tokenCanonicalDigest =
            read.publicationToken->canonicalDigest;
    }
    *guard = std::move(result);
    if (error != nullptr) error->clear();
    return true;
}

FileCallerResolveContextProviderV1::FileCallerResolveContextProviderV1(
    std::string scopeRoot)
    : scopeRoot_(std::move(scopeRoot))
{
}

bool FileCallerResolveContextProviderV1::Resolve(int32_t callingUid,
    uint32_t userId, CallerResolveContextV1* caller, std::string* error)
{
    if (caller == nullptr || callingUid < 0 || userId != 0 ||
        !IsAbsolutePath(scopeRoot_)) {
        if (error != nullptr) *error = "invalid caller scope request";
        return false;
    }
    CallerResolveContextV1 result;
    result.callingUid = callingUid;
    if (callingUid == ROOT_UID || callingUid == SYSTEM_UID) {
        result.callerPackageName =
            callingUid == ROOT_UID ? "android.root" : "android";
        result.visibilityScopeDigest =
            callingUid == ROOT_UID ? "trusted-root-v1" : "trusted-system-v1";
        result.canSeeAllPackages = true;
        result.grantedPermissions = {"*"};
        *caller = std::move(result);
        if (error != nullptr) error->clear();
        return true;
    }

    const std::string path =
        scopeRoot_ + "/uid-" + std::to_string(callingUid) + ".scope";
    std::vector<uint8_t> bytes;
    bool absent = false;
    struct stat metadata {};
    if (!ReadRegularFileNoFollow(
            path, MAX_SCOPE_BYTES, &bytes, &absent, error, &metadata)) {
        if (absent && error != nullptr) *error = "caller scope absent";
        return false;
    }
    if ((metadata.st_uid != static_cast<uid_t>(ROOT_UID) &&
            metadata.st_uid != static_cast<uid_t>(SYSTEM_UID)) ||
        (metadata.st_mode & (S_IWGRP | S_IWOTH)) != 0) {
        if (error != nullptr) {
            *error = "caller scope owner or mode is not trusted";
        }
        return false;
    }
    std::istringstream input(std::string(bytes.begin(), bytes.end()));
    std::string line;
    bool sawSchema = false;
    bool sawUid = false;
    bool sawUser = false;
    bool sawCaller = false;
    bool sawCanSeeAll = false;
    while (std::getline(input, line)) {
        if (line.empty() || line.find('\r') != std::string::npos) {
            if (error != nullptr) *error = "caller scope line malformed";
            return false;
        }
        const size_t separator = line.find('=');
        if (separator == std::string::npos || separator == 0) {
            if (error != nullptr) *error = "caller scope key malformed";
            return false;
        }
        const std::string key = line.substr(0, separator);
        const std::string value = line.substr(separator + 1);
        if (key == "schemaVersion" && !sawSchema) {
            sawSchema = value == "1";
        } else if (key == "callingUid" && !sawUid) {
            int32_t parsed = -1;
            sawUid = ParseInteger(value, &parsed) && parsed == callingUid;
        } else if (key == "userId" && !sawUser) {
            uint32_t parsed = 0;
            sawUser = ParseInteger(value, &parsed) && parsed == userId;
        } else if (key == "callerPackageName" && !sawCaller) {
            sawCaller = ScopeToken(value);
            result.callerPackageName = value;
        } else if (key == "canSeeAllPackages" && !sawCanSeeAll) {
            sawCanSeeAll = value == "true" || value == "false";
            result.canSeeAllPackages = value == "true";
        } else if (key == "visiblePackage") {
            if (!ScopeToken(value)) return false;
            result.visiblePackageNames.push_back(value);
        } else if (key == "grantedPermission") {
            if (!ScopeToken(value)) return false;
            result.grantedPermissions.push_back(value);
        } else {
            if (error != nullptr) *error = "caller scope key unknown";
            return false;
        }
    }
    if (!sawSchema || !sawUid || !sawUser || !sawCaller ||
        !sawCanSeeAll) {
        if (error != nullptr) *error = "caller scope identity incomplete";
        return false;
    }
    result.visibilityScopeDigest = Sha256Hex(bytes);
    *caller = std::move(result);
    if (error != nullptr) error->clear();
    return true;
}

bool ConfigureComponentResolverRuntimeV1(
    ComponentCatalogProviderV1* catalogProvider,
    PackageGuardReaderV1* guardReader,
    CallerResolveContextProviderV1* callerProvider,
    ResolveFaultInjectorV1* faultInjector, std::string* error)
{
    if (catalogProvider == nullptr || guardReader == nullptr ||
        callerProvider == nullptr || faultInjector == nullptr) {
        if (error != nullptr) *error = "runtime dependency is null";
        return false;
    }
    std::unique_lock<std::shared_mutex> lock(runtimeMutex);
    if (runtimeCatalog != nullptr) {
        if (error != nullptr) *error = "runtime is already configured";
        return false;
    }
    runtimeCatalog = catalogProvider;
    runtimeGuard = guardReader;
    runtimeCaller = callerProvider;
    runtimeFault = faultInjector;
    if (error != nullptr) error->clear();
    return true;
}

void ClearComponentResolverRuntimeV1()
{
    std::unique_lock<std::shared_mutex> lock(runtimeMutex);
    runtimeCatalog = nullptr;
    runtimeGuard = nullptr;
    runtimeCaller = nullptr;
    runtimeFault = nullptr;
}

std::string QueryComponentResolverRuntimeJsonV1(
    ComponentResolveRequestV1 request, int32_t callingUid)
{
    std::shared_lock<std::shared_mutex> lock(runtimeMutex);
    if (runtimeCatalog == nullptr || runtimeGuard == nullptr ||
        runtimeCaller == nullptr || runtimeFault == nullptr) {
        return ComponentResolveResponseJsonV1(ClosedResponse(
            request, "COMPONENT_RESOLVER_RUNTIME_NOT_CONFIGURED"));
    }
    std::string error;
    if (!runtimeCaller->Resolve(
            callingUid, request.userId, &request.caller, &error)) {
        return ComponentResolveResponseJsonV1(ClosedResponse(
            request, "CALLER_CONTEXT_NOT_READY"));
    }
    ComponentResolverServiceV1 service(
        runtimeCatalog, runtimeGuard, runtimeFault);
    return ComponentResolveResponseJsonV1(service.Resolve(request));
}

struct ComponentResolverRuntimeOwnerV1::Impl {
    mutable std::mutex mutex;
    bool started = false;
    std::unique_ptr<package_transaction::FilePackageStore> store;
    std::unique_ptr<FileComponentCatalogProviderV1> catalog;
    std::unique_ptr<StorePackageGuardReaderV1> guard;
    std::unique_ptr<FileCallerResolveContextProviderV1> caller;
    std::unique_ptr<NoResolveFaultInjectorV1> fault;
};

ComponentResolverRuntimeOwnerV1::ComponentResolverRuntimeOwnerV1()
    : impl_(std::make_unique<Impl>())
{
}

ComponentResolverRuntimeOwnerV1::~ComponentResolverRuntimeOwnerV1()
{
    Stop();
}

bool ComponentResolverRuntimeOwnerV1::Start(
    const ComponentResolverRuntimeConfigV1& config, std::string* error)
{
    std::lock_guard<std::mutex> lock(impl_->mutex);
    if (impl_->started) {
        if (error != nullptr) error->clear();
        return true;
    }
    if (!IsAbsolutePath(config.packageStoreRoot) ||
        !IsAbsolutePath(config.componentIndexPath) ||
        !IsAbsolutePath(config.callerScopeRoot)) {
        if (error != nullptr) *error = "runtime paths must be absolute";
        return false;
    }
    auto store = std::make_unique<package_transaction::FilePackageStore>(
        config.packageStoreRoot);
    if (!store->OpenReadOnly(error)) return false;
    auto catalog = std::make_unique<FileComponentCatalogProviderV1>(
        config.componentIndexPath);
    auto guard =
        std::make_unique<StorePackageGuardReaderV1>(store.get());
    auto caller = std::make_unique<FileCallerResolveContextProviderV1>(
        config.callerScopeRoot);
    auto fault = std::make_unique<NoResolveFaultInjectorV1>();
    if (!ConfigureComponentResolverRuntimeV1(
            catalog.get(), guard.get(), caller.get(), fault.get(), error)) {
        return false;
    }
    impl_->store = std::move(store);
    impl_->catalog = std::move(catalog);
    impl_->guard = std::move(guard);
    impl_->caller = std::move(caller);
    impl_->fault = std::move(fault);
    impl_->started = true;
    if (error != nullptr) error->clear();
    return true;
}

void ComponentResolverRuntimeOwnerV1::Stop()
{
    std::lock_guard<std::mutex> lock(impl_->mutex);
    if (!impl_->started) return;
    ClearComponentResolverRuntimeV1();
    impl_->fault.reset();
    impl_->caller.reset();
    impl_->guard.reset();
    impl_->catalog.reset();
    impl_->store.reset();
    impl_->started = false;
}

bool ComponentResolverRuntimeOwnerV1::IsStarted() const
{
    std::lock_guard<std::mutex> lock(impl_->mutex);
    return impl_->started;
}

bool StartProductComponentResolverRuntimeV1(std::string* error)
{
    return ProductOwner().Start(
        {PRODUCT_STORE_ROOT, PRODUCT_INDEX_PATH, PRODUCT_SCOPE_ROOT}, error);
}

void StopProductComponentResolverRuntimeV1()
{
    ProductOwner().Stop();
}

}  // namespace oh_adapter::component_resolver
