# T25 geometry adapter blueprint (design only)

The candidate's geometry failures are not implemented by the a9ab shim: its dynamic exports include only the paired lock/unlock Android window entries. The selected T23 log has 120 failures on 1080x1920/fmt2 and one on 576x1024/YV12. Exact libandroid765 passes its input directly to OH HandleOpt; exact surface8f returns 40001000 before opcode dispatch when the window/surface/magic admission fails. The actual T23 geometry resolver winner was not captured. The candidate hypothesis is a missing wrapper-to-OH boundary conversion, not a proven explanation for black video.

## Planned interface

A new translation unit exposes only `int32_t ANativeWindow_setBuffersGeometry(void *window, int32_t width, int32_t height, int32_t format)`. All helper symbols remain hidden. Its internal seam is conceptually:

- `int owner_acquire(void *wrapper)` / `int owner_release(void *wrapper)`: exact owner exports oh_anw_try_acquire/oh_anw_try_release, success is 1; acquire must succeed before get/ops, release occurs once on all acquired exits.
- `OHNativeWindow *owner_get(void *wrapper)` and internal `owner.unwrap(ctx, wrapper, &borrowed_oh) -> int`: reuse exact oh_anw_get_oh and the trusted T20 owner capability; do not inspect arbitrary window layouts.
- `int32_t (*handle_opt)(OHNativeWindow *, int32_t opcode, ...)`: exact OH_NativeWindow_NativeWindowHandleOpt; variadic opcode0 receives two int32 dimensions and opcode3 one mapped int32 format. Borrowed pointer remains under the extra wrapper reference for both calls.
- `binding.resolve_and_admit(ctx, &handle_opt, &identity) -> int`: select only the already loaded owner/provider instance, prove identity with the actual relevant slots/resolved function and exact ELF metadata. Unknown or foreign ownership fails before calling OH.
- `geometry.apply(ops, wrapper, width, height, format, &report) -> int`: invoke HandleOpt(oh, 0, width, height), then only if rc=0 and format>0 invoke HandleOpt(oh, 3, mapped_format). Never rewrite dimensions or turn failure into success.
- Report fields: original wrapper, borrowed OH, geometry entry/HandleOpt addresses, provider base/file identity, unwrap_rc, geometry_called/geometry_rc, format_called/format_rc, result. Uncalled statuses are explicit, not fabricated zero rc.

The borrowed pointer has the same valid-call lifetime and external serialization requirement as the existing trusted owner API. The accepted caller already holds a valid ANativeWindow reference. Exact dca owner_acquire takes one additional wrapper reference before unwrap; owner_release balances it once after both opcodes or any failure. This extends the call lifetime and does not transfer ownership. The owner is not an arbitrary-pointer validator. Loader calls use existing handles only; no fresh namespace or fallback provider load. Runtime evidence must show that the player's actual geometry call entered this new entry. Static exported names or successful CPU lock binding alone cannot establish that.

The first host test seams compile the actual new C unit, not a reimplementation. Cover trusted success and the exact format mapping, null and rejected foreign owner, missing/mismatched provider, geometry failure blocking format, format failure propagating, and zero/negative dimensions passed unchanged. The implementation and selectors do not exist yet; these are proposed acceptance commands, not completed tests.

## Reproducible verification commands

Current contract validation:

```sh
agent-spec parse specs/toutiao-video-playback/t25-geometry-unwrapping.spec.md
agent-spec lint specs/toutiao-video-playback/t25-geometry-unwrapping.spec.md --min-score 0.7
agent-spec contract specs/toutiao-video-playback/t25-geometry-unwrapping.spec.md
```

After root review authorizes implementation:

```sh
python3 benchmark/2026-10-20-t25-geometry/check.py
cargo test --manifest-path tools/spec-checks/Cargo.toml --test toutiao_t25_geometry ttvideo_t25_geometry -- --nocapture
python3 benchmark/2026-10-20-t23-egl-import/check.py
python3 scripts/lab/check_frozen.py
```

Build interface to implement: `build.py --repo REPO --sdk SDK --t23-build T23_BUILD --out NEW_PERSISTENT_DIR [--execute]`, default preview; all arguments and raw stdout/stderr/rc are persisted. It must first reproduce the pinned T23 input with unchanged objects, then add the one geometry TU; reject if the baseline cannot be reproduced. The ABI comparison is `python3 scripts/lab/abi_diff.py --old T23_SO --new T25_SO --consumer EXACT_HWUI_SO`, plus dynamic-symbol/version inventory proving old77 preserved and only geometry added. Do not substitute ABI success for runtime routing or visual acceptance.

