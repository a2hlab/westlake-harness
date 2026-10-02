#include "platform.h"
#include <media/NdkMediaCodec.h>
#include <media/NdkMediaExtractor.h>
#include <media/NdkImageReader.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include "objects.c.inc"

const char westlake_mediandk_presence_provenance[] = "westlake-mediandk-v2-typed-unsupported-no-codec";

media_status_t AImageReader_acquireLatestImage(AImageReader* argument0, AImage** argument1) {
    (void)argument0;
    (void)argument1;
    if (argument1 != NULL) *argument1 = NULL;
    return unsupported_media(__func__);
}

void AImageReader_delete(AImageReader* argument0) {
    (void)argument0;
    unsupported_media(__func__);
}

media_status_t AImageReader_getWindow(AImageReader* argument0, ANativeWindow** argument1) {
    (void)argument0;
    (void)argument1;
    if (argument1 != NULL) *argument1 = NULL;
    return unsupported_media(__func__);
}

media_status_t AImageReader_newWithUsage(int32_t argument0, int32_t argument1, int32_t argument2, uint64_t argument3, int32_t argument4, AImageReader** argument5) {
    (void)argument0;
    (void)argument1;
    (void)argument2;
    (void)argument3;
    (void)argument4;
    (void)argument5;
    if (argument5 != NULL) *argument5 = NULL;
    return unsupported_media(__func__);
}

media_status_t AImageReader_setBufferRemovedListener(AImageReader* argument0, AImageReader_BufferRemovedListener* argument1) {
    (void)argument0;
    (void)argument1;
    return unsupported_media(__func__);
}

media_status_t AImageReader_setImageListener(AImageReader* argument0, AImageReader_ImageListener* argument1) {
    (void)argument0;
    (void)argument1;
    return unsupported_media(__func__);
}

void AImage_delete(AImage* argument0) {
    (void)argument0;
    unsupported_media(__func__);
}

void AImage_deleteAsync(AImage* argument0, int argument1) {
    (void)argument0;
    if (argument1 >= 0) close(argument1);
}

media_status_t AImage_getHardwareBuffer(const AImage* argument0, AHardwareBuffer** argument1) {
    (void)argument0;
    (void)argument1;
    if (argument1 != NULL) *argument1 = NULL;
    return unsupported_media(__func__);
}

media_status_t AImage_getTimestamp(const AImage* argument0, int64_t* argument1) {
    (void)argument0;
    (void)argument1;
    return unsupported_media(__func__);
}

media_status_t AImage_getWidth(const AImage* argument0, int32_t* argument1) {
    (void)argument0;
    (void)argument1;
    return unsupported_media(__func__);
}

media_status_t AMediaCodec_configure(AMediaCodec* argument0, const AMediaFormat* argument1, ANativeWindow* argument2, AMediaCrypto *argument3, uint32_t argument4) {
    (void)argument0;
    (void)argument1;
    (void)argument2;
    (void)argument3;
    (void)argument4;
    return unsupported_media(__func__);
}

AMediaCodec* AMediaCodec_createDecoderByType(const char *argument0) {
    (void)argument0;
    unsupported_media(__func__);
    return NULL;
}

media_status_t AMediaCodec_delete(AMediaCodec* argument0) {
    (void)argument0;
    return unsupported_media(__func__);
}

ssize_t AMediaCodec_dequeueInputBuffer(AMediaCodec* argument0, int64_t argument1) {
    (void)argument0;
    (void)argument1;
    return unsupported_media(__func__);
}

ssize_t AMediaCodec_dequeueOutputBuffer(AMediaCodec* argument0, AMediaCodecBufferInfo *argument1, int64_t argument2) {
    (void)argument0;
    (void)argument1;
    (void)argument2;
    return unsupported_media(__func__);
}

media_status_t AMediaCodec_flush(AMediaCodec* argument0) {
    (void)argument0;
    return unsupported_media(__func__);
}

uint8_t* AMediaCodec_getInputBuffer(AMediaCodec* argument0, size_t argument1, size_t *argument2) {
    (void)argument0;
    (void)argument1;
    (void)argument2;
    if (argument2 != NULL) *argument2 = 0;
    unsupported_media(__func__);
    return NULL;
}

uint8_t* AMediaCodec_getOutputBuffer(AMediaCodec* argument0, size_t argument1, size_t *argument2) {
    (void)argument0;
    (void)argument1;
    (void)argument2;
    if (argument2 != NULL) *argument2 = 0;
    unsupported_media(__func__);
    return NULL;
}

AMediaFormat* AMediaCodec_getOutputFormat(AMediaCodec* argument0) {
    (void)argument0;
    unsupported_media(__func__);
    return NULL;
}

media_status_t AMediaCodec_queueInputBuffer(AMediaCodec* argument0, size_t argument1, off_t argument2, size_t argument3, uint64_t argument4, uint32_t argument5) {
    (void)argument0;
    (void)argument1;
    (void)argument2;
    (void)argument3;
    (void)argument4;
    (void)argument5;
    return unsupported_media(__func__);
}

