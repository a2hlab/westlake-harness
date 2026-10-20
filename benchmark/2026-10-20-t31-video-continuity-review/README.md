# T31 video continuity checkpoint

Launcher triage is deferred. No new black-screen fault is established. The latest inspected pair shows a swollen phone followed by a person gaming on a phone, with different subtitles. Actual captured_at separation is 19.877780 seconds, not a fabricated strict 20 seconds. Earlier images show real feed then charging-topic video content. Black letterboxing/background is not a failed video ROI. User has confirmed manual video opening with sound; do not ask for per-clip sound confirmation again.

## Exact-source boundary

`provider_adapter.c:29-35,58-81` releases only this pristine reserved record after a nonzero request with NULL buffer, fd=-1 and no collision/concurrent pollution. It returns the original error; it does not itself retry RequestBuffer. `window_module.c:117-132` frees the corresponding resource-free failed reservation and finishes the cache with retained=0. Other acquired/uncertain paths retain ownership conservatively. `pair.c:119-132` releases the extra owner ref on non-retained lock failure or successful unlock. These conditions are intentional safety boundaries, not new observed defects. Production and current physical/private pins match the T30/T31 tuple in results.json.

Existing consumer observations cover SurfaceTexture attach/detach/update (`oh_surface_texture_jni.cpp:293-411`) and TextureView old/new producer plus separate ref/unref returns (`oh_texture_view_jni.cpp:73-161`). They can correlate a transition with subsequent CPU request/output/flush without adding a probe. Reused addresses alone never establish the same object generation. The current checkpoint has no transition log excerpt, so a complete resource-release/next-request runtime chain is not claimed. No additional binary gap requiring REA was identified.

## Shortest existing-window evidence sequence

1. Keep the current live child. Use the visible pause control: record actual click time, compare video ROI at pause+0/+3s, resume and compare +0/+10s. Do not mistake clock/subtitle controls for video content motion.
2. Perform one visually selected fullscreen/back or feed/video transition, then play the next selected item and retain actual +0/+20s images. Compare content, preserve any transient/lasting black ROI; do not infer a new fault from historical T28 images.
3. Exit to desktop and use the normal icon once; retain resulting feed/video screenshot and PID/birth to distinguish warm reentry from a new child. Do not terminate a healthy child just to manufacture cold reentry.
4. Reuse the existing fixed-range stderr collector once around these actions, preserving boot/PID/birth, inode, [start,end), SHA and action timestamps. Read WL-R29 consumer old/new/ref/unref and CPU request/retained/output/flush sequence only for that interval. Cap/filter silence is unknown, not proof of absence; if UI passes, missing internal logs are explanatory limits rather than a new deployment gate.

After each uitest click/keyEvent, use the already-approved same serial shell to set override 86400000 and read it back; restore the original setting at closure. Root remains the only device executor. Preserve the existing experiment/recovery deadlines. No source change, build, deployment, extra audio question or new test framework is proposed.
