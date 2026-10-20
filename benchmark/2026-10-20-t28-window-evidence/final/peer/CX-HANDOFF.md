# T28 actual transition handoff

Exact fixed video log: e2b0c32f14e7e910bb2b13296dc92b37d990f395ae2f03769bf08d3835c17100, 48,685,186 bytes, 554,390 lines. See video-analysis.json and video-excerpts.json. No new REA was performed.

The original playback/pause/resume succeeds visually. Later fullscreen tutorial then return to feed yields a 20-second pure-black video ROI. This later symptom is separate. All four recorded geometry calls requested YV12, not RGBX2. The first 256 T27 records show native OH12 and Android YV12, including three actual Mali +0x33e814 / target0x34e1 nonnull returns. Five R23 images in total and five successful destroys appear; the latter two images follow the window transition. No R23 create-failed or InvalidGrBackendTexture appears in this prefix.

Review the identity transition first: old OH 0x7f8b853970; wrapper changes at L364980, new OH 0x7d10194650 at L429804; old images destroyed at L430027-430030; two new images at L430857/L431068 destroyed at L432744/L441056. TextureView at L441058 again names old OH 0x7f8b853970, and L454064 creates wrapper0x7ec65848e0 for that OH with no later R25 line in the prefix. This is an observation, not proof of wrong association or stale ownership.

R20 logs end at seq63/L70074 and T27 caps at L75980, before the transition. Therefore later lock/cache/format outcomes are unknown. The post-trigger hilog only covers epoch1792476433.951-6439.656; it misses the transition and cannot establish the first error. Repeated missing optional-plugin and OhWindowPolicy messages are not established as the cause.

Suggested next narrow analysis: correlate actual TextureView/SurfaceTexture lifetime to the old/new OH identity; if runtime evidence remains needed, collect bounded per-window lifecycle/error records beyond the exhausted global caps. Do not change format policy or diagnose a Mali format rejection from these later black pixels alone.
