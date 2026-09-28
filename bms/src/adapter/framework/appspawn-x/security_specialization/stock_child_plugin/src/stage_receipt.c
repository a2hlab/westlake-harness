#include "westlake_android_child_plugin.h"

static void ZeroBytes(void *memory, size_t size)
{
    uint8_t *bytes = (uint8_t *)memory;
    size_t index;
    for (index = 0; index < size; ++index) {
        bytes[index] = UINT8_C(0);
    }
}

static WlascReason Fail(WlascStageLedgerV1 *ledger, WlascReason reason)
{
    if (ledger != (WlascStageLedgerV1 *)0) {
        ledger->last_reason = reason;
        ledger->state = WLASC_RECEIPT_FAILED;
    }
    return reason;
}

WlascReason WLASC_ReceiptParentTail(WlascStageLedgerV1 *ledger,
                                    uint64_t runtime_generation,
                                    uint64_t client_cookie,
                                    uint32_t message_id)
{
    if (ledger == (WlascStageLedgerV1 *)0 || runtime_generation == 0U ||
        client_cookie == 0U) {
        return WLASC_REASON_INVALID_ARGUMENT;
    }
    ZeroBytes(ledger, sizeof(*ledger));
    ledger->abi_version = WLASC_ABI_VERSION;
    ledger->struct_size = (uint32_t)sizeof(*ledger);
    ledger->runtime_generation = runtime_generation;
    ledger->client_cookie = client_cookie;
    ledger->message_id = message_id;
    ledger->parent_stage = WLASC_PARENT_STAGE;
    ledger->parent_tail_priority = WLASC_TAIL_PRIORITY;
    ledger->state = WLASC_RECEIPT_PARENT_TAIL;
    return WLASC_REASON_NONE;
}

WlascReason WLASC_ReceiptBypassGuard(WlascStageLedgerV1 *ledger,
                                     uint64_t client_cookie,
                                     uint32_t required_security_tlvs_present,
                                     uint32_t no_sandbox,
                                     uint32_t ignore_sandbox)
{
#if defined(WLASC_MUTANT_ALLOW_NO_SANDBOX)
    (void)no_sandbox;
#endif
    if (ledger == (WlascStageLedgerV1 *)0) {
        return WLASC_REASON_INVALID_ARGUMENT;
    }
#if !defined(WLASC_MUTANT_ALLOW_MISSING_PARENT)
    if (ledger->state != WLASC_RECEIPT_PARENT_TAIL) {
        return Fail(ledger, WLASC_REASON_SEQUENCE_INVALID);
    }
#endif
    if (ledger->client_cookie != client_cookie || client_cookie == 0U) {
        return Fail(ledger, WLASC_REASON_CLIENT_MISMATCH);
    }
    if (required_security_tlvs_present != UINT32_C(1)) {
        return Fail(ledger, WLASC_REASON_REQUIRED_SECURITY_TLV_MISSING);
    }
#if !defined(WLASC_MUTANT_ALLOW_NO_SANDBOX)
    if (no_sandbox != UINT32_C(0)) {
        return Fail(ledger, WLASC_REASON_NO_SANDBOX_FORBIDDEN);
    }
#endif
    if (ignore_sandbox != UINT32_C(0)) {
        return Fail(ledger, WLASC_REASON_IGNORE_SANDBOX_FORBIDDEN);
    }
    ledger->bypass_guard_passed = UINT32_C(1);
    ledger->state = WLASC_RECEIPT_BYPASS_GUARD;
    return WLASC_REASON_NONE;
}

WlascReason WLASC_ReceiptChildTail(WlascStageLedgerV1 *ledger,
                                   uint64_t client_cookie)
{
    if (ledger == (WlascStageLedgerV1 *)0) {
        return WLASC_REASON_INVALID_ARGUMENT;
    }
#if !defined(WLASC_MUTANT_ALLOW_MISSING_GUARD)
    if (ledger->state != WLASC_RECEIPT_BYPASS_GUARD ||
        ledger->bypass_guard_passed != UINT32_C(1)) {
        return Fail(ledger, WLASC_REASON_SEQUENCE_INVALID);
    }
#endif
    if (ledger->client_cookie != client_cookie || client_cookie == 0U) {
        return Fail(ledger, WLASC_REASON_CLIENT_MISMATCH);
    }
    ledger->child_stage = WLASC_CHILD_STAGE;
    ledger->child_tail_priority = WLASC_TAIL_PRIORITY;
    ledger->state = WLASC_RECEIPT_CHILD_TAIL;
    return WLASC_REASON_NONE;
}

WlascReason WLASC_ReceiptConsume(WlascStageLedgerV1 *ledger,
                                 uint64_t client_cookie,
                                 WlascStockStageReceiptV1 *out_receipt)
{
    if (ledger == (WlascStageLedgerV1 *)0 ||
        out_receipt == (WlascStockStageReceiptV1 *)0) {
        return WLASC_REASON_INVALID_ARGUMENT;
    }
    ZeroBytes(out_receipt, sizeof(*out_receipt));
#if !defined(WLASC_MUTANT_ALLOW_MISSING_CHILD_TAIL)
    if (ledger->state != WLASC_RECEIPT_CHILD_TAIL) {
        return Fail(ledger, ledger->state == WLASC_RECEIPT_CONSUMED ?
            WLASC_REASON_REPLAY : WLASC_REASON_SEQUENCE_INVALID);
    }
#endif
    if (ledger->client_cookie != client_cookie || client_cookie == 0U) {
        return Fail(ledger, WLASC_REASON_CLIENT_MISMATCH);
    }
    out_receipt->abi_version = WLASC_ABI_VERSION;
    out_receipt->struct_size = (uint32_t)sizeof(*out_receipt);
    out_receipt->runtime_generation = ledger->runtime_generation;
    out_receipt->message_id = ledger->message_id;
    out_receipt->parent_stage_tail_reached = UINT32_C(1);
    out_receipt->child_stage_tail_reached = UINT32_C(1);
    out_receipt->bypass_guard_passed = ledger->bypass_guard_passed;
    out_receipt->security_owner_stock_appspawn = UINT32_C(1);
    out_receipt->parent_tail_priority = ledger->parent_tail_priority;
    out_receipt->child_tail_priority = ledger->child_tail_priority;
    ledger->state = WLASC_RECEIPT_CONSUMED;
    return WLASC_REASON_NONE;
}