The Rust selector will dispatch the real Python host/receipt checker. Static scenarios may pass while the final human scenario remains pending_review. Device entry admission and rollback remain separate outer operations. No T25 implementation, build, device call or runtime result is claimed here.

## Donors and boundaries

Reuse T20 `entry.h` owner contract and the already validated owner/provider binding mechanism. Related sources containing unwrap-before-geometry are `sources/api-implementations/shared-native-production/related-source/framework/android-runtime/src/android_graphics_compat_shim.cpp` and `sources/api-implementations/source-build-native691/westlake/framework/webview-shim/webview_bionic_shim.c`. Do not copy the former's unconditional return0 or the latter's broader loader/dimension semantics. Exact765 behavior controls the format mapping. The established T20/T23 files and frozen records are read-only; any adapted source is copied into this new directory with donor SHA/blob and modifications documented.

The existing REA/LLVM and selected-log evidence is persistently indexed under `$HOME/.local/share/westlake/t23-codex-rea/geometry/`. Before construction, copy only small sanitized identity/excerpt evidence into the new directory, preserving original raw receipts elsewhere. The evidence does not prove the actual geometry slot. No additional static inference is promoted to a recorded runtime observation.

## Adversarial review response (actual spec exists; no implementation)

1. **Concrete same-instance gate.** Copy the T20 resolver pattern into an independent T25 unit, retaining original T20 untouched. Open the already-loaded exact owner with RTLD_NOLOAD only; require its get/acquire/release offsets 0x125dc0/0x125dfc/0x125e4c. Validate readable ELF PT_LOAD coverage before reading actual owner Reference/Unreference slots 0x1740a0/0x173fc8. Their values must equal owner-handle dependency-scope dlsym resolutions and share one libsurface base. Resolve HandleOpt through that same owner handle, require its dladdr base equal that proven base and its offset equal exact8f 0x68c10. Log this new geometry route and compare actual player entry/winner evidence; the CPU pair log alone cannot satisfy this gate. This proves the candidate's selected HandleOpt instance, not the historical765 winner.

2. **Lifetime is supported for the accepted valid-wrapper domain.** Exact deployed dca owner disassembly in review-response/ proves acquire atomically increments wrapper refs at 0x125e28–38 and release decrements at 0x125e80–9c with final destroy. The older source comments describe a conditional no-op build and must not override the exact ELF. Hold one extra owner reference before unwrap, through both opcodes, and balance once on each exit. The caller must already own a valid ANativeWindow reference on entry, as T20 explicitly requires. An already stale pointer cannot be made safe by acquiring it. No new magic-based classifier is introduced.

3. **Format ring is a real side effect, not a new public geometry contract.** Exact765 remembers requested Android format under the original wrapper key *before* HandleOpt even on geometry failure. Related libandroid_webview_core_shim.c has the ring writer at 527 and reader at 547, consumed by its legacy lock at 745 to select YV12 scratch conversion. T20 lock's actual module obtains format from the returned OH buffer and never reads this private765 ring. Therefore no extra T25 ring should be invented: it would not update the old private consumer and keying it on OH would be wrong. Within an admitted player whose lock/unlock are proved to use T20, the legacy ring is outside that selected data path. If a caller still uses765 lock, intercepting its geometry without preserving the original wrapper-key ring is a regression risk; reject candidate admission for mixed routing until that requirement is explicitly handled. Do not call old geometry solely to mutate its ring, because it has unintended provider calls.

4. **Native OH classification is unavailable.** The owner_get/acquire methods validate their own known bridge wrapper layout and assume a valid input object. They do not provide a provenance registry for raw OH pointers. The proposed generic raw-OH pass-through cannot be implemented safely by probing WIND, and is explicitly outside this bounded candidate. The contract accepts trusted player/bridge wrappers only, with foreign rejection before OH calls. If broad raw-OH compatibility is required, a real owner-provenance classification capability is needed first.

Build readiness blockers are now explicit: actual geometry entry route and player lock-route admission still need their own runtime evidence; safe raw-OH/mixed765 routing is not established and is excluded, not silently assumed. The same-instance resolver and exact-owner lifetime seams are implementable from existing evidence. Geometry rc preservation was already explicit in the generated contract and remains unchanged. No geometry-only success can sign video playback.
