#include "candidate.c"
#include <assert.h>

static int callback_count;

static void closed(void *userdata) {
    assert(userdata != NULL);
    callback_count++;
}

int main(void) {
    _Static_assert(sizeof(off_t) == 8, "AArch64 offset ABI");
    _Static_assert(sizeof(AMediaCodecBufferInfo) == 24, "codec output ABI");
    assert(AMEDIA_ERROR_UNSUPPORTED == -10002);
    assert(AMEDIA_ERROR_UNSUPPORTED != -1002);
    assert(AMediaCodec_createDecoderByType("video/avc") == NULL);
    assert(AMediaCodec_start(NULL) == AMEDIA_ERROR_UNSUPPORTED);
    assert(AMediaCodec_dequeueInputBuffer(NULL, 0) == AMEDIA_ERROR_UNSUPPORTED);
    size_t size = 123;
    assert(AMediaCodec_getInputBuffer(NULL, 0, &size) == NULL && size == 0);
    AImageReader *reader = (AImageReader *)(uintptr_t)1;
    assert(AImageReader_newWithUsage(1, 1, 1, UINT64_C(0xffff00000000), 2, &reader) == AMEDIA_ERROR_UNSUPPORTED);
    assert(reader == NULL);
    AMediaExtractor *extractor = AMediaExtractor_new();
    assert(extractor != NULL);
    assert(AMediaExtractor_setDataSource(extractor, "file:///fixture.mp4") == AMEDIA_ERROR_UNSUPPORTED);
    assert(AMediaExtractor_getTrackCount(extractor) == 0);
    assert(AMediaExtractor_getSampleTime(extractor) == -1);
    assert(!AMediaExtractor_advance(extractor));
    assert(AMediaExtractor_delete(extractor) == AMEDIA_OK);
    AMediaFormat *format = AMediaFormat_new();
    assert(format != NULL);
    AMediaFormat_setInt32(format, "width", 1080);
    int32_t value = -1;
    assert(AMediaFormat_getInt32(format, "width", &value) && value == 1080);
    AMediaFormat_setInt32(format, "width", 1920);
    assert(AMediaFormat_getInt32(format, "width", &value) && value == 1920);
    value = 77;
    assert(!AMediaFormat_getInt32(format, "absent", &value) && value == 77);
    float floating = 33.0f;
    assert(!AMediaFormat_getFloat(format, "width", &floating) && floating == 33.0f);
    assert(AMediaFormat_delete(format) == AMEDIA_OK);
    AMediaDataSource *source = AMediaDataSource_new();
    assert(source != NULL);
    AMediaDataSource_setUserdata(source, &callback_count);
    AMediaDataSource_setClose(source, closed);
    assert(source->userdata == &callback_count && source->close == closed);
    AMediaDataSource_delete(source);
    assert(callback_count == 0);
    puts("typed media boundary PASS: unsupported=-10002, codec/image absent, real object lifetimes and int32 properties");
    return 0;
}
