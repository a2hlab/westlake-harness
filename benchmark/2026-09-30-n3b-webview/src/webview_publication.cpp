// N3b: unchanged Westlake 532633da provider publication bodies.
#include <jni.h>
#include <cstdio>
#include <string>
#include <mutex>
#include <unistd.h>
namespace {
std::string jstr(JNIEnv* env, jstring s) {
    if (!s) return "";
    const char* raw = env->GetStringUTFChars(s, nullptr);
    std::string result(raw);
    env->ReleaseStringUTFChars(s, raw);
    return result;
}

static void wl_log_and_clear_webview_exception(JNIEnv* env, const char* where) {
    jthrowable thrown = env->ExceptionOccurred();
    if (thrown == nullptr) return;
    env->ExceptionClear();

    std::string detail("<unprintable>");
    jclass thrownClass = env->GetObjectClass(thrown);
    jmethodID toString = thrownClass != nullptr
        ? env->GetMethodID(thrownClass, "toString", "()Ljava/lang/String;") : nullptr;
    if (!env->ExceptionCheck() && toString != nullptr) {
        jstring text = static_cast<jstring>(env->CallObjectMethod(thrown, toString));
        if (!env->ExceptionCheck() && text != nullptr) {
            detail = jstr(env, text);
            env->DeleteLocalRef(text);
        }
    }
    if (env->ExceptionCheck()) env->ExceptionClear();
    fprintf(stderr, "[WESTLAKE-WEBVIEW-PROVIDER] %s threw %s\n",
            where, detail.c_str());
    fflush(stderr);
    if (thrownClass != nullptr) env->DeleteLocalRef(thrownClass);
    env->DeleteLocalRef(thrown);
}

static bool wl_set_webview_supported_cache(
        JNIEnv* env, jclass webViewFactoryClass, bool supported) {
    // The application-ready watcher can arrive after post-bind publication.
    // Serialize this state transition, and never let cache-only priming undo
    // a successfully verified publication. Reset the latch for each fork.
    static std::mutex featureMutex;
    static pid_t featurePid = 0;
    static bool published = false;
    std::lock_guard<std::mutex> lock(featureMutex);
    if (featurePid != getpid()) { featurePid = getpid(); published = false; }
    supported = supported || published;
    jclass booleanClass = env->FindClass("java/lang/Boolean");
    const char* booleanFieldName = supported ? "TRUE" : "FALSE";
    jfieldID booleanField = booleanClass != nullptr
        ? env->GetStaticFieldID(booleanClass, booleanFieldName,
                                "Ljava/lang/Boolean;")
        : nullptr;
    jfieldID supportedField = webViewFactoryClass != nullptr
        ? env->GetStaticFieldID(webViewFactoryClass, "sWebViewSupported",
                                "Ljava/lang/Boolean;")
        : nullptr;
    jobject booleanValue = booleanField != nullptr
        ? env->GetStaticObjectField(booleanClass, booleanField)
        : nullptr;
    if (env->ExceptionCheck() || booleanClass == nullptr ||
            booleanField == nullptr || supportedField == nullptr ||
            booleanValue == nullptr) {
        wl_log_and_clear_webview_exception(
            env, "WebViewFactory.sWebViewSupported lookup");
        if (booleanValue != nullptr) env->DeleteLocalRef(booleanValue);
        if (booleanClass != nullptr) env->DeleteLocalRef(booleanClass);
        return false;
    }

    env->SetStaticObjectField(webViewFactoryClass, supportedField, booleanValue);
    jobject readback = env->GetStaticObjectField(
        webViewFactoryClass, supportedField);
    const bool success = !env->ExceptionCheck() && readback != nullptr &&
                         env->IsSameObject(readback, booleanValue);
    if (success && supported) published = true;
    if (!success && env->ExceptionCheck()) {
        wl_log_and_clear_webview_exception(
            env, "WebViewFactory.sWebViewSupported publish");
    }
    if (readback != nullptr) env->DeleteLocalRef(readback);
    env->DeleteLocalRef(booleanValue);
    env->DeleteLocalRef(booleanClass);
    return success;
}

static bool wl_prime_webview_update_service_impl(
        JNIEnv* env, bool publishFeatureAfterBind) {
    jclass updateClass = env->FindClass(
        "adapter/core/WebViewUpdateServiceAdapter");
    if (env->ExceptionCheck() || updateClass == nullptr) {
        wl_log_and_clear_webview_exception(env, "WebViewUpdateServiceAdapter lookup");
        return false;
    }

    jmethodID isAvailable = env->GetStaticMethodID(
        updateClass, "isAvailable", "()Z");
    jboolean available = isAvailable != nullptr
        ? env->CallStaticBooleanMethod(updateClass, isAvailable) : JNI_FALSE;
    if (env->ExceptionCheck()) {
        wl_log_and_clear_webview_exception(env, "WebViewUpdateServiceAdapter.isAvailable");
        env->DeleteLocalRef(updateClass);
        return false;
    }
    if (available != JNI_TRUE) {
        fprintf(stderr,
                "[WESTLAKE-WEBVIEW-PROVIDER] configured provider unavailable\n");
        fflush(stderr);
        env->DeleteLocalRef(updateClass);
        return false;
    }

    jmethodID getInstance = env->GetStaticMethodID(
        updateClass, "getInstance",
        "()Ladapter/core/WebViewUpdateServiceAdapter;");
    jobject updateService = getInstance != nullptr
        ? env->CallStaticObjectMethod(updateClass, getInstance) : nullptr;
    if (env->ExceptionCheck() || updateService == nullptr) {
        wl_log_and_clear_webview_exception(env, "WebViewUpdateServiceAdapter.getInstance");
        env->DeleteLocalRef(updateClass);
        return false;
    }

    jclass serviceManagerClass = env->FindClass("android/os/ServiceManager");
    jclass webViewFactoryClass = env->FindClass("android/webkit/WebViewFactory");
    jfieldID cacheField = serviceManagerClass != nullptr
        ? env->GetStaticFieldID(serviceManagerClass, "sCache", "Ljava/util/Map;")
        : nullptr;
    jfieldID serviceNameField = webViewFactoryClass != nullptr
        ? env->GetStaticFieldID(webViewFactoryClass,
                                "WEBVIEW_UPDATE_SERVICE_NAME",
                                "Ljava/lang/String;")
        : nullptr;
    jmethodID publicGetService = serviceManagerClass != nullptr
        ? env->GetStaticMethodID(serviceManagerClass, "getService",
                                 "(Ljava/lang/String;)Landroid/os/IBinder;")
        : nullptr;
    jobject cache = cacheField != nullptr
        ? env->GetStaticObjectField(serviceManagerClass, cacheField) : nullptr;
    // Resolve put/get on the concrete cache class (normally ArrayMap).  This
    // avoids invoke-interface dispatch here: older ART bridge builds have been
    // observed to return normally from Map.put without changing this object.
    // Always read the entry back before reporting that the cache was seeded.
    jclass cacheClass = cache != nullptr ? env->GetObjectClass(cache) : nullptr;
    jmethodID put = cacheClass != nullptr
        ? env->GetMethodID(cacheClass, "put",
                           "(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;")
        : nullptr;
    jmethodID get = cacheClass != nullptr
        ? env->GetMethodID(cacheClass, "get",
                           "(Ljava/lang/Object;)Ljava/lang/Object;")
        : nullptr;
    // Use the exact String object consumed by WebViewFactory. This port has
    // had ART String/ArrayMap dispatch defects where put/get with the same
    // freshly allocated key succeeds but a later equal String misses. A
    // same-object cache check therefore did not prove the framework lookup.
    jstring serviceName = serviceNameField != nullptr
        ? static_cast<jstring>(env->GetStaticObjectField(webViewFactoryClass,
                                                         serviceNameField))
        : nullptr;
    if (env->ExceptionCheck() || cache == nullptr || put == nullptr || get == nullptr ||
            serviceName == nullptr || publicGetService == nullptr) {
        wl_log_and_clear_webview_exception(env, "ServiceManager.sCache lookup");
        if (serviceName != nullptr) env->DeleteLocalRef(serviceName);
        if (cacheClass != nullptr) env->DeleteLocalRef(cacheClass);
        if (cache != nullptr) env->DeleteLocalRef(cache);
        if (webViewFactoryClass != nullptr) env->DeleteLocalRef(webViewFactoryClass);
        if (serviceManagerClass != nullptr) env->DeleteLocalRef(serviceManagerClass);
        env->DeleteLocalRef(updateService);
        env->DeleteLocalRef(updateClass);
        return false;
    }

    jobject previous = env->CallObjectMethod(
        cache, put, serviceName, updateService);
    const char* previousState = previous == nullptr ? "null"
        : (env->IsSameObject(previous, updateService) ? "same" : "other");
    jobject readback = nullptr;
    jobject publicReadback = nullptr;
    bool cacheSuccess = !env->ExceptionCheck();
    if (cacheSuccess) {
        readback = env->CallObjectMethod(cache, get, serviceName);
        cacheSuccess = !env->ExceptionCheck() && readback != nullptr &&
                       env->IsSameObject(readback, updateService);
    }
    if (cacheSuccess) {
        publicReadback = env->CallStaticObjectMethod(
            serviceManagerClass, publicGetService, serviceName);
        cacheSuccess = !env->ExceptionCheck() && publicReadback != nullptr &&
                       env->IsSameObject(publicReadback, updateService);
    }
    if (!cacheSuccess && env->ExceptionCheck()) {
        wl_log_and_clear_webview_exception(env, "ServiceManager.sCache.put");
    }
    if (cacheSuccess) {
        fprintf(stderr,
                "[WESTLAKE-WEBVIEW-PROVIDER] primed ServiceManager webviewupdate cache public-readback=OK\n");
        fflush(stderr);
    } else {
        fprintf(stderr,
                "[WESTLAKE-WEBVIEW-PROVIDER] failed ServiceManager webviewupdate cache readback\n");
        fflush(stderr);
    }

    // Toutiao asks CookieManager for an instance while LoadedApk is still
    // constructing its Application.  At that point AppGlobals has not yet
    // published ActivityThread.mInitialApplication, so WebViewFactory's normal
    // feature query observes a null PackageManager and permanently caches
    // Boolean.FALSE in sWebViewSupported.  Do not force TRUE at this early
    // checkpoint: doing so would let provider creation continue without an
    // Application context. Only the explicit post-bind caller requests feature
    // publication, and only after the configured provider's isAvailable()
    // check above succeeded.
    bool featureSuccess = true;
    const char* featureState = "held-unsupported";
    jclass activityThreadClass = nullptr;
    jobject application = nullptr;
    if (!publishFeatureAfterBind) {
        // OH child construction is not yet a valid WebView context. Pin the
        // same cached false that WebViewFactory would compute at this stage,
        // but make its lifetime explicit: the post-bind callback below
        // replaces it with TRUE. This prevents a later CookieManager retry
        // during Application.onCreate from starting Chromium on the bind path.
        featureSuccess = wl_set_webview_supported_cache(
            env, webViewFactoryClass, false);
        if (!featureSuccess) featureState = "hold-failed";
    } else {
        featureState = "application-pending";
        activityThreadClass = env->FindClass("android/app/ActivityThread");
        jmethodID currentApplication = activityThreadClass != nullptr
            ? env->GetStaticMethodID(activityThreadClass, "currentApplication",
                                     "()Landroid/app/Application;")
            : nullptr;
        application = currentApplication != nullptr
            ? env->CallStaticObjectMethod(activityThreadClass, currentApplication)
            : nullptr;
        if (env->ExceptionCheck() || activityThreadClass == nullptr ||
                currentApplication == nullptr) {
            wl_log_and_clear_webview_exception(
                env, "ActivityThread.currentApplication");
            featureSuccess = false;
            featureState = "application-check-failed";
        } else if (application == nullptr) {
            // A publish request is valid only at the explicit post-bind
            // checkpoint. Treat an absent Application as retryable failure;
            // never turn it into an early TRUE feature bit.
            featureSuccess = false;
        } else {
            featureSuccess = wl_set_webview_supported_cache(
                env, webViewFactoryClass, true);
            featureState = featureSuccess ? "published" : "publish-failed";
        }
    }

    fprintf(stderr,
            "[WESTLAKE-WEBVIEW-FEATURE] application=%s feature=%s\n",
            application != nullptr ? "ready" : "pending", featureState);
    fflush(stderr);

    // Cache priming is independently useful before bind. When the post-bind
    // caller requests feature publication, that publication is part of the
    // success invariant and may be retried by the checkpoint path.
    const bool success = cacheSuccess && featureSuccess;
    if (success) {
        fprintf(stderr,
                "[WESTLAKE-WEBVIEW-PROVIDER] startup service cache=OK previous=%s\n",
                previousState);
        fflush(stderr);
    } else {
        fprintf(stderr,
                "[WESTLAKE-WEBVIEW-PROVIDER] startup service cache failed\n");
        fflush(stderr);
    }

    if (publicReadback != nullptr) env->DeleteLocalRef(publicReadback);
    if (application != nullptr) env->DeleteLocalRef(application);
    if (activityThreadClass != nullptr) env->DeleteLocalRef(activityThreadClass);
    if (readback != nullptr) env->DeleteLocalRef(readback);
    if (previous != nullptr) env->DeleteLocalRef(previous);
    env->DeleteLocalRef(serviceName);
    env->DeleteLocalRef(cacheClass);
    env->DeleteLocalRef(cache);
    env->DeleteLocalRef(webViewFactoryClass);
    env->DeleteLocalRef(serviceManagerClass);
    env->DeleteLocalRef(updateService);
    env->DeleteLocalRef(updateClass);
    return success;
}
} // namespace