media_status_t AMediaCodec_releaseOutputBuffer(AMediaCodec* argument0, size_t argument1, bool argument2) {
    (void)argument0;
    (void)argument1;
    (void)argument2;
    return unsupported_media(__func__);
}

media_status_t AMediaCodec_setOutputSurface(AMediaCodec* argument0, ANativeWindow* argument1) {
    (void)argument0;
    (void)argument1;
    return unsupported_media(__func__);
}

media_status_t AMediaCodec_start(AMediaCodec* argument0) {
    (void)argument0;
    return unsupported_media(__func__);
}

media_status_t AMediaCodec_stop(AMediaCodec* argument0) {
    (void)argument0;
    return unsupported_media(__func__);
}

void AMediaDataSource_delete(AMediaDataSource* argument0) {
    free(argument0);
}

AMediaDataSource* AMediaDataSource_new() {
    return calloc(1, sizeof(AMediaDataSource));
}

void AMediaDataSource_setClose(AMediaDataSource* argument0, AMediaDataSourceClose argument1) {
    if (argument0 != NULL) argument0->close = argument1;
}

void AMediaDataSource_setGetSize(AMediaDataSource* argument0, AMediaDataSourceGetSize argument1) {
    if (argument0 != NULL) argument0->get_size = argument1;
}

void AMediaDataSource_setReadAt(AMediaDataSource* argument0, AMediaDataSourceReadAt argument1) {
    if (argument0 != NULL) argument0->read_at = argument1;
}

void AMediaDataSource_setUserdata(AMediaDataSource* argument0, void *argument1) {
    if (argument0 != NULL) argument0->userdata = argument1;
}

bool AMediaExtractor_advance(AMediaExtractor* argument0) {
    (void)argument0;
    return false;
}

media_status_t AMediaExtractor_delete(AMediaExtractor* argument0) {
    free(argument0);
    return AMEDIA_OK;
}

int64_t AMediaExtractor_getSampleTime(AMediaExtractor* argument0) {
    (void)argument0;
    return -1;
}

int AMediaExtractor_getSampleTrackIndex(AMediaExtractor* argument0) {
    (void)argument0;
    return -1;
}

size_t AMediaExtractor_getTrackCount(AMediaExtractor* argument0) {
    (void)argument0;
    return 0;
}

AMediaFormat* AMediaExtractor_getTrackFormat(AMediaExtractor* argument0, size_t argument1) {
    (void)argument0;
    (void)argument1;
    unsupported_media(__func__);
    return NULL;
}

AMediaExtractor* AMediaExtractor_new() {
    return calloc(1, sizeof(AMediaExtractor));
}

ssize_t AMediaExtractor_readSampleData(AMediaExtractor* argument0, uint8_t *argument1, size_t argument2) {
    (void)argument0;
    (void)argument1;
    (void)argument2;
    return -1;
}

media_status_t AMediaExtractor_seekTo(AMediaExtractor* argument0, int64_t argument1, SeekMode argument2) {
    (void)argument0;
    (void)argument1;
    (void)argument2;
    return unsupported_media(__func__);
}

media_status_t AMediaExtractor_selectTrack(AMediaExtractor* argument0, size_t argument1) {
    (void)argument0;
    (void)argument1;
    return unsupported_media(__func__);
}

media_status_t AMediaExtractor_setDataSource(AMediaExtractor* argument0, const char *argument1) {
    (void)argument0;
    (void)argument1;
    return unsupported_media(__func__);
}

media_status_t AMediaExtractor_setDataSourceCustom(AMediaExtractor* argument0, AMediaDataSource *argument1) {
    (void)argument0;
    (void)argument1;
    return unsupported_media(__func__);
}

media_status_t AMediaExtractor_setDataSourceFd(AMediaExtractor* argument0, int argument1, off64_t argument2, off64_t argument3) {
    (void)argument0;
    (void)argument1;
    (void)argument2;
    (void)argument3;
    return unsupported_media(__func__);
}

media_status_t AMediaFormat_delete(AMediaFormat* argument0) {
    delete_format(argument0);
    return AMEDIA_OK;
}

bool AMediaFormat_getFloat(AMediaFormat* argument0, const char *argument1, float *argument2) {
    (void)argument0;
    (void)argument1;
    (void)argument2;
    return false;
}

bool AMediaFormat_getInt32(AMediaFormat* argument0, const char *argument1, int32_t *argument2) {
    return get_int32(argument0, argument1, argument2);
}

bool AMediaFormat_getInt64(AMediaFormat* argument0, const char *argument1, int64_t *argument2) {
    (void)argument0;
    (void)argument1;
    (void)argument2;
    return false;
}

bool AMediaFormat_getString(AMediaFormat* argument0, const char *argument1, const char **argument2) {
    (void)argument0;
    (void)argument1;
    (void)argument2;
    return false;
}

void AMediaFormat_setInt32(AMediaFormat* argument0, const char* argument1, int32_t argument2) {
    set_int32(argument0, argument1, argument2);
}
