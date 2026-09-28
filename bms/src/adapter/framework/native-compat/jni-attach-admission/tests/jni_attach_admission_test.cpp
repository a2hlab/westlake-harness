#include "westlake_jni_attach_admission.h"

#include <cstdlib>
#include <initializer_list>
#include <iostream>
#include <string>
#include <vector>

namespace {

enum class VerifyMode {
    kReady,
    kNoReadyThenPrepared,
    kTerminal,
};

struct FakeState {
    jint getEnvResult = JNI_OK;
    jint attachResult = JNI_OK;
    jint detachResult = JNI_OK;
    VerifyMode verifyMode = VerifyMode::kReady;
    bool issueFails = false;
    bool prepareFails = false;
    bool mismatchPreparedReceipt = false;
    bool prepared = false;
    WltgAdmissionKind readyAdmission =
        WLTG_ADMISSION_MAIN_POST_SPECIALIZATION;
    WltgThreadRole readyRole = WLTG_THREAD_ROLE_MAIN;
    JNIEnv* env = reinterpret_cast<JNIEnv*>(0x1234);
    WltgThreadReceiptV1 preparedReceipt{};
    std::vector<std::string> events;
};

FakeState g;

WltgResult Result(WltgStatus status, WltgReason reason,
                  WltgThreadState state = WLTG_THREAD_FREE) {
    return WltgResult{status, reason, WLTG_PROCESS_ARMED, state};
}

void FillReceipt(WltgThreadReceiptV1* receipt, WltgAdmissionKind admission,
                 WltgThreadRole role, std::uint64_t ticketId) {
    *receipt = {};
    receipt->abi_version = WLTG_ABI_VERSION;
    receipt->struct_size = sizeof(*receipt);
    receipt->state = WLTG_THREAD_READY;
    receipt->admission_kind = admission;
    receipt->role = role;
    receipt->ticket_id = ticketId;
    receipt->one_shot_nonce = ticketId + 10;
    receipt->adapter_generation = 45;
    receipt->process_epoch = 100;
    receipt->policy_epoch = 200;
    receipt->issuer_thread_id = 300;
    receipt->current_thread_id = 300;
    receipt->owner_cookie = 400;
    receipt->written_address = 0x500;
    receipt->tp_offset = WLTG_STACK_GUARD_TP_OFFSET;
    receipt->width = WLTG_STACK_GUARD_WIDTH;
    receipt->publication_sequence = 600;
}

void Reset(jint getEnvResult, VerifyMode verifyMode) {
    g = {};
    g.getEnvResult = getEnvResult;
    g.verifyMode = verifyMode;
    g.env = reinterpret_cast<JNIEnv*>(0x1234);
}

void Expect(bool condition, const char* message) {
    if (!condition) {
        std::cerr << "FAIL " << message << "\n";
        std::exit(1);
    }
}

void ExpectEvents(std::initializer_list<const char*> expected) {
    std::vector<std::string> values(expected.begin(), expected.end());
    if (g.events != values) {
        std::cerr << "FAIL events expected:";
        for (const auto& item : values) std::cerr << ' ' << item;
        std::cerr << " actual:";
        for (const auto& item : g.events) std::cerr << ' ' << item;
        std::cerr << '\n';
        std::exit(1);
    }
}

jint FakeDestroy(JavaVM*) { return JNI_OK; }

jint FakeAttach(JavaVM*, JNIEnv** env, void*) {
    g.events.emplace_back("Attach");
    if (g.attachResult == JNI_OK) *env = g.env;
    return g.attachResult;
}

jint FakeAttachDaemon(JavaVM*, JNIEnv** env, void*) {
    g.events.emplace_back("AttachDaemon");
    if (g.attachResult == JNI_OK) *env = g.env;
    return g.attachResult;
}

jint FakeDetach(JavaVM*) {
    g.events.emplace_back("Detach");
    return g.detachResult;
}

jint FakeGetEnv(JavaVM*, void** env, jint) {
    g.events.emplace_back("GetEnv");
    if (g.getEnvResult == JNI_OK) *env = g.env;
    return g.getEnvResult;
}

const JNIInvokeInterface kVmFunctions{
    nullptr,
    nullptr,
    nullptr,
    FakeDestroy,
    FakeAttach,
    FakeDetach,
    FakeGetEnv,
    FakeAttachDaemon,
};
JavaVM kVm{&kVmFunctions};

}  // namespace

