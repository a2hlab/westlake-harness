# Article WebView investigation after #45

R2: partially; #46 article-rendering validation is in progress. #45 remains resident on board61 as crash material.
This work uses only board5ea34a45 and the feed-capable ability38-v7/out-sp20 base.
The earlier four-arm timing work is deprioritized in favor of article rendering.

## Address correction and call inference

cold-a4's faultlog prints `libwebviewchromium.so+0x3e026f0`, but this is not a
valid ELF PC for that frame. Registers PC `0x7e113806f0`, LR `0x7e13aa6fd4`, and
RX mapping `0x7e0f580000` at file offset0 give ELF PC **0x1e006f0** and LR
**0x4526fd4**. The first PT_LOAD has both offset and vaddr0. The deployed library
matches the analyzed SHA256 `27c34ff45b14fe68a397a6dbe78733731a8da5822ffcb334f8a8588f1546777b`.
The faultlog's frame0 overstates the relative PC by `0x2002000`.

At 0x1e006f0 the instruction is `ldr x8,[x0]`, with x0=0, agreeing with the
NULL SIGSEGV. At callsite0x4526fd0, `bl 0x1e006e0` follows a load of x0 from
`[x8,#240]`. Direct addr2line has no symbols. Do not interpret objdump's distant
nearest exported JNI label as this function's name.

**Source/disassembly inference, not symbolized proof:** the caller beginning at
0x4526dfc closely matches Chromium109 `viz::SkiaOutputSurfaceImplOnGpu` destructor
in `components/viz/service/display_embedder/skia_output_surface_impl_on_gpu.cc:327–384`:
remove context-lost observer, MakeCurrent, destroy output device and shared-image
collections/factory, conditionally use shader cache, initialize zero GrFlushInfo,
Vulkan cleanup, `gr_context()->flush(flush_info)`, `gr_context()->submit(true)`, then
destroy sync-point state. The suspected immediate callee is `GrDirectContext::flush`.
The source accessor returns `context_state_->gr_context()` without a null check.
The local Skia m133 flush implementation also matches the small function's
abandoned/callback branches, but m133 is not the exact WebView109 Skia revision.
Thus exact names remain inferred until independent symbol/source confirmation.

cold-a4 stderr supplies independent preceding failures:

- SharedContextState::InitializeGL: max_vertex_attribs0 < minimum8.
- GL version string is nullptr.
- GrGLInterface extension initialization failed.

These support failed GL/Skia initialization preceding the null GrContext use;
this is separate from npth's fork child and work_thread signal re-delivery.

## Narrow loader fix

`framework/webview-shim/webview_bionic_shim.c` already redirects direct WebView
requests for libGLESv2.so to `/system/lib64/platformsdk/libGLESv3.so`. Its comment
explains the Android NDK GLES facade lacks OH platform EGL thread hooks. However,
the earlier bare-soname `.z.so` fallback first dlopens the original name and
returns on success, so it bypasses GLES translation whenever the NDK facade loads.

Source commit **ae6d388380517b1595df551b286c4134ed3d3d50** moves the existing
GLES translation before that early return. It retains caller scoping, uses the
real platform GLES implementation and does not fabricate GL values or skip drawing.
Before editing, source bytes matched out-sp20's frozen shim source exactly.

Per #36, the build compiles one C object and relinks one .so using the unchanged
assembly object. Candidate SHA256: `ecc7b12c3591c979f3d9aece5bb1d414acc04d01d2c500a88364525082f9df9f`.
No full native-runtime or downstream build was run. Candidate substitution is
limited to the #38 application runtime. Earlier automated trials restored the
original after each trial; the explicit #46 manual verification keeps the patched
runtime resident for inspection.

## Trial validity

The baseline already logs `--single-process` and
`--disable-features=AndroidSurfaceControl`. Explicit in-process-gpu reaches the
child environment and produces the expected command-line marker.

- inprocess-1: no acceptance article touch; incomplete view-tree selection.
- inprocess-2: idle gate failed; no acceptance article touch.
- inprocess-3: startup consent/render ordering invalidated selection; lifecycle
  target was TikTokActivity, not NewDetailActivity. It is not article evidence.
