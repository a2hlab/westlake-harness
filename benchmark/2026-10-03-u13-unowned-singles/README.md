# Three unowned single keys: glmark2, chessclock, fd-api — U13 first-fatals, mechanism, minimal fix

#90, offline, no board. The three unowned keys from `u13-dead-keys-recheck`. Per key: the U13 first-fatal + earliest
wall (verbatim in `evidence/three-singles.txt`), mechanism classification (is the gap in **our** layer, and which — or
is it the **app's own** precondition), and the minimal fix + the U15 artifact for the small ones. (Trampoline / AMS
caller-record work for x is cc-t3's — not touched here.)

| key | U13 first-fatal | layer | U15 small-fix artifact |
|---|---|---|---|
| glmark2 | SIGABRT: `GetLongField` JniAbort in glmark2's own `getSceneInfo` | **app-native JNI** (surfaced by route-A ART) | none clean (runtime JNI-check toggle, needs experiment) |
| chessclock | `InvalidDisplayException` ← our `createSession: Not connected to SceneSessionManager` | **ours: window-session bridge** (+ secondary JAR skew) | secondary: JAR method decl; terminal: window-session (not a single-key fix) |
| fd-api | `IllegalStateException: need a Theme.AppCompat theme` | **ours: theme/resource resolution** | activity/theme bridge (JAR): apply the target AppCompat theme to the activity context |

## glmark2 — app-native JNI abort (not our missing class/field)
`Java_org_linaro_glmark2_native_getSceneInfo(JNIEnv*, jclass, jobject)` → `JNI::GetLongField` → `JavaVMExt::JniAbort` →
SIGABRT. The native reads a `long` field from the passed `SceneInfo` jobject; ART aborts in `GetLongField`. The
class/field are **glmark2's own**, so this is **not** a missing-class/field in our layer. The abort is either (a) an
**uninitialized/mismatched `jfieldID`** (the app's native init is visibly unhappy just before — `nativePrimeDefaultTypeface
reflect FAILED`, `InputManagerGlobal.sService NoSuchFieldException`, `libiGraphicsCore.z.so` ENOENT → the GL/typeface
init path that caches field IDs did not complete), so `GetLongField(obj, bad-id)`; or (b) **route-A ART's JNI validation**
aborting an access a stock *release* ART would tolerate. The ART abort reason text was not captured in this buffer, so (a)
vs (b) is not decidable statically.
- **Minimal fix:** no clean small fix in our layer — the call is the app's own native. If it is (b) (JNI-check strictness),
  running app child processes with JNI checks **off** (release-mode, matching stock) would let `getSceneInfo` through —
  a runtime-config change, **not recommended blind** (it masks real JNI bugs). The decider is a ≤10-min on-board
  experiment: flip the runtime's JNI-check flag for the app process and re-launch glmark2 — if the abort disappears → (b)
  check-strictness (then weigh the toggle); if it still aborts → (a) a real bad field-id (app-native, effectively unfixable
  from our side). glmark2 is a GL benchmark tool — **low value**; recommend leaving unowned pending that experiment.
- **Prediction:** not moved by any current U14/U15 part.

## chessclock — our window-session bridge (terminal) + a JAR/RegHook skew (secondary)
**Terminal:** `WindowManager$InvalidDisplayException "the specified display can not be found"` at `addView`
(`handleResumeActivity`). The root is **ours**: `OH_WindowMgrClient createSession: Not connected to SceneSessionManager`
→ `OH_WSAdapter Failed to create OH session, wsErr=1005 -> addCode=-9` → AOSP maps `addCode=-9` (WM_ADD_INVALID_DISPLAY)
to `InvalidDisplayException`. So it is **not** a display problem — our window-session bridge failed to connect to OH's
SceneSessionManager for this app, and the -9 surfaces as "display not found" (the same window-session machinery family as
the M-walls).
**Secondary (earlier, non-terminal):** `NoSuchMethodError … ActivityManagerAdapter.nativeConsumeConnectionFailure(I)Z`,
thrown from `Runtime.nativeLoad` during `MediaPlayer.<clinit>` (ChessClock.initRingtone). The RegHook **registered**
`nativeConsumeConnectionFailure` (→ `liboh_adapter_bridge.so`) but the deployed `ActivityManagerAdapter` JAR class does
**not declare** the native method → `RegisterNatives` fails → NSME. **Ours** — a RegHook/JAR version skew.
- **Minimal fix (secondary, clean, U15 JAR):** add the `private static native boolean nativeConsumeConnectionFailure(int)`
  declaration to `adapter.activity.ActivityManagerAdapter` in the runtime JAR (`oh-adapter-runtime.jar`) so it matches the
  RegHook table. This clears the NSME. **But it is not the terminal** — chessclock still dies on the window-session
  `InvalidDisplayException`.
- **Minimal fix (terminal):** the window-session bridge must connect to OH SceneSessionManager at resume (`createSession`
  succeeding instead of wsErr=1005). That is the window-session path (M-family), **not** a chessclock-specific small fix —
  flag to whoever owns the session bridge. Prediction: chessclock lights only when the session bridge connects; the JAR
  method-decl fix alone does not light it.

## fd-api (com.termux.api) — our theme/resource resolution for an aliased AppCompatActivity
`TermuxAPIMainActivity` (AppCompatActivity) is launched via the alias `TermuxAPILauncherActivity`. Our `[B8-ALIASTHEME]`
re-resolves the target theme `0x1030237 → 0x7f120252` — which **is** the activity's manifest-declared theme
(`<activity TermuxAPIMainActivity android:theme="@ref/0x7f120252">`), so we picked the **right id**. Yet
`AppCompatDelegateImpl.createSubDecor` still throws "need a Theme.AppCompat theme" (it checks the current theme for
`R.styleable.AppCompatTheme_windowActionBar`). termux-api runs on stock Android, so `0x7f120252` is a real AppCompat theme
in the app's resources → on route-A the theme does **not expose its AppCompat parent/attributes at runtime**: either its
parent chain (inheriting `Theme.AppCompat.*`) is not resolved, or the theme AppCompat actually reads is the **application**
theme `0x1030237` (DeviceDefault, non-AppCompat) rather than the activity theme. **Ours** — resource/theme resolution or
theme-context application for the aliased activity.
- **Minimal fix (U15, activity/theme bridge in the runtime JAR):** ensure the context AppCompatDelegate reads carries the
  **target activity's** declared theme `0x7f120252` **with its parent chain** — i.e. the `[B8-ALIASTHEME]` path must
  *apply* the target theme to the activity's context (`Context.setTheme` / the ActivityInfo theme used at `attach`), not
  only re-resolve+log it, and the resource resolver must resolve the theme's AppCompat parent. **To confirm the exact leg**
  (parent-chain unresolved vs application-theme-read), a cheap check: dump the app's `0x7f120252` theme parent from its
  `resources.arsc` (does it inherit `Theme.AppCompat*`?) and verify at runtime whether `obtainStyledAttributes(AppCompatTheme)`
  sees `windowActionBar`. Prediction: with the activity's AppCompat theme correctly applied/resolved, `createSubDecor`
  passes → fd-api moves past this wall (next wall unknown; the bg `LocalSocketImpl.bindLocal` ULE is non-fatal — termux-api
  talks to termux over a local socket, degraded but not fatal).

## This round's rule
Classify an unowned white/dead key by *whose* contract the fatal violates: glmark2's `GetLongField` is the **app's own**
native on its own object (our side at most makes ART stricter); chessclock's `InvalidDisplayException` is **ours**
(a window-session bridge connect failure dressed up by AOSP as "display not found") plus a **JAR/RegHook** method-decl
skew; fd-api's AppCompat-theme error is **ours** (we pick the right theme id but do not resolve/apply its AppCompat parent).
A small, well-scoped fix exists for the two *ours* that are JAR-level (chessclock's native-method decl; fd-api's theme
application); the terminal window-session (chessclock) and the app-native abort (glmark2) are not single-key small fixes.

## Files
- `evidence/three-singles.txt` — per-key first-fatal + earliest wall + mechanism, with hilog line refs and the manifest
  theme trail.
- `results.json`, `documentation.json`, `landing-paths.txt`.

## Boundaries
Offline; no board; no push. Static from the U13 hilogs + the app manifests (apkanalyzer). glmark2's (a)-vs-(b) and
fd-api's exact theme leg need the noted cheap checks/experiment to finalize. Sources read read-only: the U13 hilogs
(`westlake-harness-u7-executor/.../window1,window2-61b`), the app apks (`westlake-inputs/apks`), the adapter source
(`westlake-harness/bms`).
