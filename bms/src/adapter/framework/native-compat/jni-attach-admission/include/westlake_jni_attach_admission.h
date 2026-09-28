#ifndef WESTLAKE_JNI_ATTACH_ADMISSION_H
#define WESTLAKE_JNI_ATTACH_ADMISSION_H

#include <jni.h>

#include <cstdint>

#include "westlake_thread_guard_registry.h"

namespace westlake::jni {

enum class AttachMode : std::uint8_t {
    kThread = 0,
    kDaemon = 1,
};

enum class AttachStatus : std::uint8_t {
    kInvalidVm = 0,
    kReadyVerified,
    kAttachedWithExistingAdmission,
    kAttachedWithOwnedAdmission,
    kGetEnvFailed,
    kReadyVerificationFailed,
    kTicketIssueFailed,
    kPrepareFailed,
    kPreparedReceiptMismatch,
    kJvmAttachFailed,
    kJvmDetachFailed,
    kReceiptRetireFailed,
    kDetached,
};

[[nodiscard]] const char* AttachStatusString(AttachStatus status) noexcept;

/*
 * The only adapter-owned route from an OH native callback thread into JNI.
 *
 * Construction always asks the VM for the current state first. An already
 * attached thread must already own a READY MAIN/GUEST/JNI receipt and is only
 * verified. A detached thread first reuses any existing READY MAIN/GUEST
 * admission; only a truly unadmitted callback thread may issue the one-shot
 * JNI_ATTACH ticket, prepare its TLS slot, verify the exact receipt, and then
 * enter the JVM. Destruction detaches only a JVM attachment owned by this
 * object and retires exactly the JNI receipt owned by this object.
 */
class ScopedJniAttachment final {
public:
    explicit ScopedJniAttachment(
        JavaVM* vm, const char* threadName = nullptr,
        AttachMode mode = AttachMode::kThread) noexcept;
    ~ScopedJniAttachment();

    ScopedJniAttachment(const ScopedJniAttachment&) = delete;
    ScopedJniAttachment& operator=(const ScopedJniAttachment&) = delete;

    ScopedJniAttachment(ScopedJniAttachment&&) = delete;
    ScopedJniAttachment& operator=(ScopedJniAttachment&&) = delete;

    [[nodiscard]] JNIEnv* env() const noexcept { return env_; }
    [[nodiscard]] bool valid() const noexcept { return env_ != nullptr; }
    [[nodiscard]] bool ownsJvmAttachment() const noexcept {
        return ownsJvmAttachment_;
    }
    [[nodiscard]] bool ownsAdmissionReceipt() const noexcept {
        return ownsAdmissionReceipt_;
    }
    [[nodiscard]] AttachStatus status() const noexcept { return status_; }
    [[nodiscard]] const char* statusString() const noexcept {
        return AttachStatusString(status_);
    }
    [[nodiscard]] jint getEnvResult() const noexcept { return getEnvResult_; }
    [[nodiscard]] const char* lastWltgOperation() const noexcept {
        return lastWltgOperation_;
    }
    [[nodiscard]] WltgResult lastWltgResult() const noexcept {
        return lastWltgResult_;
    }

    AttachStatus Detach() noexcept;

private:
    void RecordWltgResult(const char* operation,
                          const WltgResult& result) noexcept;
    void RetireOwnedReceiptAfterAttachFailure() noexcept;

    JavaVM* vm_ = nullptr;
    JNIEnv* env_ = nullptr;
    WltgThreadReceiptV1 receipt_{};
    WltgResult lastWltgResult_{};
    const char* lastWltgOperation_ = "none";
    jint getEnvResult_ = JNI_ERR;
    AttachStatus status_ = AttachStatus::kInvalidVm;
    bool ownsJvmAttachment_ = false;
    bool ownsAdmissionReceipt_ = false;
};

}  // namespace westlake::jni

#endif  // WESTLAKE_JNI_ATTACH_ADMISSION_H
