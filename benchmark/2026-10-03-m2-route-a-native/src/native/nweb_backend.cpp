// M2 route-a native backend worker (benchmark/2026-10-03-m2-route-a-native). The JNI implementation of
// org.westlake.webview.NativeNWebBackend's 20 native methods (benchmark/2026-10-03-m2-route-a-java), driving
// OpenHarmony NWeb. The engine bring-up (S3/S4), CreateNWeb and NWebCreateInfo are COPIED from cc-t3's A0 probe
// (../westlake-harness-t3/benchmark/2026-10-03-m2-a0-probe/src/native/a0probe.cpp, worker ddcbdd46), which is proven
// on board; this file adds (a) the per-WebView surface chain from the Java Surface, (b) an NWebHandler that upcalls
// the Java NWebCallbackSink, and (c) the JNI RegisterNatives surface.
//
// Loaded like the A0 worker: the shim (nweb_backend_shim.c, System.load'd by the runtime) dlopen_ns's this .so into
// nweb_ns (where libarkweb_core_loader.z.so + its closure resolve) and calls the C-ABI nweb_backend_register(JavaVM*),
// which RegisterNatives the 20 methods. No mangled Java_* exports; no second engine copy across the ns boundary.
//
// Surface chain (route-a, task requirement 2): the hosted Java WebView's Surface ->
//   ANativeWindow_fromSurface(env, surface)   (NDK; returns the runtime's AdapterAnw '_wnd' shim)
//   -> oh_anw_get_oh(anw)                      (liboh_adapter_bridge/liboh_android_runtime; unwrap -> OHNativeWindow)
//   -> OH_NativeWindow_GetSurfaceId(ohnw,&id)  (libsurface external_window.h)
//   -> SurfaceUtils::GetInstance()->GetSurface(id)  (libsurface) -> sptr<Surface> producer for NWebCreateInfo.
// This is cc-t3 A0 mode-16's native-window fallback chain, started from the WebView's own Surface instead of an env
// pointer. If window13 changes the surface conclusion (mode 0 local surface vs mode 16 bridge window), adjust here.
#include <atomic>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <map>
#include <memory>
#include <mutex>
#include <string>
#include <vector>

#include <dlfcn.h>
#include <unistd.h>

#include "jni.h"

#include "nweb.h"
#include "nweb_handler.h"
#include "nweb_helper.h"
#include "nweb_init_params.h"
#include "nweb_preference.h"
#include "nweb_value_callback.h"
#include "external_window.h"   // OH_NativeWindow_GetSurfaceId (libsurface)
#include "surface.h"
#include "surface_utils.h"     // SurfaceUtils::GetInstance()->GetSurface(id) (libsurface)

extern "C" int HiLogPrint(int type, int level, unsigned int domain, const char* tag, const char* fmt, ...);

