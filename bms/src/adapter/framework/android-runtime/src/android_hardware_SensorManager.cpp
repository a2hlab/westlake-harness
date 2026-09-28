// ============================================================================
// android_hardware_SensorManager.cpp
//
// JNI bindings for android.hardware.SystemSensorManager (+ its inner
// $BaseEventQueue). Evidence-driven gap fill for the Unity (betweentwoworlds)
// Route-A bring-up.
//
// WHY (evidence):
//   UnityPlayer.toggleGyroscopeSensor(boolean)  [jadx UnityPlayer.java:1051]
//     android.hardware.SensorManager sm =
//         (SensorManager) ctx.getSystemService("sensor");   // -> SystemSensorManager
//     Sensor s = sm.getDefaultSensor(11 /*TYPE_ROTATION_VECTOR*/);
//     if (z) sm.registerListener(m_FakeListener, s, 1); else sm.unregisterListener(...);
//
//   getSystemService("sensor") instantiates android.hardware.SystemSensorManager,
//   whose constructor (frameworks/base .../SystemSensorManager.java:144-167)
//   *unconditionally* calls:
//        nativeClassInit()              (once, guarded by sNativeClassInited)
//        nativeCreate(opPackageName)
//        nativeGetSensorAtIndex(...)    in a loop to build the sensor list
//   So merely obtaining the sensor service is a hard UnsatisfiedLinkError abort
//   if these natives are unregistered — exactly the android.os.Debug wall shape.
//   AOSP registers these in libandroid_runtime.so
//   (register_android_hardware_SensorManager); the WestLake adapter had not yet
//   ported them.
//
// SEMANTICS — "zero sensors", design-consistent with the already-shipped NDK
//   ASensor* stub (android_ndk_libandroid_shim.cpp: getDefaultSensor->null,
//   getSensorList->0). We report an empty sensor list:
//     nativeGetSensorAtIndex returns false at index 0  -> mFullSensorsList empty
//   Therefore getDefaultSensor(11) returns null and
//   SystemSensorManager.registerListenerImpl (SystemSensorManager.java:243:
//   `if (listener == null || sensor == null) ... return false;`) returns false
//   *without throwing* — i.e. exactly the graceful behaviour of a real Android
//   device that has no rotation-vector sensor. The native abort is replaced by
//   a benign "no gyro available". The $BaseEventQueue natives are stubbed too
//   (never reached on the zero-sensor path, but registered for robustness so a
//   future non-empty path cannot regress into a fresh UnsatisfiedLinkError).
//
//   Handles (nativeCreate / nativeInitBaseEventQueue) return a non-zero sentinel
//   so the Java side's `mNativeInstance != 0` style checks stay happy; we never
//   dereference them.
//
// Registration is per-method and failure-tolerant (mirrors android_os_Debug.cpp)
// so any single signature drift across OH boot-image revisions of
// SystemSensorManager.java skips just that method instead of aborting the class.
// ============================================================================

#include "AndroidRuntime.h"

#include <jni.h>
#include <stdint.h>

