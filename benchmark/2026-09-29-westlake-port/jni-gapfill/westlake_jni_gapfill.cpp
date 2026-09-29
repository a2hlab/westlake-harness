// libwestlake_jni_gapfill.so — jni-noimpl 簇补缺(r17a 排名①,40min 限时)
//
// 照抄源(vm-copies/westlake-current @ 532633d,一手行号):
//   android_os_Process.cpp L20-21 + oh_process_cpu_time.cpp L14-28
//     -> android.os.Process.getElapsedCpuTime()J(CLOCK_PROCESS_CPUTIME_ID,毫秒截断,同 AOSP)
//   class_library_services.cpp L68-127 + L410-427
//     -> android.os.FileObserver$ObserverThread init/observe/startWatching/stopWatching
//        (inotify 全真实现,回调 onEvent(IILjava/lang/String;)V)
//   activity_manager_adapter.cpp L130-135(L209 注册表)
//     -> ActivityManagerAdapter.nativeStopServiceAbility(bundle,ability)I —— 该文件在
//        #91 westlake-commonevent 包里整文件照抄;此处注册一个转发桩(返回 0=START_
//        DELIVERED_TO_TOP 语义成功),避免与该包链接冲突。
// Westlake 没有的给类型正确空桩(绝不返回会 NPE 的 null):
//   android.hardware.Camera.getNumberOfCameras()I -> 0
//   com.google.android.gles_jni.EGLImpl._nativeClassInit()V -> no-op
// 每个 RegisterNatives 单独 try:类找不到只 log 继续(硬要求③)。
// 交 cx-t0:runtime JAR System.load(同 TLS/HTML 模式);cx-bms 全量清单出来后,
// Westlake 有实现的符号逐个并入(README 记追加点)。
#include <jni.h>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <ctime>
#include <unistd.h>
#include <errno.h>
#include <algorithm>
#include <vector>
#include <sys/inotify.h>
#include <sys/resource.h>
#include <fcntl.h>

namespace {

void logf_(const char* fmt, ...) __attribute__((format(printf, 1, 2)));
void logf_(const char* fmt, ...) {
    char b[512];
    va_list ap; va_start(ap, fmt);
    int n = vsnprintf(b, sizeof b, fmt, ap);
    va_end(ap);
    if (n > 0) { ssize_t w = write(2, b, static_cast<size_t>(n)); (void)w; }
}

// ---------- android.os.Process.getElapsedCpuTime (Westlake oh_process_cpu_time.cpp L14-18) ----------
jlong Process_getElapsedCpuTime(JNIEnv*, jclass) {
    timespec ts{};
    if (clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &ts) != 0) return 0;
    return static_cast<jlong>(ts.tv_sec) * 1000 + ts.tv_nsec / 1000000;
}

// ---------- android.os.FileObserver (Westlake class_library_services.cpp L68-127) ----------
jmethodID g_on_event;

jint FileObserver_init(JNIEnv*, jobject) {
    return static_cast<jint>(inotify_init1(IN_CLOEXEC));
}

void FileObserver_observe(JNIEnv* env, jobject observer, jint fd) {
    alignas(inotify_event) char buffer[4096];
    for (;;) {
        const ssize_t count = read(fd, buffer, sizeof(buffer));
        if (count < 0) {
            if (errno == EINTR) continue;
            return;
        }
        if (count == 0) return;
        size_t offset = 0;
        while (offset + sizeof(inotify_event) <= static_cast<size_t>(count)) {
            const auto* event = reinterpret_cast<const inotify_event*>(buffer + offset);
            const size_t event_size = sizeof(inotify_event) + event->len;
            if (offset + event_size > static_cast<size_t>(count)) break;
            jstring path = event->len != 0 ? env->NewStringUTF(event->name) : nullptr;
            env->CallVoidMethod(observer, g_on_event,
                                static_cast<jint>(event->wd),
                                static_cast<jint>(event->mask), path);
            if (path != nullptr) env->DeleteLocalRef(path);
            if (env->ExceptionCheck()) env->ExceptionClear();
            offset += event_size;
        }
    }
}

void FileObserver_start_watching(JNIEnv* env, jobject, jint fd,
                                 jobjectArray paths, jint mask, jintArray wds) {
    if (fd < 0 || paths == nullptr || wds == nullptr) return;
    const jsize count = std::min(env->GetArrayLength(paths), env->GetArrayLength(wds));
    std::vector<jint> descriptors(static_cast<size_t>(count), -1);
    for (jsize i = 0; i < count; ++i) {
        auto path = static_cast<jstring>(env->GetObjectArrayElement(paths, i));
        const char* chars = path != nullptr ? env->GetStringUTFChars(path, nullptr) : nullptr;
        if (chars != nullptr) {
            descriptors[static_cast<size_t>(i)] = inotify_add_watch(fd, chars, mask);
            env->ReleaseStringUTFChars(path, chars);
        }
        if (path != nullptr) env->DeleteLocalRef(path);
    }
    if (count != 0) env->SetIntArrayRegion(wds, 0, count, descriptors.data());
}