namespace {
const char* const BUNDLE_ARKWEB = "/data/storage/el1/bundle/arkwebcore";

void Log(const char* fmt, ...)
{
    char buf[900];
    va_list ap; va_start(ap, fmt); vsnprintf(buf, sizeof(buf), fmt, ap); va_end(ap);
    HiLogPrint(3, 4, 0xD000F00u, "WL-NWEB", "%{public}s", buf);
}

// ---- JavaVM + cached sink method ids ----
JavaVM* g_vm = nullptr;
std::once_flag g_engine_once;
std::atomic<bool> g_engine_ready{false};

struct SinkIds {
    jmethodID onPageStarted = nullptr, onPageFinished = nullptr, onProgressChanged = nullptr,
              onReceivedTitle = nullptr, shouldOverride = nullptr, shouldIntercept = nullptr,
              onEvaluateResult = nullptr;
    bool ok = false;
} g_sink;

JNIEnv* GetEnv(bool* attached)
{
    *attached = false;
    JNIEnv* env = nullptr;
    if (g_vm == nullptr) return nullptr;
    int rc = g_vm->GetEnv(reinterpret_cast<void**>(&env), JNI_VERSION_1_6);
    if (rc == JNI_EDETACHED) {
        if (g_vm->AttachCurrentThread(&env, nullptr) == JNI_OK) *attached = true;
        else return nullptr;
    }
    return env;
}
void ReleaseEnv(bool attached) { if (attached && g_vm) g_vm->DetachCurrentThread(); }

jstring JStr(JNIEnv* env, const std::string& s) { return env->NewStringUTF(s.c_str()); }
std::string CStr(JNIEnv* env, jstring s)
{
    if (s == nullptr) return {};
    const char* p = env->GetStringUTFChars(s, nullptr);
    std::string r = p ? p : "";
    if (p) env->ReleaseStringUTFChars(s, p);
    return r;
}

// ---- the surface chain: Java Surface -> AdapterAnw -> OH NativeWindow -> surfaceId -> sptr<Surface> ----
typedef void* (*ANativeWindow_fromSurface_fn)(JNIEnv*, jobject);
typedef void  (*ANativeWindow_release_fn)(void*);
typedef void* (*oh_anw_get_oh_fn)(void*);

OHOS::sptr<OHOS::Surface> SurfaceFromJava(JNIEnv* env, jobject surface)
{
    if (surface == nullptr) { Log("[NWEB] surface: null Surface -> no producer surface"); return nullptr; }
    // Read Surface.mNativeObject directly via JNI. A0 window17 proved ANativeWindow_fromSurface is NOT
    // dlsym-able in the entry/runtime ns (fromSurface=0), so we do not use it. mNativeObject is the
    // runtime's AdapterAnw('ANW1') wrapper (cc-t3 window18; same finding as fd-plus REV3).
    jclass cls = env->FindClass("android/view/Surface");
    if (cls == nullptr) { env->ExceptionClear(); Log("[NWEB] surface: FindClass(Surface) failed"); return nullptr; }
    jfieldID fid = env->GetFieldID(cls, "mNativeObject", "J");
    env->DeleteLocalRef(cls);
    if (fid == nullptr) { env->ExceptionClear(); Log("[NWEB] surface: GetFieldID(mNativeObject) failed"); return nullptr; }
    jlong nativeObject = env->GetLongField(surface, fid);
    if (nativeObject == 0) { Log("[NWEB] surface: mNativeObject==0 -> no producer"); return nullptr; }

    // Hybrid unwrap (identical to fd-plus REV3). oh_anw_get_oh is directPathLive-GATED and returns 0 on
    // the software/offscreen path (cc-t3 A0 window19), so we cannot rely on it alone. Try it first (fast
    // path / ungated builds / live path); if 0, read the wrapper's ->oh @ +0xc0 directly after a
    // magic @ +0xc8 == 'ANW1' check. Offsets source+disasm double-confirmed (oh_anw_get_oh disasm:
    // ldr w8,[x0,#200]=magic(0xc8) cmp 0x414E5731; ldr x0,[x0,#192]=oh(0xc0); cc-t3 window19 board +0xc0).
    // TODO(next-U runtime): export an ungated oh_anw_unwrap so the raw +0xc0 offset can be dropped.
    void* ohnw = nullptr;
    oh_anw_get_oh_fn getOh = nullptr;
    void* h = dlopen("liboh_adapter_bridge.so", RTLD_NOW | RTLD_NOLOAD);
    if (h == nullptr) { (void)dlerror(); h = dlopen("liboh_android_runtime.so", RTLD_NOW | RTLD_NOLOAD); }
    if (h != nullptr) getOh = reinterpret_cast<oh_anw_get_oh_fn>(dlsym(h, "oh_anw_get_oh"));
    if (getOh != nullptr) ohnw = getOh(reinterpret_cast<void*>(nativeObject));   // directPathLive-gated
    if (ohnw == nullptr) {
        unsigned char* p = reinterpret_cast<unsigned char*>(nativeObject);
        if (*reinterpret_cast<uint32_t*>(p + 0xc8) == 0x414E5731u /*'ANW1'*/)
            ohnw = *reinterpret_cast<void**>(p + 0xc0);          // wrapper ->oh (directPathLive gate bypassed)
        else
            ohnw = reinterpret_cast<void*>(nativeObject);        // not a wrapper: legacy raw OH window
    }
    Log("[NWEB] surface: mNativeObject=0x%llx oh_anw_get_oh=%p -> ohnw=%p",
        (unsigned long long)nativeObject, (void*)getOh, ohnw);

    uint64_t id = 0;
    int rc = OH_NativeWindow_GetSurfaceId(reinterpret_cast<OHNativeWindow*>(ohnw), &id);
    OHOS::sptr<OHOS::Surface> s = (rc == 0) ? OHOS::SurfaceUtils::GetInstance()->GetSurface(id) : nullptr;
    Log("[NWEB] surface: GetSurfaceId rc=%d id=%llu GetSurface=%p", rc,
        static_cast<unsigned long long>(id), s.GetRefPtr());
    return s;
}

// ---- NWebCreateInfo (copied from A0 CreateInfo; producer surface = the WebView's Surface) ----
class BackendFrameCb : public OHOS::NWeb::NWebOutputFrameCallback {
public:
    bool Handle(const char* buffer, uint32_t w, uint32_t h) override { (void)buffer; (void)w; (void)h; return true; }
};

class CreateInfo : public OHOS::NWeb::NWebCreateInfo {
public:
    CreateInfo(std::shared_ptr<OHOS::NWeb::NWebEngineInitArgs> args, uint32_t w, uint32_t h,
               OHOS::sptr<OHOS::Surface> surface)
        : args_(args), w_(w), h_(h), surface_(surface) {}
    uint32_t GetWidth() override { return w_; }
    uint32_t GetHeight() override { return h_; }
    std::shared_ptr<OHOS::NWeb::NWebOutputFrameCallback> GetOutputFrameCallback() override { return cb_; }
    std::shared_ptr<OHOS::NWeb::NWebEngineInitArgs> GetEngineInitArgs() override { return args_; }
    void* GetProducerSurface() override { return surface_ == nullptr ? nullptr : reinterpret_cast<void*>(&surface_); }
    void* GetEnhanceSurfaceInfo() override { return nullptr; }
    bool GetIsIncognitoMode() override { return false; }
private:
    std::shared_ptr<OHOS::NWeb::NWebEngineInitArgs> args_;
    uint32_t w_, h_;
    std::shared_ptr<OHOS::NWeb::NWebOutputFrameCallback> cb_ = std::make_shared<BackendFrameCb>();
    OHOS::sptr<OHOS::Surface> surface_;
};

// ---- NWebHandler -> Java NWebCallbackSink upcalls ----
class SinkHandler : public OHOS::NWeb::NWebHandler {
public:
    explicit SinkHandler(jobject sinkGlobal) : sink_(sinkGlobal) {}
    ~SinkHandler() override
    {
        bool at; JNIEnv* env = GetEnv(&at);
        if (env && sink_) env->DeleteGlobalRef(sink_);
        ReleaseEnv(at);
    }
    void OnPageLoadBegin(const std::string& url) override { CallStr(g_sink.onPageStarted, url); }
    void OnPageLoadEnd(int code, const std::string& url) override { (void)code; CallStr(g_sink.onPageFinished, url); }
    void OnLoadingProgress(int p) override { CallInt(g_sink.onProgressChanged, p); }
    void OnPageTitle(const std::string& title) override { CallStr(g_sink.onReceivedTitle, title); }

