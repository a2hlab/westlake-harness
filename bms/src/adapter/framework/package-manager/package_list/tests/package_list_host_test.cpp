#include "package_list_v1.h"

#include <algorithm>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <set>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

namespace {

using oh_adapter::package_list::ListPackagesRequestV1;
using oh_adapter::package_list::ListPackagesResponseV1;
using oh_adapter::package_list::NoPackageListFaultInjector;
using oh_adapter::package_list::PackageCatalogSnapshotSource;
using oh_adapter::package_list::PackageCatalogFailure;
using oh_adapter::package_list::PackageListClock;
using oh_adapter::package_list::PackageListEntropy;
using oh_adapter::package_list::PackageListFaultInjector;
using oh_adapter::package_list::PackageListFilterKind;
using oh_adapter::package_list::PackageListLimitsV1;
using oh_adapter::package_list::PackageListPhase;
using oh_adapter::package_list::PackageListVerdict;
using oh_adapter::package_list::StablePackageListService;
using oh_adapter::package_query::CallerContextV1;
using oh_adapter::package_query::PackageManagementSnapshotV1;

struct TestContext {
    std::ofstream results;
    size_t passed = 0;
    size_t failed = 0;

    explicit TestContext(const std::string& path) : results(path)
    {
        if (!results) {
            std::cerr << "cannot open result path: " << path << "\n";
            std::exit(2);
        }
    }

    void Check(bool condition, const std::string& name,
        const std::string& detail)
    {
        results << "{\"case\":\"" << name << "\",\"status\":\""
                << (condition ? "PASS" : "FAIL") << "\",\"detail\":\""
                << detail << "\"}\n";
        std::cout << (condition ? "PASS " : "FAIL ") << name << " "
                  << detail << "\n";
        if (condition) {
            ++passed;
        } else {
            ++failed;
        }
    }
};

class FakeClock final : public PackageListClock {
public:
    uint64_t NowMillis() const override
    {
        return now_;
    }

    void Advance(uint64_t amount)
    {
        now_ += amount;
    }

private:
    uint64_t now_ = 1000;
};

class DeterministicEntropy final : public PackageListEntropy {
public:
    bool Fill(uint8_t* bytes, size_t size, std::string* error) override
    {
        if (fail_) {
            if (error != nullptr) *error = "INJECTED_ENTROPY_FAILURE";
            return false;
        }
        for (size_t i = 0; i < size; ++i) {
            bytes[i] = static_cast<uint8_t>(
                (serial_ + i * static_cast<uint64_t>(29)) & 0xff);
        }
        ++serial_;
        return true;
    }

    void Fail(bool value)
    {
        fail_ = value;
    }

private:
    uint64_t serial_ = 1;
    bool fail_ = false;
};

class FaultOnce final : public PackageListFaultInjector {
public:
    explicit FaultOnce(PackageListPhase phase) : phase_(phase)
    {
    }

    bool InterruptAfter(PackageListPhase phase) override
    {
        if (!fired_ && phase == phase_) {
            fired_ = true;
            return true;
        }
        return false;
    }

private:
    PackageListPhase phase_;
    bool fired_ = false;
};

class FakeCatalogSource final : public PackageCatalogSnapshotSource {
public:
    explicit FakeCatalogSource(
        std::vector<PackageManagementSnapshotV1> entries)
        : live_(std::move(entries))
    {
    }

    bool Capture(uint32_t userId, std::string* sourceSnapshotId,
        uint64_t* catalogRevision, PackageCatalogFailure* failure,
        std::string* error) override
    {
        *failure = PackageCatalogFailure::NONE;
        if (captureFails_) {
            *failure = PackageCatalogFailure::IO_ERROR;
            if (error != nullptr) *error = "INJECTED_CAPTURE_FAILURE";
            return false;
        }
        *sourceSnapshotId = "source-" + std::to_string(nextSnapshot_++);
        *catalogRevision = revision_;
        snapshots_[*sourceSnapshotId] = live_;
        users_[*sourceSnapshotId] = userId;
        return true;
    }

