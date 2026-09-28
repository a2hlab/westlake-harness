#include "westlake_android_child_plugin.h"

#include <stdbool.h>
#include <stdio.h>
#include <string.h>

static int failures;
static int tests_run;

static bool HappyPath(void)
{
    WlascStageLedgerV1 ledger;
    WlascStockStageReceiptV1 receipt;
    memset(&ledger, 0, sizeof(ledger));
    return WLASC_ReceiptParentTail(&ledger, UINT64_C(99), UINT64_C(0x1234),
                                   UINT32_C(77)) == WLASC_REASON_NONE &&
           WLASC_ReceiptBypassGuard(&ledger, UINT64_C(0x1234), 1U, 0U, 0U) ==
               WLASC_REASON_NONE &&
           WLASC_ReceiptChildTail(&ledger, UINT64_C(0x1234)) ==
               WLASC_REASON_NONE &&
           WLASC_ReceiptConsume(&ledger, UINT64_C(0x1234), &receipt) ==
               WLASC_REASON_NONE &&
           ledger.state == WLASC_RECEIPT_CONSUMED &&
           receipt.runtime_generation == UINT64_C(99) &&
           receipt.message_id == UINT32_C(77) &&
           receipt.parent_stage_tail_reached == 1U &&
           receipt.child_stage_tail_reached == 1U &&
           receipt.bypass_guard_passed == 1U &&
           receipt.security_owner_stock_appspawn == 1U &&
           receipt.parent_tail_priority == WLASC_TAIL_PRIORITY &&
           receipt.child_tail_priority == WLASC_TAIL_PRIORITY;
}

static bool MissingParentRejected(void)
{
    WlascStageLedgerV1 ledger;
    memset(&ledger, 0, sizeof(ledger));
    ledger.client_cookie = UINT64_C(0x1234);
    ledger.runtime_generation = UINT64_C(99);
    return WLASC_ReceiptBypassGuard(&ledger, UINT64_C(0x1234), 1U, 0U, 0U) ==
               WLASC_REASON_SEQUENCE_INVALID &&
           ledger.state == WLASC_RECEIPT_FAILED;
}

static bool ClientMismatchRejected(void)
{
    WlascStageLedgerV1 ledger;
    memset(&ledger, 0, sizeof(ledger));
    if (WLASC_ReceiptParentTail(&ledger, 1U, UINT64_C(0x1234), 1U) !=
        WLASC_REASON_NONE) return false;
    return WLASC_ReceiptBypassGuard(&ledger, UINT64_C(0x5678), 1U, 0U, 0U) ==
           WLASC_REASON_CLIENT_MISMATCH;
}

static bool MissingSecurityTlvRejected(void)
{
    WlascStageLedgerV1 ledger;
    memset(&ledger, 0, sizeof(ledger));
    if (WLASC_ReceiptParentTail(&ledger, 1U, UINT64_C(0x1234), 1U) !=
        WLASC_REASON_NONE) return false;
    return WLASC_ReceiptBypassGuard(&ledger, UINT64_C(0x1234), 0U, 0U, 0U) ==
           WLASC_REASON_REQUIRED_SECURITY_TLV_MISSING;
}

static bool NoSandboxRejected(void)
{
    WlascStageLedgerV1 ledger;
    memset(&ledger, 0, sizeof(ledger));
    if (WLASC_ReceiptParentTail(&ledger, 1U, UINT64_C(0x1234), 1U) !=
        WLASC_REASON_NONE) return false;
    return WLASC_ReceiptBypassGuard(&ledger, UINT64_C(0x1234), 1U, 1U, 0U) ==
           WLASC_REASON_NO_SANDBOX_FORBIDDEN;
}

static bool IgnoreSandboxRejected(void)
{
    WlascStageLedgerV1 ledger;
    memset(&ledger, 0, sizeof(ledger));
    if (WLASC_ReceiptParentTail(&ledger, 1U, UINT64_C(0x1234), 1U) !=
        WLASC_REASON_NONE) return false;
    return WLASC_ReceiptBypassGuard(&ledger, UINT64_C(0x1234), 1U, 0U, 1U) ==
           WLASC_REASON_IGNORE_SANDBOX_FORBIDDEN;
}

static bool MissingGuardRejected(void)
{
    WlascStageLedgerV1 ledger;
    memset(&ledger, 0, sizeof(ledger));
    if (WLASC_ReceiptParentTail(&ledger, 1U, UINT64_C(0x1234), 1U) !=
        WLASC_REASON_NONE) return false;
    return WLASC_ReceiptChildTail(&ledger, UINT64_C(0x1234)) ==
           WLASC_REASON_SEQUENCE_INVALID;
}

static bool MissingChildTailRejected(void)
{
    WlascStageLedgerV1 ledger;
    WlascStockStageReceiptV1 receipt;
    memset(&ledger, 0, sizeof(ledger));
    if (WLASC_ReceiptParentTail(&ledger, 1U, UINT64_C(0x1234), 1U) !=
            WLASC_REASON_NONE ||
        WLASC_ReceiptBypassGuard(&ledger, UINT64_C(0x1234), 1U, 0U, 0U) !=
            WLASC_REASON_NONE) return false;
    return WLASC_ReceiptConsume(&ledger, UINT64_C(0x1234), &receipt) ==
           WLASC_REASON_SEQUENCE_INVALID;
}

static bool ReplayRejected(void)
{
    WlascStageLedgerV1 ledger;
    WlascStockStageReceiptV1 receipt;
    memset(&ledger, 0, sizeof(ledger));
    if (WLASC_ReceiptParentTail(&ledger, 1U, UINT64_C(0x1234), 1U) !=
            WLASC_REASON_NONE ||
        WLASC_ReceiptBypassGuard(&ledger, UINT64_C(0x1234), 1U, 0U, 0U) !=
            WLASC_REASON_NONE ||
        WLASC_ReceiptChildTail(&ledger, UINT64_C(0x1234)) !=
            WLASC_REASON_NONE ||
        WLASC_ReceiptConsume(&ledger, UINT64_C(0x1234), &receipt) !=
            WLASC_REASON_NONE) return false;
    return WLASC_ReceiptConsume(&ledger, UINT64_C(0x1234), &receipt) ==
           WLASC_REASON_REPLAY;
}

static bool ZeroGenerationRejected(void)
{
    WlascStageLedgerV1 ledger;
    memset(&ledger, 0, sizeof(ledger));
    return WLASC_ReceiptParentTail(&ledger, 0U, UINT64_C(0x1234), 1U) ==
           WLASC_REASON_INVALID_ARGUMENT;
}

static void Run(const char *name, bool (*test)(void))
{
    ++tests_run;
    if (!test()) {
        ++failures;
        fprintf(stderr, "FAIL %s\n", name);
    }
}

int main(void)
{
    Run("happy_path", HappyPath);
    Run("missing_parent", MissingParentRejected);
    Run("client_mismatch", ClientMismatchRejected);
    Run("missing_security_tlv", MissingSecurityTlvRejected);
    Run("no_sandbox", NoSandboxRejected);
    Run("ignore_sandbox", IgnoreSandboxRejected);
    Run("missing_guard", MissingGuardRejected);
    Run("missing_child_tail", MissingChildTailRejected);
    Run("replay", ReplayRejected);
    Run("zero_generation", ZeroGenerationRejected);
    if (failures != 0) {
        fprintf(stderr, "RESULT FAIL tests=%d failures=%d\n", tests_run,
                failures);
        return 1;
    }
    printf("RESULT PASS tests=%d\n", tests_run);
    return 0;
}
