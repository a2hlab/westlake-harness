# Candidate window5: eight SIGABRT roots and conditional repair donors

## Correction first

SIGABRT is a termination mechanism, not a repair cluster. The proposed
"Flutter five keys hit libandroid preload -> libsurface.z.so" is **not** the
first-fatal path in these selected window5 attempts. All five plus LocalSend
and glmark2 enter the same **AAssetManager converter -> JNI GetLongField -> ART
JniAbort** path. Each app's own captured caller PC independently disassembles
to `bl AAssetManager_fromJava@plt`. None of the eight app-PID preterminal streams
contains a libsurface.z.so preload failure.

The eighth key, Subway Surfers, calls JNI FatalError from libmain's native loader
after same-TID libunity load failures for **libmediandk.so**, a different root.
Earlier GLESv3/VKQUALITY errors are not promoted to this first terminal.

**Read-only audit, no native patch, no device access, no current package changes.**
The unrelated unintegrated PLAY completion work was stopped on reassignment;
it is excluded from this listing and no audio candidate is proposed here.

## Identity and evidence discipline

Only master `2aa6c49df0` sources.json selects the attempts, all from candidate
window5. `observations.json` pins sources, hilog/record and runtime fingerprint
SHA256; every run fingerprint contains root libandroid9ccf and runtimeac59 below.
Do not substitute the incorrect earlier run_index/U9-layout cluster table.

All eight standalone `faultlogs/` directories are empty. Abort-message text is
not captured. Instead each hilog carries a DfxFaultLogger crash report matched
to the **app PID/TID/time**, despite its lines being emitted by a different
reporter PID. Last20 app-PID F/E logs, signal, report header and full native frames
are retained in `evidence/<key>-hilog.txt`, preserving original line numbers.
Those F/E messages include caught plugin/graphics errors: they are context, not
automatically the abort message or root cause.

The generic first_fatal report retains six frames for these records; the audit
continues the same matched raw crash block through `Registers:` so the app caller
is not lost. It does not change first_fatal.py or its original selector.

| Key | App PID/TID | First signal hilog line | Native app caller / complete stack line | Root |
|---|---|---|---|---|
| fd-fluffychat | 26309/26342 | 19656 | libflutter0x4cdb6c /19888 | Asset converter |
| fd-immich | 27586/27613 | 19210 | libflutter0x4f1094 /19655 | Asset converter |
| fd-kitchenowl | 27065/27089 | 25295 | libflutter0x4cdb6c /25725 | Asset converter |
| fd-libre | 28881/28904 | 19213 | libflutter0x4f1090 /19377 | Asset converter |
| fd-saber | 20351/20374 | 19194 | libflutter0x4f1090 /19637 | Asset converter |
| localsend | 5521/5548 | 25573 | libflutter0x4c09d0 /25994 | Asset converter |
| cv2-org-linaro-glmark2 | 3139/3163 | 43110 | native_getSceneInfo+60=0xad648 /43236 | Asset converter |
| subwaysurfers | 3245/3271 | 44194 | libmain0x4dc0 /44360 | Native loader FatalError |

Full source file paths are each row's `run/hilog.txt` in observations.json and
`signal_evidence` in results.json; table lines are those original files, not
renumbered excerpt positions. APK/member SHA and exact caller disassembly commands
are pinned per key. No stripped Flutter function name is invented.

## Cluster1: seven AssetManager converter JNI aborts

The common function is **not** an app's direct field lookup. Both currently
archived provider converters tail-call JNI GetLongField, preserving the caller's
link register; therefore no converter frame appears between libflutter/glmark2
and GetLongField in the crash stack.

| Current provider | SHA256 | Converter/cache |
|---|---|---|
| root libandroid.so | 9ccf64f8d1f6e1748665057273eaa4c2770098934d39afa160f2c6b4c18b06db | AAssetManager_fromJava0x7d9d8; gAssetManagerOffsets0x8b9e0; SONAME liboh_android_runtime.so |
| root liboh_android_runtime.so | ac59dec077195bc7678c712505b0d802c56e07edea8d049be4a188d20485b7bf | AAssetManager_fromJava0x1db7a4; gAssetManagerOffsets0x211500 |

WHOIS reports private libandroid ee2fb82c in two domains too. These names are
not interchangeable providers. Both listed root converters load a cached ID
through their GOT then `br x3`, JNI table offset0x328=808. Their cache definitions
are separate. **The actual resolved GOT owner was not captured for these dead
processes**; choosing it from the DT_NEEDED name alone is invalid.

The cache identifies `android/content/res/AssetManager.mObject:J`:
local AOSP14r1 `frameworks/base/core/jni/android_util_AssetManager.cpp:1564`,
and the upstream reference `android_util_AssetManager_aosp.cpp:141` consumes it,
`:1650` initializes it. The earlier same-member glmark audit identified a null
cached field ID in U8; see `benchmark/2026-10-01-b10-registration-impact/NATIVE-FIRST-FATAL.md`.
Here the stack/caller/current converter path is re-established, but the **exact
null-ID operand/abort text is not captured in window5**. Do not assert that the
Java field is missing, or that a specific owner's cache is zero, solely from this
stack. Cache/registration/owner mismatch is the conditional root hypothesis.

### Validated donor and route-A adaptation

