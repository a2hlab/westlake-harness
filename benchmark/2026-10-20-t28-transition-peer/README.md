# T28 transition black-ROI — adversarial read-out (window/Surface lifecycle; same-address, reuse UNPROVEN)

Read-only adversarial review of the fullscreen-mask → feed transition that leaves a **persistent black video
ROI (child alive)** after the first video played (dynamic/pause/resume/audio all PASS). CC: **no REA, no HDC, no
device, no T28 edit, no rebuild.** Evidence (SHA-pinned): `…/t28-5cd-window-01/candidate-log-7636-video/
selected.raw` — 48,685,186 B, sha256 `e2b0c32f14e7e910bb2b13296dc92b37d990f395ae2f03769bf08d3835c17100`,
554,390 lines, pid 7636.

## Timeline (cited) — producer migrates oh; the old video-window ADDRESS reappears in the feed (reuse unproven)
- **The user-confirmed pass is the initial in-feed clip** (dynamic/pause/resume/audio; its TextureViews are the
  earlier `window=0x7f8b7df1f0/0x7f8b7df790` at L8744/L8753). The **fullscreen phase showed only a tutorial
  overlay — not a confirmed video pass**, so no pass is claimed for it. What the log shows at oh `0x7f8b853970`
  (wrapper `0x7f8b689910`) is a **healthy producer+import** (not a visual pass): `[WL-R25-GEOMETRY] oh=0x7f8b853970
  wh=476x360 fmt=842094169(YV12) result=0` (L67858, L68218); `[WL-T27] fmt=12 w=476 h=360 stride=1920 usageL=9
  window=0x7f8b853970 wbuf=… native=…` (L68007+) — buffer is **OH12/RGBA** (the T26 retarget, Mali-accepted);
  `[WL-R20-PAIR]` lock/unlock rc=0 L68009–70023; `[WL-R23-EGL] client/image` L68114+.
- A later same-address re-target: `[WL-R25-GEOMETRY] wrapper=0x7f8a373ba0 oh=0x7f8b853970` (L364980) — **different
  wrapper, same oh address.**
- **Return-to-feed after the mask** = a **NEW display node**: `[WESTLAKE-RSNODE] … TikTokActivity GetSurface=
  0x7e96461f50` (L428434), preceded by `[WESTLAKE-WSA] getSurfaceNodeId / nativeShowWindow_impl / wl_send_app_visible`
  re-attach (L428563–429739).
- **Producer geometry migrates to a NEW oh**: `[WL-R25-GEOMETRY] wrapper=0x7f89e933e0 oh=0x7d10194650 wh=476x360`
  (L429804) — post-mask the player targets **oh `0x7d10194650`** (the L428880 TextureView window), **not**
  `0x7f8b853970`.
- **The old fullscreen video-window ADDRESS re-appears in the feed**: `[WESTLAKE-TEXTUREVIEW] create
  surfaceTexture=0x7eee190dbc window=0x7f8b853970` (L430040) and `surfaceTexture=0x7eee1906ac window=0x7f8b853970`
  (L441058) — **distinct SurfaceTexture objects naming the SAME window pointer** `0x7f8b853970`; `[WESTLAKE-ANWFS]
  #15 mNativeObject=0x7f8b853970` (L454063). This proves **only that the address is the same**; it does **NOT**
  prove the OH window was freed and re-allocated. Same-address here could be **(a)** one **live** OH NativeWindow
  **shared** by multiple SurfaceTextures (TextureView recycling / nativeWindow sharing), **(b)** free-then-realloc
  to the same address, or **(c)** coincidence — deciding needs **destroy/free + object-generation** evidence,
  which this log does **not** contain. All `native-image init` are `detached=1 tex=0`.

So a shared window pointer does **not** by itself tell us whether producer and consumer see the **same OH window**:
`0x7f8b853970` is named by both the fullscreen video and the post-transition feed SurfaceTexture(s); whether that
is one shared live window or two distinct ones at the same address is **undetermined** from this log.

## Minimal falsifiable hypotheses (ranked; directly answering "source buffer/new OH window vs display consumer same?")
**H1 — producer and the black ROI's consumer are bound to DIFFERENT OH windows after the transition (strongest).**
Post-mask the player producer's geometry targets `oh=0x7d10194650` (L429804), while the feed re-created a
SurfaceTexture at the same-address fullscreen window `0x7f8b853970` (L430040/L441058). If the black ROI's display
consumer samples `0x7f8b853970` while the producer fills `0x7d10194650` (or vice-versa), the ROI samples a surface
no one is filling → persistent black. **Contingent note (unproven):** *if* `0x7f8b853970` was actually freed and
re-allocated (case (b) above), it would imply the T26/R20 "prevent address reuse via an owner reference" did not
hold across the fullscreen→feed teardown — but that requires destroy/free + object-generation evidence this log
lacks, so it stays a hypothesis, not a fact.
- *Falsify (next minimal observation, read-only):* for the post-mask feed, capture the **oh window + SurfaceTexture
  state the player actually PRODUCES into** AND the **oh window + SurfaceTexture the black ROI's display node
  (TikTokActivity surface `0x7e96461f50`) SAMPLES** — one oh or two distinct (`0x7d10194650` vs `0x7f8b853970`)?
  Two distinct ⇒ H1 confirmed. This needs the T27 observer **cap raised / reset or scoped to the transition**
  (its 256 budget is exhausted early in the first-video phase — see caveat), since the producer/consumer oh identities post-mask are
  currently budget-masked.

**H2 — orphaned SurfaceTexture at the same address, never re-attached under the new node.** The feed
SurfaceTexture at same-address `0x7f8b853970` is `detached=1 tex=0`; on the TikTokActivity re-parent it may never be
re-attached/updated under the new RSNODE `0x7e96461f50`, so the ROI samples an empty (black) texture — whereas the
first video's SurfaceTexture was freshly attached under its own node.
- *Falsify:* compare the attach/update sequence of the first (working) feed SurfaceTexture vs the post-mask
  reused-address one under their respective RSNODEs (same observation hook as H1).

## Explicitly NOT supported by this log (honesty caveats)
- **Marker absence proves nothing about the post-mask producer/consumer.** The T27 256-budget is exhausted
  **during the early first-video / fullscreen phase** (`[WL-T27] print-cap=256 reached` L75980; last `WL-R20-PAIR`
  L70023 — both early, **not** "at boot"). After that the log **cannot exclude** other buffer formats, later
  producer activity, or subsequent failures — their absence is a **coverage gap**, not evidence. `[WL-R23-EGL]
  destroy … result=1` (L441056) shows import activity continues post-mask. Which oh the black ROI samples is
  **uncaptured**.
- Geometry **succeeded** in the captured window (4× YV12 rc0, buffer fmt=12/Mali-accepted). This does **not**
  assert geometry/format is excluded as a contributor, nor that no later format/failure occurred (coverage gap).
  The transition lifecycle / window-identity reading is a **lead hypothesis**, not an established cause; a
  format/other contribution is not ruled out.
- "allocation freed/reused" is **not proven** — only same-address is observed (see the sharing-semantics note above).

## Scope
Read-only on the SHA-pinned T28 log. No REA/HDC/device, no T28 edit, no rebuild, no new deploy. The producer-vs-
consumer oh identity post-mask is the one open fact; it needs a transition-scoped (budget-raised) observation to
settle. Read-only static review of the T28 source's owner retain/release and SurfaceTexture↔nativeWindow sharing
semantics may continue to narrow (a)/(b)/(c) — without a destroy/free + generation signal, "reuse" stays a hypothesis.
