# ANativeWindow_lock / ANativeWindow_unlockAndPost — design + patch draft (U11 native, offline)

Our `libandroid.so` exports `ANativeWindow_acquire/release/fromSurface/getWidth/getHeight/getFormat/query/
setBuffersGeometry/setBuffersDataSpace/setBuffersTransform/tryAllocateBuffers` but **not** `ANativeWindow_lock` /
`ANativeWindow_unlockAndPost` (verified: `llvm-nm -D` on
`westlake-generation-n11b-ref-u8/.../libandroid.so`). Toutiao's native libs reference the lock pair (7 `.so`), and
fd-plus's "Surface software lock" wall is the same capability. This is the NDK software-canvas path: an app calls
`ANativeWindow_lock` to get a CPU-writable pixel buffer, draws into it, then `ANativeWindow_unlockAndPost` to
present — no GPU/EGL. Map to OH `NativeWindowRequestBuffer` (dequeue) + the buffer's CPU address + `FlushBuffer`
(post), exactly as the already-working `[WESTLAKE-CPUFILL]` and `oh_canvas_renderer` lockCanvas paths do.

## AOSP 14 reference semantics (frameworks/base native_window_jni.cpp + libgui Surface.cpp)
- `int ANativeWindow_lock(ANativeWindow* w, ANativeWindow_Buffer* outBuffer, ARect* inOutDirtyBounds)` →
  `Surface::lock(outBuffer, inOutDirtyBounds)`:
  1. `dequeueBuffer()` → a GraphicBuffer (+ acquire fence).
  2. wait the fence (CPU must not read/write until the producer/GPU is done).
  3. `GraphicBuffer::lock(CPU_READ|CPU_WRITE, &vaddr)` (gralloc CPU lock) → `vaddr`.
  4. fill `ANativeWindow_Buffer{ width, height, stride(**pixels**), format(AOSP), bits=vaddr }`; copy the dirty
     region forward from the previously-posted buffer if partial; set `inOutDirtyBounds` to the actual dirty rect.
  5. remember the locked buffer (`mLockedBuffer`).
- `int ANativeWindow_unlockAndPost(ANativeWindow* w)` → `Surface::unlockAndPost()`:
  1. `GraphicBuffer::unlock()` (gralloc CPU unlock).
  2. `queueBuffer(mLockedBuffer)` (post). Clear `mLockedBuffer`.
- Re-entrancy: a second `lock` without an `unlockAndPost` returns `-EINVAL` (one locked buffer at a time).
- The surface must be CPU-accessible (usage `CPU_READ_OFTEN|CPU_WRITE_OFTEN`), else dequeued buffers aren't
  CPU-mappable.