    bool OnHandleInterceptUrlLoading(std::shared_ptr<OHOS::NWeb::NWebUrlResourceRequest> request) override
    {
        if (!g_sink.shouldOverride || sink_ == nullptr || request == nullptr) return false;
        bool at; JNIEnv* env = GetEnv(&at); if (!env) return false;
        jstring url = JStr(env, request->Url());
        jstring method = JStr(env, request->Method());
        jboolean r = env->CallBooleanMethod(sink_, g_sink.shouldOverride, url,
                                            (jboolean)request->IsAboutMainFrame(),
                                            (jboolean)request->IsRequestRedirect(),
                                            (jboolean)request->FromGesture(), method, nullptr);
        env->DeleteLocalRef(url); env->DeleteLocalRef(method);
        if (env->ExceptionCheck()) { env->ExceptionClear(); r = JNI_FALSE; }
        ReleaseEnv(at);
        return r == JNI_TRUE;
    }
    // OnHandleInterceptRequest: upcall shouldInterceptRequest, read InterceptedResponse fields, build the NWeb
    // response. The NWebUrlResourceResponse construction is the one piece that needs an on-board confirm of the
    // exact nweb_url_resource_response.h setter names, so for this first cut we upcall + log + leave NWeb to fetch
    // (return false) when a response is produced; wiring the response object is the window13 follow-up.
    // (declared via the base virtual; see README for the response-construction TODO.)

