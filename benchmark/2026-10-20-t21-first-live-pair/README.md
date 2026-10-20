# First actual paired CPU-window results

The initial impression that all three candidate children stopped immediately after unwrap was wrong. **Child 11040 completed five successful CPU lock/unlock pairs**: request, handle, conversion and map returned zero; each unlock unmap/flush returned zero. The same NativeImage state emitted five frame-available callbacks. It then logged `Invalid GrBackendTexture` (1200×2132) and RenderThread SIGABRT. This moves the observed API wall beyond the old fixed `-19`; it does not establish displayed video or a cause shared by the other two exits.

| Child | Bind / unwrap | Successful lock / unlock | Explicit fatal in complete saved stderr |
|---|---|---|---|
| 8306 | context creation zero; one successful unwrap | 0 / 0 | None found; no returned PAIR record after unwrap, exit cause unknown |
| 11040 | context creation zero; six successful unwraps | 5 / 5 | `FATAL skia` at source byte 442461; SIGABRT at 447480, RenderThread 11814 |
| 13834 | No R20 marker | 0 / 0 | None found; caught window-policy class-init error is not by itself proof of exit cause |

Each reviewed raw file was supplied by the outer loop after its fixed-file hash collection. Exact input hashes, counts, public technical excerpts and original byte positions are in `results.json`/`excerpts.json`. This review itself made zero device calls. Player GOT slots and fresh maps are not supplied here, so successful operation logs are not presented as the missing four-slot receipt.

## Object and size chain

For 11040, the main UI BLAST path uses wrapper `0x7e240d07a0` at 1200×1920. A separate logged SurfaceTexture initializes state `0x7d12fe5500`, NativeImage `0x7d12fc3c30` and raw OH producer window `0x7d12fd5dd0` (source byte 293810). TextureView and Surface.nativeCreate use that raw window. ANWFS #2 wraps it to `0x7d22edff20` at byte 308247; every R20 lock uses this wrapper and unwraps back to the same raw OH pointer. Its frame callbacks name the same state/image.

The creation stack explicitly includes `BDASplashVideoView.onSurfaceTextureAvailable`: this is the launch splash-video TextureView, before feed, not the later 712×360 feed video. At byte 317306 its default size is set to 1200×2132 with consumer/producer rc zero. Five later player requests for 1080×1920/format2 return 40001000; that is a real geometry failure, but these logs do not prove it causes the backend-texture abort. The full-screen dimensions alone do not prove that the main UI producer was reused, and wrapper versus raw OH addresses must not be compared as equivalent object layers.

The repository source has separate creation paths: `oh_surface_texture_jni.cpp:127–143` creates a NativeImage and acquires its producer; `:425–437` exposes that same state/image to the consumer adapter. `oh_texture_view_jni.cpp:38–50` obtains that producer. `oh_anativewindow_shim.cpp:691` retains/wraps the supplied OH pointer rather than selecting a main UI window. The main UI `focus34/.../oh_surface_bridge.cpp:210` obtains `surfaceNode->GetSurface()`. The HWUI adapter `oh_surface_texture.cpp:170–225` acquires the latest buffer from its NativeImage, converts it to OH_NativeBuffer and returns that object through the AHardwareBuffer boundary. These source facts and observed pointer chain do not support adopting the shared-main-UI hypothesis without further evidence.

The next minimum evidence is already-saved hilog for child11040 / RenderThread11814 around 10:56:31–32: identify the actual backend and EGL/Vulkan buffer-import failure preceding `Invalid GrBackendTexture`. Do not re-run the five already observed successful pairs merely to establish that the original lock wall was crossed. Do not classify the two other exits as the same failure or investigate an unrelated random crash. No new runtime build or deployment is part of this review.
