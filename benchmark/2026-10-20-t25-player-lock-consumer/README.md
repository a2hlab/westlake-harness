# T25 exact player lock-return consumer

Successful lock and flush do not prove the player wrote a decoded frame. Exact player `0b4d95c5` first compares the returned width, height and format against its expected layout. A format-2 result while YV12 remains expected takes the `window is changed` branch; it does not automatically select RGBX video writing and does not continue YV12 video writing. That branch optionally clears the buffer, unlocks/posts, requests geometry again and returns.

Evidence: reused complete REA `drawPicture` record `ev_25df362b51418dd3cd64bdec8631e8f1070f65397ce136fc2de3e83e8ced9f9a` (provider `0x2f977c`, ELF `0x1f977c`), independently cross-checked at ELF `0x1f9b28–0x1f9b34`. The optional clear helper at ELF `0x1fad50` treats returned format 2 as packed four-byte pixels, but this only clears memory; it is not a video converter. Two functions examined, no new REA query, no device calls.

T25 logs contain three `window is changed` diagnostics and subsequent successful geometry calls. The actual lock output and reset flag were not recorded, so which comparison failed remains unknown. Runtime caller-address arithmetic is consistent with a candidate player base but is explicitly **not maps-bound**. No claim that this layout mismatch caused the separate EGL image-creation failure is made.

See `results.json` for exact addresses, branch evidence, runtime limits and private raw hashes.

## Bounded configuration follow-up

The third examined function slice, beginning at ELF `0x1f7f88`, stores YV12 `0x32315659` into the expected-format field `this+0x1d8` at `0x1f86b8` and passes YV12 to geometry at `0x1f8990`. The drawPicture retry clears only the reset flag after geometry succeeds; it leaves expected format unchanged. The reviewed R14 successful output set is `{1,2,3,4,5,0x16,0x2b}` and contains no YV12. Consequently, **while this caller retains YV12 mode, the format equality gate cannot succeed on any supported successful R14 result**, regardless of the live OH format. Dimensions or reset state may reject first, and concurrent mode changes remain outside this static proof. This contract mismatch does not prove the separate EGL image-create failure cause.
