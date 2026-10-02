// Minimal android.media.AudioSystem capability JNI used while the framework
// initializes AudioFormat. Real playback remains the responsibility of the
// AudioTrack/AudioRenderer bridge.

#include <jni.h>

namespace android {
namespace {

jint JNICALL getMaxChannelCount(JNIEnv*, jclass) {
    // The current D600 route is stereo; this is the smallest truthful value
    // that accepts FMOD's CHANNEL_OUT_STEREO configuration.
    return 2;
}

jint JNICALL getMaxSampleRate(JNIEnv*, jclass) {
    return 192000;
}

jint JNICALL getMinSampleRate(JNIEnv*, jclass) {
    return 4000;
}

jint JNICALL listAudioProductStrategies(JNIEnv*, jclass, jobject) {
    // The compatibility runtime has no Android audio-policy service.  An empty
    // strategy list makes AudioAttributes fall back to DEFAULT_ATTRIBUTES,
    // which is the framework-defined behavior needed by FMOD's legacy stream.
    return 0;
}

// Westlake art-build/stubs/audiosystem_jni_stub.cc:248. No Android
// AudioFlinger exists here; zero is AUDIO_UNIQUE_ID_ALLOCATE, not a claimed
// unique ID or successful playback. Keep the framework fallback explicit.
jint JNICALL newAudioSessionId(JNIEnv*, jclass) { return 0; }

const JNINativeMethod kMethods[] = {
    { "newAudioSessionId", "()I", reinterpret_cast<void*>(newAudioSessionId) },
    { "native_getMaxChannelCount", "()I", reinterpret_cast<void*>(getMaxChannelCount) },
    { "native_getMaxSampleRate",   "()I", reinterpret_cast<void*>(getMaxSampleRate) },
    { "native_getMinSampleRate",   "()I", reinterpret_cast<void*>(getMinSampleRate) },
};

}  // namespace

__attribute__((visibility("hidden")))
int register_android_media_AudioSystemCapabilities(JNIEnv* env) {
    jclass clazz = env->FindClass("android/media/AudioSystem");
    if (!clazz) {
        if (env->ExceptionCheck()) env->ExceptionClear();
        return -1;
    }
    const jint rc = env->RegisterNatives(
        clazz, kMethods, sizeof(kMethods) / sizeof(kMethods[0]));
    env->DeleteLocalRef(clazz);
    return rc == JNI_OK ? 0 : -1;
}

__attribute__((visibility("hidden")))
int register_android_media_AudioProductStrategy(JNIEnv* env) {
    jclass clazz = env->FindClass(
        "android/media/audiopolicy/AudioProductStrategy");
    if (!clazz) {
        if (env->ExceptionCheck()) env->ExceptionClear();
        return -1;
    }
    const JNINativeMethod methods[] = {
        { "native_list_audio_product_strategies", "(Ljava/util/ArrayList;)I",
          reinterpret_cast<void*>(listAudioProductStrategies) },
    };
    const jint rc = env->RegisterNatives(clazz, methods, 1);
    env->DeleteLocalRef(clazz);
    return rc == JNI_OK ? 0 : -1;
}

}  // namespace android

#if defined(WESTLAKE_AUDIO_BACKEND_EXPORT)
namespace android {
__attribute__((visibility("hidden")))
int register_android_media_AudioTrack(JNIEnv* env);
}

extern "C" __attribute__((visibility("default")))
int westlake_register_audio_compat(JNIEnv* env) {
    if (!env ||
        android::register_android_media_AudioSystemCapabilities(env) != 0 ||
        android::register_android_media_AudioProductStrategy(env) != 0 ||
        android::register_android_media_AudioTrack(env) != 0) {
        return -1;
    }
    return 0;
}
#endif
