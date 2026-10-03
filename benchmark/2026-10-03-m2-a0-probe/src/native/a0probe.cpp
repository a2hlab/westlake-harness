// M2 A0 in-process ArkWeb probe (benchmark/2026-10-03-m2-a0-probe). Test-only; never part of a generation.
//
// Loaded into an Android app process (appspawn-x child) by liba0shim.so with dlopen_ns into musl's "default"
// namespace, the namespace liboh_adapter_bridge.so lives in. Steps, each logged as "[A0] Sn ...":
//   S0 environment (pid/uid, OH main EventRunner, existing ApplicationContext)
//   S1 the loader: NWebHelper symbol address (libarkweb_core_loader.z.so is a NEEDED of this .so)
//   S2 ApplicationContext attach (ContextImpl + ApplicationInfo{bundleName}) unless one exists
//   S3 NWebHelper::SetBundlePath("/data/storage/el1/bundle/arkwebcore"), Init(fromArk) (loads the engine), then the
//      optional SetRenderProcessMode(SINGLE) (a no-op before the engine is loaded)
//   S4 NWebHelper::InitAndRun(fromArk)
//   S5 NWebHelper::CreateNWeb(our NWebCreateInfo: W x H, our OutputFrameCallback, own producer surface)
//   S6 handler + JavaScript enabled, OnContinue, Resize
//   S7 LoadWithDataAndBaseUrl(Chinese text + a script that paints the page #12ab34)
//   S8 frames: OutputFrameCallback and/or the producer surface's consumer; centre pixel sampled; RESULT after 20 s
// Mode bits from param debug.westlake.a0probe.mode (default 0): 16 = route-a faithful (bridge-published Activity window
// surface instead of a local consumer surface; RS-holder primary, native-window fallback); 1 = single render process, 2 = InitAndRun(false)
// (mock path via the bundle path), 4 = skip the ApplicationContext attach, 8 = no producer surface.
#include <atomic>
#include <cinttypes>
#include <cstdarg>
#include <cstdio>
#include <dlfcn.h>
#include <memory>
#include <string>
#include <unistd.h>

#include "application_context.h"
#include "application_info.h"
#include "context_impl.h"
#include "event_handler.h"
#include "event_runner.h"
#ifndef WL_A0_RUNTIME
#include "iconsumer_surface.h"   // outside the runtime CL ns search (ndk / chipset-pub-sdk); runtime variant omits it
#endif
#include "nweb.h"
#include "nweb_handler.h"
#include "nweb_helper.h"
#include "nweb_init_params.h"
#include "nweb_preference.h"
#ifndef WL_A0_RUNTIME
#include "parameters.h"   // outside the runtime CL ns search (ndk / chipset-pub-sdk); runtime variant omits it
#endif
#ifndef WL_A0_RUNTIME
#include "surface.h"   // outside the runtime CL ns search (ndk / chipset-pub-sdk); runtime variant omits it
#include "surface_utils.h"      // mode 16 fallback: SurfaceUtils::GetSurface(uniqueId) (in libsurface)
#include "external_window.h"    // mode 16 fallback: OH_NativeWindow_GetSurfaceId (in libsurface)
// mode 16 primary: a minimal decl of the non-virtual export RSSurfaceNode::GetSurface() — avoids the deep
// render_service_client header tree (rs_surface_node.h -> platform/drawing/rs_surface.h -> ...). GetSurface is only ever
// called on a pointer owned by the bridge's std::shared_ptr; members are never accessed through this type, so the empty
// layout is irrelevant — the call binds to _ZNK4OHOS5Rosen13RSSurfaceNode10GetSurfaceEv (librender_service_client) with
// this = the real object. (genstub pattern, like src/genstub/*.h for the IDL headers.)
namespace OHOS { namespace Rosen { class RSSurfaceNode { public: OHOS::sptr<OHOS::Surface> GetSurface() const; }; } }
#endif
#ifndef WL_A0_RUNTIME
#include "sync_fence.h"   // outside the runtime CL ns search (ndk / chipset-pub-sdk); runtime variant omits it
#endif

extern "C" int HiLogPrint(int type, int level, unsigned int domain, const char* tag, const char* fmt, ...);

