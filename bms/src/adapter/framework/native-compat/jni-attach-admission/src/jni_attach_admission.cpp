#include "westlake_jni_attach_admission.h"

namespace westlake::jni {
namespace {

bool ResultOk(const WltgResult& result) noexcept {
    return result.status == WLTG_STATUS_OK ||
           result.status == WLTG_STATUS_OK_IDEMPOTENT;
}

bool NoReadyReceipt(const WltgResult& result) noexcept {
    return result.status == WLTG_STATUS_DENIED_TRANSIENT &&
           result.reason == WLTG_REASON_PROCESS_NOT_ARMED;
}

bool ReadyReceipt(const WltgThreadReceiptV1& receipt) noexcept {
    if (receipt.abi_version != WLTG_ABI_VERSION ||
        receipt.struct_size != sizeof(receipt) ||
        receipt.state != WLTG_THREAD_READY) {
        return false;
    }
    return (receipt.admission_kind ==
                WLTG_ADMISSION_MAIN_POST_SPECIALIZATION &&
            receipt.role == WLTG_THREAD_ROLE_MAIN) ||
           (receipt.admission_kind ==
                WLTG_ADMISSION_NAMESPACE_PTHREAD_CREATE &&
            receipt.role == WLTG_THREAD_ROLE_GUEST_PTHREAD) ||
           (receipt.admission_kind == WLTG_ADMISSION_ADAPTER_JNI_ATTACH &&
            receipt.role == WLTG_THREAD_ROLE_ADAPTER_JNI_ATTACH);
}

bool ReusableExistingAdmission(const WltgThreadReceiptV1& receipt) noexcept {
    return ReadyReceipt(receipt) &&
           (receipt.admission_kind ==
                WLTG_ADMISSION_MAIN_POST_SPECIALIZATION ||
            receipt.admission_kind ==
                WLTG_ADMISSION_NAMESPACE_PTHREAD_CREATE);
}

bool SameReceipt(const WltgThreadReceiptV1& left,
                 const WltgThreadReceiptV1& right) noexcept {
    return left.abi_version == right.abi_version &&
           left.struct_size == right.struct_size &&
           left.state == right.state &&
           left.admission_kind == right.admission_kind &&
           left.role == right.role &&
           left.reserved_zero == right.reserved_zero &&
           left.ticket_id == right.ticket_id &&
           left.one_shot_nonce == right.one_shot_nonce &&
           left.adapter_generation == right.adapter_generation &&
           left.process_epoch == right.process_epoch &&
           left.policy_epoch == right.policy_epoch &&
           left.issuer_thread_id == right.issuer_thread_id &&
           left.current_thread_id == right.current_thread_id &&
           left.owner_cookie == right.owner_cookie &&
           left.written_address == right.written_address &&
           left.tp_offset == right.tp_offset &&
           left.width == right.width &&
           left.publication_sequence == right.publication_sequence;
}

jint AttachJvm(JavaVM* vm, JNIEnv** env, const char* threadName,
               AttachMode mode) noexcept {
    JavaVMAttachArgs args{
        JNI_VERSION_1_6,
        const_cast<char*>(threadName),
        nullptr,
    };
    void* opaqueArgs = threadName == nullptr ? nullptr : &args;
    if (mode == AttachMode::kDaemon) {
        return vm->AttachCurrentThreadAsDaemon(env, opaqueArgs);
    }
    return vm->AttachCurrentThread(env, opaqueArgs);
}

}  // namespace

const char* AttachStatusString(AttachStatus status) noexcept {
    switch (status) {
        case AttachStatus::kInvalidVm:
            return "invalid_vm";
        case AttachStatus::kReadyVerified:
            return "ready_verified";
        case AttachStatus::kAttachedWithExistingAdmission:
            return "attached_with_existing_admission";
        case AttachStatus::kAttachedWithOwnedAdmission:
            return "attached_with_owned_admission";
        case AttachStatus::kGetEnvFailed:
            return "get_env_failed";
        case AttachStatus::kReadyVerificationFailed:
            return "ready_verification_failed";
        case AttachStatus::kTicketIssueFailed:
            return "ticket_issue_failed";
        case AttachStatus::kPrepareFailed:
            return "prepare_failed";
        case AttachStatus::kPreparedReceiptMismatch:
            return "prepared_receipt_mismatch";
        case AttachStatus::kJvmAttachFailed:
            return "jvm_attach_failed";
        case AttachStatus::kJvmDetachFailed:
            return "jvm_detach_failed";
        case AttachStatus::kReceiptRetireFailed:
            return "receipt_retire_failed";
        case AttachStatus::kDetached:
            return "detached";
    }
    return "unknown";
}

ScopedJniAttachment::ScopedJniAttachment(JavaVM* vm, const char* threadName,
                                         AttachMode mode) noexcept
    : vm_(vm) {
    if (vm_ == nullptr) {
        return;
    }

    getEnvResult_ =
        vm_->GetEnv(reinterpret_cast<void**>(&env_), JNI_VERSION_1_6);
    if (getEnvResult_ == JNI_OK && env_ != nullptr) {
        WltgThreadReceiptV1 verified{};
        const WltgResult verifyResult =
            WLTG_VerifyCurrentThreadReady(&verified);
        RecordWltgResult("verify_attached", verifyResult);
        if (ResultOk(verifyResult) && ReadyReceipt(verified)) {
            status_ = AttachStatus::kReadyVerified;
        } else {
            env_ = nullptr;
            status_ = AttachStatus::kReadyVerificationFailed;
        }
        return;
    }
    env_ = nullptr;
    if (getEnvResult_ != JNI_EDETACHED) {
        status_ = AttachStatus::kGetEnvFailed;
        return;
    }

    WltgThreadReceiptV1 existing{};
    const WltgResult existingResult =
        WLTG_VerifyCurrentThreadReady(&existing);
    RecordWltgResult("verify_detached", existingResult);
    if (ResultOk(existingResult) && ReusableExistingAdmission(existing)) {
        if (AttachJvm(vm_, &env_, threadName, mode) == JNI_OK &&
            env_ != nullptr) {
            ownsJvmAttachment_ = true;
            status_ = AttachStatus::kAttachedWithExistingAdmission;
        } else {
            env_ = nullptr;
            status_ = AttachStatus::kJvmAttachFailed;
        }
        return;
    }
    if (ResultOk(existingResult)) {
        status_ = AttachStatus::kReadyVerificationFailed;
        return;
    }
    if (!NoReadyReceipt(existingResult)) {
        status_ = AttachStatus::kReadyVerificationFailed;
        return;
    }

    WltgThreadTicketV1 ticket{};
    const WltgResult issueResult = WLTG_IssueThreadTicket(
        WLTG_ADMISSION_ADAPTER_JNI_ATTACH,
        WLTG_THREAD_ROLE_ADAPTER_JNI_ATTACH, &ticket);
    RecordWltgResult("issue_jni_attach", issueResult);
    if (!ResultOk(issueResult)) {
        status_ = AttachStatus::kTicketIssueFailed;
        return;
    }

    const WltgResult prepareResult =
        WLTG_PrepareCurrentThread(&ticket, &receipt_);
    RecordWltgResult("prepare_jni_attach", prepareResult);
    if (!ResultOk(prepareResult)) {
        (void)WLTG_CancelThreadTicket(&ticket);
        status_ = AttachStatus::kPrepareFailed;
        return;
    }
    ownsAdmissionReceipt_ = true;

    WltgThreadReceiptV1 verified{};
    const WltgResult verifyResult =
        WLTG_VerifyCurrentThreadReady(&verified);
    RecordWltgResult("verify_prepared", verifyResult);
    if (!ResultOk(verifyResult) || !ReadyReceipt(verified) ||
        !SameReceipt(receipt_, verified)) {
        (void)WLTG_RetireCurrentThread(&receipt_);
        ownsAdmissionReceipt_ = false;
        receipt_ = {};
        status_ = AttachStatus::kPreparedReceiptMismatch;
        return;
    }

    if (AttachJvm(vm_, &env_, threadName, mode) != JNI_OK || env_ == nullptr) {
        env_ = nullptr;
        RetireOwnedReceiptAfterAttachFailure();
        status_ = AttachStatus::kJvmAttachFailed;
        return;
    }
    ownsJvmAttachment_ = true;
    status_ = AttachStatus::kAttachedWithOwnedAdmission;
}

ScopedJniAttachment::~ScopedJniAttachment() {
    (void)Detach();
}

AttachStatus ScopedJniAttachment::Detach() noexcept {
    if (!ownsJvmAttachment_) {
        return status_;
    }
    if (vm_ == nullptr || vm_->DetachCurrentThread() != JNI_OK) {
        status_ = AttachStatus::kJvmDetachFailed;
        return status_;
    }
    ownsJvmAttachment_ = false;
    env_ = nullptr;

    if (ownsAdmissionReceipt_) {
        const WltgResult retireResult =
            WLTG_RetireCurrentThread(&receipt_);
        RecordWltgResult("retire_jni_attach", retireResult);
        if (!ResultOk(retireResult)) {
            status_ = AttachStatus::kReceiptRetireFailed;
            return status_;
        }
        ownsAdmissionReceipt_ = false;
        receipt_ = {};
    }
    status_ = AttachStatus::kDetached;
    return status_;
}

void ScopedJniAttachment::RecordWltgResult(
    const char* operation, const WltgResult& result) noexcept {
    lastWltgOperation_ = operation == nullptr ? "unknown" : operation;
    lastWltgResult_ = result;
}

void ScopedJniAttachment::RetireOwnedReceiptAfterAttachFailure() noexcept {
    if (!ownsAdmissionReceipt_) {
        return;
    }
    (void)WLTG_RetireCurrentThread(&receipt_);
    ownsAdmissionReceipt_ = false;
    receipt_ = {};
}

}  // namespace westlake::jni
