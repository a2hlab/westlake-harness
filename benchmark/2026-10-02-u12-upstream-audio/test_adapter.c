#define _GNU_SOURCE 1
#include "candidate/opensles_android_adapter.c"

static unsigned char rendered[8];
static unsigned refill_count;
static const unsigned char packet[2] = {0x12, 0x34};
static SLuint32 submitted_length;

static SLresult fixture_get_buffer(SLOHBufferQueueItf self, SLuint8** buffer, SLuint32* size)
{
    (void)self;
    *buffer = rendered;
    *size = sizeof(rendered);
    return SL_RESULT_SUCCESS;
}

static SLresult fixture_submit(SLOHBufferQueueItf self, const void* buffer, SLuint32 size)
{
    (void)self;
    (void)buffer;
    submitted_length = size;
    return SL_RESULT_SUCCESS;
}

static void refill(ASbqItf self, void* context)
{
    (void)context;
    refill_count++;
    if (refill_count < 4) (*self)->Enqueue(self, packet, sizeof(packet));
}

static SLresult fixture_unsupported_register(SLPlayItf self, slPlayCallback callback, void* context)
{
    (void)self;
    (void)callback;
    (void)context;
    return SL_RESULT_FEATURE_UNSUPPORTED;
}

static SLresult fixture_unsupported_mask(SLPlayItf self, SLuint32 mask)
{
    (void)self;
    (void)mask;
    return SL_RESULT_FEATURE_UNSUPPORTED;
}

static void ignored_play_callback(APlayItf self, void* context, a_u32 event)
{
    (void)self;
    (void)context;
    (void)event;
}

static void fixture_ids_ready(void)
{
}

static SLresult fixture_object_state(SLObjectItf self, SLuint32* state)
{
    (void)self;
    *state = 3;
    return SL_RESULT_SUCCESS;
}

int main(void)
{
    const struct U12AndroidId android = {0x12345678, 0x1234, 0x5678, 0x4321, {1, 2, 3, 4, 5, 6}};
    const struct SLInterfaceID_ owner = {0x12345678, 0x1234, 0x5678, 0x4321, {1, 2, 3, 4, 5, 6}};
    const struct SLInterfaceID_ high = {0x112345678UL, 0x1234, 0x5678, 0x4321, {1, 2, 3, 4, 5, 6}};
    if (!U12EqualAndroidOwnerId(&android, &owner)) return 1;
    if (U12EqualAndroidOwnerId(&android, &high)) return 2;
    if (memcmp(&android, &owner, sizeof(android)) == 0) return 3;
    oh.engine = &owner;
    if (!iid_is((SLInterfaceID)&android, oh.engine)) return 4;
    oh_iids[0] = &owner;
    pthread_once(&oh_iids_once, fixture_ids_ready);
    oh_iids[0] = &owner;
    oh.lib = (void*)1;
    if (canon_iid((SLInterfaceID)&android) != &owner) return 5;
    if (sizeof(westlake_sl_iid_android_config) != 16 || sizeof(westlake_sl_iid_android_sbq) != 16) return 6;
    const a_u32 pcm[7] = {A_FMT_PCM, 2, 44100000, 16, 16, 3, 2};
    OhBlock format;
    if (sizeof(pcm) != 28 || sizeof(format.pcm) != 56) return 13;
    if (translate_format(pcm, &format) != &format.pcm) return 14;
    if (format.pcm.numChannels != 2 || format.pcm.samplesPerSec != 44100000 || format.pcm.bitsPerSample != 16) return 15;
    static const struct SLObjectItf_ object_methods = {.GetState = fixture_object_state};
    const struct SLObjectItf_* object_interface = &object_methods;
    Obj object = {.itf = &object_vtable, .real = &object_interface};
    struct { a_u32 state; a_u32 canary; } state = {0, 0xdeadbeef};
    if (o_get_state((AObjectItf)&object.itf, &state.state) != 0 || state.state != 3 || state.canary != 0xdeadbeef) return 16;
    static const struct SLOHBufferQueueItf_ queue_methods = {
        .Enqueue = fixture_submit,
        .GetBuffer = fixture_get_buffer,
    };
    const struct SLOHBufferQueueItf_* queue_interface = &queue_methods;
    SLOHBufferQueueItf queue = &queue_interface;
    SbqAdapter adapter = {.itf = &sbq_vtable, .oh_bq = queue};
    pthread_mutex_init(&adapter.lock, NULL);
    ASbqItf android_queue = (ASbqItf)&adapter.itf;
    sbq_register_callback(android_queue, refill, NULL);
    if (sbq_enqueue(android_queue, packet, sizeof(packet)) != SL_RESULT_SUCCESS) return 7;
    sbq_on_oh_need(queue, &adapter, sizeof(rendered));
    if (submitted_length != 8 || refill_count != 4) return 8;
    for (unsigned index = 0; index < sizeof(rendered); index++) if (rendered[index] != packet[index % 2]) return 9;
    memset(rendered, 0xff, sizeof(rendered));
    sbq_on_oh_need(queue, &adapter, sizeof(rendered));
    for (unsigned index = 0; index < sizeof(rendered); index++) if (rendered[index] != 0) return 10;
    static const struct SLPlayItf_ play_methods = {
        .RegisterCallback = fixture_unsupported_register,
        .SetCallbackEventsMask = fixture_unsupported_mask,
    };
    const struct SLPlayItf_* play_interface = &play_methods;
    PlayW play = {.itf = &play_vtable, .real = &play_interface};
    APlayItf android_play = (APlayItf)&play.itf;
    if (p_register_callback(android_play, ignored_play_callback, NULL) != 12) return 11;
    if (p_set_mask(android_play, 1) != 12) return 12;
    pthread_mutex_destroy(&adapter.lock);
    puts("PASS: Android IID16/OH IID24 field conversion, canonical pointer, continuous refill8 bytes, silence-only underrun; NEGATIVE PLAY callbacks/mask=12 retained");
    return 0;
}