namespace {
constexpr uint32_t W = 720;
constexpr uint32_t H = 720;
constexpr uint8_t JS_R = 0x12, JS_G = 0xab, JS_B = 0x34;
const char* const BUNDLE_ARKWEB = "/data/storage/el1/bundle/arkwebcore";

void Log(const char* fmt, ...)
{
    char buf[900];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    HiLogPrint(3, 4, 0xD000F00u, "WL-A0", "%{public}s", buf);
    fprintf(stderr, "[A0] %s\n", buf);
    fflush(stderr);
}

std::atomic<int> g_cbFrames{0}, g_cbJs{0}, g_surfFrames{0}, g_surfJs{0}, g_consoleJs{0}, g_loadEnd{0}, g_renderExit{-1};
std::string g_stage = "S0";

bool IsJs(const uint8_t* p) { return p[0] == JS_R && p[1] == JS_G && p[2] == JS_B; }

class FrameCb : public OHOS::NWeb::NWebOutputFrameCallback {
public:
    bool Handle(const char* buffer, uint32_t width, uint32_t height) override
    {
        int n = ++g_cbFrames;
        if (buffer == nullptr || width == 0 || height == 0) {
            Log("[A0] S8 callback frame %d: empty (%u x %u)", n, width, height);
            return false;
        }
        const uint8_t* c = reinterpret_cast<const uint8_t*>(buffer) + ((height / 2) * width + width / 2) * 4;
        bool js = IsJs(c);
        if (js) ++g_cbJs;
        if (n <= 5 || n % 30 == 0 || (js && g_cbJs == 1)) {
            Log("[A0] S8 callback frame %d %ux%u centre rgba=%02x%02x%02x%02x js_colour=%d", n, width, height,
                c[0], c[1], c[2], c[3], js ? 1 : 0);
        }
        return true;
    }
};

#ifndef WL_A0_RUNTIME
class ConsumerListener : public OHOS::IBufferConsumerListener {
public:
    explicit ConsumerListener(OHOS::sptr<OHOS::IConsumerSurface> c) : consumer_(c) {}
    void OnBufferAvailable() override
    {
        OHOS::sptr<OHOS::SurfaceBuffer> buf;
        OHOS::sptr<OHOS::SyncFence> fence;
        int64_t ts = 0;
        OHOS::Rect damage = {};
        if (consumer_->AcquireBuffer(buf, fence, ts, damage) != OHOS::GSERROR_OK || buf == nullptr) {
            return;
        }
        int n = ++g_surfFrames;
        if (fence != nullptr) {
            fence->Wait(100);
        }
        const uint8_t* base = reinterpret_cast<const uint8_t*>(buf->GetVirAddr());
        int w = buf->GetWidth(), h = buf->GetHeight(), stride = buf->GetStride();
        if (base != nullptr && w > 0 && h > 0 && stride > 0) {
            const uint8_t* c = base + (h / 2) * stride + (w / 2) * 4;
            bool js = IsJs(c);
            if (js) ++g_surfJs;
            if (n <= 5 || n % 30 == 0 || (js && g_surfJs == 1)) {
                Log("[A0] S8 surface frame %d %dx%d stride=%d fmt=%d centre rgba=%02x%02x%02x%02x js_colour=%d", n, w,
                    h, stride, buf->GetFormat(), c[0], c[1], c[2], c[3], js ? 1 : 0);
            }
        } else if (n <= 5) {
            Log("[A0] S8 surface frame %d %dx%d: no CPU mapping (virAddr=%p)", n, w, h, base);
        }
        consumer_->ReleaseBuffer(buf, OHOS::SyncFence::InvalidFence());
    }

private:
    OHOS::sptr<OHOS::IConsumerSurface> consumer_;
};
#endif

#ifndef WL_A0_RUNTIME
// mode 16 (route-a faithful): the Activity window's surface, published by the bridge into same-process env pointers.
// Primary = the RSSurfaceNode holder (WESTLAKE_RS_SURFACE_NODE_HOLDER_PTR_V1, a std::shared_ptr<RSSurfaceNode>*) ->
//   RSSurfaceNode::GetSurface() (non-virtual export of librender_service_client) -- the same object OH ACE WebPattern
//   hands NWeb. Fallback = the native window (WESTLAKE_NATIVE_WINDOW_PTR_V1, an OHNativeWindow*) ->
//   OH_NativeWindow_GetSurfaceId -> SurfaceUtils::GetSurface(id) (both in libsurface). Missing/parse-fail -> clear log,
//   then return null (CreateNWeb fails = RESULT FAIL, no crash).
OHOS::sptr<OHOS::Surface> GetBridgeSurface()
{
    const char* holder = nullptr;
    const char* nw = nullptr;
    for (int i = 0; i < 40; i++) {   // the window target is published only once the Activity window session exists (~<10s)
        holder = getenv("WESTLAKE_RS_SURFACE_NODE_HOLDER_PTR_V1");
        nw = getenv("WESTLAKE_NATIVE_WINDOW_PTR_V1");
        if ((holder != nullptr && holder[0]) || (nw != nullptr && nw[0])) break;
        usleep(250 * 1000);
    }
    Log("[A0] S5 bridge env: RS_holder=%s native_window=%s", holder ? holder : "(absent)", nw ? nw : "(absent)");
    if (holder != nullptr && holder[0]) {
        void* p = nullptr;
        if (sscanf(holder, "%p", &p) == 1 && p != nullptr) {
            auto* sp = reinterpret_cast<std::shared_ptr<OHOS::Rosen::RSSurfaceNode>*>(p);
            std::shared_ptr<OHOS::Rosen::RSSurfaceNode> node = *sp;
            if (node) {
                OHOS::sptr<OHOS::Surface> s = node->GetSurface();
                Log("[A0] S5 bridge RSSurfaceNode=%p GetSurface=%p", node.get(), s.GetRefPtr());
                if (s != nullptr) return s;
                Log("[A0] S5 bridge RSSurfaceNode.GetSurface()=null -> native-window fallback");
            } else {
                Log("[A0] S5 bridge RS holder empty -> native-window fallback");
            }
        } else {
            Log("[A0] S5 bridge RS holder parse failed -> native-window fallback");
        }
    }
    if (nw != nullptr && nw[0]) {
        void* p = nullptr;
        if (sscanf(nw, "%p", &p) == 1 && p != nullptr) {
            uint64_t id = 0;
            int rc = OH_NativeWindow_GetSurfaceId(reinterpret_cast<OHNativeWindow*>(p), &id);
            OHOS::sptr<OHOS::Surface> s = (rc == 0) ? OHOS::SurfaceUtils::GetInstance()->GetSurface(id) : nullptr;
            Log("[A0] S5 bridge nativeWindow=%p GetSurfaceId rc=%d id=%llu GetSurface=%p", p, rc,
                static_cast<unsigned long long>(id), s.GetRefPtr());
            if (s != nullptr) return s;
        } else {
            Log("[A0] S5 bridge native window parse failed");
        }
    }
    Log("[A0] S5 bridge surface UNAVAILABLE (FAIL, not crash)");
    return nullptr;
}
#endif

class CreateInfo : public OHOS::NWeb::NWebCreateInfo {
public:
    CreateInfo(std::shared_ptr<OHOS::NWeb::NWebEngineInitArgs> args, int mode) : args_(args)
    {
#ifndef WL_A0_RUNTIME
        if (mode & 16) {   // route-a faithful: the bridge-published Activity window surface (no local consumer)
            surface_ = GetBridgeSurface();   // the native-window fallback logs the surface uniqueId non-virtually
            Log("[A0] S5 bridge surface=%p", surface_.GetRefPtr());
            return;
        }
        if ((mode & 8) != 0) {   // callback-only (no producer surface)
            return;
        }
        consumer_ = OHOS::IConsumerSurface::Create("WlA0Probe");
        if (consumer_ == nullptr) {
            Log("[A0] S5 consumer surface create failed");
            return;
        }
        consumer_->SetDefaultWidthAndHeight(W, H);
        OHOS::sptr<OHOS::IBufferConsumerListener> l = new ConsumerListener(consumer_);
        consumer_->RegisterConsumerListener(l);
        auto producer = consumer_->GetProducer();
        surface_ = OHOS::Surface::CreateSurfaceAsProducer(producer);
        Log("[A0] S5 producer surface %p (consumer %p)", surface_.GetRefPtr(), consumer_.GetRefPtr());
#else
        (void)mode;   // callback-only: no producer surface, so no libsurface/libsync_fence NEEDED
#endif
    }
    uint32_t GetWidth() override { return W; }
    uint32_t GetHeight() override { return H; }
    std::shared_ptr<OHOS::NWeb::NWebOutputFrameCallback> GetOutputFrameCallback() override { return cb_; }
    std::shared_ptr<OHOS::NWeb::NWebEngineInitArgs> GetEngineInitArgs() override { return args_; }
    void* GetProducerSurface() override {
#ifndef WL_A0_RUNTIME
        return surface_ == nullptr ? nullptr : reinterpret_cast<void*>(&surface_);
#else
        return nullptr;
#endif
    }
    void* GetEnhanceSurfaceInfo() override { return nullptr; }
    bool GetIsIncognitoMode() override { return false; }

private:
    std::shared_ptr<OHOS::NWeb::NWebEngineInitArgs> args_;
    std::shared_ptr<OHOS::NWeb::NWebOutputFrameCallback> cb_ = std::make_shared<FrameCb>();
#ifndef WL_A0_RUNTIME
    OHOS::sptr<OHOS::IConsumerSurface> consumer_;
    OHOS::sptr<OHOS::Surface> surface_;
#endif
};

class Handler : public OHOS::NWeb::NWebHandler {
public:
    void OnPageLoadBegin(const std::string& url) override { Log("[A0] S7 OnPageLoadBegin %s", url.c_str()); }
    void OnPageLoadEnd(int code, const std::string& url) override
    {
        ++g_loadEnd;
        Log("[A0] S7 OnPageLoadEnd code=%d url=%s", code, url.c_str());
    }
    void OnLoadingProgress(int p) override { Log("[A0] S7 progress %d", p); }
    bool OnConsoleLog(std::shared_ptr<OHOS::NWeb::NWebConsoleLog> m) override
    {
        std::string s = m ? m->Log() : std::string("(null)");
        if (s.find("A0 JS ran") != std::string::npos) ++g_consoleJs;
        Log("[A0] S7 console: %s", s.c_str());
        return true;
    }
    void OnRenderExited(OHOS::NWeb::RenderExitReason reason) override
    {
        g_renderExit = static_cast<int>(reason);
        Log("[A0] S8 OnRenderExited reason=%d", static_cast<int>(reason));
    }
    void OnFirstContentfulPaint(int64_t nav, int64_t fcp) override
    {
        Log("[A0] S8 FirstContentfulPaint nav=%" PRId64 " fcp=%" PRId64 "ms", nav, fcp);
    }
};

std::shared_ptr<OHOS::AppExecFwk::EventRunner> g_runner;
std::shared_ptr<OHOS::AppExecFwk::EventHandler> g_handler;
std::shared_ptr<OHOS::NWeb::NWeb> g_nweb;
std::shared_ptr<CreateInfo> g_info;

const char* kHtml =
    "<!doctype html><html><head><meta charset='utf-8'>"
    "<meta name='viewport' content='width=device-width,initial-scale=1'></head>"
    "<body id='b' style='margin:0;height:100vh;background:#ffffff'>"
    "<h1 style='font-size:48px'>\xE4\xB8\xAD\xE6\x96\x87 A0 \xE6\x8E\xA2\xE9\x92\x88</h1>"
    "<script>document.getElementById('b').style.background='#12ab34';"
    "document.documentElement.style.background='#12ab34';console.log('A0 JS ran');</script>"
    "</body></html>";

void Summary()
{
    bool frames = g_cbFrames > 0 || g_surfFrames > 0;
    bool js = g_cbJs > 0 || g_surfJs > 0;
    Log("[A0] RESULT %s stage=%s callback_frames=%d callback_js=%d surface_frames=%d surface_js=%d console_js=%d "
        "load_end=%d render_exit=%d pid=%d",
        (frames && js) ? "PASS" : "FAIL", g_stage.c_str(), g_cbFrames.load(), g_cbJs.load(), g_surfFrames.load(),
        g_surfJs.load(), g_consoleJs.load(), g_loadEnd.load(), g_renderExit.load(), getpid());
}

void Run(std::string bundle, int mode)
{
    using namespace OHOS;
    g_stage = "S0";
    auto mainRunner = AppExecFwk::EventRunner::GetMainEventRunner();
    auto existing = AbilityRuntime::Context::GetApplicationContext();
    Log("[A0] S0 pid=%d uid=%d bundle=%s mode=%d mainEventRunner=%p existingAppContext=%p", getpid(), getuid(),
        bundle.c_str(), mode, mainRunner.get(), existing.get());

    g_stage = "S1";
    Dl_info di = {};
    void* sym = reinterpret_cast<void*>(&NWeb::NWebHelper::Instance);
    dladdr(sym, &di);
    Log("[A0] S1 NWebHelper::Instance at %p in %s", sym, di.dli_fname ? di.dli_fname : "?");

    g_stage = "S2";
    if (existing == nullptr && (mode & 4) == 0) {
        auto app = AbilityRuntime::ApplicationContext::GetInstance();
        auto impl = std::make_shared<AbilityRuntime::ContextImpl>();
        auto info = std::make_shared<AppExecFwk::ApplicationInfo>();
        info->bundleName = bundle;
        info->name = bundle;
        impl->SetApplicationInfo(info);
        app->AttachContextImpl(impl);
        auto ctx = AbilityRuntime::Context::GetApplicationContext();
        Log("[A0] S2 attached ApplicationContext %p baseDir=%s bundleName=%s", ctx.get(),
            ctx ? ctx->GetBaseDir().c_str() : "-", ctx ? ctx->GetBundleName().c_str() : "-");
    } else {
        Log("[A0] S2 attach skipped (existing=%p mode=%d)", existing.get(), mode);
    }

    g_stage = "S3";
    bool fromArk = (mode & 2) == 0;
    NWeb::NWebHelper::Instance().SetBundlePath(BUNDLE_ARKWEB);
    bool loaded = NWeb::NWebHelper::Instance().Init(fromArk);
    Log("[A0] S3 bundlePath=%s Init(%d) -> %d (engine library loaded, not yet initialised)", BUNDLE_ARKWEB,
        fromArk ? 1 : 0, loaded ? 1 : 0);
    if (!loaded) {
        Summary();
        return;
    }
    if (mode & 1) {
        NWeb::NWebHelper::Instance().SetRenderProcessMode(NWeb::RenderProcessMode::SINGLE_MODE);
    }
    Log("[A0] S3 renderProcessMode=%d (requested single=%d)",
        static_cast<int>(NWeb::NWebHelper::Instance().GetRenderProcessMode()), (mode & 1) ? 1 : 0);

    g_stage = "S4";
    bool ok = NWeb::NWebHelper::Instance().InitAndRun(fromArk);
    Log("[A0] S4 InitAndRun(%d) -> %d", fromArk ? 1 : 0, ok ? 1 : 0);
    if (!ok) {
        Summary();
        return;
    }

    g_stage = "S5";
    auto args = std::make_shared<NWeb::NWebEngineInitArgsImpl>();
    args->SetIsMultiRendererProcess(false);
    g_info = std::make_shared<CreateInfo>(args, mode);
    g_nweb = NWeb::NWebHelper::Instance().CreateNWeb(g_info);
    Log("[A0] S5 CreateNWeb -> %p", g_nweb.get());
    if (g_nweb == nullptr) {
        Summary();
        return;
    }

    g_stage = "S6";
    g_nweb->SetNWebHandler(std::make_shared<Handler>());
    auto pref = g_nweb->GetPreference();
    if (pref) {
        pref->PutJavaScriptEnabled(true);
    }
    g_nweb->Resize(W, H);
    g_nweb->OnContinue();
    Log("[A0] S6 handler set, preference=%p, resized %ux%u, OnContinue", pref.get(), W, H);

    g_stage = "S7";
    int rc = g_nweb->LoadWithDataAndBaseUrl("https://a0probe.local/", kHtml, "text/html", "utf-8", "");
    Log("[A0] S7 LoadWithDataAndBaseUrl rc=%d", rc);
    g_stage = "S8";
}
} // namespace

extern "C" __attribute__((visibility("default"))) int a0_probe_start(const char* bundle)
{
    std::string b = bundle ? bundle : "";
#ifdef WL_A0_RUNTIME
    int mode = 1 | 8;   // single render process, callback-only (no producer surface)
#else
    int mode = std::stoi(OHOS::system::GetParameter("debug.westlake.a0probe.mode", "0"));
#endif
    g_runner = OHOS::AppExecFwk::EventRunner::Create("WlA0Probe");
    g_handler = std::make_shared<OHOS::AppExecFwk::EventHandler>(g_runner);
    bool posted = g_handler->PostTask([b, mode]() { Run(b, mode); }, "a0-run");
    g_handler->PostTask([]() { Summary(); }, "a0-summary", 20000);
    Log("[A0] start posted=%d runner=%p", posted ? 1 : 0, g_runner.get());
    return posted ? 0 : -1;
}