void FileObserver_stop_watching(JNIEnv* env, jobject, jint fd, jintArray watches) {
    if (fd < 0 || watches == nullptr) return;
    const jsize count = env->GetArrayLength(watches);
    std::vector<jint> descriptors(static_cast<size_t>(count));
    if (count != 0) env->GetIntArrayRegion(watches, 0, count, descriptors.data());
    for (jint d : descriptors) if (d >= 0) inotify_rm_watch(fd, d);
}

// ---------- ActivityManagerAdapter.nativeStopServiceAbility ----------
// (Westlake activity_manager_adapter.cpp L130-135 真实现随 #91 commonevent 包链接;
//  此处独立桩:返回 0 = 成功语义,类型正确)
jint AMSA_nativeStopServiceAbility(JNIEnv*, jclass, jstring, jstring) { return 0; }

// ---------- 空桩(类型正确,绝不 null) ----------
jint Camera_getNumberOfCameras(JNIEnv*, jclass) { return 0; }        // opencamera
void EGLImpl_nativeClassInit(JNIEnv*, jclass) {}                     // spd

void try_register(JNIEnv* env, const char* cls, const char* tag,
                  const JNINativeMethod* methods, int n) {
    jclass c = env->FindClass(cls);
    if (c == nullptr || env->ExceptionCheck()) {
        env->ExceptionClear();
        logf_("[JNI-GAPFILL] %s: class %s not found — skip\n", tag, cls);
        return;
    }
    jint rc = env->RegisterNatives(c, methods, n);
    if (env->ExceptionCheck()) env->ExceptionClear();
    logf_("[JNI-GAPFILL] %s RegisterNatives(%s, %d) rc=%d\n", tag, cls, n, (int)rc);
    env->DeleteLocalRef(c);
}

void install(JNIEnv* env) {
    {   // android.os.Process.getElapsedCpuTime
        const JNINativeMethod m[] = {
            {"getElapsedCpuTime", "()J", reinterpret_cast<void*>(Process_getElapsedCpuTime)}};
        try_register(env, "android/os/Process", "Process", m, 1);
    }
    {   // FileObserver$ObserverThread: need onEvent first (Westlake L411-413)
        jclass obs = env->FindClass("android/os/FileObserver$ObserverThread");
        if (obs != nullptr && !env->ExceptionCheck()) {
            g_on_event = env->GetMethodID(obs, "onEvent", "(IILjava/lang/String;)V");
            if (g_on_event == nullptr && env->ExceptionCheck()) env->ExceptionClear();
            env->DeleteLocalRef(obs);
        } else if (env->ExceptionCheck()) env->ExceptionClear();
        const JNINativeMethod m[] = {
            {"init", "()I", reinterpret_cast<void*>(FileObserver_init)},
            {"observe", "(I)V", reinterpret_cast<void*>(FileObserver_observe)},
            {"startWatching", "(I[Ljava/lang/String;I[I)V",
             reinterpret_cast<void*>(FileObserver_start_watching)},
            {"stopWatching", "(I[I)V", reinterpret_cast<void*>(FileObserver_stop_watching)}};
        try_register(env, "android/os/FileObserver$ObserverThread", "FileObserver", m, 4);
    }
    {   // ActivityManagerAdapter.nativeStopServiceAbility(String,String)I
        const JNINativeMethod m[] = {
            {"nativeStopServiceAbility", "(Ljava/lang/String;Ljava/lang/String;)I",
             reinterpret_cast<void*>(AMSA_nativeStopServiceAbility)}};
        try_register(env, "adapter/activity/ActivityManagerAdapter", "StopService", m, 1);
    }
    {   // android.hardware.Camera.getNumberOfCameras
        const JNINativeMethod m[] = {
            {"getNumberOfCameras", "()I", reinterpret_cast<void*>(Camera_getNumberOfCameras)}};
        try_register(env, "android/hardware/Camera", "Camera", m, 1);
    }
    {   // com.google.android.gles_jni.EGLImpl._nativeClassInit
        const JNINativeMethod m[] = {
            {"_nativeClassInit", "()V", reinterpret_cast<void*>(EGLImpl_nativeClassInit)}};
        try_register(env, "com/google/android/gles_jni/EGLImpl", "EGLImpl", m, 1);
    }
}

}  // namespace

extern "C" JNIEXPORT jint JNI_OnLoad(JavaVM* vm, void*) {
    JNIEnv* env = nullptr;
    if (vm == nullptr ||
        vm->GetEnv(reinterpret_cast<void**>(&env), JNI_VERSION_1_6) != JNI_OK ||
        env == nullptr) return JNI_ERR;
    install(env);
    return JNI_VERSION_1_6;
}
