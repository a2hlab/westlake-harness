# M3 GLSurfaceView: not the M1 last-session overwrite

## Correction and rule

The proposed causal chain was **child SurfaceView creates a second WMS session →
overwrites M1's process slot → null native window → EGL IAE**. It is contradicted
by all three signed window5 runs. Each app creates/publishes **one** session, and
its SurfaceView creates a **different RS producer under that same session**.
The dedicated child ANativeWindow is nonnull before the GL exception.

**Do not count these three keys as beneficiaries of M1's per-session slot repair.**
An RS child node is not another WMS session. An `unknown sessionId` message from
one bridge copy is not a null final result: the main VRI obtains its nonnull
published window immediately afterwards. The three apps are alive-white; the
GL exception is caught, not a process-terminating first fatal.

## Identity and scope

`results.json` pins the signed reference `u10-1-t8-reference/sources.json`, exact
run directories, raw hilog/record/t20/maps and both per-board fingerprints. All
three runs independently pin:

| Component | Full deployed SHA256 |
|---|---|
| bridge | `84695d62f515cfec6bb317c959ec55b1d5085bf82303f792a764cf549a22267a` |
| current runtime | `ac59dec077195bc7678c712505b0d802c56e07edea8d049be4a188d20485b7bf` |
| root libandroid, old renamed runtime | `9ccf64f8d1f6e1748665057273eaa4c2770098934d39afa160f2c6b4c18b06db` |
| framework.jar | `3e106350d882cd1f2f6d71c3cc4e9f124412d16f50a2dcb160007c34e6dde9af` |

`deployed_whois` raw output is retained. Its final maps summary is the tool's
**signed U9** inventory, not evidence that these window5 PIDs loaded a particular
copy. The per-key window5 maps and registration addresses are retained separately.
Each target maps two instances of the current runtime; the EGL JNI registration
lands in one instance at relative `0x1dd8bc`.

Only app-PID lines in launch−3s through min(t20, hilog end) are counted. Mirrored
`AppSpawnXJava` lines are excluded; compositor/system logs are not app failures.
The logs end **5.505 / 5.169 / 5.887 seconds before t20**, respectively. Absence
claims apply to that captured interval, not the uncovered final seconds.

## Three-key timeline

Line numbers below are in each row's original `hilog.txt`; complete portable
file paths and SHA256 are in `results.json`. Numbered copies are in `evidence/`.

| Key / app PID | Session success / publish | Main VRI window | Dedicated child ANW | GL thread / IAE |
|---|---|---|---|---|
| cv2-com-bytehamster-flowitgame / 31714 | 652:49293 / 49322 | `7F385F9B50`:49520–49521 | `7F371DB010`:49611–49614 | 31741:49828 |
| fd-app / 22614 | 664:25466 / 25485 | `7F3549EA10`:25644–25645 | `7F3549E8D0`:25753–25760 | 22664:26001 |
| fd-shatteredpixeldungeon / 30745 | 674:25335 / 25379 | `7F345BA010`:25529–25530 | `7F345BAB50`:25639–25646 | 30786:25858 |

- SurfaceView `SC.create`, `BBQ.create` and `oh_rs_get_child_surface_window`
  carry session **652 / 664 / 674**, not a new session number. Child and main
  pointers differ. There is no later publication of another session before IAE.
- Unciv and SPD's `S_nativeGetFromBlastBufferQueue` explicitly return those
  child ANWs (25760 / 25646). Flowit has the dedicated child update but does not
  print that getter line; do not invent its missing getter observation.
- Successful `OH_EglHijack eglCreateWindowSurface` lines belong to the **main
  hwui threads**, 31739 / 22644 / 30772, and use the **main** pointer, not the
  failing GL threads. Their lines are 49813 / 25995 / 25829. They cannot be used
  as proof that the child GL surface reached EGL.
- The failing GL threads never print `OH_NWFromSurface [STAGE0] ENTER` or an
  `OH_EglHijack` window-pointer call. **The GL JNI input jobject/mNativeObject
  and EGL native-window pointer are not observed.** Record this as unobserved,
  not `0x0`. The IAE occurs before the native EGL call.
- Exact deployed DEX shows `SurfaceHolder.getSurface()` unwrapping in EGLImpl,
  and the default window-surface factory catching/logging IAE and returning
  null (`evidence/framework-methods.json`). The same DEX pins SurfaceView's
  constructor allocating `mSurface` and `SurfaceView$1.getSurface` returning it
  directly (classes4.dex dexdump780068–780070); the normal holder path therefore
  supplies a Java Surface object, even when its native pointer is invalid.
  The subsequent `!readyToDraw()`
  warnings are 49837 / 26008 / 25865. Alive process is consistent with a caught
  rendering failure.

There are no explicit `readProcessWindowTarget` request/result logs in these
runs. Publication, lookup requests and final BBQ pointers are observed; a read
return must not be fabricated. One successful publication and a successful
dedicated child refute the stipulated **second-session overwrite** mechanism.

## Native root: EGL JNI conversion / owner lookup

The registered legacy **EGL10/EGLImpl**, not EGL14, comes from deployed ac59.
Its disassembly is authoritative:

1. `0x1ddbc4`: `dlsym(RTLD_DEFAULT, "ANativeWindow_fromSurface")` (x0=0),
   saved at `0x2117c0` at `0x1ddbc8` under a one-time static guard.
2. `0x1dd9a8–0x1dd9ac`: a null cached function goes straight to the failure
   branch; `0x1dd9b8` calls a nonnull function, whose null return also fails.
3. `0x1dd9c0` is the invalid-Surface IAE branch; `0x1ddb54` is the **later**
   actual EGL call. A failure of that EGL call logs EGL error instead; it does
   not generate this invalid-Surface IAE.
