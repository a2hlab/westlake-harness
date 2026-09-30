# Flutter dependency boundary: offline repair proposal

The earlier assumption that adding two names to the shared-library list would
fix this cluster is incomplete. Both names already exist in v3c. Its
`libandroid.so` declares SONAME `liboh_android_runtime.so` (22 NEEDED entries),
but is a different binary: 9ccf64f8 / 744856 bytes versus current runtime
9e14bf20 / 2287968 bytes, while its `libGLESv2.so` exports **zero GL functions**.
The six apps fail before rendering, not at the previously investigated Flutter
Impeller first-frame failure. This report proposes a bounded experiment; it does
not claim a tested BMS fix or six lit apps.

## Evidence and provenance

* [First exceptions](evidence/two-board-first-errors.json): 12 archived observations,
  six keys on each of 5ea/61b r17p. FluffyChat, KitchenOwl and LocalSend report
  `Error loading shared library libandroid.so`; Immich, Aves Libre and Saber
  report `Error loading shared library libGLESv2.so`, all needed by libflutter.
  The extracted/relinked `app_lib` fallback also fails. These errors establish
  failed dependency resolution, not whether absence, isolation, or a deeper
  dependency caused each name to be rejected.
* [ELF identities](evidence/elf-identities.json) and `.elf.txt` files inspect the
  local v3c candidate, not a new device read. `libandroid` includes dependencies
  on GLES2/3, the bridge, runtime support, and OH surface/tracing libraries.
  The GLES2 recipe explicitly describes an empty soname placeholder.
* [LocalSend historical maps](evidence/localsend-historical-maps.txt), from
  [the September 27 run](../2026-09-27-localsend-bringup/README.md), show a small
  separate `/data/local/tmp/asx/libandroid.so`, real `/system/lib64/ndk/libGLESv2.so`,
  libflutter and libapp loaded. That run reached native windows and then crashed
  at a null graphics proc. It proves **loading progress**, not rendering success.
* [Source provenance](evidence/sources.json): Mac Westlake @532633da, 00.Workspace
  @f7373f9d, real-work @be16148da. The latter two policies already share
  `libandroid.so`, but omit `libGLESv2.so`; neither inspected policy supplies a
  validated Flutter-specific solution. Westlake's simple loader uses plain
  `dlopen`; its native-platform recipe builds a separate libandroid.
* Mac first, then OrbStack: the more complete loader is
  `/home/zhaoyue/a2hlab/ws/art-build/stubs/link_stubs_arm64.cc`, SHA
  `3f7e87a93a1707ad6039c7a676916d045276b4a2aa758f84eed1ce8d7acc98ab`.
  [Saved excerpt](evidence/westlake-vm-namespace.txt) selects native libraries by
  exact basename, creates one Android namespace, and explicitly inherits from
  its parent. The adjacent Westlake repo is @22b94532; **the stub is outside that
  repo and is identified by SHA, not falsely attributed to its commit**.
  The historical LocalSend launch environment was not recovered here, so its
  exact selection of this branch remains unproven. Relevant source was found;
  no hw248 search/download or build was needed.
* Westlake [GLES boundary source](evidence/westlake-gles.txt), section734, explains
  why the OH NDK GLES2 facade can return null GL state and uses
  `/system/lib64/platformsdk/libGLESv3.so` for WebView's GLES2 request. This is
  validated precedent for the provider choice, **not evidence of a Flutter fix**.

## Selected minimal experiment

**Change the Flutter load boundary, not the global namespace policy.** Copy
Westlake's exact-basename namespace selection and explicit owner inheritance;
adapt it inside the current ANL boundary, retaining v2 path admission, big-pthread,
error reporting and handle ownership. Select only the six listed packages' app
native domain when loading libflutter; keep their subsequent libapp/plugin loads
in the same domain. Non-Flutter domains keep the signed baseline behavior.
No generic fallback from every failed app dlopen to the default namespace.

1. Reuse the existing, already loaded runtime owner for `libandroid.so` through
   an explicit direct inheritance edge. Verify filename-alias lookup and identity;
   do not load a second copy of the runtime in the app domain. The stale runtime-named copy
   is neither the current runtime nor the historical small facade. Do not
   introduce that copy into the Flutter domain. Failure to resolve the alias is an
   explicit stop condition, not permission to broaden all paths.
2. Supply a **Flutter-private** GLES2 soname facade with a real dependency on
   the existing OH platform GLES3 implementation. Copy the provider selection
   from Westlake section734. It needs a direct owner edge for that dependency;
   do not search OH directories locally and instantiate duplicate OH libraries.
   A wrapper of the application's `dlopen` call alone cannot fix DT_NEEDED.
   Require strong Flutter GL imports to resolve through the facade's dependency
   closure, and dlsym on its handle to reach the same provider. Do not replace the
   global empty GLES2 library for unrelated apps in this experiment.
3. Share only the actual Flutter/app dependency names with their existing owners.
   Preserve the bionic ABI shim and pthread bridge ordering. The six APKs may
   import different symbol versions: enumerate each ELF before building, not a
   union of every system library. No new ART, host, provider, installer or JAR.

Expected delivery: **one replacement ANL** plus **one declared private GLES2
facade**, deployed/rolled back together. Existing loader APIs are present via
musl; the proposal avoids changing the host callback ABI. Implementation must
verify that independent namespace creation retains all current ANL lifecycle
semantics; if it cannot, report that boundary instead of silently modifying host.
A separate thin libandroid facade copied from Westlake is a fallback only if
alias ownership cannot be preserved; it is not pre-approved as part of this
minimal two-file candidate.

Why this choice: next2/3/4 expanded namespaces globally and repeatedly regressed
ZigZag. Next3 duplicated DFX initialization; next4 removed that failure but still
crashed in native-window handling. They are rejected experiments, not recipes to
copy. This plan limits the new path to Flutter and retains existing OH owners.
It is an adaptation of the inspected Westlake mechanisms, not a verbatim tested
BMS implementation. The exact owner edge/alias behavior is the critical pending
runtime experiment.

## Predictions and acceptance for outer scheduling

[predictions.csv](predictions.csv) predicts **6/6 can pass their currently named
missing-library layer**, conditional on the owner/facade gates above. Full
libflutter load and first frame remain unknown. LocalSend has specific prior
risk of a null graphics proc after loading; other Flutter versions may reveal
new symbol/version, TLS, plugin or rendering walls.

Before board scheduling: verify all six engines' strong imports/versions against
the proposed closure; verify SONAME/NEEDED and bounded owner lists; dry-run the
replacement/add package and rollback. This offline assignment did not extract
or audit all six engine ELFs, compile a candidate, or run these future gates.

First scheduled run: LocalSend + Immich cover both error families; HW/ZigZag are
controls. Log namespace owners and exact dlerror, capture maps after libflutter
load. Pass this layer only when the two named errors disappear and libflutter
actually loads. Require one ART, one runtime, one DFX instance and the intended
GLES provider; failure rolls back both files. If controls regress, reject without
running a long batch. Then run the other four and record screenshots/facts.
A successful dlopen or live process is not a lit app. Use compare_runs.py for
any later A/B causal claim and fix native/JAR/installer/boot/data variables.

## Scope of this result

Offline facts verified; repair unverified. No device commands, locks, builds,
new screenshots or process samples. No agent-spec was assigned to this proposal.
