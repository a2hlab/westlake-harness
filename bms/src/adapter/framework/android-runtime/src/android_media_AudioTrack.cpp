// Minimal android.media.AudioTrack JNI backed by the OpenHarmony native
// AudioRenderer. The first consumer is FMOD's streaming PCM16 stereo path.

#include <jni.h>

#include <ohaudio/native_audiorenderer.h>
#include <ohaudio/native_audiostreambuilder.h>

#include <pthread.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

namespace android {
namespace {

constexpr jint kSuccess = 0;
constexpr jint kBadValue = -2;
constexpr jint kInvalidOperation = -3;
constexpr jint kWouldBlock = -7;
constexpr jint kPcm16 = 2;
constexpr jint kChannelOutStereo = 0x0c;
constexpr size_t kBytesPerFrame = 4;
constexpr size_t kFmodCallbackFrames = 1024;
constexpr size_t kFmodCallbackBytes = kFmodCallbackFrames * kBytesPerFrame;

struct TrackState {
    OH_AudioRenderer* renderer;
    pthread_mutex_t mutex;
    pthread_cond_t writable;
    uint8_t* ring;
    size_t capacity;
    size_t readOffset;
    size_t queued;
    uint64_t framesRendered;
    jint sampleRate;
    bool started;
    bool released;
};

jfieldID gNativeTrackField = nullptr;

TrackState* getTrack(JNIEnv* env, jobject audioTrack) {
    return reinterpret_cast<TrackState*>(
        env->GetLongField(audioTrack, gNativeTrackField));
}

void setTrack(JNIEnv* env, jobject audioTrack, TrackState* state) {
    env->SetLongField(audioTrack, gNativeTrackField,
        reinterpret_cast<jlong>(state));
}

int32_t onWriteData(OH_AudioRenderer*, void* userData, void* buffer,
                    int32_t length) {
    auto* state = static_cast<TrackState*>(userData);
    if (!state || !buffer || length <= 0) {
        return AUDIOSTREAM_ERROR_INVALID_PARAM;
    }

    pthread_mutex_lock(&state->mutex);
    size_t requested = static_cast<size_t>(length);
    size_t copied = state->queued < requested ? state->queued : requested;
    size_t first = copied;
    if (first > state->capacity - state->readOffset) {
        first = state->capacity - state->readOffset;
    }
    if (first != 0) {
        memcpy(buffer, state->ring + state->readOffset, first);
    }
    if (copied > first) {
        memcpy(static_cast<uint8_t*>(buffer) + first, state->ring,
               copied - first);
    }
    if (copied < requested) {
        memset(static_cast<uint8_t*>(buffer) + copied, 0,
               requested - copied);
    }
    state->readOffset = (state->readOffset + copied) % state->capacity;
    state->queued -= copied;
    state->framesRendered += copied / kBytesPerFrame;
    pthread_cond_broadcast(&state->writable);
    pthread_mutex_unlock(&state->mutex);
    return AUDIOSTREAM_SUCCESS;
}

void destroyTrack(TrackState* state) {
    if (!state) return;
    pthread_mutex_lock(&state->mutex);
    state->released = true;
    state->started = false;
    pthread_cond_broadcast(&state->writable);
    pthread_mutex_unlock(&state->mutex);
    if (state->renderer) {
        OH_AudioRenderer_Stop(state->renderer);
        OH_AudioRenderer_Release(state->renderer);
    }
    pthread_cond_destroy(&state->writable);
    pthread_mutex_destroy(&state->mutex);
    free(state->ring);
    free(state);
}

jint JNICALL getMinBufferSize(JNIEnv*, jclass, jint sampleRate,
                              jint channelConfig, jint audioFormat) {
    if (sampleRate < 4000 || sampleRate > 192000 ||
        channelConfig != kChannelOutStereo || audioFormat != kPcm16) {
        return kBadValue;
    }
    return static_cast<jint>(kFmodCallbackBytes);
}

jint JNICALL getOutputSampleRate(JNIEnv*, jclass, jint) {
    return 48000;
}

jint JNICALL setup(JNIEnv* env, jobject audioTrack, jobject, jobject,
                   jintArray sampleRates, jint channelMask,
                   jint channelIndexMask, jint audioFormat,
                   jint bufferSizeInBytes, jint mode, jintArray session,
                   jobject, jlong, jboolean offload, jint, jobject, jstring) {
    if (!sampleRates || env->GetArrayLength(sampleRates) < 1 ||
        !session || env->GetArrayLength(session) < 1 ||
        channelMask != kChannelOutStereo || channelIndexMask != 0 ||
        audioFormat != kPcm16 || bufferSizeInBytes <= 0 || mode != 1 || offload) {
        return kBadValue;
    }

    jint sampleRate = 0;
    env->GetIntArrayRegion(sampleRates, 0, 1, &sampleRate);
    if (env->ExceptionCheck() || sampleRate < 4000 || sampleRate > 192000) {
        return kBadValue;
    }

    auto* state = static_cast<TrackState*>(calloc(1, sizeof(TrackState)));
    if (!state) return kInvalidOperation;
    state->sampleRate = sampleRate;
    state->capacity = static_cast<size_t>(bufferSizeInBytes) * 4;
    if (state->capacity < kFmodCallbackBytes * 4) {
        state->capacity = kFmodCallbackBytes * 4;
    }
    state->ring = static_cast<uint8_t*>(malloc(state->capacity));
    if (!state->ring) {
        free(state);
        return kInvalidOperation;
    }
    if (pthread_mutex_init(&state->mutex, nullptr) != 0) {
        free(state->ring);
        free(state);
        return kInvalidOperation;
    }
    if (pthread_cond_init(&state->writable, nullptr) != 0) {
        pthread_mutex_destroy(&state->mutex);
        free(state->ring);
        free(state);
        return kInvalidOperation;
    }

    OH_AudioStreamBuilder* builder = nullptr;
    OH_AudioRenderer_Callbacks callbacks{};
    callbacks.OH_AudioRenderer_OnWriteData = onWriteData;
    bool configured =
        OH_AudioStreamBuilder_Create(&builder, AUDIOSTREAM_TYPE_RENDERER) ==
            AUDIOSTREAM_SUCCESS &&
        OH_AudioStreamBuilder_SetSamplingRate(builder, sampleRate) ==
            AUDIOSTREAM_SUCCESS &&
        OH_AudioStreamBuilder_SetChannelCount(builder, 2) ==
            AUDIOSTREAM_SUCCESS &&
        OH_AudioStreamBuilder_SetSampleFormat(builder, AUDIOSTREAM_SAMPLE_S16LE) ==
            AUDIOSTREAM_SUCCESS &&
        OH_AudioStreamBuilder_SetEncodingType(
            builder, AUDIOSTREAM_ENCODING_TYPE_RAW) == AUDIOSTREAM_SUCCESS &&
        OH_AudioStreamBuilder_SetLatencyMode(
            builder, AUDIOSTREAM_LATENCY_MODE_NORMAL) == AUDIOSTREAM_SUCCESS &&
        OH_AudioStreamBuilder_SetRendererInfo(builder, AUDIOSTREAM_USAGE_GAME) ==
            AUDIOSTREAM_SUCCESS &&
        OH_AudioStreamBuilder_SetRendererCallback(builder, callbacks, state) ==
            AUDIOSTREAM_SUCCESS;
    if (configured) {
        // FMOD produces 1024 PCM16 stereo frames per write. A matching callback
        // keeps the push-to-pull bridge deterministic and avoids re-chunking.
        OH_AudioStreamBuilder_SetFrameSizeInCallback(
            builder, static_cast<int32_t>(kFmodCallbackFrames));
        configured = OH_AudioStreamBuilder_GenerateRenderer(
            builder, &state->renderer) == AUDIOSTREAM_SUCCESS;
    }
    if (builder) OH_AudioStreamBuilder_Destroy(builder);
    if (!configured || !state->renderer) {
        destroyTrack(state);
        return kInvalidOperation;
    }

    jint sessionId = 0;
    env->GetIntArrayRegion(session, 0, 1, &sessionId);
    if (sessionId == 0) {
        sessionId = 1;
        env->SetIntArrayRegion(session, 0, 1, &sessionId);
    }
    setTrack(env, audioTrack, state);
    return kSuccess;
}

void JNICALL setPlayerIId(JNIEnv*, jobject, jint) {}

void JNICALL deviceCallback(JNIEnv*, jobject) {}

void JNICALL start(JNIEnv* env, jobject audioTrack) {
    TrackState* state = getTrack(env, audioTrack);
    if (!state) return;
    if (OH_AudioRenderer_Start(state->renderer) == AUDIOSTREAM_SUCCESS) {
        pthread_mutex_lock(&state->mutex);
        state->started = true;
        pthread_mutex_unlock(&state->mutex);
    }
}

void JNICALL pause(JNIEnv* env, jobject audioTrack) {
    TrackState* state = getTrack(env, audioTrack);
    if (!state) return;
    OH_AudioRenderer_Pause(state->renderer);
    pthread_mutex_lock(&state->mutex);
    state->started = false;
    pthread_mutex_unlock(&state->mutex);
}

void JNICALL stop(JNIEnv* env, jobject audioTrack) {
    TrackState* state = getTrack(env, audioTrack);
    if (!state) return;
    OH_AudioRenderer_Stop(state->renderer);
    pthread_mutex_lock(&state->mutex);
    state->started = false;
    state->readOffset = 0;
    state->queued = 0;
    pthread_cond_broadcast(&state->writable);
    pthread_mutex_unlock(&state->mutex);
}

void JNICALL flush(JNIEnv* env, jobject audioTrack) {
    TrackState* state = getTrack(env, audioTrack);
    if (!state) return;
    OH_AudioRenderer_Flush(state->renderer);
    pthread_mutex_lock(&state->mutex);
    state->readOffset = 0;
    state->queued = 0;
    pthread_cond_broadcast(&state->writable);
    pthread_mutex_unlock(&state->mutex);
}

void JNICALL release(JNIEnv* env, jobject audioTrack) {
    TrackState* state = getTrack(env, audioTrack);
    if (!state) return;
    setTrack(env, audioTrack, nullptr);
    destroyTrack(state);
}

jint JNICALL writeBytes(JNIEnv* env, jobject audioTrack, jbyteArray audioData,
                        jint offset, jint size, jint, jboolean blocking) {
    TrackState* state = getTrack(env, audioTrack);
    if (!state || !audioData) return kInvalidOperation;
    const jsize arraySize = env->GetArrayLength(audioData);
    if (offset < 0 || size < 0 || offset > arraySize - size) return kBadValue;
    if (size == 0) return 0;

    auto* bytes = static_cast<uint8_t*>(malloc(static_cast<size_t>(size)));
    if (!bytes) return kInvalidOperation;
    env->GetByteArrayRegion(audioData, offset, size,
                            reinterpret_cast<jbyte*>(bytes));
    if (env->ExceptionCheck()) {
        free(bytes);
        return kBadValue;
    }

    size_t written = 0;
    pthread_mutex_lock(&state->mutex);
    while (written < static_cast<size_t>(size) && !state->released &&
           state->started) {
        while (state->queued == state->capacity && !state->released &&
               state->started) {
            if (!blocking) {
                pthread_mutex_unlock(&state->mutex);
                free(bytes);
                return written == 0 ? kWouldBlock : static_cast<jint>(written);
            }
            pthread_cond_wait(&state->writable, &state->mutex);
        }
        if (state->released) break;
        const size_t freeBytes = state->capacity - state->queued;
        size_t chunk = static_cast<size_t>(size) - written;
        if (chunk > freeBytes) chunk = freeBytes;
        size_t writeOffset = (state->readOffset + state->queued) % state->capacity;
        size_t first = chunk;
        if (first > state->capacity - writeOffset) {
            first = state->capacity - writeOffset;
        }
        memcpy(state->ring + writeOffset, bytes + written, first);
        if (chunk > first) {
            memcpy(state->ring, bytes + written + first, chunk - first);
        }
        state->queued += chunk;
        written += chunk;
    }
    const bool usable = !state->released && state->started;
    pthread_mutex_unlock(&state->mutex);
    free(bytes);
    return usable ? static_cast<jint>(written) : kInvalidOperation;
}

jint JNICALL getPosition(JNIEnv* env, jobject audioTrack) {
    TrackState* state = getTrack(env, audioTrack);
    if (!state) return 0;
    pthread_mutex_lock(&state->mutex);
    jint position = static_cast<jint>(state->framesRendered & 0xffffffffu);
    pthread_mutex_unlock(&state->mutex);
    return position;
}

const JNINativeMethod kMethods[] = {
    { "native_get_min_buff_size", "(III)I",
      reinterpret_cast<void*>(getMinBufferSize) },
    { "native_get_output_sample_rate", "(I)I",
      reinterpret_cast<void*>(getOutputSampleRate) },
    { "native_setup",
      "(Ljava/lang/Object;Ljava/lang/Object;[IIIIII[ILandroid/os/Parcel;JZILjava/lang/Object;Ljava/lang/String;)I",
      reinterpret_cast<void*>(setup) },
    { "native_setPlayerIId", "(I)V", reinterpret_cast<void*>(setPlayerIId) },
    { "native_enableDeviceCallback", "()V",
      reinterpret_cast<void*>(deviceCallback) },
    { "native_disableDeviceCallback", "()V",
      reinterpret_cast<void*>(deviceCallback) },
    { "native_start", "()V", reinterpret_cast<void*>(start) },
    { "native_pause", "()V", reinterpret_cast<void*>(pause) },
    { "native_stop", "()V", reinterpret_cast<void*>(stop) },
    { "native_flush", "()V", reinterpret_cast<void*>(flush) },
    { "native_release", "()V", reinterpret_cast<void*>(release) },
    { "native_finalize", "()V", reinterpret_cast<void*>(release) },
    { "native_write_byte", "([BIIIZ)I", reinterpret_cast<void*>(writeBytes) },
    { "native_get_position", "()I", reinterpret_cast<void*>(getPosition) },
};

}  // namespace

__attribute__((visibility("hidden")))
int register_android_media_AudioTrack(JNIEnv* env) {
    jclass clazz = env->FindClass("android/media/AudioTrack");
    if (!clazz) {
        if (env->ExceptionCheck()) env->ExceptionClear();
        return -1;
    }
    gNativeTrackField = env->GetFieldID(
        clazz, "mNativeTrackInJavaObj", "J");
    if (!gNativeTrackField || env->ExceptionCheck()) {
        if (env->ExceptionCheck()) env->ExceptionClear();
        env->DeleteLocalRef(clazz);
        return -1;
    }
    const jint rc = env->RegisterNatives(
        clazz, kMethods, sizeof(kMethods) / sizeof(kMethods[0]));
    env->DeleteLocalRef(clazz);
    return rc == JNI_OK ? 0 : -1;
}

}  // namespace android
