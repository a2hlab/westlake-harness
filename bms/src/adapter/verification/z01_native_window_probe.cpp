/*
 * z01_native_window_probe.cpp — Z01 independent graphics probe for AonB D600.
 *
 * Creates a RenderService-backed RSSurfaceNode, wraps its producer Surface with
 * an OHNativeWindow, requests/flushes a CPU-filled buffer, and reports whether
 * the buffer-commit path succeeds.
 *
 * This proves the OHNativeWindow -> RenderService consumer path decoupled from
 * Android HWUI/EGL/ART.
 *
 * Build: see verification/build_probes.sh
 */

#include "ui/rs_surface_node.h"
#include "transaction/rs_transaction.h"
#include "transaction/rs_interfaces.h"

#include <native_window/external_window.h>

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdint>
#include <unistd.h>

using namespace OHOS;
using namespace OHOS::Rosen;

static constexpr int32_t kW = 640;
static constexpr int32_t kH = 480;

static inline uint32_t rgba(uint8_t r, uint8_t g, uint8_t b, uint8_t a = 0xFF) {
    return (uint32_t)r | ((uint32_t)g << 8) | ((uint32_t)b << 16) | ((uint32_t)a << 24);
}

int main(int argc, char** argv) {
    (void)argc; (void)argv;
    printf("[z01] start pid=%d %dx%d\n", getpid(), kW, kH);

    RSSurfaceNodeConfig cfg;
    cfg.SurfaceNodeName = "Z01NativeWindowProbe";
    auto node = RSSurfaceNode::Create(cfg, /*isWindow=*/false);
    if (!node) {
        fprintf(stderr, "[z01] RSSurfaceNode::Create failed\n");
        return 1;
    }

    sptr<Surface> surface = node->GetSurface();
    if (!surface) {
        fprintf(stderr, "[z01] GetSurface returned null\n");
        return 1;
    }
    surface->SetQueueSize(3);

    OHNativeWindow* window = OH_NativeWindow_CreateNativeWindow(static_cast<void*>(&surface));
    if (!window) {
        fprintf(stderr, "[z01] OH_NativeWindow_CreateNativeWindow failed\n");
        return 1;
    }

    int32_t ret = 0;
    ret = OH_NativeWindow_NativeWindowHandleOpt(window, SET_BUFFER_GEOMETRY, kW, kH);
    printf("[z01] SET_BUFFER_GEOMETRY ret=%d\n", ret);
    ret = OH_NativeWindow_NativeWindowHandleOpt(window, SET_FORMAT, NATIVEBUFFER_PIXEL_FMT_RGBA_8888);
    printf("[z01] SET_FORMAT ret=%d\n", ret);
    uint64_t usage = NATIVEBUFFER_USAGE_CPU_READ | NATIVEBUFFER_USAGE_CPU_WRITE |
                     NATIVEBUFFER_USAGE_MEM_DMA | NATIVEBUFFER_USAGE_HW_RENDER;
    ret = OH_NativeWindow_NativeWindowHandleOpt(window, SET_USAGE, usage);
    printf("[z01] SET_USAGE ret=%d\n", ret);

    node->SetBounds(0, 0, (float)kW, (float)kH);
    node->SetFrame(0, 0, (float)kW, (float)kH);
    node->SetFrameGravity(Gravity::RESIZE);
    node->SetPositionZ(RSSurfaceNode::POINTER_WINDOW_POSITION_Z);
    node->SetBackgroundColor(rgba(0x20, 0x20, 0x20));

    ScreenId screenId = RSInterfaces::GetInstance().GetDefaultScreenId();
    printf("[z01] default screenId=%llu\n", (unsigned long long)screenId);

    RSDisplayNodeConfig dcfg;
    dcfg.screenId = screenId;
    dcfg.isMirrored = false;
    auto display = RSDisplayNode::Create(dcfg);
    if (!display) {
        fprintf(stderr, "[z01] RSDisplayNode::Create failed\n");
        return 1;
    }
    display->SetScreenId(screenId);
    display->AddChild(node, -1);
    display->AddDisplayNodeToTree();
    RSTransaction::FlushImplicitTransaction();

    const uint32_t colors[3] = { rgba(0xFF, 0, 0), rgba(0, 0xFF, 0), rgba(0, 0, 0xFF) };
    int committed = 0;
    for (int frame = 0; frame < 3; ++frame) {
        OHNativeWindowBuffer* buffer = nullptr;
        int fenceFd = -1;
        ret = OH_NativeWindow_NativeWindowRequestBuffer(window, &buffer, &fenceFd);
        if (ret != 0 || !buffer) {
            fprintf(stderr, "[z01] RequestBuffer failed ret=%d\n", ret);
            break;
        }
        if (fenceFd >= 0) {
            close(fenceFd);
        }

        BufferHandle* handle = OH_NativeWindow_GetBufferHandleFromNative(buffer);
        if (!handle) {
            fprintf(stderr, "[z01] GetBufferHandleFromNative returned null\n");
            OH_NativeWindow_NativeWindowAbortBuffer(window, buffer);
            break;
        }

        if (!handle->virAddr) {
            fprintf(stderr, "[z01] BufferHandle virAddr is null (cannot CPU fill)\n");
            OH_NativeWindow_NativeWindowAbortBuffer(window, buffer);
            break;
        }

        const uint32_t color = colors[frame % 3];
        const int32_t strideBytes = handle->stride;
        uint8_t* base = static_cast<uint8_t*>(handle->virAddr);
        for (int32_t y = 0; y < kH; ++y) {
            uint32_t* row = reinterpret_cast<uint32_t*>(base + (size_t)y * strideBytes);
            for (int32_t x = 0; x < kW; ++x) {
                row[x] = color;
            }
        }

        Region region;
        Region::Rect rect = { 0, 0, (uint32_t)kW, (uint32_t)kH };
        region.rects = &rect;
        region.rectNumber = 1;
        ret = OH_NativeWindow_NativeWindowFlushBuffer(window, buffer, -1, region);
        printf("[z01] frame %d FlushBuffer ret=%d color=0x%08x stride=%d\n",
               frame, ret, color, strideBytes);
        if (ret == 0) {
            ++committed;
        }
        usleep(300 * 1000);
    }

    OH_NativeWindow_DestroyNativeWindow(window);
    printf("[z01] done committed=%d/3\n", committed);
    return (committed > 0) ? 0 : 1;
}
