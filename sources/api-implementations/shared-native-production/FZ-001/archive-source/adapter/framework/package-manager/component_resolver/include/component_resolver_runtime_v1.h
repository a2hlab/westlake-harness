#ifndef OH_ADAPTER_COMPONENT_RESOLVER_RUNTIME_V1_H
#define OH_ADAPTER_COMPONENT_RESOLVER_RUNTIME_V1_H

#include "component_resolver_v1.h"

#include <cstdint>
#include <memory>
#include <string>

namespace oh_adapter::component_resolver {

class CallerResolveContextProviderV1 {
public:
    virtual ~CallerResolveContextProviderV1() = default;
    virtual bool Resolve(int32_t callingUid, uint32_t userId,
        CallerResolveContextV1* caller, std::string* error) = 0;
};

struct ComponentResolverRuntimeConfigV1 {
    std::string packageStoreRoot;
    std::string componentIndexPath;
    std::string callerScopeRoot;
};

class FileComponentCatalogProviderV1 final
    : public ComponentCatalogProviderV1 {
public:
    explicit FileComponentCatalogProviderV1(std::string indexPath);
    bool Read(ComponentCatalogV1* catalog, std::string* indexDigest,
        std::string* error) override;

private:
    std::string indexPath_;
};

class StorePackageGuardReaderV1 final : public PackageGuardReaderV1 {
public:
    explicit StorePackageGuardReaderV1(
        package_transaction::FilePackageStore* store);
    bool Read(uint32_t userId, const std::string& packageName,
        PackageGuardV1* guard, std::string* error) override;

private:
    package_transaction::FilePackageStore* store_;
};

class FileCallerResolveContextProviderV1 final
    : public CallerResolveContextProviderV1 {
public:
    explicit FileCallerResolveContextProviderV1(std::string scopeRoot);
    bool Resolve(int32_t callingUid, uint32_t userId,
        CallerResolveContextV1* caller, std::string* error) override;

private:
    std::string scopeRoot_;
};

class ComponentResolverRuntimeOwnerV1 {
public:
    ComponentResolverRuntimeOwnerV1();
    ~ComponentResolverRuntimeOwnerV1();
    ComponentResolverRuntimeOwnerV1(const ComponentResolverRuntimeOwnerV1&) =
        delete;
    ComponentResolverRuntimeOwnerV1& operator=(
        const ComponentResolverRuntimeOwnerV1&) = delete;

    bool Start(const ComponentResolverRuntimeConfigV1& config,
        std::string* error);
    void Stop();
    bool IsStarted() const;

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

bool ConfigureComponentResolverRuntimeV1(
    ComponentCatalogProviderV1* catalogProvider,
    PackageGuardReaderV1* guardReader,
    CallerResolveContextProviderV1* callerProvider,
    ResolveFaultInjectorV1* faultInjector, std::string* error);
void ClearComponentResolverRuntimeV1();

std::string QueryComponentResolverRuntimeJsonV1(
    ComponentResolveRequestV1 request, int32_t callingUid);

bool StartProductComponentResolverRuntimeV1(std::string* error);
void StopProductComponentResolverRuntimeV1();

}  // namespace oh_adapter::component_resolver

#endif  // OH_ADAPTER_COMPONENT_RESOLVER_RUNTIME_V1_H