extern "C" WltgResult WLTG_IssueThreadTicket(
    WltgAdmissionKind admission, WltgThreadRole role,
    WltgThreadTicketV1* ticket) {
    g.events.emplace_back("Issue");
    Expect(admission == WLTG_ADMISSION_ADAPTER_JNI_ATTACH,
           "wrong admission kind");
    Expect(role == WLTG_THREAD_ROLE_ADAPTER_JNI_ATTACH, "wrong thread role");
    if (g.issueFails) {
        return Result(WLTG_STATUS_DENIED_TERMINAL,
                      WLTG_REASON_PROCESS_TERMINAL);
    }
    *ticket = {};
    ticket->abi_version = WLTG_ABI_VERSION;
    ticket->struct_size = sizeof(*ticket);
    ticket->ticket_id = 7;
    ticket->one_shot_nonce = 17;
    ticket->adapter_generation = 45;
    ticket->process_epoch = 100;
    ticket->policy_epoch = 200;
    ticket->issuer_thread_id = 300;
    ticket->admission_kind = admission;
    ticket->role = role;
    return Result(WLTG_STATUS_OK, WLTG_REASON_NONE, WLTG_THREAD_ISSUED);
}

extern "C" WltgResult WLTG_CancelThreadTicket(
    const WltgThreadTicketV1*) {
    g.events.emplace_back("Cancel");
    return Result(WLTG_STATUS_OK, WLTG_REASON_NONE, WLTG_THREAD_CANCELLED);
}

extern "C" WltgResult WLTG_PrepareCurrentThread(
    const WltgThreadTicketV1*, WltgThreadReceiptV1* receipt) {
    g.events.emplace_back("Prepare");
    if (g.prepareFails) {
        return Result(WLTG_STATUS_DENIED_TERMINAL,
                      WLTG_REASON_OWNER_UNAVAILABLE, WLTG_THREAD_FAILED);
    }
    FillReceipt(&g.preparedReceipt, WLTG_ADMISSION_ADAPTER_JNI_ATTACH,
                WLTG_THREAD_ROLE_ADAPTER_JNI_ATTACH, 7);
    *receipt = g.preparedReceipt;
    g.prepared = true;
    return Result(WLTG_STATUS_OK, WLTG_REASON_NONE, WLTG_THREAD_READY);
}

extern "C" WltgResult WLTG_VerifyCurrentThreadReady(
    WltgThreadReceiptV1* receipt) {
    g.events.emplace_back("Verify");
    if (g.verifyMode == VerifyMode::kTerminal) {
        *receipt = {};
        return Result(WLTG_STATUS_DENIED_TERMINAL,
                      WLTG_REASON_PROCESS_TERMINAL);
    }
    if (g.verifyMode == VerifyMode::kNoReadyThenPrepared && !g.prepared) {
        *receipt = {};
        return Result(WLTG_STATUS_DENIED_TRANSIENT,
                      WLTG_REASON_PROCESS_NOT_ARMED);
    }
    if (g.prepared) {
        *receipt = g.preparedReceipt;
        if (g.mismatchPreparedReceipt) ++receipt->publication_sequence;
    } else {
        FillReceipt(receipt, g.readyAdmission, g.readyRole, 1);
    }
    return Result(WLTG_STATUS_OK, WLTG_REASON_NONE, WLTG_THREAD_READY);
}

extern "C" WltgResult WLTG_RetireCurrentThread(
    const WltgThreadReceiptV1*) {
    g.events.emplace_back("Retire");
    return Result(WLTG_STATUS_OK, WLTG_REASON_NONE, WLTG_THREAD_RETIRED);
}

