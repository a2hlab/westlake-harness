# WebView first-screen impact: seven keys, provider-only repair

The earlier whole-DEX WebView reference list did not answer **when** WebView is
required. Calling an app a local expense/counter app hides its startup changelog
WebView; calling a Fragment a later page hides a first-page NavHost/ViewPager.
The new scanner combines subclass-aware DEX calls, layout XML, inherited lifecycle
paths and **target-PID terminal-first** diagnostic calibration. No unanchored
callback is silently classified as post-first-screen.

## Frozen evidence and limits

- **7 exact APKs, 8 DEX members, 769 WebView/WebSettings/subclass calls**. All SHA
  and manifest package identities pass. 7 require WebView during startup;
  **0 are later-page-only**. Later help/fullscreen/tab references coexist with
  startup requirements and remain in the per-key machine-readable table.
- `facts.json.gz.b64`: every exact callsite, DEX hash/member/offset/dump line,
  relevant whole-method instructions, XML WebView resources and bounded lifecycle
  paths. A resource literal is not a general argument-flow proof. DEX resource
  constants can print as `#float ... // #7f...`, not `0x7f...`; both are recognized.
- `provider-evidence.json`: actual **U8 J9** runtime JAR
  `87fd463ddb82e803480a93bd76fc55d4bbb92a2261caa75c6a23cfd0f812c8be`,
  candidate manifest-bound, with compiled B7BindFixes injection, cache seeding and
  ZeroHandler. Do not substitute the older J8 JAR `6895b9e4...`.
- Before framework bytecode inspection, artifact_identity returned **0/DEPLOYED**
  for unchanged framework.jar `3e106350d882...` against U7 expected-run.
  Framework WebView.getSettings directly delegates to WebViewProvider.getSettings.
  Native construction gets an interface proxy, but **WebSettings is a class**:
  ZeroHandler's source lines 72–85 return null for non-interface objects. Compiled
  `isInterface` and zero-object returns are also retained. This does not implement
  WebSettings or a renderer.
  `class-kinds.json` independently confirms DEX access flags: WebSettings
  **0x0401 PUBLIC ABSTRACT**, provider types **0x0601 PUBLIC INTERFACE ABSTRACT**.
  It is supplementary type evidence, not a change to the frozen forecast.
- Source attribution is pinned to master `9c77495c3` and its WebViewProviderFix.java
  SHA; code and bytecode remain different evidence types. The fix may fail to seed,
  or a real provider may already exist; all predictions assume successful seeding
  **and no real Chromium provider**.
- Old **U7** diagnostic runs are seven PID-bound calibrations, not U8 observations
  or replacements for the earlier cv2 signed t20. Six have a terminating
  getProvider exception. YAM's terminating root is **Capacitor bridge null in
  onStart**, not getProvider. A preceding initializer failure is not reconstructed
  without its own log evidence.

## Predictions (conditional, not guaranteed unlocks)

| Key suffix | Startup demand | Provider-only first-screen forecast | Candidate next wall |
|---|---|---|---|
| trickytripper | TrickyTripperActivity.onCreate → changelog helper constructs WebView | Native changelog dialog chrome can appear; **lit-webview-fallback**, not functional HTML | loadDataWithBaseURL no-ops; changelog/help HTML stays blank |
| beecount | WelcomeActivity.onCreate → ChangeLog.getDialog constructs WebView | Native changelog dialog chrome can appear; **lit-webview-fallback** | Blank HTML; later app screens still unproven |
| jiten-webview | activity_main XML + MainActivity.setupWebView | **blocked**, predicted dead | Null settings → setJavaScriptEnabled |
| caniwebview | MainActivity NavHost inflates first WebViewFragment; fullscreen Activity is additional | **blocked**, predicted dead | onViewCreated/onResume Kotlin settings-null check/dereference |
| privacybrowser | MainWebViewActivity.onCreate calls enableSlowWholeDocumentDraw before a WebView user-agent probe | **blocked**, predicted dead | getSettings().getUserAgentString null in onCreate |
| jslab | First ViewPager2 PlaceholderFragment inflates fragment_main | **blocked**, predicted dead | getSettings().setJavaScriptEnabled in onCreateView |
| yam | MainActivity/Capacitor bridge requires WebView/JavaScript during startup | **blocked or unresolved**, predicted dead | Existing bridge-null onStart; settings-null is another candidate if bridge setup is reached |