    bool Read(const std::string& sourceSnapshotId,
        std::vector<PackageManagementSnapshotV1>* entries,
        PackageCatalogFailure* failure, std::string* error) const override
    {
        *failure = PackageCatalogFailure::NONE;
        if (readFails_) {
            *failure = PackageCatalogFailure::IO_ERROR;
            if (error != nullptr) *error = "INJECTED_READ_FAILURE";
            return false;
        }
        const auto item = snapshots_.find(sourceSnapshotId);
        if (item == snapshots_.end()) {
            *failure = PackageCatalogFailure::COMPACTED;
            if (error != nullptr) *error = "SNAPSHOT_COMPACTED";
            return false;
        }
        *entries = item->second;
        return true;
    }

    void Release(const std::string& sourceSnapshotId) override
    {
        snapshots_.erase(sourceSnapshotId);
        users_.erase(sourceSnapshotId);
    }

    void ReplaceGeneration(const std::string& packageName)
    {
        for (auto& entry : live_) {
            if (entry.packageName == packageName) {
                ++entry.generation;
                entry.canonicalDigest =
                    "digest-generation-" + std::to_string(entry.generation);
            }
        }
        ++revision_;
    }

    void MarkRemoving(const std::string& packageName)
    {
        for (auto& entry : live_) {
            if (entry.packageName == packageName) {
                entry.lifecycle = "REMOVING";
                entry.readiness = "NOT_READY";
            }
        }
        ++revision_;
    }

    void CompactAll()
    {
        snapshots_.clear();
        users_.clear();
    }

    void SetCaptureFails(bool value)
    {
        captureFails_ = value;
    }

    void SetReadFails(bool value)
    {
        readFails_ = value;
    }

    void AppendDuplicate()
    {
        live_.push_back(live_.front());
        ++revision_;
    }

private:
    std::vector<PackageManagementSnapshotV1> live_;
    std::map<std::string, std::vector<PackageManagementSnapshotV1>> snapshots_;
    std::map<std::string, uint32_t> users_;
    uint64_t revision_ = 1;
    uint64_t nextSnapshot_ = 1;
    bool captureFails_ = false;
    bool readFails_ = false;
};

PackageManagementSnapshotV1 MakeEntry(
    const std::string& packageName, uint64_t generation)
{
    PackageManagementSnapshotV1 entry;
    entry.packageName = packageName;
    entry.userId = 0;
    entry.userState = "INSTALLED";
    entry.lifecycle = "ACTIVE";
    entry.generation = generation;
    entry.canonicalDigest =
        "digest-generation-" + std::to_string(generation);
    entry.readiness = "READY";
    return entry;
}

std::vector<PackageManagementSnapshotV1> MakeEntries(
    const std::string& packagePrefix, size_t count)
{
    std::vector<PackageManagementSnapshotV1> entries;
    entries.reserve(count);
    for (size_t i = 0; i < count; ++i) {
        entries.push_back(MakeEntry(
            packagePrefix + ".member." + std::to_string(i), i + 1));
    }
    return entries;
}

CallerContextV1 AllCaller(const std::string& identity)
{
    CallerContextV1 caller;
    caller.callerId = identity;
    caller.visibilityScopeDigest = "scope-" + identity;
    caller.canSeeAllPackages = true;
    return caller;
}

ListPackagesRequestV1 FirstRequest(const std::string& requestId,
    uint32_t pageSize, const CallerContextV1& caller)
{
    ListPackagesRequestV1 request;
    request.requestId = requestId;
    request.pageSize = pageSize;
    request.caller = caller;
    return request;
}

ListPackagesRequestV1 NextRequest(const std::string& requestId,
    const ListPackagesRequestV1& first, const std::string& token)
{
    ListPackagesRequestV1 request = first;
    request.requestId = requestId;
    request.pageToken = token;
    return request;
}

struct ServiceHarness {
    FakeCatalogSource source;
    FakeClock clock;
    DeterministicEntropy entropy;
    NoPackageListFaultInjector noFault;
    PackageListLimitsV1 limits;
    std::vector<uint8_t> signingKey;
    std::string epoch;
    std::unique_ptr<StablePackageListService> service;