- gles-fixed-1: actual feed touch reached InputConsumer DOWN+UP at uptime83274956/961ms, then parent reported signal11. No detail Activity or GLES translation marker; cause unknown, not assigned to RenderThread.
- gles-fixed-2: the initial automatic touch was invalidated by optional login.
  After physically dismissing login, the manual retry at uptime83521.44s opened
  NewDetailActivity record3, RESUMED83530.186s (+8.746s). `article-current.jpeg`
  shows the complete short article body. The old filename `after-120s.jpeg` is
  **+41.80s after this valid retry**, not 120s; its clock began at the invalid
  first attempt. Assertions are 1/0/0, with no matching child faultlog. The
  automated runner intentionally stopped this instance after observation.

## Explicit #46 deployment and manual article sequence

Run `wv46-articles-1` deploys the supplied **out-wv46/patched** artifact rather
than rebuilding. Its full hash is identical to the independently built #38 fix.
The original SHA256 is `ae6ac82830c2cd143469047c404765cd13b0c38106d2ccfe92596059f8e6b6ea`.
Before replacement it was backed up both on device at
`/data/local/tmp/ability38-webview46-original.<original-sha256>.so` and in VM
`ability38/wv46-verification/original-shim.so`; both hashes were checked. See
`evidence/wv46-verification/deployment.json` for exact target and source paths.
No npth or other library was changed for this sequence.

One data-preserving warm instance: child18719, parent18683; each article is opened
from an inspected feed with real `uinput -T -d x y -u x y`, then returned with
the visible back arrow. No i/c injection, no profiler, and no timeout-killing
observer. Article records and screenshots, rather than settings JSON matches,
are the acceptance evidence. Times use device uptime before DOWN to RESUMED;
they include uinput invocation overhead and are not precise touch-to-first-frame.

| Article | Physical coordinate | INPUT_BEFORE (s) | NewDetail record | RESUMED (s) | Elapsed |
|---|---|---|---|---|---|
| First feed item, Xinhua short body | 380,297 | 83891.730 | 2 | 83902.619 | 10.889s |
| Second item, CCTV body and image | 380,377 | 84001.580 | 3 | 84004.598 | 3.018s |

First item screenshot `article1-after60.jpeg` was re-captured after uptime
83962.59s (at least +70.86s); the earlier same-name capture at +51s was replaced.
The final hash manifest identifies the later image. Second item body screenshot
shows article text above and below an embedded video poster; video playback was
not requested or tested.

**New failure after the second article:** child18719 was alive at uptime84041.74s
(+40.16s), but absent at84089.95s. Its stderr ends after main-loop marker84058.925s
with SIGTRAP, TRAP_BRKPT, thread20753 `ThreadPoolForeg`, PC0x7d832fccd4;
parent confirms `child 18719 killed by signal 5`. No matching faultlog was found.
This is not the old RenderThread SIGSEGV signature, but its precise cause is
not established. `article2-after60.jpeg` was captured after process death and
is a **stale window, explicitly invalid as survival evidence**. The earlier
`article2-body.jpeg` is valid while the child was alive. Thus the two-article
sequence does not establish 60s survival for the second article. Its orphan19336
was archived and removed after verifying the same runtime namespace, before
restarting the unchanged patched runtime for the third physical article open.

Three required log counts so far are 1/0/0. An additional proposed assertion,
**no ndk/libGLESv2.so anywhere in process maps, does not hold**: it remains
mapped alongside platform GLESv3. The direct WebView translation log and real
rendered body establish the corrected selection for this path; global mapping
absence must not be claimed. Article1 comments show a network error. Neither
comments nor the old <2s performance target are fixed by these observations.

Screenshots must show body content, backed by the correct Activity lifecycle;
PID survival, JSON substring matches, video pages, gray surfaces and old windows
are not article success. Existing physical i/c injection is not used: uinput
provides touches, and mailbox v/T only requests diagnostics.
