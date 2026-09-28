#include "test_fixture_signing.h"
#include "westlake_native_compat.h"
#include "wlnc_aperture_fixture.h"

#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

_Static_assert(sizeof(WlafFixturePermitV1) != sizeof(WlncLoadPermit),
               "fixture permit must not alias the audit-core permit");
_Static_assert(WLAF_PERMIT_STRUCT_TYPE != WLNC_ABI_VERSION,
               "fixture type discriminator must not alias core ABI");

#define CHECK(expression)                                                        \
    do {                                                                         \
        if (!(expression)) {                                                     \
            (void)fprintf(stderr, "CHECK failed %s:%d: %s\n", __FILE__,       \
                          __LINE__, #expression);                                \
            return 0;                                                            \
        }                                                                        \
    } while (0)

typedef struct TestContext {
    _Alignas(16) uint8_t aperture[WLAF_RESERVATION_SIZE];
    WlafPublication publication;
    WlafCurrentBinding binding;
    uint64_t owner_cookie;
    uint32_t owner_start;
    uint32_t owner_size;
    int signature_accept;
    int binding_accept;
    int owner_accept;
    int csprng_accept;
    int csprng_zero;
    int binding_calls;
    int signature_calls;
    int owner_calls;
    int csprng_calls;
    int ready_events;
    int saw_ready_without_metadata;
} TestContext;

static void FillBytes(uint8_t *bytes, size_t size, uint8_t seed)
{
    size_t index;
    for (index = 0; index < size; ++index) {
        bytes[index] = (uint8_t)(seed + (uint8_t)(index * 13U));
    }
}

static WlafFixturePermitV1 MakePermit(void)
{
    WlafFixturePermitV1 permit;
    (void)memset(&permit, 0, sizeof(permit));
    permit.abi_version = WLAF_ABI_VERSION;
    permit.struct_size = (uint32_t)sizeof(permit);
    permit.struct_type = WLAF_PERMIT_STRUCT_TYPE;
    permit.permit_kind = WLAF_PERMIT_KIND_FIXTURE_ONLY;
    permit.mechanism = WLAF_MECHANISM_APERTURE_NATIVE_FIXTURE;
    permit.signature_size = WLAF_SIGNATURE_SIZE;
    permit.tp_offset = WLAF_STACK_GUARD_TP_OFFSET;
    permit.width = WLAF_STACK_GUARD_WIDTH;
    permit.adapter_generation = UINT64_C(0x2026071208);
    permit.process_epoch = UINT64_C(0x41);
    permit.policy_epoch = UINT64_C(0x17);
    permit.one_shot_nonce = UINT64_C(0xabcddcba11002233);
    FillBytes(permit.target_digest, WLAF_TARGET_DIGEST_SIZE, UINT8_C(0x31));
    WLAF_TestFixtureSign(&permit);
    return permit;
}

static void InitContext(TestContext *context,
                        const WlafFixturePermitV1 *permit)
{
    (void)memset(context, 0, sizeof(*context));
    context->binding.abi_version = WLAF_ABI_VERSION;
    context->binding.adapter_generation = permit->adapter_generation;
    context->binding.process_epoch = permit->process_epoch;
    context->binding.policy_epoch = permit->policy_epoch;
    (void)memcpy(context->binding.target_digest, permit->target_digest,
                 WLAF_TARGET_DIGEST_SIZE);
    context->owner_cookie = UINT64_C(0x77eeddccaa551122);
    context->owner_start = WLAF_RESERVATION_TP_START;
    context->owner_size = WLAF_RESERVATION_SIZE;
    context->signature_accept = 1;
    context->binding_accept = 1;
    context->owner_accept = 1;
    context->csprng_accept = 1;
    atomic_init(&context->publication.state,
                (uint32_t)WLAF_PUBLICATION_UNSEEN);
}

static int ReadBinding(void *opaque, WlafCurrentBinding *out_binding)
{
    TestContext *context = (TestContext *)opaque;
    context->binding_calls += 1;
    if (!context->binding_accept) {
        return 0;
    }
    *out_binding = context->binding;
    return 1;
}

static int VerifySignature(void *opaque,
                           const WlafFixturePermitV1 *permit)
{
    TestContext *context = (TestContext *)opaque;
    context->signature_calls += 1;
    if (!context->signature_accept) {
        return 0;
    }
    return WLAF_TestFixtureVerify(permit);
}

static int ResolveOwner(void *opaque, const WlafFixturePermitV1 *permit,
                        WlafOwnedRegion *out_region)
{
    TestContext *context = (TestContext *)opaque;
    context->owner_calls += 1;
    if (!context->owner_accept) {
        return 0;
    }
    (void)memset(out_region, 0, sizeof(*out_region));
    out_region->abi_version = WLAF_ABI_VERSION;
    out_region->owner_kind = WLAF_OWNER_MAIN_ELF_TLS_RESERVATION;
    out_region->tp_start_offset = context->owner_start;
    out_region->byte_size = context->owner_size;
    out_region->base = context->aperture;
    out_region->publication = &context->publication;
    out_region->owner_cookie = context->owner_cookie;
    out_region->adapter_generation = permit->adapter_generation;
    out_region->process_epoch = permit->process_epoch;
    out_region->policy_epoch = permit->policy_epoch;
    return 1;
}

static int ReadOsRandom(void *opaque, uint64_t required_process_epoch,
                        WlafGuardSample *out_sample)
{
    TestContext *context = (TestContext *)opaque;
    uint8_t *bytes = (uint8_t *)(void *)&out_sample->value;
    size_t remaining = sizeof(out_sample->value);
    int descriptor;
    context->csprng_calls += 1;
    if (!context->csprng_accept) {
        return 0;
    }
    if (context->csprng_zero) {
        out_sample->value = UINT64_C(0);
    } else {
        descriptor = open("/dev/urandom", O_RDONLY);
        if (descriptor < 0) {
            return 0;
        }
        while (remaining != 0U) {
            ssize_t count = read(descriptor, bytes, remaining);
            if (count <= 0) {
                (void)close(descriptor);
                return 0;
            }
            bytes += (size_t)count;
            remaining -= (size_t)count;
        }
        (void)close(descriptor);
    }
    out_sample->source_epoch = required_process_epoch;
    out_sample->quality = WLAF_GUARD_SOURCE_OS_CSPRNG;
    out_sample->reserved_zero = UINT32_C(0);
    return 1;
}

static void OnEvent(void *opaque, const WlafEvent *event)
{
    TestContext *context = (TestContext *)opaque;
    if (event->type == WLAF_EVENT_READY_PUBLISHED) {
        context->ready_events += 1;
        if (context->publication.adapter_generation == UINT64_C(0) ||
            context->publication.one_shot_nonce == UINT64_C(0) ||
            context->publication.guard_value == UINT64_C(0) ||
            context->publication.guard_value !=
                context->publication.readback_value ||
            context->publication.written_address == (uintptr_t)0) {
            context->saw_ready_without_metadata = 1;
        }
    }
}

static WlafFixtureOps MakeOps(TestContext *context)
{
    WlafFixtureOps ops;
    (void)memset(&ops, 0, sizeof(ops));
    ops.abi_version = WLAF_ABI_VERSION;
    ops.context = context;
    ops.read_current_binding = ReadBinding;
    ops.verify_fixture_signature = VerifySignature;
    ops.resolve_current_thread_region = ResolveOwner;
    ops.get_os_csprng = ReadOsRandom;
    ops.emit_event = OnEvent;
    return ops;
}

static int ApertureIsZero(const TestContext *context)
{
    size_t index;
    uint8_t value = UINT8_C(0);
    for (index = 0; index < sizeof(context->aperture); ++index) {
        value = (uint8_t)(value | context->aperture[index]);
    }
    return value == UINT8_C(0);
}

static int TestPositivePublication(void)
{
    WlafFixturePermitV1 permit = MakePermit();
    TestContext context;
    WlafFixtureOps ops;
    WlafResult result;
    uint64_t slot_value;
    InitContext(&context, &permit);
    ops = MakeOps(&context);
    result = WLAF_PublishFixtureAperture(&permit, &ops);
    CHECK(result.status == WLAF_STATUS_OK);
    CHECK(result.reason == WLAF_REASON_NONE);
    CHECK(result.publication_state == WLAF_PUBLICATION_READY);
    CHECK(atomic_load_explicit(&context.publication.state,
                               memory_order_acquire) ==
          (uint32_t)WLAF_PUBLICATION_READY);
    (void)memcpy(&slot_value,
                 context.aperture +
                     (WLAF_STACK_GUARD_TP_OFFSET -
                      WLAF_RESERVATION_TP_START),
                 sizeof(slot_value));
    CHECK(slot_value != UINT64_C(0));
    CHECK(slot_value == context.publication.guard_value);
    CHECK(slot_value == context.publication.readback_value);
    CHECK(context.publication.adapter_generation == permit.adapter_generation);
    CHECK(context.publication.process_epoch == permit.process_epoch);
    CHECK(context.publication.policy_epoch == permit.policy_epoch);
    CHECK(context.publication.one_shot_nonce == permit.one_shot_nonce);
    CHECK(context.publication.tp_offset == WLAF_STACK_GUARD_TP_OFFSET);
    CHECK(context.publication.width == WLAF_STACK_GUARD_WIDTH);
    CHECK(context.publication.owner_cookie == context.owner_cookie);
    CHECK(context.ready_events == 1);
    CHECK(context.saw_ready_without_metadata == 0);
    CHECK(context.signature_calls == 1);
    CHECK(context.owner_calls == 1);
    CHECK(context.csprng_calls == 1);
    return 1;
}

static int TestSignatureRequiredAndTamper(void)
{
    WlafFixturePermitV1 permit = MakePermit();
    TestContext context;
    WlafFixtureOps ops;
    WlafResult result;
    InitContext(&context, &permit);
    ops = MakeOps(&context);
    permit.signature[7] ^= UINT8_C(1);
    result = WLAF_PublishFixtureAperture(&permit, &ops);
    CHECK(result.status == WLAF_STATUS_DENIED);
    CHECK(result.reason == WLAF_REASON_SIGNATURE_REJECTED);
    CHECK(ApertureIsZero(&context));
    CHECK(context.owner_calls == 0);
    CHECK(context.csprng_calls == 0);
    return 1;
}

static int TestBindingAndPermitFields(void)
{
    WlafFixturePermitV1 permit = MakePermit();
    TestContext context;
    WlafFixtureOps ops;
    WlafResult result;
    InitContext(&context, &permit);
    ops = MakeOps(&context);
    context.binding.policy_epoch += UINT64_C(1);
    result = WLAF_PublishFixtureAperture(&permit, &ops);
    CHECK(result.status == WLAF_STATUS_DENIED);
    CHECK(result.reason == WLAF_REASON_BINDING_MISMATCH);
    CHECK(context.signature_calls == 0);
    CHECK(context.owner_calls == 0);
    CHECK(ApertureIsZero(&context));

    permit = MakePermit();
    permit.tp_offset = UINT32_C(0x30);
    WLAF_TestFixtureSign(&permit);
    InitContext(&context, &permit);
    ops = MakeOps(&context);
    result = WLAF_PublishFixtureAperture(&permit, &ops);
    CHECK(result.status == WLAF_STATUS_DENIED);
    CHECK(result.reason == WLAF_REASON_PERMIT_FIELDS_INVALID);
    CHECK(context.binding_calls == 0);
    CHECK(ApertureIsZero(&context));
    return 1;
}

static int TestOwnerBounds(void)
{
    WlafFixturePermitV1 permit = MakePermit();
    TestContext context;
    WlafFixtureOps ops;
    WlafResult result;
    InitContext(&context, &permit);
    context.owner_start = UINT32_C(0x18);
    ops = MakeOps(&context);
    result = WLAF_PublishFixtureAperture(&permit, &ops);
    CHECK(result.status == WLAF_STATUS_DENIED);
    CHECK(result.reason == WLAF_REASON_OWNER_BOUNDS);
    CHECK(context.csprng_calls == 0);
    CHECK(ApertureIsZero(&context));
    return 1;
}

static int TestCsprngFailureIsTerminalAndNoFallback(void)
{
    WlafFixturePermitV1 permit = MakePermit();
    TestContext context;
    WlafFixtureOps ops;
    WlafResult result;
    InitContext(&context, &permit);
    context.csprng_accept = 0;
    ops = MakeOps(&context);
    result = WLAF_PublishFixtureAperture(&permit, &ops);
    CHECK(result.status == WLAF_STATUS_TERMINAL);
    CHECK(result.reason == WLAF_REASON_CSPRNG_FAILED);
    CHECK(result.publication_state == WLAF_PUBLICATION_FAILED);
    CHECK(ApertureIsZero(&context));
    CHECK(context.ready_events == 0);
    result = WLAF_PublishFixtureAperture(&permit, &ops);
    CHECK(result.status == WLAF_STATUS_DENIED);
    CHECK(result.reason == WLAF_REASON_PERMIT_REPLAY);
    CHECK(context.csprng_calls == 1);
    return 1;
}

static int TestZeroGuardRejected(void)
{
    WlafFixturePermitV1 permit = MakePermit();
    TestContext context;
    WlafFixtureOps ops;
    WlafResult result;
    InitContext(&context, &permit);
    context.csprng_zero = 1;
    ops = MakeOps(&context);
    result = WLAF_PublishFixtureAperture(&permit, &ops);
    CHECK(result.status == WLAF_STATUS_TERMINAL);
    CHECK(result.reason == WLAF_REASON_GUARD_VALUE_INVALID);
    CHECK(result.publication_state == WLAF_PUBLICATION_FAILED);
    CHECK(ApertureIsZero(&context));
    CHECK(context.ready_events == 0);
    return 1;
}

static int TestOneShotReplay(void)
{
    WlafFixturePermitV1 permit = MakePermit();
    TestContext context;
    WlafFixtureOps ops;
    WlafResult first;
    WlafResult second;
    uint64_t first_guard;
    InitContext(&context, &permit);
    ops = MakeOps(&context);
    first = WLAF_PublishFixtureAperture(&permit, &ops);
    CHECK(first.status == WLAF_STATUS_OK);
    first_guard = context.publication.guard_value;
    second = WLAF_PublishFixtureAperture(&permit, &ops);
    CHECK(second.status == WLAF_STATUS_DENIED);
    CHECK(second.reason == WLAF_REASON_PERMIT_REPLAY);
    CHECK(context.publication.guard_value == first_guard);
    CHECK(context.csprng_calls == 1);
    CHECK(context.ready_events == 1);
    return 1;
}

static int TestAuditCorePermitCannotActivate(void)
{
    WlafFixturePermitV1 permit;
    WlafFixturePermitV1 valid_permit = MakePermit();
    WlncLoadPermit core_permit;
    TestContext context;
    WlafFixtureOps ops;
    WlafResult result;
    (void)memset(&core_permit, 0, sizeof(core_permit));
    core_permit.abi_version = WLNC_ABI_VERSION;
    core_permit.mechanism = WLNC_MECHANISM_AUDIT_ONLY;
    (void)memset(&permit, 0, sizeof(permit));
    (void)memcpy(&permit, &core_permit, sizeof(core_permit));
    InitContext(&context, &valid_permit);
    ops = MakeOps(&context);
    result = WLAF_PublishFixtureAperture(&permit, &ops);
    CHECK(result.status == WLAF_STATUS_DENIED);
    CHECK(result.reason == WLAF_REASON_ABI_MISMATCH);
    CHECK(context.binding_calls == 0);
    CHECK(context.signature_calls == 0);
    CHECK(context.owner_calls == 0);
    CHECK(context.csprng_calls == 0);
    CHECK(ApertureIsZero(&context));
    return 1;
}

static int TestMissingCallbacksCannotActivate(void)
{
    WlafFixturePermitV1 permit = MakePermit();
    TestContext context;
    WlafFixtureOps ops;
    WlafResult result;
    InitContext(&context, &permit);
    ops = MakeOps(&context);
    ops.verify_fixture_signature = (WlafVerifyFixtureSignature)0;
    result = WLAF_PublishFixtureAperture(&permit, &ops);
    CHECK(result.status == WLAF_STATUS_INVALID_ARGUMENT);
    CHECK(result.reason == WLAF_REASON_INVALID_ARGUMENT);
    CHECK(ApertureIsZero(&context));
    return 1;
}

int main(void)
{
    int passed = 0;
    passed += TestPositivePublication();
    passed += TestSignatureRequiredAndTamper();
    passed += TestBindingAndPermitFields();
    passed += TestOwnerBounds();
    passed += TestCsprngFailureIsTerminalAndNoFallback();
    passed += TestZeroGuardRejected();
    passed += TestOneShotReplay();
    passed += TestAuditCorePermitCannotActivate();
    passed += TestMissingCallbacksCannotActivate();
    if (passed != 9) {
        (void)fprintf(stderr, "FAIL aperture fixture host tests passed=%d/9\n",
                      passed);
        return 1;
    }
    (void)printf("PASS aperture fixture host tests=9\n");
    return 0;
}