**2 native-chrome fallback candidates, 4 settings-null candidates, 1 bridge-null
or unresolved case; 0 predicted functional WebView first screens.** Clearing six
observed provider exceptions is not six expected lights. Exact paths, branches,
Activity/page context and callback unknowns are in results.json; CSV keeps seven
discrete forecasts plus checkpoint, next-wall and screenshot criteria.

Concrete evidence examples (line scope: original whole-DEX dump):

- Tricky helper `Lb/a/a/a/c/a;->a(Z)AlertDialog`: WebView constructor line 235517,
  loadDataWithBaseURL 235528, then native AlertDialog.Builder title/buttons/view.
  Help DialogFragment also uses loadUrl; it does not erase the startup helper.
- BeeCount ChangeLog.getDialog: constructor 127033, loadDataWithBaseURL 127042,
  native dialog Builder 127048 onward; no getSettings in this helper.
- Jiten setupWebView: getSettings 1010379, setJavaScriptEnabled 1010382.
- Privacy Browser MainWebViewActivity.onCreate: getSettings 367771,
  getUserAgentString 367773 (same returned register); static API exception is
  the old first fatal, not proof that later settings become valid after repair.
- JS Lab PlaceholderFragment.onCreateView: getSettings 1428424. MainActivity
  creates SectionsPagerAdapter and sets ViewPager2 adapter in onCreate; old
  terminal frames confirm the first Fragment inflation failed, closing the
  static callback gap without declaring all other callbacks startup calls.
- CanI uses XML/Fragment binding; old terminal frames name activity_main and
  fragment_webview during MainActivity startup. Frame-based calibration, not a
  guessed exact static Fragment-dispatch edge, supplies the startup linkage.
- YAM diagnostic root is hilog line 37629 → MainActivity.onStart:37630; the
  null object is `com.getcapacitor.j`, not WebSettings. Static bridge.K contains
  getSettings 376540 / setJavaScriptEnabled 376543, but no prior getProvider
  fatal is attributed to this key.

## Freeze chronology and scoring

CSV SHA256 **94d701664e337bd6f4c1544704927a60a331d0b6a4dcffae3fbfce1f7e08e66b**.
Registered `PROGRESS(97 freeze)` at **2026-10-01T11:34:35+08:00**.
**Late relative to U8 rollout LOCK/apply dispatch (11:29:25)**; do not present
this as strictly before deployment. No U8 target observation was read or used;
no full-sweep-start entry had appeared in the board excerpt at registration.
Freeze chronology remains disclosed even if the seven apps are first launched
after registration. FREEZE.json is the authority; do not edit CSV after results.

Score provider checkpoint, terminal-first root, visible native chrome, HTML
content and signed t20 independently. A blank embedded WebView with app-owned
dialog controls is fallback, not functional-lit. Use first_fatal.py and outer
signed screenshots; alive/PASS does not prove a first screen. A never-reached
settings call stays unknown, not a hit.

ActionBar scoring remains **pending** complete U8 results plus outer signoff:
use the original B10 CSV `c115d17c...`, 21 startup/first-content and 28 later-only
(22 previously lit). A lit t20 does not disprove a later-only risk without
exercising that page. This task does not fabricate a U8 score.

## Replay and handoff

```sh
python3 benchmark/2026-10-01-webview-startup-prediction/scan_webview.py --output /tmp/webview-facts.json
python3 benchmark/2026-10-01-webview-startup-prediction/audit_provider.py --output /tmp/webview-provider.json
python3 benchmark/2026-10-01-webview-startup-prediction/predict.py --output /tmp/webview-predictions
python3 benchmark/2026-10-01-webview-startup-prediction/test_webview.py
```

Collectors use WORKSPACES/HOME/script-relative paths. New evidence requires a
new version; do not overwrite frozen inputs. See validation.json for actual
gate exits and landing-paths.txt for outer handoff. documentation.json contains
only the exact shared README/DIGEST additions. No device writes or push.

### Software validation

Six Python tests and three contract scenarios pass (lint quality 1.0).
Fixed master `4d2a4d5dfa1b4165d2b949f3000f9385405d81fa` plus only this handoff
passes **spec_checks exit 0**: raw cargo 101, **149 passed / 9 failed**, all nine
approved, zero unexpected. User-path gate **exit 0**: 12200 files, 25 exceptions,
zero violations. Isolated-master known answers: **82 tests, 3 skipped, 0 failed**;
own known answers: 69 tests, 2 skipped, 0 failed. Frozen B10 and corpus-v2 v1 CSV
bytes are unchanged. Git add exits 128 on shared index.lock; outer commits the
17 listed paths plus exact documentation lines, excluding old staged U7 files.