bool wl_prime_webview_update_service(JNIEnv* env) {
    return wl_prime_webview_update_service_impl(env, false);
}

bool wl_publish_webview_update_service_after_bind(JNIEnv* env) {
    return wl_prime_webview_update_service_impl(env, true);
}

// Explicit Java cooperation point. Do not run during native registration,
// on log output, or on a background watcher. The owning Java helper calls
// prime before bind and publish only after Application.onCreate returned.
// Serialize whole transactions, including the donor's cache readbacks.
namespace { std::recursive_mutex publication_mutex; }
extern "C" JNIEXPORT jboolean JNICALL
Java_adapter_core_WestlakeWebViewInstall_nativePrime(JNIEnv* env, jclass) {
    if (env->ExceptionCheck()) return JNI_FALSE;
    std::lock_guard<std::recursive_mutex> lock(publication_mutex);
    return wl_prime_webview_update_service(env) ? JNI_TRUE : JNI_FALSE;
}
extern "C" JNIEXPORT jboolean JNICALL
Java_adapter_core_WestlakeWebViewInstall_nativePublishAfterBind(JNIEnv* env, jclass) {
    if (env->ExceptionCheck()) return JNI_FALSE;
    std::lock_guard<std::recursive_mutex> lock(publication_mutex);
    return wl_publish_webview_update_service_after_bind(env) ? JNI_TRUE : JNI_FALSE;
}
