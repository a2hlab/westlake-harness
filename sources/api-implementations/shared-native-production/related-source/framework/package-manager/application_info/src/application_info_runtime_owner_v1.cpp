#include "application_info_runtime_owner_v1.h"

#include "application_info_runtime_v1.h"
#include "sha256.h"

#include <charconv>
#include <cerrno>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <map>
#include <mutex>
#include <optional>
#include <sys/stat.h>
#include <unistd.h>
#include <utility>

namespace oh_adapter::application_info {
namespace {

constexpr size_t MAX_FACTS_BYTES = 64 * 1024;
constexpr int32_t ROOT_UID = 0;
constexpr int32_t SYSTEM_UID = 1000;
constexpr const char* FN01_STATE_ROOT_ENV = "OH_ADAPTER_FN01_STATE_ROOT";
constexpr const char* STORE_ROOT_SUFFIX = "/package-store-v1";
constexpr const char* FACTS_ROOT_SUFFIX = "/application-runtime-facts-v1";

std::string Sha256Hex(const std::string& value)
{
    uint8_t digest[32];
    sha256(reinterpret_cast<const uint8_t*>(value.data()), value.size(), digest);
    static constexpr char HEX[] = "0123456789abcdef";
    std::string result(64, '0');
    for (size_t index = 0; index < 32; ++index) {
        result[index * 2] = HEX[digest[index] >> 4];
        result[index * 2 + 1] = HEX[digest[index] & 15];
    }
    return result;
}

bool IsAbsoluteRoot(const std::string& path)
{
    return path.size() > 1 && path.front() == '/' &&
        path.back() != '/' && path.find('\n') == std::string::npos &&
        path.find('\r') == std::string::npos;
}

template <typename T>
bool ParseUnsigned(const std::string& value, T* result)
{
    if (result == nullptr || value.empty() || value.front() == '-') return false;
    T parsed = 0;
    const auto conversion =
        std::from_chars(value.data(), value.data() + value.size(), parsed);
    if (conversion.ec != std::errc() ||
        conversion.ptr != value.data() + value.size()) {
        return false;
    }
    *result = parsed;
    return true;
}

bool ParseSigned32(const std::string& value, int32_t* result)
{
    if (result == nullptr || value.empty()) return false;
    int32_t parsed = 0;
    const auto conversion =
        std::from_chars(value.data(), value.data() + value.size(), parsed);
    if (conversion.ec != std::errc() ||
        conversion.ptr != value.data() + value.size()) {
        return false;
    }
    *result = parsed;
    return true;
}

bool ParseBool(const std::string& value, bool* result)
{
    if (result == nullptr) return false;
    if (value == "true") {
        *result = true;
        return true;
    }
    if (value == "false") {
        *result = false;
        return true;
    }
    return false;
}

bool ReadRegularFileNoFollow(const std::string& path, std::string* contents,
    bool* absent, std::string* error)
{
    if (contents == nullptr || absent == nullptr) return false;
    *absent = false;
    const int file = open(path.c_str(), O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (file < 0) {
        if (errno == ENOENT) {
            *absent = true;
        } else if (error != nullptr) {
            *error = std::strerror(errno);
        }
        return false;
    }
    struct stat status {};
    if (fstat(file, &status) != 0 || !S_ISREG(status.st_mode) ||
        status.st_size < 0 ||
        static_cast<uint64_t>(status.st_size) > MAX_FACTS_BYTES) {
        if (error != nullptr) *error = "runtime facts file is not a bounded regular file";
        close(file);
        return false;
    }
    const uid_t effectiveUid = geteuid();
    if ((status.st_uid != static_cast<uid_t>(ROOT_UID) &&
            status.st_uid != static_cast<uid_t>(SYSTEM_UID) &&
            status.st_uid != effectiveUid) ||
        (status.st_mode & (S_IWGRP | S_IWOTH)) != 0) {
        if (error != nullptr) {
            *error = "runtime facts file owner or mode is not trusted";
        }
        close(file);
        return false;
    }
    std::string result(static_cast<size_t>(status.st_size), '\0');
    size_t offset = 0;
    while (offset < result.size()) {
        const ssize_t count =
            read(file, result.data() + offset, result.size() - offset);
        if (count < 0 && errno == EINTR) continue;
        if (count <= 0) {
            if (error != nullptr) *error = "runtime facts short read";
            close(file);
            return false;
        }
        offset += static_cast<size_t>(count);
    }
    close(file);
    *contents = std::move(result);
    return true;
}

bool ParseFields(const std::string& contents,
    std::map<std::string, std::string>* fields, std::string* error)
{
    if (fields == nullptr) return false;
    size_t offset = 0;
    while (offset < contents.size()) {
        const size_t newline = contents.find('\n', offset);
        const size_t end =
            newline == std::string::npos ? contents.size() : newline;
        const std::string line = contents.substr(offset, end - offset);
        if (line.empty()) {
            if (error != nullptr) *error = "runtime facts contains empty line";
            return false;
        }
        const size_t separator = line.find('=');
        if (separator == std::string::npos || separator == 0 ||
            separator + 1 == line.size() ||
            line.find('\r') != std::string::npos) {
            if (error != nullptr) *error = "runtime facts line is malformed";
            return false;
        }
        const auto inserted =
            fields->emplace(line.substr(0, separator),
                line.substr(separator + 1));
        if (!inserted.second) {
            if (error != nullptr) *error = "runtime facts key is duplicated";
            return false;
        }
        if (newline == std::string::npos) break;
        offset = newline + 1;
    }
    return !fields->empty();
}

const std::string* Required(const std::map<std::string, std::string>& fields,
    const char* key, std::string* error)
{
    const auto iterator = fields.find(key);
    if (iterator != fields.end()) return &iterator->second;
    if (error != nullptr) *error = std::string("runtime facts missing ") + key;
    return nullptr;
}

bool ParsePath(const std::map<std::string, std::string>& fields,
    const char* pathKey, const char* digestKey, const char* ownerKey,
    ManagedPathKind kind, ManagedPathExpectationV1* expectation,
    std::string* error)
{
    const auto* path = Required(fields, pathKey, error);
    const auto* digest = Required(fields, digestKey, error);
    const auto* owner = Required(fields, ownerKey, error);
    uint32_t ownerUid = 0;
    if (path == nullptr || digest == nullptr || owner == nullptr ||
        path->front() != '/' || !ParseUnsigned(*owner, &ownerUid)) {
        if (error != nullptr && error->empty()) {
            *error = std::string("runtime facts invalid ") + pathKey;
        }
        return false;
    }
    *expectation = {kind, *path, *digest, ownerUid};
    return true;
}

ApplicationInfoRuntimeOwnerV1& ProductOwner()
{
    static ApplicationInfoRuntimeOwnerV1 owner;
    return owner;
}

}  // namespace

FileHostApplicationRuntimeFactsResolverV1::
    FileHostApplicationRuntimeFactsResolverV1(std::string runtimeFactsRoot)
    : runtimeFactsRoot_(std::move(runtimeFactsRoot))
{
}

std::string FileHostApplicationRuntimeFactsResolverV1::FactsPath(
    const std::string& packageName, uint32_t userId) const
{
    return runtimeFactsRoot_ + "/user-" + std::to_string(userId) + "/" +
        Sha256Hex(packageName) + ".facts";
}

HostApplicationFactsVerdict
FileHostApplicationRuntimeFactsResolverV1::Resolve(
    const std::string& packageName, uint32_t userId, uint64_t generation,
    const std::string& canonicalDigest,
    HostApplicationRuntimeFactsV1* facts, std::string* error)
{
    if (facts == nullptr || packageName.empty() || generation == 0 ||
        canonicalDigest.empty()) {
        if (error != nullptr) *error = "invalid runtime facts request";
        return HostApplicationFactsVerdict::DATA_INCONSISTENT;
    }
    std::string contents;
    bool absent = false;
    if (!ReadRegularFileNoFollow(FactsPath(packageName, userId), &contents,
            &absent, error)) {
        return absent ? HostApplicationFactsVerdict::PACKAGE_NOT_READY
                      : HostApplicationFactsVerdict::DATA_INCONSISTENT;
    }
    std::map<std::string, std::string> fields;
    if (!ParseFields(contents, &fields, error)) {
        return HostApplicationFactsVerdict::DATA_INCONSISTENT;
    }
    const auto* schema = Required(fields, "schemaVersion", error);
    const auto* storedPackage = Required(fields, "packageName", error);
    const auto* storedUser = Required(fields, "userId", error);
    const auto* storedGeneration = Required(fields, "generation", error);
    const auto* storedCanonical = Required(fields, "canonicalDigest", error);
    const auto* projectionDigest =
        Required(fields, "projectionDigest", error);
    const auto* bundleName = Required(fields, "bundleName", error);
    const auto* appId = Required(fields, "appId", error);
    const auto* uid = Required(fields, "uid", error);
    const auto* accessTokenId = Required(fields, "accessTokenId", error);
    const auto* projectionActive =
        Required(fields, "projectionActive", error);
    const auto* tokenExternalReady =
        Required(fields, "tokenExternalReady", error);
    const auto* installed = Required(fields, "installed", error);
    const auto* enabled = Required(fields, "enabled", error);
    const auto* hidden = Required(fields, "hidden", error);
    if (schema == nullptr || storedPackage == nullptr || storedUser == nullptr ||
        storedGeneration == nullptr || storedCanonical == nullptr ||
        projectionDigest == nullptr || bundleName == nullptr ||
        appId == nullptr || uid == nullptr || accessTokenId == nullptr ||
        projectionActive == nullptr || tokenExternalReady == nullptr ||
        installed == nullptr || enabled == nullptr || hidden == nullptr) {
        return HostApplicationFactsVerdict::DATA_INCONSISTENT;
    }

    HostApplicationRuntimeFactsV1 parsed;
    uint32_t parsedUser = 0;
    if (*schema != "1" || !ParseUnsigned(*storedUser, &parsedUser) ||
        !ParseUnsigned(*storedGeneration, &parsed.generation) ||
        !ParseSigned32(*uid, &parsed.uid) ||
        !ParseUnsigned(*accessTokenId, &parsed.accessTokenId) ||
        !ParseBool(*projectionActive, &parsed.projectionActive) ||
        !ParseBool(*tokenExternalReady, &parsed.tokenExternalReady) ||
        !ParseBool(*installed, &parsed.installed) ||
        !ParseBool(*enabled, &parsed.enabled) ||
        !ParseBool(*hidden, &parsed.hidden)) {
        if (error != nullptr) *error = "runtime facts scalar is invalid";
        return HostApplicationFactsVerdict::DATA_INCONSISTENT;
    }
    parsed.packageName = *storedPackage;
    parsed.userId = parsedUser;
    parsed.canonicalDigest = *storedCanonical;
    parsed.projectionDigest = *projectionDigest;
    parsed.bundleName = *bundleName;
    parsed.appId = *appId;
    if (!ParsePath(fields, "dataDirectory", "dataDirectoryDigest",
            "dataDirectoryOwnerUid", ManagedPathKind::DATA_DIRECTORY,
            &parsed.dataDirectory, error) ||
        !ParsePath(fields, "deviceProtectedDataDirectory",
            "deviceProtectedDataDirectoryDigest",
            "deviceProtectedDataDirectoryOwnerUid",
            ManagedPathKind::DATA_DIRECTORY,
            &parsed.deviceProtectedDataDirectory, error) ||
        !ParsePath(fields, "credentialProtectedDataDirectory",
            "credentialProtectedDataDirectoryDigest",
            "credentialProtectedDataDirectoryOwnerUid",
            ManagedPathKind::DATA_DIRECTORY,
            &parsed.credentialProtectedDataDirectory, error)) {
        return HostApplicationFactsVerdict::DATA_INCONSISTENT;
    }
    const auto nativePath = fields.find("nativeLibraryDirectory");
    if (nativePath != fields.end()) {
        ManagedPathExpectationV1 native;
        if (!ParsePath(fields, "nativeLibraryDirectory",
                "nativeLibraryDirectoryDigest",
                "nativeLibraryDirectoryOwnerUid",
                ManagedPathKind::NATIVE_LIBRARY_DIRECTORY, &native, error)) {
            return HostApplicationFactsVerdict::DATA_INCONSISTENT;
        }
        parsed.nativeLibraryDirectory = std::move(native);
    }
    const auto abi = fields.find("primaryCpuAbi");
    if (abi != fields.end()) parsed.primaryCpuAbi = abi->second;

    if (parsed.packageName != packageName || parsed.userId != userId ||
        parsed.generation != generation ||
        parsed.canonicalDigest != canonicalDigest) {
        if (error != nullptr) *error = "runtime facts generation join mismatch";
        return HostApplicationFactsVerdict::DATA_INCONSISTENT;
    }
    *facts = std::move(parsed);
    if (error != nullptr) error->clear();
    return HostApplicationFactsVerdict::READY;
}

StoreBackedCallerVisibilityResolverV1::
    StoreBackedCallerVisibilityResolverV1(
        package_transaction::FilePackageStore* store,
        HostApplicationRuntimeFactsResolverV1* hostFactsResolver)
    : store_(store), hostFactsResolver_(hostFactsResolver)
{
}

ApplicationInfoCallerVerdictV1
StoreBackedCallerVisibilityResolverV1::Resolve(int32_t callingUid,
    const std::string& packageName, uint32_t userId,
    package_query::CallerContextV1* caller, std::string* error)
{
    if (caller == nullptr || store_ == nullptr ||
        hostFactsResolver_ == nullptr || packageName.empty() ||
        callingUid < 0) {
        if (error != nullptr) *error = "invalid visibility request";
        return ApplicationInfoCallerVerdictV1::DATA_INCONSISTENT;
    }
    if (userId != 0) {
        if (error != nullptr) *error = "secondary user is not supported in v1";
        return ApplicationInfoCallerVerdictV1::NOT_SUPPORTED;
    }
    caller->callerId = "uid:" + std::to_string(callingUid);
    caller->visibilityScopeDigest =
        Sha256Hex("application-info-scope-v1\n" + caller->callerId +
            "\nuser:" + std::to_string(userId));
    if (callingUid == ROOT_UID || callingUid == SYSTEM_UID) {
        caller->canSeeAllPackages = true;
        caller->visiblePackageNames.clear();
        if (error != nullptr) error->clear();
        return ApplicationInfoCallerVerdictV1::VISIBLE;
    }

    package_transaction::PackageManagementReadV1 state;
    if (!store_->ReadPackageManagementState(
            userId, packageName, &state, error)) {
        return ApplicationInfoCallerVerdictV1::DATA_INCONSISTENT;
    }
    if (!state.canonical.has_value()) {
        if (error != nullptr) *error = "package not found";
        return ApplicationInfoCallerVerdictV1::PACKAGE_NOT_FOUND;
    }
    HostApplicationRuntimeFactsV1 facts;
    const auto verdict = hostFactsResolver_->Resolve(packageName, userId,
        state.canonical->generation, state.canonical->canonicalDigest,
        &facts, error);
    if (verdict == HostApplicationFactsVerdict::PACKAGE_NOT_READY) {
        return ApplicationInfoCallerVerdictV1::PACKAGE_NOT_READY;
    }
    if (verdict == HostApplicationFactsVerdict::DATA_INCONSISTENT) {
        return ApplicationInfoCallerVerdictV1::DATA_INCONSISTENT;
    }
    if (facts.uid != callingUid) {
        if (error != nullptr && error->empty()) {
            *error = "caller is not package owner";
        }
        return ApplicationInfoCallerVerdictV1::DENIED;
    }
    caller->canSeeAllPackages = false;
    caller->visiblePackageNames = {packageName};
    if (error != nullptr) error->clear();
    return ApplicationInfoCallerVerdictV1::VISIBLE;
}

struct ApplicationInfoRuntimeOwnerV1::Impl {
    mutable std::mutex mutex;
    bool started = false;
    std::unique_ptr<package_transaction::FilePackageStore> store;
    std::unique_ptr<FileHostApplicationRuntimeFactsResolverV1> hostFacts;
    std::unique_ptr<StoreBackedCallerVisibilityResolverV1> visibility;
    std::unique_ptr<PosixManagedPathReaderV1> pathReader;
    std::unique_ptr<NoApplicationInfoFaultInjector> fault;
};

ApplicationInfoRuntimeOwnerV1::ApplicationInfoRuntimeOwnerV1()
    : impl_(std::make_unique<Impl>())
{
}

ApplicationInfoRuntimeOwnerV1::~ApplicationInfoRuntimeOwnerV1()
{
    Stop();
}

bool ApplicationInfoRuntimeOwnerV1::Start(
    const ApplicationInfoRuntimeOwnerConfigV1& config, std::string* error)
{
    std::lock_guard<std::mutex> lock(impl_->mutex);
    if (impl_->started) {
        if (error != nullptr) error->clear();
        return true;
    }
    if (!IsAbsoluteRoot(config.packageStoreRoot) ||
        !IsAbsoluteRoot(config.runtimeFactsRoot)) {
        if (error != nullptr) *error = "runtime roots must be absolute";
        return false;
    }
    auto store = std::make_unique<package_transaction::FilePackageStore>(
        config.packageStoreRoot);
    if (!store->OpenReadOnly(error)) return false;
    auto hostFacts =
        std::make_unique<FileHostApplicationRuntimeFactsResolverV1>(
            config.runtimeFactsRoot);
    auto visibility =
        std::make_unique<StoreBackedCallerVisibilityResolverV1>(
            store.get(), hostFacts.get());
    auto pathReader = std::make_unique<PosixManagedPathReaderV1>();
    auto fault = std::make_unique<NoApplicationInfoFaultInjector>();
    if (!ConfigureApplicationInfoRuntimeV1(store.get(), visibility.get(),
            hostFacts.get(), pathReader.get(), fault.get(), error)) {
        return false;
    }
    impl_->store = std::move(store);
    impl_->hostFacts = std::move(hostFacts);
    impl_->visibility = std::move(visibility);
    impl_->pathReader = std::move(pathReader);
    impl_->fault = std::move(fault);
    impl_->started = true;
    if (error != nullptr) error->clear();
    return true;
}

void ApplicationInfoRuntimeOwnerV1::Stop()
{
    std::lock_guard<std::mutex> lock(impl_->mutex);
    if (!impl_->started) return;
    // Clear waits for any in-flight public query before dependencies die.
    ClearApplicationInfoRuntimeV1();
    impl_->fault.reset();
    impl_->pathReader.reset();
    impl_->visibility.reset();
    impl_->hostFacts.reset();
    impl_->store.reset();
    impl_->started = false;
}

bool ApplicationInfoRuntimeOwnerV1::IsStarted() const
{
    std::lock_guard<std::mutex> lock(impl_->mutex);
    return impl_->started;
}

bool StartProductApplicationInfoRuntimeV1(std::string* error)
{
    const char* stateRootValue = std::getenv(FN01_STATE_ROOT_ENV);
    if (stateRootValue == nullptr || stateRootValue[0] == '\0') {
        if (error != nullptr) {
            *error = std::string(FN01_STATE_ROOT_ENV) +
                " is not configured by the product launcher";
        }
        return false;
    }
    const std::string stateRoot(stateRootValue);
    if (!IsAbsoluteRoot(stateRoot)) {
        if (error != nullptr) {
            *error = std::string(FN01_STATE_ROOT_ENV) +
                " must be an absolute state root";
        }
        return false;
    }
    return ProductOwner().Start(
        {stateRoot + STORE_ROOT_SUFFIX, stateRoot + FACTS_ROOT_SUFFIX},
        error);
}

void StopProductApplicationInfoRuntimeV1()
{
    ProductOwner().Stop();
}

}  // namespace oh_adapter::application_info
