# EGL surface ownership proposal (not implemented)

The colorspace retry did not fix the measured failure. Both Wikipedia and
Noice create a surface successfully, then receive EGL_BAD_ALLOC twice on
each subsequent attempt using the same shim, OH NativeWindow, display and
config. Retrying stripped attributes leaves the error at 0x3003. A cache of
raw handles alone would introduce a second lifetime bug: either caller could
destroy a handle still held by the other.

This is a design handoff only. No surface code was changed, compiled or deployed.

## Evidence and remaining distinction

The extracted logs retain original line numbers and their source SHA256 is in
`results.json`. Source run: master worktree
`benchmark/2026-09-30-egl-5ea/runs/egl-apps/5ea34a4500000000000000001123012c/`.

| App | First successful surface | Shim / OH NativeWindow | Later attempts |
|---|---|---|---|
| Wikipedia | 0x7F07ECE770 | 0x7F1198BB50 / 0x7F08CC9C90 | two creates, both first and stripped attempts fail |
| Noice | 0x7F08512440 | 0x7F0C71AB50 / 0x7F0A26F290 | two creates, both first and stripped attempts fail |

All three creates for each app run on the same RenderThread. That identifies
a thread, not a pipeline owner: multiple CanvasContexts use that thread.
The current wrapper does not log destroy. The remaining distinction is a
second owner versus incomplete/failed destruction of the first surface.

The local verified references were checked first: real-work at
`be16148da9ae7bb89c62e81e144ed0bceb5c4669` and the games suite's
`src/adapter/aosp_patches/libs/hwui/hwui_oh_abi_patch.cpp` both have the same
surface-to-shim map and unconditional forwarding destroy. Neither contains
an owner-aware duplicate-window repair to copy. The proposal reuses their
unwrap/callback plumbing and HWUI's existing unbind path.

Inspected exact a578 build inputs, retained under `bms/src/.work/b11-egl-retry/`:

- `oh61-rebuild-adapter/aosp_patches/libs/hwui/hwui_oh_abi_patch.cpp:738-822`:
  create unwraps the window; only a surface-to-shim callback map exists;
  successful destroy immediately erases it. There is no window-to-surface
  registry, owner token or current-binding tracking.
- `oh7-reference/base-full/libs/hwui/pipeline/skia/SkiaOpenGLPipeline.cpp:254`:
  `setSurface` destroys its own old handle before creating a new one.
  `onStop` unbinds but keeps the handle; `onContextDestroyed` destroys it.
  `getFrame` aborts if its handle is absent. The directory name does not change
  the recorded AOSP14/OH6.1 build provenance.
- `.../renderthread/EglManager.cpp:488,513`: create consumes `eglGetError` on
  failure; destroy first unbinds a surface if the manager considers it current.
- The shim source in `bms/src/adapter/framework/window/jni/oh_anativewindow_shim.cpp`
  has paired AOSP `common.incRef/decRef`; its `oh_anw_try_acquire/release` are
  deliberately no-ops. A new lifetime pin must not use these no-op probes.
  The callback map currently contains an unpinned raw pointer; its exact
  deployed bridge ABI must be checked before adding a pin.