int main() {
    using westlake::jni::AttachMode;
    using westlake::jni::AttachStatus;
    using westlake::jni::ScopedJniAttachment;

    Reset(JNI_OK, VerifyMode::kReady);
    {
        ScopedJniAttachment attachment(&kVm);
        Expect(attachment.valid(), "attached READY thread rejected");
        Expect(!attachment.ownsJvmAttachment(), "attached thread ownership");
        Expect(attachment.status() == AttachStatus::kReadyVerified,
               "attached status");
    }
    ExpectEvents({"GetEnv", "Verify"});

    Reset(JNI_OK, VerifyMode::kNoReadyThenPrepared);
    {
        ScopedJniAttachment attachment(&kVm);
        Expect(!attachment.valid(),
               "already-attached thread without READY admission accepted");
        Expect(!attachment.ownsJvmAttachment(),
               "already-attached no-READY thread claimed JVM ownership");
        Expect(!attachment.ownsAdmissionReceipt(),
               "already-attached no-READY thread issued an admission");
    }
    ExpectEvents({"GetEnv", "Verify"});

    Reset(JNI_EDETACHED, VerifyMode::kReady);
    {
        ScopedJniAttachment attachment(&kVm, "main");
        Expect(attachment.valid(), "detached admitted MAIN rejected");
        Expect(attachment.ownsJvmAttachment(), "MAIN JVM ownership missing");
        Expect(!attachment.ownsAdmissionReceipt(), "MAIN receipt stolen");
    }
    ExpectEvents({"GetEnv", "Verify", "Attach", "Detach"});

    Reset(JNI_EDETACHED, VerifyMode::kReady);
    g.readyAdmission = WLTG_ADMISSION_NAMESPACE_PTHREAD_CREATE;
    g.readyRole = WLTG_THREAD_ROLE_GUEST_PTHREAD;
    {
        ScopedJniAttachment attachment(&kVm, "guest");
        Expect(attachment.valid(), "detached admitted guest rejected");
        Expect(attachment.ownsJvmAttachment(), "guest JVM ownership missing");
        Expect(!attachment.ownsAdmissionReceipt(), "guest receipt stolen");
    }
    ExpectEvents({"GetEnv", "Verify", "Attach", "Detach"});

    Reset(JNI_EDETACHED, VerifyMode::kReady);
    g.readyAdmission = WLTG_ADMISSION_ADAPTER_JNI_ATTACH;
    g.readyRole = WLTG_THREAD_ROLE_ADAPTER_JNI_ATTACH;
    {
        ScopedJniAttachment attachment(&kVm);
        Expect(!attachment.valid(),
               "detached stale JNI admission was reused as MAIN/GUEST");
    }
    ExpectEvents({"GetEnv", "Verify"});

    Reset(JNI_EDETACHED, VerifyMode::kNoReadyThenPrepared);
    {
        ScopedJniAttachment attachment(&kVm, "native-callback");
        Expect(attachment.valid(), "native callback admission rejected");
        Expect(attachment.ownsJvmAttachment(), "JVM ownership missing");
        Expect(attachment.ownsAdmissionReceipt(), "receipt ownership missing");
    }
    ExpectEvents({"GetEnv", "Verify", "Issue", "Prepare", "Verify",
                  "Attach", "Detach", "Retire"});

    Reset(JNI_EDETACHED, VerifyMode::kNoReadyThenPrepared);
    {
        ScopedJniAttachment attachment(&kVm, "daemon", AttachMode::kDaemon);
        Expect(attachment.valid(), "daemon admission rejected");
    }
    ExpectEvents({"GetEnv", "Verify", "Issue", "Prepare", "Verify",
                  "AttachDaemon", "Detach", "Retire"});

    Reset(JNI_OK, VerifyMode::kTerminal);
    {
        ScopedJniAttachment attachment(&kVm);
        Expect(!attachment.valid(), "unadmitted attached thread accepted");
    }
    ExpectEvents({"GetEnv", "Verify"});

    Reset(JNI_EDETACHED, VerifyMode::kTerminal);
    {
        ScopedJniAttachment attachment(&kVm);
        Expect(!attachment.valid(), "terminal verification bypassed");
    }
    ExpectEvents({"GetEnv", "Verify"});

    Reset(JNI_EDETACHED, VerifyMode::kNoReadyThenPrepared);
    g.issueFails = true;
    {
        ScopedJniAttachment attachment(&kVm);
        Expect(!attachment.valid(), "ticket failure bypassed");
    }
    ExpectEvents({"GetEnv", "Verify", "Issue"});

    Reset(JNI_EDETACHED, VerifyMode::kNoReadyThenPrepared);
    g.prepareFails = true;
    {
        ScopedJniAttachment attachment(&kVm);
        Expect(!attachment.valid(), "prepare failure bypassed");
    }
    ExpectEvents({"GetEnv", "Verify", "Issue", "Prepare", "Cancel"});

    Reset(JNI_EDETACHED, VerifyMode::kNoReadyThenPrepared);
    g.mismatchPreparedReceipt = true;
    {
        ScopedJniAttachment attachment(&kVm);
        Expect(!attachment.valid(), "receipt mismatch bypassed");
    }
    ExpectEvents({"GetEnv", "Verify", "Issue", "Prepare", "Verify",
                  "Retire"});

    Reset(JNI_EDETACHED, VerifyMode::kNoReadyThenPrepared);
    g.attachResult = JNI_ERR;
    {
        ScopedJniAttachment attachment(&kVm);
        Expect(!attachment.valid(), "JVM attach failure bypassed");
    }
    ExpectEvents({"GetEnv", "Verify", "Issue", "Prepare", "Verify",
                  "Attach", "Retire"});

    Reset(JNI_EDETACHED, VerifyMode::kNoReadyThenPrepared);
    g.detachResult = JNI_ERR;
    {
        ScopedJniAttachment attachment(&kVm);
        Expect(attachment.valid(), "detach-failure setup rejected");
        Expect(attachment.Detach() == AttachStatus::kJvmDetachFailed,
               "JVM detach failure not surfaced");
        Expect(attachment.ownsJvmAttachment(),
               "failed JVM detach lost attachment ownership");
        Expect(attachment.ownsAdmissionReceipt(),
               "failed JVM detach retired admission receipt");
    }
    ExpectEvents({"GetEnv", "Verify", "Issue", "Prepare", "Verify",
                  "Attach", "Detach", "Detach"});

    std::cout << "PASS central JNI attach admission host contract "
                 "cases=14 detach_failure_retire=0\n";
    return 0;
}
