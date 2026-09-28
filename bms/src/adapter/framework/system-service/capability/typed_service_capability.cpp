#include "typed_service_capability.h"

#include <utility>

namespace oh_adapter {
namespace service {

bool TypedServiceCapabilityRegistry::registerCapability(
    const CapabilitySpec& spec) {
    if (spec.service_name.empty() || spec.descriptor.empty() ||
        spec.schema_hash.empty() || spec.timeout_ns <= 0 ||
        (spec.placement != ServicePlacement::EXPLICIT_UNSUPPORTED &&
         spec.methods.empty()) ||
        (spec.placement == ServicePlacement::PRIVILEGED_BROKER &&
         !spec.death_aware)) {
        return false;
    }
    std::lock_guard<std::mutex> lock(mutex_);
    return specs_.emplace(spec.service_name, spec).second;
}

bool TypedServiceCapabilityRegistry::publishEndpoint(
    const std::string& service_name,
    const std::string& descriptor,
    const std::string& schema_hash,
    ServicePlacement placement,
    uint64_t endpoint_generation) {
    if (endpoint_generation == 0) {
        return false;
    }
    std::lock_guard<std::mutex> lock(mutex_);
    auto spec_it = specs_.find(service_name);
    if (spec_it == specs_.end() ||
        spec_it->second.placement == ServicePlacement::EXPLICIT_UNSUPPORTED ||
        spec_it->second.descriptor != descriptor ||
        spec_it->second.schema_hash != schema_hash ||
        spec_it->second.placement != placement) {
        return false;
    }
    auto endpoint_it = endpoints_.find(service_name);
    if (endpoint_it != endpoints_.end() &&
        endpoint_generation <= endpoint_it->second.generation) {
        return false;
    }
    endpoints_[service_name] = Endpoint{endpoint_generation, true};
    return true;
}

bool TypedServiceCapabilityRegistry::endpointDied(
    const std::string& service_name,
    uint64_t endpoint_generation) {
    std::lock_guard<std::mutex> lock(mutex_);
    auto endpoint_it = endpoints_.find(service_name);
    if (endpoint_it == endpoints_.end() ||
        endpoint_it->second.generation != endpoint_generation ||
        !endpoint_it->second.alive) {
        return false;
    }
    endpoint_it->second.alive = false;
    for (auto it = in_flight_.begin(); it != in_flight_.end();) {
        if (it->second.receipt.service_name == service_name &&
            it->second.receipt.endpoint_generation == endpoint_generation) {
            LookupReceipt receipt = it->second.receipt;
            receipt.status = LookupStatus::DEAD_PEER;
            receipt.reason = "DEAD_PEER";
            receipts_.push_back(receipt);
            it = in_flight_.erase(it);
        } else {
            ++it;
        }
    }
    return true;
}

LookupReceipt TypedServiceCapabilityRegistry::beginLookup(
    const LookupRequest& request) {
    std::lock_guard<std::mutex> lock(mutex_);
    if (request.request_id.empty() ||
        !seen_request_ids_.insert(request.request_id).second) {
        return terminal(request, LookupStatus::DUPLICATE_REQUEST,
                        "DUPLICATE_REQUEST",
                        ServicePlacement::EXPLICIT_UNSUPPORTED, 0);
    }
    if (request.caller.uid < 0 || request.caller.pid < 0 ||
        request.caller.user_id < 0 ||
        request.caller.process_generation == 0) {
        return terminal(request, LookupStatus::DENIED, "INVALID_CALLER",
                        ServicePlacement::EXPLICIT_UNSUPPORTED, 0);
    }

    auto spec_it = specs_.find(request.service_name);
    if (spec_it == specs_.end()) {
        return terminal(request, LookupStatus::ABSENT, "ABSENT",
                        ServicePlacement::EXPLICIT_UNSUPPORTED, 0);
    }
    const CapabilitySpec& spec = spec_it->second;
    if (spec.placement == ServicePlacement::EXPLICIT_UNSUPPORTED) {
        return terminal(request, LookupStatus::UNSUPPORTED, "UNSUPPORTED",
                        spec.placement, 0);
    }
    if (request.descriptor != spec.descriptor ||
        request.schema_hash != spec.schema_hash) {
        return terminal(request, LookupStatus::SCHEMA_MISMATCH,
                        "SCHEMA_MISMATCH", spec.placement, 0);
    }
    if (!spec.methods.count(request.method)) {
        return terminal(request, LookupStatus::UNKNOWN_METHOD,
                        "UNKNOWN_METHOD", spec.placement, 0);
    }
    auto endpoint_it = endpoints_.find(request.service_name);
    if (endpoint_it == endpoints_.end() || !endpoint_it->second.alive) {
        return terminal(request, LookupStatus::ABSENT,
                        "ENDPOINT_ABSENT", spec.placement, 0);
    }

    LookupReceipt receipt;
    receipt.request_id = request.request_id;
    receipt.service_name = request.service_name;
    receipt.descriptor = request.descriptor;
    receipt.schema_hash = request.schema_hash;
    receipt.method = request.method;
    receipt.placement = spec.placement;
    receipt.endpoint_generation = endpoint_it->second.generation;
    receipt.status = LookupStatus::IN_FLIGHT;
    receipt.reason = "IN_FLIGHT";
    in_flight_.emplace(
        request.request_id,
        InFlight{receipt, request.caller, request.now_ns + spec.timeout_ns});
    return receipt;
}

LookupReceipt TypedServiceCapabilityRegistry::completeLookup(
    const std::string& request_id,
    uint64_t endpoint_generation,
    int64_t now_ns) {
    std::lock_guard<std::mutex> lock(mutex_);
    auto request_it = in_flight_.find(request_id);
    if (request_it == in_flight_.end()) {
        LookupReceipt receipt;
        receipt.request_id = request_id;
        receipt.status = LookupStatus::STALE_GENERATION;
        receipt.reason = "REQUEST_NOT_IN_FLIGHT";
        receipts_.push_back(receipt);
        return receipt;
    }

    InFlight in_flight = request_it->second;
    in_flight_.erase(request_it);
    LookupReceipt receipt = in_flight.receipt;
    auto endpoint_it = endpoints_.find(receipt.service_name);
    if (now_ns > in_flight.deadline_ns) {
        receipt.status = LookupStatus::TIMEOUT;
        receipt.reason = "TIMEOUT";
    } else if (endpoint_it == endpoints_.end() ||
               !endpoint_it->second.alive) {
        receipt.status = LookupStatus::DEAD_PEER;
        receipt.reason = "DEAD_PEER";
    } else if (endpoint_generation != receipt.endpoint_generation ||
               endpoint_it->second.generation != receipt.endpoint_generation) {
        receipt.status = LookupStatus::STALE_GENERATION;
        receipt.reason = "STALE_GENERATION";
    } else {
        receipt.status = LookupStatus::BOUND;
        receipt.reason = "BOUND";
    }
    receipts_.push_back(receipt);
    return receipt;
}

void TypedServiceCapabilityRegistry::expire(int64_t now_ns) {
    std::lock_guard<std::mutex> lock(mutex_);
    for (auto it = in_flight_.begin(); it != in_flight_.end();) {
        if (now_ns > it->second.deadline_ns) {
            LookupReceipt receipt = it->second.receipt;
            receipt.status = LookupStatus::TIMEOUT;
            receipt.reason = "TIMEOUT";
            receipts_.push_back(receipt);
            it = in_flight_.erase(it);
        } else {
            ++it;
        }
    }
}

bool TypedServiceCapabilityRegistry::allConstructionCriticalReady() const {
    std::lock_guard<std::mutex> lock(mutex_);
    bool found_critical = false;
    for (const auto& entry : specs_) {
        const CapabilitySpec& spec = entry.second;
        if (!spec.construction_critical) {
            continue;
        }
        found_critical = true;
        auto endpoint_it = endpoints_.find(spec.service_name);
        if (spec.placement ==
                ServicePlacement::EXPLICIT_UNSUPPORTED ||
            endpoint_it == endpoints_.end() ||
            !endpoint_it->second.alive) {
            return false;
        }
    }
    return found_critical;
}

std::vector<LookupReceipt>
TypedServiceCapabilityRegistry::receipts() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return receipts_;
}

LookupReceipt TypedServiceCapabilityRegistry::terminal(
    const LookupRequest& request,
    LookupStatus status,
    const std::string& reason,
    ServicePlacement placement,
    uint64_t endpoint_generation) {
    LookupReceipt receipt;
    receipt.request_id = request.request_id;
    receipt.service_name = request.service_name;
    receipt.descriptor = request.descriptor;
    receipt.schema_hash = request.schema_hash;
    receipt.method = request.method;
    receipt.placement = placement;
    receipt.endpoint_generation = endpoint_generation;
    receipt.status = status;
    receipt.reason = reason;
    receipts_.push_back(receipt);
    return receipt;
}

}  // namespace service
}  // namespace oh_adapter