EGL specifies BAD_ALLOC for an already-associated native window as well as
allocation failure. Destroy invalidates the handle, while resource release
can be delayed by current bindings. Therefore a successful destroy call alone
is not proof that immediate recreation is safe, and a deleted handle must
never be resurrected. See [EGL 1.5 sections 3.2 and 3.5](https://registry.khronos.org/EGL/specs/eglspec.1.5.pdf).

## Proposed minimal repair: explicit exclusive ownership

Keep the registry in OH_EglHijack, but put ownership decisions at the HWUI
caller seam. Do not silently change the public EGL create/destroy contract
into reference-counted sharing for unknown callers.

1. Add a private acquire/release interface between SkiaOpenGLPipeline,
   EglManager and OH_EglHijack. Assign each pipeline a monotonic owner token;
   do not use just the thread ID or reusable `this` address. Record display,
   actual NativeWindow, shim, window/session generation, config, requested and
   effective attributes, context/thread, owner token, surface and state.
   Pin the shim and native window through matched, verified reference APIs
   while the entry exists; avoid pointer-reuse identity errors. If a stable
   logical generation cannot be established, cross-owner transfer is disabled.
2. Same owner, same live window generation, config and rendering attributes:
   return the existing handle through the private acquire interface. This is
   idempotent; it does not add an extra release obligation. Move this check
   before `setSurface` releases its old handle. Mutable dataspace and swap
   behavior must match too. Incompatible changes follow ordinary release/create.
3. A different owner cannot reuse or destroy the existing handle merely because
   its window address matches. A stopped/detaching old owner may explicitly
   relinquish on RenderThread: cancel its future draws, unbind, clear its own
   handle, then release. Only after that acknowledgement may the new owner
   create. Keep this as ordinary release/create, not an implicit ownership steal.
4. If the old owner remains active, return an internal `BusyOwned` result and
   log both identities. HWUI must propagate this as a skipped/deferred frame,
   without calling `getFrame` on a missing surface, reporting successful
   rendering, spinning, or waiting synchronously on RenderThread. Retry only
   on a release/window lifecycle event; a bounded deadline reports failure.
   Two simultaneously active logical windows mapped to one NativeWindow are a
   bridge window-association defect: they require distinct backing windows.
   This conflict is not counted as a successful lifecycle repair.
5. On release, only the matching owner can release a live entry. Check actual
   current draw/read handles against EglManager's cache; unbind using the
   existing pbuffer path and require success before real destroy. Cross-thread
   or untracked current use is a conflict, not permission to force destruction.
   Preserve a retiring/error entry on failure. Once real destroy succeeds,
   invalidate the handle permanently. Recreate only after known bindings have
   been released; failure to reconnect is evidence to investigate, not a
   reason to return the deleted handle.
6. Serialize driver operations on the owning RenderThread, reserve a
   `Creating` entry before calling EGL, and do not hold the registry mutex
   while calling drivers or bridge callbacks. Keep callback lifetime valid
   through completion. Context loss/termination invalidates that display's
   entries and every corresponding pipeline handle; no stale entry survives
   a context/display generation change. Unknown EGL callers use the original
   behavior and cannot borrow managed handles.

The small state machine is `Absent -> Creating -> Live(owner) -> Releasing ->
Absent`, with explicit `Conflict` and `ReleaseFailed` outcomes. A failed real
create never creates a live map entry. Logs include an operation sequence,
owner/window generations, both current handles, create/destroy return values,
and the captured error; this resolves the present missing-destroy ambiguity
in the same candidate run as the repair.

The current retry wrapper consumes the final EGL error before EglManager reads
it. For the private HWUI interface, return `{surface, error, disposition}`
directly and use that error at the caller. For ordinary EGL callers, leave the
final driver's error unread; do not install a global fake eglGetError layer.
Intermediate retry diagnostics must not turn a final failure into EGL_SUCCESS.

## Predicted behavior and acceptance

| Scenario | Required observation |
|---|---|
| Same owner reacquires an identical live window | one real create; one handle; one final real destroy |
| Old owner explicitly detaches, new owner attaches | old draws cancelled; unbind succeeds; destroy once; new create succeeds |
| Two active owners / different logical windows | conflict reported; no forced destroy, shared raw handle, or false rendering success |
| Changed config/attributes/window generation | no incompatible reuse; old ownership released before recreation |
| Destroy or unbind fails; foreign current binding | no deletion/reuse claim; no stale handle returned; original owner remains accountable |
| Context loss, destroy/recreate loops, concurrent acquire attempts | no stale entries, duplicate real creates, double releases, or unmatched reference pins |
| Repeated Wikipedia welcome transitions and Noice onboarding | intended UI visible, no BAD_ALLOC loop, BAD_SURFACE, SIGABRT, or cross-window frame overwrites |
| HelloWorld, ZigZag, Auxio controls | screenshots retain their known UI; unchanged native inputs except libhwui |

Host tests should use a counting fake EGL driver and exercise both release
orders, current bindings, failure paths and context generation changes. Device
acceptance requires 10 create/detach transitions for each affected app, lifecycle
logs that return to the expected live-entry count after detachment, and t5/t20
screenshots/facts from the master runner. Repeated active-owner conflicts mean
the ownership hypothesis was not sufficient; fix logical window association
instead of adding shared-surface exceptions.

When implementation is scheduled, rebuild only libhwui using the retained a578
recipe and publish a SHA-checked single-file package. Keep Java fixed. If any
control regresses, restore the exact pre-experiment libhwui and rerun controls;
on the current 5ea experiment that file is a578b949, with be59260f retained as
the earlier signed baseline. No board lock or write is needed for this proposal.