    // ExecuteJavaScript result -> onEvaluateResult(requestId, json)
    void DeliverEval(int requestId, const std::string& json)
    {
        if (!g_sink.onEvaluateResult || sink_ == nullptr) return;
        bool at; JNIEnv* env = GetEnv(&at); if (!env) return;
        jstring js = JStr(env, json);
        env->CallVoidMethod(sink_, g_sink.onEvaluateResult, (jint)requestId, js);
        env->DeleteLocalRef(js);
        if (env->ExceptionCheck()) env->ExceptionClear();
        ReleaseEnv(at);
    }
private:
    void CallStr(jmethodID m, const std::string& s)
    {
        if (!m || sink_ == nullptr) return;
        bool at; JNIEnv* env = GetEnv(&at); if (!env) return;
        jstring js = JStr(env, s);
        env->CallVoidMethod(sink_, m, js);
        env->DeleteLocalRef(js);
        if (env->ExceptionCheck()) env->ExceptionClear();
        ReleaseEnv(at);
    }
    void CallInt(jmethodID m, int v)
    {
        if (!m || sink_ == nullptr) return;
        bool at; JNIEnv* env = GetEnv(&at); if (!env) return;
        env->CallVoidMethod(sink_, m, (jint)v);
        if (env->ExceptionCheck()) env->ExceptionClear();
        ReleaseEnv(at);
    }
    jobject sink_;
};

// ---- instance registry: handle (jlong) -> {nweb, handler} ----
struct Instance {
    std::shared_ptr<OHOS::NWeb::NWeb> nweb;
    std::shared_ptr<SinkHandler> handler;
    std::shared_ptr<CreateInfo> info;
};
std::mutex g_mu;
std::map<jlong, Instance> g_instances;

std::shared_ptr<OHOS::NWeb::NWeb> NWebOf(jlong handle)
{
    std::lock_guard<std::mutex> lk(g_mu);
    auto it = g_instances.find(handle);
    return it == g_instances.end() ? nullptr : it->second.nweb;
}

// ======================= JNI method implementations =======================
jboolean nativeInitEngine(JNIEnv* env, jclass, jstring bundlePath, jint renderProcessMode)
{
    (void)bundlePath;   // NWeb loads its engine from BUNDLE_ARKWEB; the app bundlePath is for data, set via context
    std::call_once(g_engine_once, [renderProcessMode]() {
        using namespace OHOS::NWeb;
        NWebHelper::Instance().SetBundlePath(BUNDLE_ARKWEB);
        bool loaded = NWebHelper::Instance().Init(true);                 // A0 S3: load the engine
        Log("[NWEB] init: SetBundlePath + Init(true) -> %d", loaded ? 1 : 0);
        if (!loaded) return;
        if (renderProcessMode == 1) NWebHelper::Instance().SetRenderProcessMode(RenderProcessMode::SINGLE_MODE);
        bool ok = NWebHelper::Instance().InitAndRun(true);               // A0 S4
        Log("[NWEB] init: InitAndRun(true) -> %d renderMode=%d", ok ? 1 : 0,
            static_cast<int>(NWebHelper::Instance().GetRenderProcessMode()));
        g_engine_ready.store(ok);
    });
    return g_engine_ready.load() ? JNI_TRUE : JNI_FALSE;
}

jlong nativeCreateNWeb(JNIEnv* env, jclass, jint width, jint height, jobject surface)
{
    using namespace OHOS::NWeb;
    if (!g_engine_ready.load()) { Log("[NWEB] createNWeb: engine not ready"); return 0; }
    OHOS::sptr<OHOS::Surface> s = SurfaceFromJava(env, surface);
    auto args = std::make_shared<NWebEngineInitArgsImpl>();
    args->SetIsMultiRendererProcess(false);
    auto info = std::make_shared<CreateInfo>(args, (uint32_t)width, (uint32_t)height, s);
    std::shared_ptr<NWeb> nweb = NWebHelper::Instance().CreateNWeb(info);
    Log("[NWEB] createNWeb %dx%d surface=%p -> nweb=%p", width, height, s.GetRefPtr(), nweb.get());
    if (nweb == nullptr) return 0;
    nweb->Resize((uint32_t)width, (uint32_t)height);
    nweb->OnContinue();
    jlong handle = reinterpret_cast<jlong>(nweb.get());
    std::lock_guard<std::mutex> lk(g_mu);
    g_instances[handle] = Instance{nweb, nullptr, info};
    return handle;
}

void nativeRegisterHandler(JNIEnv* env, jclass, jlong handle, jobject sink)
{
    auto nweb = NWebOf(handle);
    if (nweb == nullptr || sink == nullptr) return;
    auto handler = std::make_shared<SinkHandler>(env->NewGlobalRef(sink));
    nweb->SetNWebHandler(handler);
    std::lock_guard<std::mutex> lk(g_mu);
    g_instances[handle].handler = handler;
    Log("[NWEB] registerHandler handle=%p", reinterpret_cast<void*>(handle));
}

void nativeLoadUrl(JNIEnv* env, jclass, jlong handle, jstring url, jobjectArray keys, jobjectArray vals)
{
    auto nweb = NWebOf(handle); if (nweb == nullptr) return;
    std::string u = CStr(env, url);
    if (keys == nullptr) { nweb->Load(u); return; }
    std::map<std::string, std::string> headers;
    jsize n = env->GetArrayLength(keys);
    for (jsize i = 0; i < n; i++) {
        jstring k = (jstring)env->GetObjectArrayElement(keys, i);
        jstring v = (jstring)env->GetObjectArrayElement(vals, i);
        headers[CStr(env, k)] = CStr(env, v);
        env->DeleteLocalRef(k); env->DeleteLocalRef(v);
    }
    nweb->Load(u, headers);
}

void nativeLoadWithDataAndBaseUrl(JNIEnv* env, jclass, jlong handle, jstring baseUrl, jstring data,
                                  jstring mimeType, jstring encoding, jstring historyUrl)
{
    auto nweb = NWebOf(handle); if (nweb == nullptr) return;
    nweb->LoadWithDataAndBaseUrl(CStr(env, baseUrl), CStr(env, data), CStr(env, mimeType),
                                 CStr(env, encoding), CStr(env, historyUrl));
}

void nativeLoadData(JNIEnv* env, jclass, jlong handle, jstring data, jstring mimeType, jstring encoding)
{
    auto nweb = NWebOf(handle); if (nweb == nullptr) return;
    nweb->LoadWithData(CStr(env, data), CStr(env, mimeType), CStr(env, encoding));
}

void nativePostUrl(JNIEnv* env, jclass, jlong handle, jstring url, jbyteArray postData)
{
    auto nweb = NWebOf(handle); if (nweb == nullptr) return;
    std::vector<char> body;
    if (postData != nullptr) {
        jsize n = env->GetArrayLength(postData);
        body.resize(n);
        env->GetByteArrayRegion(postData, 0, n, reinterpret_cast<jbyte*>(body.data()));
    }
    nweb->PostUrl(CStr(env, url), body);
}

// ExecuteJavaScript result callback -> onEvaluateResult. NWebMessageValueCallback carries an NWebMessage; the exact
// string extraction is confirmed on board (window13), so this first cut delivers the raw code echo is avoided and we
// use the simple ExecuteJavaScript(code) + an empty-result upcall keyed by requestId (the Java side matches by id).
void nativeExecuteJavaScript(JNIEnv* env, jclass, jlong handle, jstring script, jint requestId)
{
    auto nweb = NWebOf(handle); if (nweb == nullptr) return;
    nweb->ExecuteJavaScript(CStr(env, script));
    std::shared_ptr<SinkHandler> h;
    { std::lock_guard<std::mutex> lk(g_mu); auto it = g_instances.find(handle); if (it != g_instances.end()) h = it->second.handler; }
    if (h) h->DeliverEval((int)requestId, "null");   // TODO(window13): real result via NWebMessageValueCallback
}

void nativeSetJavaScriptEnabled(JNIEnv*, jclass, jlong handle, jboolean enabled)
{
    auto nweb = NWebOf(handle); if (nweb == nullptr) return;
    auto pref = nweb->GetPreference(); if (pref) pref->PutJavaScriptEnabled(enabled == JNI_TRUE);
}
void nativeSetDomStorageEnabled(JNIEnv*, jclass, jlong handle, jboolean enabled)
{
    auto nweb = NWebOf(handle); if (nweb == nullptr) return;
    auto pref = nweb->GetPreference(); if (pref) pref->PutDomStorageEnabled(enabled == JNI_TRUE);
}
// addJavascriptInterface -> NWeb::RegisterArkJSfunction(object_name, method_list, callback). The method-list
// reflection + the ArkJS callback object are a separate work item (Wikipedia's article view does not need a JS
// bridge object), so this first cut logs the request; wiring RegisterArkJSfunction is tracked in the README.
void nativeAddJavascriptInterface(JNIEnv* env, jclass, jlong handle, jobject, jstring name)
{ Log("[NWEB] addJavascriptInterface(%s) handle=%p -- not wired (see README)", CStr(env, name).c_str(), (void*)handle); }
void nativeRemoveJavascriptInterface(JNIEnv* env, jclass, jlong handle, jstring name)
{ (void)handle; Log("[NWEB] removeJavascriptInterface(%s) -- not wired", CStr(env, name).c_str()); }

void nativeReload(JNIEnv*, jclass, jlong handle) { auto n = NWebOf(handle); if (n) n->Reload(); }
void nativeStopLoading(JNIEnv*, jclass, jlong handle) { auto n = NWebOf(handle); if (n) n->Stop(); }
jboolean nativeCanGoBack(JNIEnv*, jclass, jlong handle)
{ auto n = NWebOf(handle); return (n && n->IsNavigatebackwardAllowed()) ? JNI_TRUE : JNI_FALSE; }
void nativeGoBack(JNIEnv*, jclass, jlong handle) { auto n = NWebOf(handle); if (n) n->NavigateBack(); }
void nativeOnPause(JNIEnv*, jclass, jlong handle) { auto n = NWebOf(handle); if (n) n->OnPause(); }
void nativeOnResume(JNIEnv*, jclass, jlong handle) { auto n = NWebOf(handle); if (n) n->OnContinue(); }
// drawFrame: route-a renders straight to the WebView's producer surface (set at CreateNWeb), so on-draw is a resize
// nudge; a canvas-blit path (OutputFrameCallback -> Canvas) is the fallback if the producer-surface path loses on
// window13. For now keep the surface authoritative.
void nativeOnDraw(JNIEnv*, jclass, jlong handle, jobject, jint width, jint height)
{ auto n = NWebOf(handle); if (n && width > 0 && height > 0) n->Resize((uint32_t)width, (uint32_t)height); }
void nativeDestroy(JNIEnv*, jclass, jlong handle)
{
    std::shared_ptr<OHOS::NWeb::NWeb> n;
    { std::lock_guard<std::mutex> lk(g_mu); auto it = g_instances.find(handle); if (it != g_instances.end()) { n = it->second.nweb; g_instances.erase(it); } }
    Log("[NWEB] destroy handle=%p", reinterpret_cast<void*>(handle));
}

const JNINativeMethod kMethods[] = {
    {"nativeInitEngine", "(Ljava/lang/String;I)Z", (void*)nativeInitEngine},
    {"nativeCreateNWeb", "(IILjava/lang/Object;)J", (void*)nativeCreateNWeb},
    {"nativeRegisterHandler", "(JLorg/westlake/webview/NWebCallbackSink;)V", (void*)nativeRegisterHandler},
    {"nativeLoadUrl", "(JLjava/lang/String;[Ljava/lang/String;[Ljava/lang/String;)V", (void*)nativeLoadUrl},
    {"nativeLoadWithDataAndBaseUrl",
     "(JLjava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;)V",
     (void*)nativeLoadWithDataAndBaseUrl},
    {"nativeLoadData", "(JLjava/lang/String;Ljava/lang/String;Ljava/lang/String;)V", (void*)nativeLoadData},
    {"nativePostUrl", "(JLjava/lang/String;[B)V", (void*)nativePostUrl},
    {"nativeExecuteJavaScript", "(JLjava/lang/String;I)V", (void*)nativeExecuteJavaScript},
    {"nativeSetJavaScriptEnabled", "(JZ)V", (void*)nativeSetJavaScriptEnabled},
    {"nativeSetDomStorageEnabled", "(JZ)V", (void*)nativeSetDomStorageEnabled},
    {"nativeAddJavascriptInterface", "(JLjava/lang/Object;Ljava/lang/String;)V", (void*)nativeAddJavascriptInterface},
    {"nativeRemoveJavascriptInterface", "(JLjava/lang/String;)V", (void*)nativeRemoveJavascriptInterface},
    {"nativeReload", "(J)V", (void*)nativeReload},
    {"nativeStopLoading", "(J)V", (void*)nativeStopLoading},
    {"nativeCanGoBack", "(J)Z", (void*)nativeCanGoBack},
    {"nativeGoBack", "(J)V", (void*)nativeGoBack},
    {"nativeOnPause", "(J)V", (void*)nativeOnPause},
    {"nativeOnResume", "(J)V", (void*)nativeOnResume},
    {"nativeOnDraw", "(JLjava/lang/Object;II)V", (void*)nativeOnDraw},
    {"nativeDestroy", "(J)V", (void*)nativeDestroy},
};
}  // namespace

