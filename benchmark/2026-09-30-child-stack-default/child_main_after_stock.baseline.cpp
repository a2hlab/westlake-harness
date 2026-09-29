/*
 * Android child entry owned by Route A.
 *
 * The stock OH appspawn host owns every process-security operation.  This
 * translation unit is linked only into the adapter runtime provider and starts
 * at the first Android step after the stock stage-31 tail receipt.  Keep it
 * free of credentials, namespaces, mounts, capabilities and security-context
 * transitions.
 */

#include "child_main.h"

#include "adapter_bridge_identity.h"
#include "appspawnx_runtime.h"

#include <cerrno>
#include <cstdio>
#include <cstring>
#include <dlfcn.h>
#include <fcntl.h>
#include <string>
#include <sys/prctl.h>
#include <unistd.h>

namespace appspawnx {
namespace {

void PrepareChildDiagnostics()
{
    const pid_t pid = getpid();
    const char *candidateDirectories[] = {
        "/data/service/el1/public/appspawnx",
        "/data/misc/appspawnx",
        "/data/local/tmp",
        "/data/log",
    };
    int errorFd = -1;
    char chosenPath[128] = {0};
    for (const char *directory : candidateDirectories) {
        (void)snprintf(chosenPath, sizeof(chosenPath),
                       "%s/adapter_child_%d.stderr", directory, pid);
        errorFd = open(chosenPath, O_WRONLY | O_CREAT | O_TRUNC, 0666);
        if (errorFd >= 0) {
            break;
        }
    }
    if (errorFd < 0) {
        LOGW("[ROUTE-A] child diagnostic fd unavailable: errno=%d %s",
             errno, strerror(errno));
        return;
    }
    (void)dup2(errorFd, STDERR_FILENO);
    (void)dup2(errorFd, STDOUT_FILENO);
    if (errorFd != STDOUT_FILENO && errorFd != STDERR_FILENO) {
        (void)close(errorFd);
    }
    (void)setvbuf(stderr, nullptr, _IOLBF, 0);
    LOGI("[ROUTE-A] native child diagnostics: %s", chosenPath);
}

void MarkGraphicsChild()
{
    constexpr const char *kLoadedHwuiPath =
        "/system/android/lib64/libhwui.so";
    using MarkFunction = void (*)(void);
    void *hwui = dlopen(kLoadedHwuiPath, RTLD_NOW | RTLD_NOLOAD);
    if (hwui == nullptr) {
        LOGW("[ROUTE-A] exact loaded libhwui unavailable for graphics child marker: %s",
             dlerror());
        return;
    }
    MarkFunction mark = reinterpret_cast<MarkFunction>(
        dlsym(hwui, "oh_typeface_mark_child"));
    if (mark != nullptr) {
        mark();
        LOGI("[ROUTE-A] graphics child marker installed");
    } else {
        LOGW("[ROUTE-A] graphics child marker absent from exact libhwui load group: %s",
             dlerror());
    }
}

void TypefaceWarmUpNoOp(JNIEnv *, jclass, jstring)
{
}

bool InstallTypefaceWarmUpOverride(JNIEnv *env)
{
    jclass typeface = env->FindClass("android/graphics/Typeface");
    if (typeface == nullptr) {
        if (env->ExceptionCheck()) {
            env->ExceptionDescribe();
            env->ExceptionClear();
        }
        LOGE("[ROUTE-A] Typeface warmup override class lookup failed");
        return false;
    }
    const JNINativeMethod method = {
        const_cast<char *>("nativeWarmUpCache"),
        const_cast<char *>("(Ljava/lang/String;)V"),
        reinterpret_cast<void *>(TypefaceWarmUpNoOp),
    };
    const jint rc = env->RegisterNatives(typeface, &method, 1);
    env->DeleteLocalRef(typeface);
    if (rc != JNI_OK || env->ExceptionCheck()) {
        if (env->ExceptionCheck()) {
            env->ExceptionDescribe();
            env->ExceptionClear();
        }
        LOGE("[ROUTE-A] Typeface warmup no-op override failed rc=%d", rc);
        return false;
    }
    LOGI("[ROUTE-A] Typeface nativeWarmUpCache overridden to child-safe no-op");
    return true;
}

int InitAdapterLayerAfterStock(JNIEnv *env, AppSpawnXRuntime *runtime)
{
    LOGI("[ROUTE-A] initializing adapter layer");
    jclass environmentClass = runtime->loadClassViaPath(
        env, "adapter.core.OHEnvironment");
    if (environmentClass == nullptr) {
        if (env->ExceptionCheck()) {
            env->ExceptionDescribe();
            env->ExceptionClear();
        }
        return -1;
    }
    jmethodID initialize = env->GetStaticMethodID(
        environmentClass, "initialize", "()V");
    if (initialize == nullptr) {
        if (env->ExceptionCheck()) {
            env->ExceptionDescribe();
            env->ExceptionClear();
        }
        env->DeleteLocalRef(environmentClass);
        return -1;
    }
    env->CallStaticVoidMethod(environmentClass, initialize);
    if (env->ExceptionCheck()) {
        env->ExceptionDescribe();
        env->ExceptionClear();
        env->DeleteLocalRef(environmentClass);
        return -1;
    }
    env->DeleteLocalRef(environmentClass);
    return 0;
}

bool ReinjectAdapterClassLoader(JNIEnv *env, AppSpawnXRuntime *runtime)
{
    jobject childLoader = runtime->getPathClassLoader();
    jmethodID loadClass = runtime->getClassLoaderLoadClass();
    JavaVM *vm = runtime->getJavaVM();
    if (childLoader == nullptr || loadClass == nullptr || vm == nullptr) {
        LOGE("[ROUTE-A] child adapter class loader unavailable");
        return false;
    }
    void *bridge = dlopen("liboh_adapter_bridge.so", RTLD_NOLOAD | RTLD_NOW);
    if (bridge == nullptr || !VerifyLoadedAdapterBridge(bridge)) {
        if (bridge != nullptr) {
            (void)dlclose(bridge);
        }
        LOGE("[ROUTE-A] exact inherited adapter bridge unavailable for child class-loader binding");
        return false;
    }
    using SetterFunction = void (*)(JavaVM *, jobject, jmethodID);
    SetterFunction setter = reinterpret_cast<SetterFunction>(
        dlsym(bridge, "adapter_bridge_set_class_loader"));
    if (setter == nullptr) {
        LOGE("[ROUTE-A] adapter class-loader setter absent");
        return false;
    }
    setter(vm, childLoader, loadClass);
    if (env->ExceptionCheck()) {
        env->ExceptionDescribe();
        env->ExceptionClear();
        LOGE("[ROUTE-A] adapter class-loader binding threw");
        return false;
    }
    LOGI("[ROUTE-A] child adapter class loader bound");
    return true;
}

void LogPendingChildException(JNIEnv *env)
{
    jthrowable throwable = env->ExceptionOccurred();
    env->ExceptionClear();
    if (throwable == nullptr) {
        return;
    }
    jclass throwableClass = env->GetObjectClass(throwable);
    jmethodID getMessage = throwableClass == nullptr ? nullptr :
        env->GetMethodID(throwableClass, "getMessage", "()Ljava/lang/String;");
    jstring message = getMessage == nullptr ? nullptr :
        static_cast<jstring>(env->CallObjectMethod(throwable, getMessage));
    if (env->ExceptionCheck()) {
        env->ExceptionClear();
    }
    const char *text = message == nullptr ? nullptr :
        env->GetStringUTFChars(message, nullptr);
    LOGE("[ROUTE-A] Android child exception: %s",
         text == nullptr ? "<no message>" : text);
    if (text != nullptr) {
        env->ReleaseStringUTFChars(message, text);
    }
    if (message != nullptr) {
        env->DeleteLocalRef(message);
    }
    if (throwableClass != nullptr) {
        env->DeleteLocalRef(throwableClass);
    }
    env->DeleteLocalRef(throwable);
}

void LaunchActivityThreadAfterStock(JNIEnv *env, const SpawnMsg &message,
                                    AppSpawnXRuntime *runtime)
{
    const std::string targetClass = message.targetClass.empty() ?
        "android.app.ActivityThread" : message.targetClass;
    jclass initClass = runtime->getAppSpawnXInitClass();
    bool localClass = false;
    if (initClass == nullptr) {
        initClass = runtime->loadClassViaPath(
            env, "com.android.internal.os.AppSpawnXInit");
        localClass = initClass != nullptr;
    }
    if (initClass == nullptr) {
        LOGE("[ROUTE-A] AppSpawnXInit unavailable");
        return;
    }
    jmethodID initChild = env->GetStaticMethodID(
        initClass, "initChild", "(Ljava/lang/String;Ljava/lang/String;I)V");
    if (initChild == nullptr) {
        if (env->ExceptionCheck()) {
            env->ExceptionDescribe();
            env->ExceptionClear();
        }
        if (localClass) {
            env->DeleteLocalRef(initClass);
        }
        LOGE("[ROUTE-A] AppSpawnXInit.initChild unavailable");
        return;
    }
    jstring processName = env->NewStringUTF(message.procName.c_str());
    jstring targetName = env->NewStringUTF(targetClass.c_str());
    if (processName == nullptr || targetName == nullptr) {
        if (env->ExceptionCheck()) {
            env->ExceptionClear();
        }
        if (processName != nullptr) {
            env->DeleteLocalRef(processName);
        }
        if (targetName != nullptr) {
            env->DeleteLocalRef(targetName);
        }
        if (localClass) {
            env->DeleteLocalRef(initClass);
        }
        LOGE("[ROUTE-A] child launch argument allocation failed");
        return;
    }
    LOGI("[ROUTE-A] entering AppSpawnXInit.initChild proc=%s target=%s sdk=%d",
         message.procName.c_str(), targetClass.c_str(),
         message.targetSdkVersion);
    env->CallStaticVoidMethod(initClass, initChild, processName, targetName,
                              static_cast<jint>(message.targetSdkVersion));
    if (env->ExceptionCheck()) {
        LogPendingChildException(env);
    } else {
        LOGE("[ROUTE-A] Android event loop returned unexpectedly");
    }
    env->DeleteLocalRef(processName);
    env->DeleteLocalRef(targetName);
    if (localClass) {
        env->DeleteLocalRef(initClass);
    }
}

} // namespace

[[noreturn]] void ChildMain::runAfterStockSpecialization(
    const SpawnMsg &message, AppSpawnXRuntime *runtime)
{
    if (runtime == nullptr || message.procName.empty() ||
        message.bundleName.empty()) {
        LOGE("[ROUTE-A] invalid post-specialization child input");
        _exit(18);
    }

    LOGI("[ROUTE-A] stock stage31 complete; entering Android child pid=%d uid=%d bundle=%s",
         getpid(), getuid(), message.bundleName.c_str());
    PrepareChildDiagnostics();
    MarkGraphicsChild();

    // The stock host has already forked and specialized this process before
    // the sealed provider creates its JavaVM.  There is therefore no
    // ART-containing fork to reconcile and no matching ZygoteHooks.preFork()
    // token.  Calling either post-fork hook here would feed a null token to
    // Thread::InitAfterFork().  Those hooks remain owned by the legacy route
    // that creates ART before its own fork; this fresh-VM path attaches the
    // specialized child main thread directly below.
    LOGI("[ROUTE-A] fresh child VM requires no zygote post-fork hooks");

    runtime->onChildInit();
    JNIEnv *env = runtime->getJNIEnv();
    if (env == nullptr) {
        LOGE("[ROUTE-A] child JNIEnv unavailable");
        _exit(14);
    }
    if (!InstallTypefaceWarmUpOverride(env)) {
        LOGE("[ROUTE-A] mandatory Typeface warmup override failed");
        _exit(22);
    }
    if (InitAdapterLayerAfterStock(env, runtime) != 0) {
        /*
         * AppSpawnXInit.initAdapterLayer() owns the Java-visible policy for
         * this optional service connection and already catches Throwable so
         * a plain Activity can enter ActivityThread.  Route A has loaded and
         * identity-checked the native bridge separately; a ClassLoader
         * manifest rejection of OHEnvironment's redundant load must not
         * terminate the child before that Java policy runs.
         */
        LOGW("[ROUTE-A] adapter initialization deferred to Java policy");
    }
    if (!ReinjectAdapterClassLoader(env, runtime)) {
        LOGE("[ROUTE-A] mandatory adapter class-loader reinjection failed");
        _exit(21);
    }
    (void)prctl(PR_SET_NAME, message.procName.c_str(), 0, 0, 0);
    LaunchActivityThreadAfterStock(env, message, runtime);
    _exit(1);
}

} // namespace appspawnx