Upstream commit **b24a118b0aa2fd9e4815cc5a09aabb5a0234bc17** records the asset
companion fix with FediSuite/Sift/CastLab drawing and Element remaining a control.
Its exact source/script snapshots, SHA256 and git-show evidence are retained.
This is upstream validation of the donor architecture, **not these seven keys**.

- `framework/webview-shim/android_asset_manager_bridge.cpp:33` defines
  wl_AAssetManager_fromJava; `:36` calls NdkAssetManagerForJavaObject. The open,
  directory/read helpers use the same runtime's AssetManager2/Asset ownership.
- `tools/build_asset_bridge.sh:28` links the companion against that runtime and
  libandroidfw, not another framework runtime. The c_str() source change fixes
  the reference Android15 String8 header difference.
- Current ac59 exports both NdkAssetManagerForJavaObject0x1a83a0 and
  AssetManagerForNdkAssetManager0x1a844c. Symbol presence is not proof that its
  cache/Java object layout or imported libandroidfw C++ ABI matches the donor.

**Minimal proposed repair:** reuse the donor's real wl_AAsset* bodies against the
initialized **sole** runtime/AssetManager2 owner, publish them through an attested
sealed owner route, and make the libandroid NDK facade forward all asset operations
to that same owner. Remove the old-runtime-as-libandroid duplicate via the already
approved narrow-root-shim design, preserving the268-export union/calls gate.
Never rebuild the provenance-missing9ccf as though source-identical.

Do **not** copy upstream shim `bridge_symbol`'s bare/default lazy dlopen here;
its framework68 plus preloaded-shim architecture differs from route-A. Validate
the exact Java registration/cache owner, field ID and Java mObject object creator,
the helper's symbol owner, complete AAsset API forwarding and Android14/15 C++
ABI before admission. Reinitializing only one of two caches or exporting only
AAssetManager_fromJava can still bind the wrong one or mix Asset objects.

Predicted first-fatal movement for each of these seven keys is **conditional**:
the converter abort disappears only if that sole initialized owner is actually
selected; next checkpoint is real asset access, Flutter engine/glmark scene init.
**The next exact fatal and t20 remain unknown**, not seven promised lights.
Fluffychat's caught AudioPortEventHandler.native_setup plugin error remains context,
not a proved later terminating wall. Graphics/libsurface failures may be later
prerequisites, but are not substituted for the captured first converter abort.

## Cluster2: Unity load failure, one key

Same app PID3245/TID3271 `hilog.txt:44187–44192` shows two attempts to resolve
`libmediandk.so` for `libunity.so`, including app/bridge namespace failure. The
actual libunity DT_NEEDED contains libmediandk and **50 undefined AMedia*/AImage*
symbols**; full list is in results.json, not the old plan's mixed81 NDK names.

`libmain` loader disassembly:

-0x4d48/0x4d5c: path then bare-name dlopen attempts;
-0x4d64: both null ->0x4df4, dlerror;
-0x4df4–0x4e1c: format rodata0x800 `Unable to load library: %s [%s]`, branch0x4db8;
-0x4db8/0x4dc0: JNI table0x90=FatalError, matching the captured caller.

The same FatalError site also handles `Unable to retrieve Java VM` and
`Unsupported VM version`. The site alone would not distinguish those causes;
the same-TID adjacent repeated media load failures plus this error branch make
the **missing required provider** the supported explanation. The actual formatted
abort text is still absent and is not relabeled as captured evidence.

No verified matching AMedia donor is present in the requested upstream tree or
its all-branch media/Unity history. b24a118 fixes assets, not this media closure;
cea21e0/f20217a fix different Flutter linkage/HDR/bare-name spelling and do not
repair this recorded Unity error. bbcb25d logs failed JNI members, an observation
tool, not a repair. Their git-show records retain these distinctions.

**Repair plan:** supply a real ABI-matched AMedia/AImage implementation plus its
app-domain DT_NEEDED closure, then verify all50 imports/versions/calling signatures
and the actual selected owner. Existing zigzag presence-only libmediandk is not
that donor. LIBMEDIANDK-PLAN-v2's unsupported/null/void media functions are not
a validated fallback for this Unity input, so are **not** proposed as a repair.
Do not alias libmedia_jni or libandroid to satisfy the missing media API name.

Prediction: without a real provider, first-fatal remains this loader abort; with
an ABI/closure-complete provider, next checkpoint is libunity relocation and
JNI_OnLoad/Unity initialization. Next exact fatal/t20 are **unknown**. A presence-only
file can merely replace missing-library with missing-symbol, not count as unlock.

## Reproduction and landing

```sh
python3 benchmark/2026-10-02-u12-sigabrt/collect.py
python3 benchmark/2026-10-02-u12-sigabrt/finalize.py
python3 benchmark/2026-10-02-u12-sigabrt/test_analysis.py -v
cargo test --manifest-path tools/spec-checks/Cargo.toml --test u12_sigabrt
```

The evidence-only tests use committed small files, not external `.artifacts`
executables. Collection rechecks original raw input identities and writes only
this audit's outputs. Persistent extracted ELFs/raw outputs are referenced by
SHA/path in receipts, excluded from Git. `landing-paths.txt` includes only this
audit and its contract/selector. Root README/DIGEST use additive documentation.json.