## OH mapping (all primitives already used in this tree)
| AOSP step | OH call | notes |
|---|---|---|
| dequeueBuffer | `OH_NativeWindow_NativeWindowRequestBuffer(oh, &ohBuf, &fenceFd)` | same as `aanw_dequeueBuffer` hook |
| wait fence | poll(`fenceFd`) then `close` | OH returns a release fence; CPU-usage buffers are usually ready — wait w/ timeout, proceed+log on timeout |
| gralloc CPU lock + vaddr | `BufferHandle* h = OH_NativeWindow_GetBufferHandleFromNative(ohBuf)`; `bits = h->virAddr` | OH mmaps CPU-usage buffers internally (`[WESTLAKE-CPUFILL]` uses `h->virAddr` directly). If `virAddr==NULL`, `mmap(NULL, h->size, PROT_READ|PROT_WRITE, MAP_SHARED, h->fd, 0)` and munmap on unlock |
| queueBuffer | `OH_NativeWindow_NativeWindowFlushBuffer(oh, ohBuf, -1, region)` | `region` from the clamped dirty rect; `fenceFd=-1` (CPU write finished synchronously) |
| gralloc unlock | (nothing for `virAddr`; `munmap` if we mmap'd) | OH owns the internal mapping |
| set CPU usage | `OH_NativeWindow_NativeWindowHandleOpt(oh, OH_OP_SET_USAGE, CPU_READ|CPU_WRITE)` | so `virAddr`/`fd` is CPU-mappable; set once before first lock |

### Buffer field mapping (the stride/format core)
`BufferHandle` (OH `external_window.h`/`buffer_handle.h`): `int fd; int width; int height; int stride; int format;
int size; void* virAddr; …` — **`stride` is the row **byte** stride**, `format` is an OH `GRAPHIC_PIXEL_FMT_*`.
`ANativeWindow_Buffer` (NDK): `int32_t width, height, stride, format; void* bits; uint32_t reserved[6];` — **`stride`
is in **pixels**, `format` is an AOSP `ANDROID_PIXEL_FORMAT_*`**. So:
```
outBuffer.width  = h->width;
outBuffer.height = h->height;
outBuffer.format = oh_pixel_format_to_android(h->format);     // pixel_format_mapper.h (OH 12 -> AOSP 1 RGBA_8888, etc.)
int bpp          = android_bytes_per_pixel(outBuffer.format);  // RGBA/RGBX/BGRA_8888=4, RGB_888=3, RGB_565=2, RGBA_FP16=8, RGBA_1010102=4
outBuffer.stride = (bpp > 0) ? (h->stride / bpp) : h->width;   // BYTE stride -> PIXEL stride  <-- the key conversion
outBuffer.bits   = h->virAddr;                                 // or mmap(h->fd, h->size)
```
`oh_pixel_format_to_android` already exists in `framework/surface/jni/pixel_format_mapper.h` (the OH↔AOSP table —
note OH's numbers are NOT Android's: RGBA_8888 is OH 12 / AOSP 1). `android_bytes_per_pixel` is a tiny helper to
add (or reuse one if present). This byte→pixel stride conversion is the single most common bug in this bridge
(OH stride-in-bytes handed to an AOSP consumer expecting pixels paints a skewed/torn image), so it is called out
explicitly.

## Shipping-library gate — ANSWERED: implement in libandroid, NOT the bridge
**`oh_anativewindow_shim.cpp` compiles into the 846 bridge, which is #96 = not reproducible from source** — so the
two functions must NOT go there. Evidence: the shim is listed in `native/bridge-sources.json` +
`native/bridge15-sources.json` (not any libandroid/hwui-shim source list), and the deployed 846
`liboh_adapter_bridge.so` *defines* `oh_anw_wrap` (`T @0xd6850`) + `oh_anw_wrap_for_activity`. Meanwhile the NDK
entries `ANativeWindow_*` live in **libandroid** (`framework/hwui-shim/jni/oh_native_window_shim.c`, in
`hwui-shim-sources.json`/`hwui15-platform-sources.json`; the deployed `libandroid.so` defines `ANativeWindow_acquire`
`T @0x40a78`), and that file **already imports `oh_anw_get_oh(w)` from the bridge** (its existing
`ANativeWindow_getWidth`/etc. call it). libandroid is rebuildable.

**So implement `ANativeWindow_lock`/`ANativeWindow_unlockAndPost` in libandroid** (a new C++ TU in the
hwui-shim/libandroid source set, e.g. `framework/hwui-shim/jni/anativewindow_lock.cpp`, added to
`hwui-shim-sources.json` + `hwui15-platform-sources.json`; C++ for the state map + `pixel_format_mapper.h`). Export
`extern "C"`. Wiring, with the bridge left **byte-identical** (no bridge rebuild → #96 is not in the way):
- **OH window**: `oh_anw_get_oh(w)` — already a bridge export imported by libandroid; returns the `OHNativeWindow*`
  for the AdapterAnw the app got from `ANativeWindow_fromSurface`.
- **OH NDK buffer ops** (`RequestBuffer`/`GetBufferHandleFromNative`/`FlushBuffer`/`AbortBuffer`/`HandleOpt`): call
  the OH platform exports **directly, resolved via `dlsym(RTLD_DEFAULT, "OH_NativeWindow_…")`** (they are resident in
  the app process — the bridge pulls them in), so libandroid gains **no new DT_NEEDED edge** (keeps the N2 native
  gate green; same `dlsym` trick the shim already uses for `SetScalingModeV2`).
- **Locked-buffer state**: lock/unlockAndPost cannot add a field to the bridge's `AdapterAnw`, so keep a
  **libandroid-local** `std::unordered_map<OHNativeWindow*, Locked>` + `std::mutex` (one locked buffer per window;
  a second `lock` without `unlockAndPost` → `-EINVAL`). `Locked` = `{OHNativeWindowBuffer* ohBuf; void* mmapAddr;
  size_t mmapSize;}` (dirty rect not needed — see refinement ③).

Relationship to `oh_anw_wrap` is unchanged: `oh_anw_wrap` (bridge) builds the `AdapterAnw` + the 10-hook GPU table;
lock/unlockAndPost (libandroid) are the CPU path that operates on the **same** OH window via `oh_anw_get_oh`, with
their own small lock-state map — they do not touch the bridge, the hook table, or `AdapterAnw`.

### Adopted refinements (outer ring 2026-10-01)
1. **`BufferHandle` field order**: take it from the **bms frozen sysroot's `buffer_handle.h`** (not a guessed
   layout); if in doubt, disassemble the on-board `libnative_window`/surface lib to confirm the `virAddr` offset
   before build. A wrong `virAddr` offset makes `bits` garbage.
2. **`.cpp`**: yes — a libandroid C++ TU (above).
3. **No copy-forward**: on return set `inOutDirtyBounds` to the **whole buffer** (`{0,0,width,height}`) and
   `FlushBuffer` the full-surface region. The NDK contract for `ANativeWindow_lock`
   (`android/native_window.h`) explicitly allows the implementation to **expand** the dirty region — reporting the
   full buffer is compliant and matches a Surface without the last-posted-buffer copy-forward optimisation.

`oh_anw_wrap(OHNativeWindow*)` builds the `AdapterAnw` (AOSP `ANativeWindow` POD + the 10-hook table that hwui's
GPU path uses). `ANativeWindow_lock/unlockAndPost` are **peers** of those hooks on the *same* `AdapterAnw`: they do
the same OH dequeue/flush but add the CPU mapping and a one-slot "locked buffer" record. `lock` gets the window via
`oh_anw_get_oh(w)` / `as_adapter(w)`; the locked `OHNativeWindowBuffer*` (and any `mmap` addr/size + the clamped
dirty rect) are stashed on the `AdapterAnw` for `unlockAndPost`. No change to the hook table or `oh_anw_wrap`
itself.

## Pending items resolved (offline, from the frozen sysroot headers)
Frozen sysroot = `westlake-inputs/oh61-oh-root/oh_mirror/foundation/graphic/graphic_surface`.

### ① `BufferHandle` field order + offsets — FIXED
`interfaces/inner_api/buffer_handle/buffer_handle.h:48–61` (included by `.../surface/external_window.h:41`, whose
`:559 OH_NativeWindow_GetBufferHandleFromNative` returns `BufferHandle*`):
```
L48 typedef struct {
L49   int32_t  fd;        // +0x00
L50   int32_t  width;     // +0x04
L51   int32_t  stride;    // +0x08   (BYTE stride)
L52   int32_t  height;    // +0x0c
L53   int32_t  size;      // +0x10
L54   int32_t  format;    // +0x14   (OH GRAPHIC_PIXEL_FMT_*)
L55   uint64_t usage;     // +0x18   <-- uint64_t, NOT int
L56   void*    virAddr;   // +0x20   <-- the bits pointer
L57   uint64_t phyAddr;   // +0x28
L58   uint32_t reserveFds;// +0x30
L59   uint32_t reserveInts;//+0x34
L60   int32_t  reserve[0];// +0x38
L61 } BufferHandle;
```
**Correction to the first draft**: `usage` is `uint64_t`, so after `format@0x14` there is 4 bytes of padding then
`usage@0x18`, putting **`virAddr` at +0x20** (not +0x1c). The draft `.cpp` struct is updated to the exact
12-field layout; `stride@0x8`, `format@0x14`, `virAddr@0x20` are the three the lock reads.

### ② OH CPU usage bits + SET_USAGE op — FIXED
`interfaces/inner_api/surface/native_buffer.h:66–79` — `enum OH_NativeBuffer_Usage`:
`L67 NATIVEBUFFER_USAGE_CPU_READ = (1ULL << 0)`, `L68 NATIVEBUFFER_USAGE_CPU_WRITE = (1ULL << 1)` → the lock sets
`usage = (1ULL<<0)|(1ULL<<1) = 0x3`. The op code: `.../external_window.h:101 enum NativeWindowOperation` →
`SET_BUFFER_GEOMETRY(0) L107, GET_BUFFER_GEOMETRY(1) L113, GET_FORMAT(2) L119, SET_FORMAT(3) L125, GET_USAGE(4)
L131, SET_USAGE(5) L137`; `SET_USAGE` takes `[in] uint64_t usage` (L133–137). So
`OH_NativeWindow_NativeWindowHandleOpt(oh, /*SET_USAGE*/5, (uint64_t)0x3)`. (Matches the shim's existing
`OH_OP_SET_USAGE=5`.)

### Board cross-check status (honest)
Pulled the deployed libs from **5ea (idle U9), read-only** via `hdc file recv`: `/system/lib64/chipset-sdk-sp/
libsurface.z.so` (sha256 `8f1879f82a307d3a…`; `/system/lib64/chipset-sdk-sp/libnative_window.so` is the same
bytes) and `/system/lib64/ndk/libnative_window_manager.so` (128680 B). The surface/native_window implementation
lib (which holds `OH_NativeWindow_GetBufferHandleFromNative` + the `SurfaceBuffer` getters) is a **stripped** ELF
(0 named symbols) — so a symbol-anchored disassembly **address** for a `virAddr`/`stride`/`format` field-read is
**not** obtainable offline without symbolizing/decompressing it, which is the heavier VM work the dispatch said to
avoid. The readable `libnative_window_manager.so` only exports the event-filter NDK (`OH_NativeWindowManager_*`),
not the buffer ops. The offsets are nonetheless pinned: (a) the platform and our libandroid compile against the
**same** `buffer_handle.h` (frozen oh_mirror → the board image is built from it), and (b) they are corroborated
**empirically on-device** — westlake-current's bridge reads `h->virAddr` (offset `+0x20`) through
`GetBufferHandleFromNative` and successfully CPU-fills+flushes a buffer (`[WESTLAKE-CPUFILL]`, oh_window_manager_
client.cpp:1987), i.e. `virAddr@0x20` works in a running build. **Deferred to cx-bms's on-board build step** (cheap,
on the board, not the VM): after building libandroid, log `handle->{stride,format,virAddr}` on the first
`ANativeWindow_lock` and confirm they equal the header offsets; if any looks off, `hdc`-pull + decompress the `.z.so`
and disassemble `OH_NativeWindow_GetBufferHandleFromNative` then.