4. Both possible deployed converters, runtime `0x1972a8` and old root libandroid
   `0x407fc`, log STAGE0 unconditionally on entry. Neither entry appears on the
   failing GL TID. The main/UI converter logs do appear, proving that the
   logging path is present in these runs.

**Leading root hypothesis: cached RTLD_DEFAULT lookup misses the local/resident
runtime converter in the JNI caller's scope.** A cached null does not retry.
This is a **native EGL JNI owner/symbol-conversion** wall, not M1's window-slot
wall and not a demonstrated Mali/EGL driver failure.

Bounded conclusion: the null-return conversion branch is pinned by the exact
IAE and ELF. The dlsym return itself is not logged, and a null native-window
jobject before calling the converter is another branch to the same IAE. The
valid child producer plus no converter-entry log make scope miss the strongest
explanation, **not a directly captured dlsym result**. Do not label it proven
until the diagnostic below distinguishes those branches.

Source lookup succeeded locally. The EGL port's relevant source is admitted at
`benchmark/2026-10-01-n5-native/native-checks/egl.cpp:33` (lookup/cache) and
`:315` (legacy window JNI); numbered excerpts and full source SHA are retained.
The frozen recipe refers to `n4-native/gl/EGLImpl.o`. Reference source and
instruction-equivalent local blocks are **not a claim of full ac59 reproduction**.
Current `oh_window_manager_client.cpp` differs from deployed bridge internals
(including its publish helper signature); its excerpt is architectural context
only. The supplied AOSP14r1 EGLImpl is also reference only. No AOSP converter
that treats AdapterAnw as `android::Surface` may be substituted.

## Minimal repair proposal and predictions

Owner: **native runtime legacy EGLImpl binding**. Do not change the M1 window
cpp, Java app, or broad namespace/global flags.

1. First add a real HiLog observation at this JNI conversion point: GL TID,
   Java Surface argument, resolved converter address + owner, native mNativeObject,
   converted AdapterAnw/OH window, failure branch and EGL error. `fprintf(stderr)`
   is not present in these captured hilogs and is insufficient as the only
   observation. Never clear a pending unrelated Java exception silently.
2. If the cached default lookup misses, factor the **existing validated runtime
   Surface converter** behind a hidden/internal function and bind legacy EGLImpl
   directly to that local helper (retain the public NDK wrapper). Do not replace
   one blind RTLD_DEFAULT lookup with another, add a second runtime load, promote
   the whole library global, or cache a failed lookup forever.
3. Preserve the dedicated child pointer, AdapterAnw validation/refcount and its
   bridge-owned unwrap. Use the uniquely admitted resident bridge owner for the
   unwrap; do not open a second bridge or pass an unrecognized adapter pointer
   to platform EGL. If JNI actually receives a null Surface, fix that Java-to-JNI
   handoff instead; the proposed scope change alone is then insufficient.

| Repair | Expected exception movers | Screenshot outcome |
|---|---:|---|
| M1 per-session env slots | **0** of these three | no justified change |
| Correct EGL JNI conversion, if scope miss confirmed | **3 conditional**: Flowit, Unciv, SPD | unknown, subsequent GL wall unknown |
| Measured/unconditional unlocks in this offline delivery | **0** | unchanged signed white |

For each target confirm: same-session child survives; GL TID enters converter;
the returned AdapterAnw equals the dedicated child (not main VRI); EGL gets its
nonzero unwrapped OH window; no invalid-Surface IAE. This proves moving the
first blocking GL exception, **not** a lit screenshot. A nonzero child reaching
EGL followed by EGL_BAD_ALLOC/other error refutes a complete conversion-only
repair and exposes the next wall. Null jobject despite a valid child refutes
the scope-only hypothesis. Capture each native failure branch explicitly.

## Controls and handoff

- **Lit ShaderEditor**, PID29695, window4 session951, child `7F1DF942D0`:53935;
  same GL IAE at54128 on TID29714, but signed **lit**. The main UI can light
  without the failing GL preview. This is a negative control for “IAE implies
  white/dead”, not a control that its GL preview works. An earlier same-package
  launch PID29662 also binds natives; no events from unrelated packages are used.
- **White noice M1**, PID27629: publish644:32425, publish645:32914, older
  AppIntroActivity BBQ returns empty644:33051; MainActivity645 resolves:33249.
  This is the actual overwrite pattern absent in all three M3 targets.

cc-t3: keep M1's single-session empty-operation assertion and do **not** add
these three keys to M1's predicted movers. EGL owner lookup is related to the
broader multi-copy namespace problem, but it is not fixed by merely indexing
the process window-pointer slots. No implementation or runtime file is changed.

## Validation

`test_evidence.py` uses admitted JSON/text only: four tests, including controls,
raw-byte fingerprint pins, GL-thread separation, honest unobserved pointers and
the master-prefix portability regression. Rust `white_m3_glsurfaceview` bridges
the same checks; no ignored `.artifacts` or external runtime binary is needed.
Raw parse/lint/lifecycle, Python/Rust and land preflight output is in `evidence/`.
The first lifecycle used `--code .`, where there is no root Cargo project: two
scenarios were skipped (retained in `lifecycle-first.txt`). Rerunning with the
actual `--code tools/spec-checks` passed both scenarios. It is not recorded as
an initial pass. Raw gate bytes are archived under `.artifacts/raw`; public
copies normalize only the workspace path prefix, with both hashes recorded.
No candidate, ABI delta, N1/N2 manifest delta or board command exists in this
read-only delivery. `landing-paths.txt` excludes unrelated worktree changes.
