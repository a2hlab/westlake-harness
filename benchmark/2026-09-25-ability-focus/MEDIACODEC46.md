# MediaCodec follow-up on board5ea34a45

ACK(blocked), R2: partially. Deployment is verified; **zero valid video-article
survival observations**, so the requested three observations remain unverified.
Four unchanged-candidate startup attempts were blocked by other exits. No
successful article observation is inferred from zero errors in
a process that never reached the video decoder.

The supplied `~/a2hlab/ws/out-mc46/patched/liboh_adapter_bridge.so` was deployed
to the existing ability38-v7/out-sp20 application's private runtime. Original
SHA256: `e4ab5de64d20b8da6c7f388a7d5f5efd536f2962bb3913975e89ce824300c45a`.
Candidate: `d4fae8e5802f3153a85175243edf665714900381d463ffc5ca1e64d0b308775b`.
The original was backed up both on device at
`/data/local/tmp/ability38-mc46-original.<full-original-sha>.so` and in VM
`ability38/mc46-verification/original-bridge.so`; both hashes were checked before
replacement. The #46 WebView shim remains
`ecc7b12c3591c979f3d9aece5bb1d414acc04d01d2c500a88364525082f9df9f`.
See `evidence/mc46-verification/deployment.json` for exact paths. No rebuild,
system-partition write, data clear, npth patch or unrelated fix was added.

The prior child31745 and its same-runtime fork child32373 were archived and
stopped before replacing the bridge. Each restart preserves app data and checks
the namespace before cleaning stale same-app processes. Physical article touches
use uinput; no i/c injection. `verify_mc46.py observe` samples process state every
three seconds and captures screenshots at15/90/125s without stopping the app.
The screenshot and state are both required: a residual dead window is invalid.

| Attempt | Child | Result |
|---|---|---|
| mc46-1 | 8842 | Reached feed, then Handler(null Looper) NPE unwound ActivityThread and exited(1); no target article. |
| mc46-2 | 11759 | Physical feed touch but no NewDetailActivity ENTRY; same Handler/Looper NPE, exit(1). |
| mc46-3 | 14295 | Parent reports signal11 before any Activity ENTRY; no article touch. |
| mc46-4 | 16213 | Parent reports signal11 before any Activity ENTRY; no article touch. |

Both excluded startup attempts have getOwnCodecInfo missing implementation=0,
FATAL=0, SIGTRAP=0, but **UnsatisfiedLinkError=1**, from `libmetasec_ml.so` failing
to map with errno13. They also log the missing FileChannelImpl.transferTo0 native
method. Video initialization failure markers are0, so they do not exercise the
patch's intended fallback. These failures already resemble pre-patch startup
failures; this observation does not establish whether the new patch affects
their frequency. Their complete logs and exception extracts are retained.

Attempts3/4 have all four requested negative counts at0, but also no Activity
ENTRY and no video-initialization attempt. There is no valid 88s or120s article
survival value or readable article screenshot from this candidate. The old
WebView-only screenshots must not be reused as MediaCodec-patch evidence.
No matching child faultlog was found in any of these four attempts; the two
signal11 origins are unclassified, not assigned to RenderThread or the decoder.

The final dead-child instance, parent and any verified same-runtime orphan were
cleaned; both patched libraries remain on device for the next experiment.
No automatic runner or guardian remains active on board5ea. No other board was
touched. The prerequisite for completing this test is a startup that survives
the existing Handler/Looper and pre-Activity signal11 failures; the MediaCodec
fallback's effectiveness is still **unverified**, not disproved by these runs.
