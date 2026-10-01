/* DRAFT — ANativeWindow_lock / ANativeWindow_unlockAndPost for libandroid.
 * Add to framework/window/jni/oh_anativewindow_shim.cpp (the AdapterAnw + OH decls live there).
 * Also: #include "../../surface/jni/pixel_format_mapper.h", <sys/mman.h>, <poll.h>, <unistd.h>;
 *       ANativeWindow_Buffer/ARect come from hwui-shim/skia_compat_headers/android/native_window.h.
 * See design.md for the AOSP<->OH mapping and the byte->pixel stride rationale.
 * NB confirm the OH BufferHandle field order against the target image's buffer_handle.h before build.
 */

/* (1) in the existing extern "C" { ... } decl block: */
struct BufferHandle { int fd; int width; int stride; int height; int size;
                      int format; int usage; void* virAddr; /* trailing OH fields unused here */ };
struct BufferHandle* OH_NativeWindow_GetBufferHandleFromNative(OHNativeWindowBuffer* buffer);

/* (2) add to struct AdapterAnw { ... } — one-slot CPU-lock state: */
//     OHNativeWindowBuffer* lockedOh   = nullptr;
//     void*                 lockedMap  = nullptr;   // set only if we mmap'd (virAddr was null)
//     size_t                lockedSize = 0;
//     int32_t               dirtyX=0, dirtyY=0, dirtyW=0, dirtyH=0;

/* (3) helper: AOSP pixel format -> bytes/pixel (for byte-stride -> pixel-stride) */
static inline int android_bytes_per_pixel(int androidFormat) {
    switch (androidFormat) {
        case 1: case 2: case 5: case 0x2b: return 4; // RGBA_8888, RGBX_8888, BGRA_8888, RGBA_1010102
        case 3: return 3;                            // RGB_888
        case 4: return 2;                            // RGB_565
        case 0x16: return 8;                         // RGBA_FP16
        default:  return 4;
    }
}

extern "C" int32_t ANativeWindow_lock(struct ANativeWindow* w,
                                      ANativeWindow_Buffer* outBuffer, ARect* inOutDirtyBounds) {
    AdapterAnw* a = as_adapter(w);
    if (!a || !outBuffer) return -EINVAL;
    if (a->lockedOh) { ALOGW("ANativeWindow_lock: already locked (one buffer at a time)"); return -EINVAL; }
    /* ensure CPU usage so OH hands back a CPU-mappable buffer (idempotent) */
    OH_NativeWindow_NativeWindowHandleOpt(a->oh, OH_OP_SET_USAGE,
        (uint64_t)((1u << 0) | (1u << 1)) /* BUFFER_USAGE_CPU_READ | CPU_WRITE */);

    OHNativeWindowBuffer* ohBuf = nullptr; int fence = -1;
    int32_t rc = OH_NativeWindow_NativeWindowRequestBuffer(a->oh, &ohBuf, &fence);
    if (rc != 0 || !ohBuf) { ALOGW("ANativeWindow_lock: RequestBuffer rc=%d", rc); return -EIO; }
    if (fence >= 0) { struct pollfd p{fence, POLLIN, 0}; poll(&p, 1, 1000); close(fence); } /* wait producer/GPU */

    BufferHandle* h = OH_NativeWindow_GetBufferHandleFromNative(ohBuf);
    if (!h) { OH_NativeWindow_NativeWindowAbortBuffer(a->oh, ohBuf); return -EIO; }

    void* bits = h->virAddr;
    if (!bits && h->fd >= 0 && h->size > 0) {
        bits = mmap(nullptr, (size_t)h->size, PROT_READ | PROT_WRITE, MAP_SHARED, h->fd, 0);
        if (bits == MAP_FAILED) { OH_NativeWindow_NativeWindowAbortBuffer(a->oh, ohBuf); return -EIO; }
        a->lockedMap = bits; a->lockedSize = (size_t)h->size;
    }

    int fmt = oh_pixel_format_to_android(h->format);
    int bpp = android_bytes_per_pixel(fmt);
    outBuffer->width  = h->width;
    outBuffer->height = h->height;
    outBuffer->format = fmt;
    outBuffer->stride = (bpp > 0) ? (h->stride / bpp) : h->width;  /* OH byte-stride -> AOSP pixel-stride */
    outBuffer->bits   = bits;

    int32_t dx = 0, dy = 0, dw = h->width, dh = h->height;
    if (inOutDirtyBounds) {
        dx = inOutDirtyBounds->left < 0 ? 0 : inOutDirtyBounds->left;
        dy = inOutDirtyBounds->top  < 0 ? 0 : inOutDirtyBounds->top;
        int32_t r = inOutDirtyBounds->right  > h->width  ? h->width  : inOutDirtyBounds->right;
        int32_t b = inOutDirtyBounds->bottom > h->height ? h->height : inOutDirtyBounds->bottom;
        dw = r > dx ? r - dx : 0; dh = b > dy ? b - dy : 0;
        inOutDirtyBounds->left = dx; inOutDirtyBounds->top = dy;
        inOutDirtyBounds->right = dx + dw; inOutDirtyBounds->bottom = dy + dh;
    }
    a->lockedOh = ohBuf;
    a->dirtyX = dx; a->dirtyY = dy;
    a->dirtyW = dw > 0 ? dw : h->width; a->dirtyH = dh > 0 ? dh : h->height;
    return 0;
}

extern "C" int32_t ANativeWindow_unlockAndPost(struct ANativeWindow* w) {
    AdapterAnw* a = as_adapter(w);
    if (!a) return -EINVAL;
    if (!a->lockedOh) { ALOGW("ANativeWindow_unlockAndPost: not locked"); return -EINVAL; }
    OHNativeWindowBuffer* ohBuf = a->lockedOh;
    if (a->lockedMap) { munmap(a->lockedMap, a->lockedSize); a->lockedMap = nullptr; a->lockedSize = 0; }
    struct Region::Rect rect{ a->dirtyX, a->dirtyY, (uint32_t)a->dirtyW, (uint32_t)a->dirtyH };
    struct Region region{ &rect, 1 };
    int32_t rc = OH_NativeWindow_NativeWindowFlushBuffer(a->oh, ohBuf, -1, region);
    a->lockedOh = nullptr;
    if (rc != 0) { ALOGW("ANativeWindow_unlockAndPost: FlushBuffer rc=%d", rc); return -EIO; }
    return 0;
}