## Patch draft
**Authoritative draft: `anativewindow-lock-draft.cpp`** (the libandroid TU, per the gate answer above — static
lock-state map, `oh_anw_get_oh(w)`, OH NDK via `dlsym`, whole-buffer dirty). The code block below is the earlier
**bridge-targeted** sketch kept only to show the field-mapping logic; it is **SUPERSEDED** by the `.cpp` because the
shim it edits is in the irreproducible 846 bridge — do not apply it.
```c
// (1) extern "C" decl block: real BufferHandle + GetBufferHandleFromNative
struct BufferHandle { int fd; int width; int stride; int height; int size;
                      int format; int usage; void* virAddr; /* …trailing fields unused here… */ };
struct BufferHandle* OH_NativeWindow_GetBufferHandleFromNative(OHNativeWindowBuffer* buffer);
// NB: confirm field ORDER against OH buffer_handle.h for the target image before build (the
// {fd,width,stride,height,size,format,usage,virAddr} order is the OH 6.1 layout; a mismatch mis-reads virAddr).

// (2) AdapterAnw: add one-slot locked state
struct AdapterAnw {
    /* …existing… */
    OHNativeWindowBuffer* lockedOh   = nullptr;   // the currently CPU-locked OH buffer (one at a time)
    void*                 lockedMap  = nullptr;   // non-null only if WE mmap'd (virAddr was null)
    size_t                lockedSize = 0;
    int32_t               dirtyX=0, dirtyY=0, dirtyW=0, dirtyH=0;
};

// (3) helper
static inline int android_bytes_per_pixel(int androidFormat) {
    switch (androidFormat) {
        case 1: case 2: case 5: case 0x2b: return 4; // RGBA_8888, RGBX_8888, BGRA_8888, RGBA_1010102
        case 3: return 3;                            // RGB_888
        case 4: return 2;                            // RGB_565
        case 0x16: return 8;                         // RGBA_FP16
        default: return 4;
    }
}

extern "C" int32_t ANativeWindow_lock(struct ANativeWindow* w,
                                      ANativeWindow_Buffer* outBuffer, ARect* inOutDirtyBounds) {
    AdapterAnw* a = as_adapter(w);
    if (!a || !outBuffer) return -EINVAL;
    if (a->lockedOh) { ALOGW("ANativeWindow_lock: already locked"); return -EINVAL; }   // one at a time
    // ensure CPU usage so OH gives a mappable buffer (idempotent)
    OH_NativeWindow_NativeWindowHandleOpt(a->oh, OH_OP_SET_USAGE,
        /*BUFFER_USAGE_CPU_READ|CPU_WRITE*/ (uint64_t)(1u<<0 | 1u<<1));
    OHNativeWindowBuffer* ohBuf = nullptr; int fence = -1;
    int32_t rc = OH_NativeWindow_NativeWindowRequestBuffer(a->oh, &ohBuf, &fence);
    if (rc != 0 || !ohBuf) { ALOGW("lock: RequestBuffer rc=%d", rc); return -EIO; }
    if (fence >= 0) { struct pollfd p{fence, POLLIN, 0}; poll(&p, 1, 1000); close(fence); } // wait producer/GPU
    BufferHandle* h = OH_NativeWindow_GetBufferHandleFromNative(ohBuf);
    if (!h) { OH_NativeWindow_NativeWindowAbortBuffer(a->oh, ohBuf); return -EIO; }
    void* bits = h->virAddr;
    if (!bits && h->fd >= 0 && h->size > 0) {
        bits = mmap(nullptr, h->size, PROT_READ|PROT_WRITE, MAP_SHARED, h->fd, 0);
        if (bits == MAP_FAILED) { bits=nullptr; OH_NativeWindow_NativeWindowAbortBuffer(a->oh, ohBuf); return -EIO; }
        a->lockedMap = bits; a->lockedSize = (size_t)h->size;
    }
    int fmt = oh_pixel_format_to_android(h->format);
    int bpp = android_bytes_per_pixel(fmt);
    outBuffer->width  = h->width;
    outBuffer->height = h->height;
    outBuffer->format = fmt;
    outBuffer->stride = (bpp > 0) ? (h->stride / bpp) : h->width;   // BYTE stride -> PIXEL stride
    outBuffer->bits   = bits;
    // dirty region: clamp caller's rect to the buffer; NULL = whole surface
    int32_t dx=0, dy=0, dw=h->width, dh=h->height;
    if (inOutDirtyBounds) {
        dx = inOutDirtyBounds->left   < 0 ? 0 : inOutDirtyBounds->left;
        dy = inOutDirtyBounds->top    < 0 ? 0 : inOutDirtyBounds->top;
        int32_t r = inOutDirtyBounds->right  > h->width  ? h->width  : inOutDirtyBounds->right;
        int32_t b = inOutDirtyBounds->bottom > h->height ? h->height : inOutDirtyBounds->bottom;
        dw = r > dx ? r - dx : 0; dh = b > dy ? b - dy : 0;
        inOutDirtyBounds->left=dx; inOutDirtyBounds->top=dy; inOutDirtyBounds->right=dx+dw; inOutDirtyBounds->bottom=dy+dh;
    }
    a->lockedOh = ohBuf; a->dirtyX=dx; a->dirtyY=dy; a->dirtyW=(uint32_t)dw>0?dw:(uint32_t)h->width; a->dirtyH=dh>0?dh:h->height;
    return 0;
}

extern "C" int32_t ANativeWindow_unlockAndPost(struct ANativeWindow* w) {
    AdapterAnw* a = as_adapter(w);
    if (!a) return -EINVAL;
    if (!a->lockedOh) { ALOGW("unlockAndPost: not locked"); return -EINVAL; }
    OHNativeWindowBuffer* ohBuf = a->lockedOh;
    if (a->lockedMap) { munmap(a->lockedMap, a->lockedSize); a->lockedMap=nullptr; a->lockedSize=0; }
    struct Region::Rect rect{ a->dirtyX, a->dirtyY, (uint32_t)a->dirtyW, (uint32_t)a->dirtyH };
    struct Region region{ &rect, 1 };
    int32_t rc = OH_NativeWindow_NativeWindowFlushBuffer(a->oh, ohBuf, -1, region);
    a->lockedOh = nullptr;
    if (rc != 0) { ALOGW("unlockAndPost: FlushBuffer rc=%d", rc); return -EIO; }
    return 0;
}
```
(Also: `#include "../../surface/jni/pixel_format_mapper.h"`, `<sys/mman.h>`, `<poll.h>`, `<unistd.h>`; declare
`struct ANativeWindow_Buffer` / `struct ARect` if not pulled from `android/native_window.h` — the `hwui-shim/
skia_compat_headers/android/native_window.h` already defines `ANativeWindow_Buffer`; reuse it.)

