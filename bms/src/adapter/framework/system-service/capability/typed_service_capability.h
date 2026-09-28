#ifndef OH_ADAPTER_TYPED_SERVICE_CAPABILITY_H
#define OH_ADAPTER_TYPED_SERVICE_CAPABILITY_H

#include <cstdint>
#include <mutex>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace oh_adapter {
namespace service {

enum class ServicePlacement {
    LOCAL_ADAPTER,
    OH_DIRECT,
    PRIVILEGED_BROKER,
    EXPLICIT_UNSUPPORTED,
};

enum class LookupStatus {
    IN_FLIGHT,
    BOUND,
    ABSENT,
    DENIED,
    UNKNOWN_METHOD,
    SCHEMA_MISMATCH,
    UNSUPPORTED,
    STALE_GENERATION,
    TIMEOUT,
    DEAD_PEER,
    DUPLICATE_REQUEST,
};

struct CallerIdentity {
    int32_t uid = -1;
    int32_t pid = -1;
    int32_t user_id = -1;
    uint64_t process_generation = 0;
};

struct CapabilitySpec {
    std::string service_name;
    std::string descriptor;
    std::string schema_hash;
    ServicePlacement placement = ServicePlacement::EXPLICIT_UNSUPPORTED;
    std::unordered_set<std::string> methods;
    bool construction_critical = false;
    bool death_aware = false;
    int64_t timeout_ns = 0;
};

struct LookupRequest {
    std::string request_id;
    std::string service_name;
    std::string descriptor;
    std::string schema_hash;
    std::string method;
    CallerIdentity caller;
    int64_t now_ns = 0;
};

struct LookupReceipt {
    std::string request_id;
    std::string service_name;
    std::string descriptor;
    std::string schema_hash;
    std::string method;
    ServicePlacement placement = ServicePlacement::EXPLICIT_UNSUPPORTED;
    uint64_t endpoint_generation = 0;
    LookupStatus status = LookupStatus::ABSENT;
    std::string reason;
};

/**
 * Typed, per-capability Fn11 construction/lookup owner model.
 *
 * There is deliberately no wildcard/default route. Every service must carry
 * its own descriptor, schema, method set, placement, timeout and death policy.
 */
class TypedServiceCapabilityRegistry {
public:
    bool registerCapability(const CapabilitySpec& spec);
    bool publishEndpoint(const std::string& service_name,
                         const std::string& descriptor,
                         const std::string& schema_hash,
                         ServicePlacement placement,
                         uint64_t endpoint_generation);
    bool endpointDied(const std::string& service_name,
                      uint64_t endpoint_generation);

    LookupReceipt beginLookup(const LookupRequest& request);
    LookupReceipt completeLookup(const std::string& request_id,
                                 uint64_t endpoint_generation,
                                 int64_t now_ns);
    void expire(int64_t now_ns);

    bool allConstructionCriticalReady() const;
    std::vector<LookupReceipt> receipts() const;

private:
    struct Endpoint {
        uint64_t generation = 0;
        bool alive = false;
    };

    struct InFlight {
        LookupReceipt receipt;
        CallerIdentity caller;
        int64_t deadline_ns = 0;
    };

    mutable std::mutex mutex_;
    std::unordered_map<std::string, CapabilitySpec> specs_;
    std::unordered_map<std::string, Endpoint> endpoints_;
    std::unordered_map<std::string, InFlight> in_flight_;
    std::unordered_set<std::string> seen_request_ids_;
    std::vector<LookupReceipt> receipts_;

    LookupReceipt terminal(const LookupRequest& request,
                           LookupStatus status,
                           const std::string& reason,
                           ServicePlacement placement,
                           uint64_t endpoint_generation);
};

}  // namespace service
}  // namespace oh_adapter

#endif  // OH_ADAPTER_TYPED_SERVICE_CAPABILITY_H