    ServiceHarness(std::vector<PackageManagementSnapshotV1> entries,
        uint32_t maxPageSize, uint64_t ttl, std::string processEpoch)
        : source(std::move(entries)),
          signingKey(32, static_cast<uint8_t>(0x6d)),
          epoch(std::move(processEpoch))
    {
        limits.maxPageSize = maxPageSize;
        limits.maxFilterBytes = maxPageSize * 64;
        limits.maxTokenBytes = maxPageSize * 128;
        limits.tokenEntropyBytes = maxPageSize + 16;
        limits.maxCatalogEntries = maxPageSize * 4;
        limits.maxActiveSnapshotsPerCaller = maxPageSize;
        limits.tokenTtlMillis = ttl;
        Reset(&noFault);
    }

    void Reset(PackageListFaultInjector* fault)
    {
        service = std::make_unique<StablePackageListService>(&source, &clock,
            &entropy, fault, limits, signingKey, epoch);
    }
};

std::vector<PackageManagementSnapshotV1> Drain(
    StablePackageListService* service, const ListPackagesRequestV1& first,
    ListPackagesResponseV1 response, std::vector<ListPackagesResponseV1>* pages)
{
    std::vector<PackageManagementSnapshotV1> result;
    while (true) {
        pages->push_back(response);
        result.insert(
            result.end(), response.entries.begin(), response.entries.end());
        if (response.verdict != PackageListVerdict::READY ||
            !response.nextPageToken.has_value()) {
            break;
        }
        response = service->ListPackages(NextRequest(
            first.requestId + "-next-" + std::to_string(pages->size()),
            first, *response.nextPageToken));
    }
    return result;
}

bool SameEntrySet(const std::vector<PackageManagementSnapshotV1>& first,
    const std::vector<PackageManagementSnapshotV1>& second)
{
    if (first.size() != second.size()) return false;
    for (size_t i = 0; i < first.size(); ++i) {
        if (first[i].packageName != second[i].packageName ||
            first[i].generation != second[i].generation ||
            first[i].canonicalDigest != second[i].canonicalDigest) {
            return false;
        }
    }
    return true;
}

bool StableMetadata(const std::vector<ListPackagesResponseV1>& pages)
{
    if (pages.empty()) return false;
    const auto& first = pages.front();
    for (const auto& page : pages) {
        if (page.verdict != PackageListVerdict::READY ||
            page.snapshotId != first.snapshotId ||
            page.catalogRevision != first.catalogRevision ||
            page.totalCount != first.totalCount ||
            page.pageEntryCount != page.entries.size()) {
            return false;
        }
    }
    return true;
}

void RunCoreCases(TestContext* test, const std::string& prefix,
    size_t memberCount, uint32_t pageSize)
{
    const auto oracle = MakeEntries(prefix, memberCount);
    auto sortedOracle = oracle;
    std::sort(sortedOracle.begin(), sortedOracle.end(),
        [](const auto& first, const auto& second) {
            return first.packageName < second.packageName;
        });
    ServiceHarness harness(
        oracle, pageSize + static_cast<uint32_t>(memberCount), 10000,
        "process-core");
    const auto first =
        FirstRequest("core-first", pageSize, AllCaller("caller-core"));
    std::vector<ListPackagesResponseV1> pages;
    const auto merged = Drain(
        harness.service.get(), first, harness.service->ListPackages(first),
        &pages);
    test->Check(SameEntrySet(sortedOracle, merged), "P01_COMPLETE_SET",
        "分页合并与创建时可见集合完全相等");
    test->Check(StableMetadata(pages), "P01_STABLE_METADATA",
        "snapshotId/catalogRevision/totalCount/pageEntryCount 跨页稳定");
    std::set<std::string> names;
    for (const auto& entry : merged) names.insert(entry.packageName);
    test->Check(names.size() == merged.size(), "P01_NO_DUPLICATE",
        "分页没有重复 package identity");

    auto replayHarness = ServiceHarness(
        oracle, pageSize + static_cast<uint32_t>(memberCount), 10000,
        "process-replay");
    const auto replayFirst =
        FirstRequest("replay-first", pageSize, AllCaller("caller-replay"));
    const auto replayPage =
        replayHarness.service->ListPackages(replayFirst);
    const auto token = *replayPage.nextPageToken;
    const auto continuation = NextRequest(
        "replay-next", replayFirst, token);
    const auto replayOne =
        replayHarness.service->ListPackages(continuation);
    const auto replayTwo =
        replayHarness.service->ListPackages(continuation);
    test->Check(
        replayOne.verdict == PackageListVerdict::READY &&
            replayTwo.verdict == PackageListVerdict::READY &&
            replayOne.snapshotId == replayTwo.snapshotId &&
            SameEntrySet(replayOne.entries, replayTwo.entries) &&
            replayOne.nextPageToken == replayTwo.nextPageToken,
        "P02_TOKEN_REPLAY", "同 token 重放返回同一冻结页且不建第二 snapshot");
}

void RunMutationCases(TestContext* test, const std::string& prefix,
    size_t memberCount, uint32_t pageSize)
{
    const auto fixture = MakeEntries(prefix, memberCount);
    ServiceHarness harness(
        fixture, pageSize + static_cast<uint32_t>(memberCount), 10000,
        "process-mutation");
    const auto caller = AllCaller("caller-mutation");
    const auto oldRequest =
        FirstRequest("old-replacement", pageSize, caller);
    const auto oldFirst = harness.service->ListPackages(oldRequest);
    const std::string replacedName = fixture[memberCount / 2].packageName;
    const uint64_t oldGeneration = fixture[memberCount / 2].generation;
    harness.source.ReplaceGeneration(replacedName);

    std::vector<ListPackagesResponseV1> oldPages;
    const auto oldMerged = Drain(
        harness.service.get(), oldRequest, oldFirst, &oldPages);
    const auto oldEntry = std::find_if(oldMerged.begin(), oldMerged.end(),
        [&](const auto& entry) { return entry.packageName == replacedName; });
    const auto newRequest =
        FirstRequest("new-replacement", pageSize, caller);
    std::vector<ListPackagesResponseV1> newPages;
    const auto newMerged = Drain(harness.service.get(), newRequest,
        harness.service->ListPackages(newRequest), &newPages);
    const auto newEntry = std::find_if(newMerged.begin(), newMerged.end(),
        [&](const auto& entry) { return entry.packageName == replacedName; });
    test->Check(
        oldEntry != oldMerged.end() && newEntry != newMerged.end() &&
            oldEntry->generation == oldGeneration &&
            newEntry->generation == oldGeneration + 1 &&
            oldPages.front().catalogRevision <
                newPages.front().catalogRevision,
        "P01_REPLACEMENT_FREEZE",
        "独立 mutation fixture 后旧 snapshot 不混代且新 snapshot 取新 generation");

    const auto removingOldRequest =
        FirstRequest("old-removing", pageSize, caller);
    const auto removingOldFirst =
        harness.service->ListPackages(removingOldRequest);
    const std::string removingName = fixture[memberCount / 3].packageName;
    harness.source.MarkRemoving(removingName);
    std::vector<ListPackagesResponseV1> removingOldPages;
    const auto removingOldMerged = Drain(harness.service.get(),
        removingOldRequest, removingOldFirst, &removingOldPages);
    const auto removingNewRequest =
        FirstRequest("new-removing", pageSize, caller);
    std::vector<ListPackagesResponseV1> removingNewPages;
    const auto removingNewMerged = Drain(harness.service.get(),
        removingNewRequest,
        harness.service->ListPackages(removingNewRequest),
        &removingNewPages);
    const auto oldCount =
        std::count_if(removingOldMerged.begin(), removingOldMerged.end(),
            [&](const auto& entry) {
                return entry.packageName == removingName;
            });
    const auto newCount =
        std::count_if(removingNewMerged.begin(), removingNewMerged.end(),
            [&](const auto& entry) {
                return entry.packageName == removingName;
            });
    test->Check(
        oldCount == 1 && newCount == 0 &&
            removingOldPages.front().totalCount == memberCount &&
            removingNewPages.front().totalCount + 1 == memberCount,
        "P01_REMOVING_FREEZE",
        "旧 snapshot 保留冻结 entry/count；新 snapshot 排除 REMOVING 并同步 count");
}

void RunVisibilityAndFilterCases(TestContext* test,
    const std::string& prefix, size_t memberCount, uint32_t pageSize)
{
    const auto fixture = MakeEntries(prefix, memberCount);
    ServiceHarness harness(
        fixture, pageSize + static_cast<uint32_t>(memberCount), 10000,
        "process-filter");
    CallerContextV1 restricted;
    restricted.callerId = "caller-restricted";
    restricted.visibilityScopeDigest = "scope-restricted";
    restricted.canSeeAllPackages = false;
    for (size_t i = 0; i < fixture.size(); i += 2) {
        restricted.visiblePackageNames.push_back(fixture[i].packageName);
    }
    auto visibleRequest =
        FirstRequest("visible-only", pageSize, restricted);
    std::vector<ListPackagesResponseV1> visiblePages;
    const auto visible = Drain(harness.service.get(), visibleRequest,
        harness.service->ListPackages(visibleRequest), &visiblePages);
    const bool allAuthorized =
        std::all_of(visible.begin(), visible.end(), [&](const auto& entry) {
            return std::find(restricted.visiblePackageNames.begin(),
                       restricted.visiblePackageNames.end(),
                       entry.packageName) !=
                restricted.visiblePackageNames.end();
        });
    test->Check(
        allAuthorized &&
            visible.size() == restricted.visiblePackageNames.size(),
        "P02_CALLER_VISIBILITY", "不可见 package 未进入 snapshot 或 count");

    auto filterRequest =
        FirstRequest("prefix-filter", pageSize, AllCaller("caller-filter"));
    filterRequest.filter.kind = PackageListFilterKind::PACKAGE_NAME_PREFIX;
    filterRequest.filter.value = prefix + ".member.1";
    std::vector<ListPackagesResponseV1> filterPages;
    const auto filtered = Drain(harness.service.get(), filterRequest,
        harness.service->ListPackages(filterRequest), &filterPages);
    const bool allMatch =
        !filtered.empty() &&
        std::all_of(filtered.begin(), filtered.end(), [&](const auto& entry) {
            return entry.packageName.compare(
                       0, filterRequest.filter.value.size(),
                       filterRequest.filter.value) == 0;
        });
    test->Check(allMatch && filterPages.front().totalCount == filtered.size(),
        "P02_FILTER_BOUND", "filter 由 snapshot owner 绑定并冻结");
}

void RunNegativeCases(TestContext* test, const std::string& prefix,
    size_t memberCount, uint32_t pageSize)
{
    const auto fixture = MakeEntries(prefix, memberCount);
    ServiceHarness harness(
        fixture, pageSize + static_cast<uint32_t>(memberCount), 10000,
        "process-negative");
    const auto caller = AllCaller("caller-negative");
    auto first = FirstRequest("negative-first", pageSize, caller);
    const auto firstResponse = harness.service->ListPackages(first);
    const std::string token = *firstResponse.nextPageToken;

    auto malformed = NextRequest("malformed", first, "not-a-token");
    test->Check(
        harness.service->ListPackages(malformed).verdict ==
            PackageListVerdict::INVALID_PAGE_TOKEN,
        "N01_MALFORMED_TOKEN", "非法 token typed reject");

    auto emptyToken = NextRequest("empty-token", first, "");
    test->Check(
        harness.service->ListPackages(emptyToken).verdict ==
            PackageListVerdict::INVALID_PAGE_TOKEN,
        "N01_EMPTY_TOKEN", "显式空 token 不退化为首次调用");

    std::string tamperedToken = token;
    tamperedToken.back() =
        tamperedToken.back() == 'a' ? 'b' : 'a';
    auto tampered = NextRequest("tampered", first, tamperedToken);
    test->Check(
        harness.service->ListPackages(tampered).verdict ==
            PackageListVerdict::INVALID_PAGE_TOKEN,
        "N01_TAMPERED_TOKEN", "MAC 不匹配 token typed reject");

    auto crossCaller = NextRequest("cross-caller", first, token);
    crossCaller.caller = AllCaller("caller-foreign");
    const auto crossCallerResponse =
        harness.service->ListPackages(crossCaller);
    test->Check(
        crossCallerResponse.verdict ==
                PackageListVerdict::PAGE_TOKEN_CALLER_MISMATCH &&
            crossCallerResponse.entries.empty() &&
            crossCallerResponse.totalCount == 0,
        "N01_CROSS_CALLER", "cross-caller token 零集合泄漏");

    auto changedSize = NextRequest("changed-size", first, token);
    ++changedSize.pageSize;
    test->Check(
        harness.service->ListPackages(changedSize).verdict ==
            PackageListVerdict::PAGE_TOKEN_CONTEXT_MISMATCH,
        "N02_PAGE_SIZE_MISMATCH", "token 不信任 caller 改写 pageSize");

    auto changedFilter = NextRequest("changed-filter", first, token);
    changedFilter.filter.kind =
        PackageListFilterKind::PACKAGE_NAME_PREFIX;
    changedFilter.filter.value = prefix;
    test->Check(
        harness.service->ListPackages(changedFilter).verdict ==
            PackageListVerdict::PAGE_TOKEN_CONTEXT_MISMATCH,
        "N02_FILTER_MISMATCH", "token 不信任 caller 改写 filter");

    auto tooLarge = first;
    tooLarge.requestId = "too-large";
    tooLarge.pageSize = harness.limits.maxPageSize + 1;
    test->Check(
        harness.service->ListPackages(tooLarge).verdict ==
            PackageListVerdict::NOT_SUPPORTED,
        "N01_PAGE_SIZE_LIMIT", "超限 pageSize typed reject");

    auto unsupportedFilter = first;
    unsupportedFilter.requestId = "unsupported-filter";
    unsupportedFilter.filter.kind =
        static_cast<PackageListFilterKind>(999);
    test->Check(
        harness.service->ListPackages(unsupportedFilter).verdict ==
            PackageListVerdict::NOT_SUPPORTED,
        "N01_UNSUPPORTED_FILTER", "unknown filter typed reject");

    auto unsupportedUser = first;
    unsupportedUser.requestId = "unsupported-user";
    unsupportedUser.userId = 17;
    test->Check(
        harness.service->ListPackages(unsupportedUser).verdict ==
            PackageListVerdict::NOT_SUPPORTED,
        "N02_USER_BOUNDARY", "非 primary user typed reject");

    ServiceHarness duplicateHarness(
        fixture, pageSize + static_cast<uint32_t>(memberCount), 10000,
        "process-duplicate");
    duplicateHarness.source.AppendDuplicate();
    const auto duplicateResponse =
        duplicateHarness.service->ListPackages(FirstRequest(
            "duplicate", pageSize, AllCaller("caller-duplicate")));
    test->Check(
        duplicateResponse.verdict ==
                PackageListVerdict::DATA_INCONSISTENT &&
            duplicateResponse.entries.empty(),
        "N02_DUPLICATE_IDENTITY", "同 revision 重复 package identity fail closed");

    ServiceHarness snapshotLimitHarness(
        fixture, pageSize + static_cast<uint32_t>(memberCount), 10000,
        "process-snapshot-limit");
    snapshotLimitHarness.limits.maxActiveSnapshotsPerCaller = 1;
    snapshotLimitHarness.Reset(&snapshotLimitHarness.noFault);
    const auto limitCaller = AllCaller("caller-snapshot-limit");
    const auto admitted = snapshotLimitHarness.service->ListPackages(
        FirstRequest("snapshot-admitted", pageSize, limitCaller));
    const auto limited = snapshotLimitHarness.service->ListPackages(
        FirstRequest("snapshot-limited", pageSize, limitCaller));
    test->Check(
        admitted.verdict == PackageListVerdict::READY &&
            limited.verdict == PackageListVerdict::NOT_SUPPORTED &&
            limited.reason == "ACTIVE_SNAPSHOT_LIMIT_EXCEEDED",
        "N01_ACTIVE_SNAPSHOT_LIMIT",
        "caller active snapshot 数受版本化 limits 约束");

    ServiceHarness catalogLimitHarness(
        fixture, pageSize + static_cast<uint32_t>(memberCount), 10000,
        "process-catalog-limit");
    catalogLimitHarness.limits.maxCatalogEntries =
        static_cast<uint32_t>(memberCount - 1);
    catalogLimitHarness.Reset(&catalogLimitHarness.noFault);
    const auto catalogLimited =
        catalogLimitHarness.service->ListPackages(FirstRequest(
            "catalog-limited", pageSize,
            AllCaller("caller-catalog-limit")));
    test->Check(
        catalogLimited.verdict == PackageListVerdict::NOT_SUPPORTED &&
            catalogLimited.reason == "CATALOG_SIZE_NOT_SUPPORTED",
        "N01_CATALOG_SIZE_LIMIT",
        "catalog member count 超限时 typed reject 且无 snapshot publication");
}

void RunFailureCases(TestContext* test, const std::string& prefix,
    size_t memberCount, uint32_t pageSize)
{
    const auto fixture = MakeEntries(prefix, memberCount);

    ServiceHarness expiryHarness(
        fixture, pageSize + static_cast<uint32_t>(memberCount), 5000,
        "process-expiry");
    const auto expiryFirst =
        FirstRequest("expiry-first", pageSize, AllCaller("caller-expiry"));
    const auto expiryResponse =
        expiryHarness.service->ListPackages(expiryFirst);
    expiryHarness.clock.Advance(expiryHarness.limits.tokenTtlMillis + 1);
    test->Check(
        expiryHarness.service->ListPackages(NextRequest("expiry-next",
            expiryFirst, *expiryResponse.nextPageToken)).verdict ==
            PackageListVerdict::PAGE_TOKEN_EXPIRED,
        "F01_TOKEN_EXPIRED", "过期 token 统一 PAGE_TOKEN_EXPIRED");

    ServiceHarness restartHarness(
        fixture, pageSize + static_cast<uint32_t>(memberCount), 10000,
        "process-before-restart");
    const auto restartFirst = FirstRequest(
        "restart-first", pageSize, AllCaller("caller-restart"));
    const auto restartResponse =
        restartHarness.service->ListPackages(restartFirst);
    restartHarness.service.reset();
    restartHarness.epoch = "process-after-restart";
    restartHarness.Reset(&restartHarness.noFault);
    const auto oldTokenAfterRestart =
        restartHarness.service->ListPackages(NextRequest("restart-old-token",
            restartFirst, *restartResponse.nextPageToken));
    auto newFirst = restartFirst;
    newFirst.requestId = "restart-new-snapshot";
    const auto newSnapshot =
        restartHarness.service->ListPackages(newFirst);
    test->Check(
        oldTokenAfterRestart.verdict ==
                PackageListVerdict::PAGE_TOKEN_EXPIRED &&
            newSnapshot.verdict == PackageListVerdict::READY &&
            newSnapshot.snapshotId != restartResponse.snapshotId,
        "F02_RESTART_EPOCH", "旧 token 过期且新首次调用建立新 snapshot");

    ServiceHarness compactHarness(
        fixture, pageSize + static_cast<uint32_t>(memberCount), 10000,
        "process-compact");
    const auto compactFirst =
        FirstRequest("compact-first", pageSize, AllCaller("caller-compact"));
    const auto compactResponse =
        compactHarness.service->ListPackages(compactFirst);
    compactHarness.source.CompactAll();
    const auto compacted =
        compactHarness.service->ListPackages(NextRequest("compact-next",
            compactFirst, *compactResponse.nextPageToken));
    test->Check(
        compacted.verdict == PackageListVerdict::CATALOG_COMPACTED &&
            compacted.entries.empty(),
        "F01_CATALOG_COMPACTED", "immutable revision 丢失 typed fail closed");

    ServiceHarness captureHarness(
        fixture, pageSize + static_cast<uint32_t>(memberCount), 10000,
        "process-capture-fail");
    captureHarness.source.SetCaptureFails(true);
    test->Check(
        captureHarness.service->ListPackages(FirstRequest(
            "capture-fail", pageSize,
            AllCaller("caller-capture-fail"))).verdict ==
            PackageListVerdict::CATALOG_READ_FAILED,
        "F01_CAPTURE_FAILURE", "catalog capture failure typed fail closed");

    ServiceHarness readHarness(
        fixture, pageSize + static_cast<uint32_t>(memberCount), 10000,
        "process-read-fail");
    const auto readFirst =
        FirstRequest("read-first", pageSize, AllCaller("caller-read-fail"));
    const auto readFirstResponse =
        readHarness.service->ListPackages(readFirst);
    readHarness.source.SetReadFails(true);
    test->Check(
        readHarness.service->ListPackages(NextRequest("read-next",
            readFirst, *readFirstResponse.nextPageToken)).verdict ==
            PackageListVerdict::CATALOG_READ_FAILED,
        "F01_READBACK_FAILURE",
        "readback I/O failure 不与 compaction 混为同一 typed code");

    ServiceHarness entropyHarness(
        fixture, pageSize + static_cast<uint32_t>(memberCount), 10000,
        "process-entropy-fail");
    entropyHarness.entropy.Fail(true);
    test->Check(
        entropyHarness.service->ListPackages(FirstRequest(
            "entropy-fail", pageSize,
            AllCaller("caller-entropy-fail"))).verdict ==
            PackageListVerdict::TOKEN_STORE_FAILED,
        "F01_TOKEN_ENTROPY_FAILURE", "token entropy/store failure typed fail closed");

    for (const auto& phase : {
             PackageListPhase::CATALOG_CAPTURED,
             PackageListPhase::SNAPSHOT_FILTERED,
             PackageListPhase::TOKEN_STORED,
             PackageListPhase::RESPONSE_SERIALIZED }) {
        ServiceHarness faultHarness(
            fixture, pageSize + static_cast<uint32_t>(memberCount), 10000,
            "process-fault-" + std::to_string(static_cast<int>(phase)));
        FaultOnce fault(phase);
        faultHarness.Reset(&fault);
        const auto response =
            faultHarness.service->ListPackages(FirstRequest(
                "phase-fault-" + std::to_string(static_cast<int>(phase)),
                pageSize, AllCaller("caller-phase-fault")));
        const bool expected =
            phase == PackageListPhase::TOKEN_STORED
            ? response.verdict == PackageListVerdict::TOKEN_STORE_FAILED
            : response.verdict == PackageListVerdict::INTERRUPTED_RETRY;
        test->Check(expected,
            "F01_PHASE_" + std::to_string(static_cast<int>(phase)),
            "phase fault typed fail closed");
    }
}

uint64_t ParsePositive(const char* value, const char* label)
{
    std::string text(value == nullptr ? "" : value);
    if (text.empty() ||
        !std::all_of(text.begin(), text.end(), [](char ch) {
            return ch >= '0' && ch <= '9';
        })) {
        std::cerr << label << " must be a positive integer\n";
        std::exit(2);
    }
    const uint64_t parsed = std::stoull(text);
    if (parsed == 0) {
        std::cerr << label << " must be non-zero\n";
        std::exit(2);
    }
    return parsed;
}

}  // namespace