## Validation (offline + later on-board; no board here)
- Build libandroid; `llvm-nm -D | grep -E 'ANativeWindow_(lock|unlockAndPost)'` present (2 new exports).
- `abi_diff --calls` vs the current libandroid: only the two new exports added (no drift / consumer breaks on the
  existing 11).
- On-board (a later window, not now): re-run fd-plus (the Surface software-lock app) and a toutiao native path
  that `ANativeWindow_lock`s; confirm no `UnsatisfiedLinkError: … ANativeWindow_lock` and a non-torn frame (the
  stride conversion is the thing to eyeball on the screenshot).

## Open items for review
- Confirm the OH `BufferHandle` field order for the target image (buffer_handle.h) — the `virAddr` offset must be
  right or `bits` is garbage.
- Decide `.c` vs `.cpp` home for the two exports (recommended: `.cpp`, above).
- Partial-dirty copy-forward (AOSP copies the untouched region from the last posted buffer) is omitted here —
  fine for full-surface redraws (the common case); add later if an app relies on partial-update preservation.
Evidence: current libandroid symbols (`westlake-generation-n11b-ref-u8/.../libandroid.so`);
`oh_anativewindow_shim.cpp` (AdapterAnw/dequeue/flush), `oh_window_manager_client.cpp:1987` (`[WESTLAKE-CPUFILL]`
virAddr fill reference), `surface/jni/pixel_format_mapper.h`, `surface/jni/oh_canvas_renderer.cpp` (lockCanvas).