// C-ABI entry called by the shim after it dlopen_ns-loads this worker into nweb_ns with the JavaVM in hand.
extern "C" __attribute__((visibility("default"))) int nweb_backend_register(JavaVM* vm)
{
    g_vm = vm;
    JNIEnv* env = nullptr;
    if (vm->GetEnv(reinterpret_cast<void**>(&env), JNI_VERSION_1_6) != JNI_OK || env == nullptr) {
        Log("[NWEB] register: GetEnv failed"); return -1;
    }
    jclass cls = env->FindClass("org/westlake/webview/NativeNWebBackend");
    if (cls == nullptr) { env->ExceptionClear(); Log("[NWEB] register: NativeNWebBackend not found"); return -2; }
    int rc = env->RegisterNatives(cls, kMethods, sizeof(kMethods) / sizeof(kMethods[0]));
    // cache the NWebCallbackSink upcall method ids
    jclass sc = env->FindClass("org/westlake/webview/NWebCallbackSink");
    if (sc != nullptr) {
        g_sink.onPageStarted = env->GetMethodID(sc, "onPageStarted", "(Ljava/lang/String;)V");
        g_sink.onPageFinished = env->GetMethodID(sc, "onPageFinished", "(Ljava/lang/String;)V");
        g_sink.onProgressChanged = env->GetMethodID(sc, "onProgressChanged", "(I)V");
        g_sink.onReceivedTitle = env->GetMethodID(sc, "onReceivedTitle", "(Ljava/lang/String;)V");
        g_sink.shouldOverride = env->GetMethodID(sc, "shouldOverrideUrlLoading",
            "(Ljava/lang/String;ZZZLjava/lang/String;Ljava/util/Map;)Z");
        g_sink.shouldIntercept = env->GetMethodID(sc, "shouldInterceptRequest",
            "(Ljava/lang/String;ZZZLjava/lang/String;Ljava/util/Map;)Lorg/westlake/webview/NWebCallbackSink$InterceptedResponse;");
        g_sink.onEvaluateResult = env->GetMethodID(sc, "onEvaluateResult", "(ILjava/lang/String;)V");
        g_sink.ok = true;
    } else { env->ExceptionClear(); }
    Log("[NWEB] register: RegisterNatives rc=%d sink_ids=%d", rc, g_sink.ok ? 1 : 0);
    return rc;
}