namespace android {

namespace {

// Non-zero sentinel handles. Never dereferenced by these stubs.
constexpr jlong kSensorManagerToken = 1;
constexpr jlong kEventQueueToken    = 1;

// ---- android.hardware.SystemSensorManager -------------------------------

void  JNICALL SSM_nativeClassInit(JNIEnv*, jclass) {
    // No Sensor field-ID caching needed: we never populate a Sensor object
    // (nativeGetSensorAtIndex always reports "no more sensors").
}

jlong JNICALL SSM_nativeCreate(JNIEnv*, jclass, jstring /*opPackageName*/) {
    return kSensorManagerToken;
}

// Return false => ends the constructor's sensor-enumeration loop => empty list.
jboolean JNICALL SSM_nativeGetSensorAtIndex(JNIEnv*, jclass, jlong /*nativeInstance*/,
                                            jobject /*sensor*/, jint /*index*/) {
    return JNI_FALSE;
}

void JNICALL SSM_nativeGetDynamicSensors(JNIEnv*, jclass, jlong /*nativeInstance*/,
                                         jobject /*list*/) {
    // Leave the List untouched: no dynamic sensors.
}

void JNICALL SSM_nativeGetRuntimeSensors(JNIEnv*, jclass, jlong /*nativeInstance*/,
                                         jint /*deviceId*/, jobject /*list*/) {
    // Leave the List untouched: no runtime (virtual-device) sensors.
}

jboolean JNICALL SSM_nativeIsDataInjectionEnabled(JNIEnv*, jclass, jlong /*nativeInstance*/) {
    return JNI_FALSE;
}

jint JNICALL SSM_nativeCreateDirectChannel(JNIEnv*, jclass, jlong /*nativeInstance*/,
                                           jint /*deviceId*/, jlong /*size*/, jint /*channelType*/,
                                           jint /*fd*/, jobject /*hardwareBuffer*/) {
    return 0;  // 0 == no channel created / unsupported
}

void JNICALL SSM_nativeDestroyDirectChannel(JNIEnv*, jclass, jlong /*nativeInstance*/,
                                            jint /*channelHandle*/) {
}

jint JNICALL SSM_nativeConfigDirectChannel(JNIEnv*, jclass, jlong /*nativeInstance*/,
                                           jint /*channelHandle*/, jint /*sensorHandle*/,
                                           jint /*rate*/) {
    return 0;
}

jint JNICALL SSM_nativeSetOperationParameter(JNIEnv*, jclass, jlong /*nativeInstance*/,
                                             jint /*handle*/, jint /*type*/,
                                             jfloatArray /*floatValues*/, jintArray /*intValues*/) {
    return 0;
}

// ---- android.hardware.SystemSensorManager$BaseEventQueue ----------------

jlong JNICALL BEQ_nativeInitBaseEventQueue(JNIEnv*, jclass, jlong /*nativeManager*/,
                                           jobject /*eventQWeak*/, jobject /*msgQ*/,
                                           jstring /*packageName*/, jint /*mode*/,
                                           jstring /*opPackageName*/, jstring /*attributionTag*/) {
    return kEventQueueToken;
}

jint JNICALL BEQ_nativeEnableSensor(JNIEnv*, jclass, jlong /*eventQ*/, jint /*handle*/,
                                    jint /*rateUs*/, jint /*maxBatchReportLatencyUs*/) {
    return 0;  // never reached with zero sensors; success-ish, delivers no events
}

jint JNICALL BEQ_nativeDisableSensor(JNIEnv*, jclass, jlong /*eventQ*/, jint /*handle*/) {
    return 0;
}

void JNICALL BEQ_nativeDestroySensorEventQueue(JNIEnv*, jclass, jlong /*eventQ*/) {
}

jint JNICALL BEQ_nativeFlushSensor(JNIEnv*, jclass, jlong /*eventQ*/) {
    return 0;
}

jint JNICALL BEQ_nativeInjectSensorData(JNIEnv*, jclass, jlong /*eventQ*/, jint /*handle*/,
                                        jfloatArray /*values*/, jint /*accuracy*/,
                                        jlong /*timestamp*/) {
    return 0;
}

struct MethodSpec {
    const char* name;
    const char* sig;
    void* fn;
};

// Signatures verbatim from AOSP frameworks/base/core/jni/
// android_hardware_SensorManager.cpp (gSystemSensorManagerMethods), cross-checked
// against the OH boot-image SystemSensorManager.java native declarations.
const MethodSpec kSsmMethods[] = {
    { "nativeClassInit",            "()V",                                  reinterpret_cast<void*>(SSM_nativeClassInit) },
    { "nativeCreate",               "(Ljava/lang/String;)J",                reinterpret_cast<void*>(SSM_nativeCreate) },
    { "nativeGetSensorAtIndex",     "(JLandroid/hardware/Sensor;I)Z",       reinterpret_cast<void*>(SSM_nativeGetSensorAtIndex) },
    { "nativeGetDynamicSensors",    "(JLjava/util/List;)V",                 reinterpret_cast<void*>(SSM_nativeGetDynamicSensors) },
    { "nativeGetRuntimeSensors",    "(JILjava/util/List;)V",                reinterpret_cast<void*>(SSM_nativeGetRuntimeSensors) },
    { "nativeIsDataInjectionEnabled","(J)Z",                                reinterpret_cast<void*>(SSM_nativeIsDataInjectionEnabled) },
    { "nativeCreateDirectChannel",  "(JIJIILandroid/hardware/HardwareBuffer;)I", reinterpret_cast<void*>(SSM_nativeCreateDirectChannel) },
    { "nativeDestroyDirectChannel", "(JI)V",                                reinterpret_cast<void*>(SSM_nativeDestroyDirectChannel) },
    { "nativeConfigDirectChannel",  "(JIII)I",                              reinterpret_cast<void*>(SSM_nativeConfigDirectChannel) },
    { "nativeSetOperationParameter","(JII[F[I)I",                           reinterpret_cast<void*>(SSM_nativeSetOperationParameter) },
};

const MethodSpec kBeqMethods[] = {
    { "nativeInitBaseEventQueue",
      "(JLjava/lang/ref/WeakReference;Landroid/os/MessageQueue;Ljava/lang/String;ILjava/lang/String;Ljava/lang/String;)J",
      reinterpret_cast<void*>(BEQ_nativeInitBaseEventQueue) },
    { "nativeEnableSensor",          "(JIII)I", reinterpret_cast<void*>(BEQ_nativeEnableSensor) },
    { "nativeDisableSensor",         "(JI)I",   reinterpret_cast<void*>(BEQ_nativeDisableSensor) },
    { "nativeDestroySensorEventQueue","(J)V",   reinterpret_cast<void*>(BEQ_nativeDestroySensorEventQueue) },
    { "nativeFlushSensor",           "(J)I",    reinterpret_cast<void*>(BEQ_nativeFlushSensor) },
    { "nativeInjectSensorData",      "(JI[FIJ)I", reinterpret_cast<void*>(BEQ_nativeInjectSensorData) },
};

int registerClassMethods(JNIEnv* env, const char* className,
                         const MethodSpec* specs, size_t n) {
    jclass clazz = env->FindClass(className);
    if (!clazz) {
        if (env->ExceptionCheck()) env->ExceptionClear();
        return -1;
    }
    int registered = 0;
    for (size_t i = 0; i < n; ++i) {
        JNINativeMethod jm = { specs[i].name, specs[i].sig, specs[i].fn };
        if (env->RegisterNatives(clazz, &jm, 1) == JNI_OK) {
            ++registered;
        } else if (env->ExceptionCheck()) {
            env->ExceptionClear();
        }
    }
    env->DeleteLocalRef(clazz);
    return registered > 0 ? 0 : -1;
}

}  // namespace

int register_android_hardware_SensorManager(JNIEnv* env) {
    // The SystemSensorManager constructor trio (nativeClassInit/nativeCreate/
    // nativeGetSensorAtIndex) is the hard dependency for getSystemService("sensor");
    // treat success of that class as success even if $BaseEventQueue drifts.
    int ssm = registerClassMethods(env, "android/hardware/SystemSensorManager",
                                   kSsmMethods, sizeof(kSsmMethods) / sizeof(kSsmMethods[0]));
    registerClassMethods(env, "android/hardware/SystemSensorManager$BaseEventQueue",
                         kBeqMethods, sizeof(kBeqMethods) / sizeof(kBeqMethods[0]));
    return ssm;
}

}  // namespace android