int main(int argc, char** argv)
{
    if (argc != 5) {
        std::cerr << "usage: package_list_host_test RESULTS_JSONL "
                     "PACKAGE_PREFIX MEMBER_COUNT PAGE_SIZE\n";
        return 2;
    }
    const std::string resultsPath = argv[1];
    const std::string packagePrefix = argv[2];
    const uint64_t memberCount64 = ParsePositive(argv[3], "MEMBER_COUNT");
    const uint64_t pageSize64 = ParsePositive(argv[4], "PAGE_SIZE");
    if (packagePrefix.empty() || memberCount64 > 100000 ||
        pageSize64 > 100000 ||
        memberCount64 < pageSize64 * 3 + 2) {
        std::cerr << "fixture must be non-empty, bounded, and span at least "
                     "three full pages plus a tail\n";
        return 2;
    }
    const size_t memberCount = static_cast<size_t>(memberCount64);
    const uint32_t pageSize = static_cast<uint32_t>(pageSize64);

    TestContext test(resultsPath);
    RunCoreCases(&test, packagePrefix, memberCount, pageSize);
    RunMutationCases(&test, packagePrefix, memberCount, pageSize);
    RunVisibilityAndFilterCases(
        &test, packagePrefix, memberCount, pageSize);
    RunNegativeCases(&test, packagePrefix, memberCount, pageSize);
    RunFailureCases(&test, packagePrefix, memberCount, pageSize);
    std::cout << "SUMMARY passed=" << test.passed
              << " failed=" << test.failed << "\n";
    return test.failed == 0 ? 0 : 1;
}
