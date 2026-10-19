# Bounded logging coverage review

Token: `video-1919-observability`. Static only; no new deployment gate or runtime change.

**Native true does not establish Java log coverage.** The pinned native JNI_OnLoad reads `debug.ttplayer.log.enable` and changes its native logging state (default false in the existing REA excerpt). New raw evidence ev_737cfd1d6d1b8bf0623385e01143462acf2241527b8415d2256b72255cf232e6 shows `X.C4cC.play()` separately checking `TTVideoEngineLog.isPredicateLoglevelTurnOn(2)` before its info log. A hotfix early return precedes that check. The released branch calls `TTVideoEngineLog.e`, but the logger's own filtering is not yet in the available method evidence. This proves another Java predicate exists, not that its implementation can never read the native property.

Java predicate/default state, possible initialization overrides, TTVideoEngineLog e/i sink, and MetaVideoPlayerLog.info sink remain **unknown**. No existing cached inspection of either logger implementation was found in the named CC session. Therefore the earlier wording “Java verbose was off” is not established merely by missing text. The two exact method requests are in REQUEST-CC.md; do not repeat the c0/h1 production investigation.

## Existing path coverage

| Evidence | What a positive observation establishes | Missing text does not establish |
|---|---|---|
| Native `log enabled by prop` / native diagnostic output | Native library reached its property-controlled logging branch, when bound to the same child/load | Java logger enabled, prepare reached, audio/video success |
| C4cC `play:` info | This Java branch was reached and the independent predicate/logger emitted | play was not called (predicate/hotfix/sink/filter can suppress) |
| Meta `the play entity is…` + playUrl/host/playType | Java prepare context before the later preDecode/prepareOnly/direct-play branch | Actual final network/MDL input or a completed player prepare |
| `_proxyUrl` `start mdl first`, `dataloader is not running`, `local host error` | Specific helper failure branch if correlated to the playing engine and same input | No failure: mState/invalid-params null returns can have no local log; logger e may filter |
| `_proxyUrl:` output / `url not transcode, not use native mdl` | Helper output/decision in that invocation | Exact player consumption or direct network success |

The `_proxyUrl` source returns null without logging at lines20–26. Other branches call e and return null (36–39,58–68). The actual playback caller's null handling remains unresolved. A helper failure may be handled by its caller; neither a null nor a log alone establishes a playback stall. The five/six-parameter xref mismatch from the prior review still precludes excluding that chain.

## Android log routing: source versus actual provider

MAIN has `shared-native-production/related-source/framework/android-runtime/src/android_util_Log.cpp`: lines79–112 route Java println_native straight to HiLogPrint (CORE, domain0xD000F00, original tag/priority), not to child stderr. Lines65–75 isLoggable uses liblog with INFO default; this is not a proven TTVideoEngineLog default. The sibling `framework/core/jni/android_log_hilog_bridge.cpp` installs a liblog logger constructor and routes accepted native logs through HiLogPrint; upstream priority filtering precedes that callback. These are real delivered source files, **explicitly marked RELATED_ONLY_UNPROVEN by source-index.json**, so they are not proof of the current RouteB JNI registration/provider or its enabled thresholds. Do not silently promote source comments to actual deployment identity.

The r4 child stderr contains a caught Settings screen_brightness exception and Java play/prepare stack, not the Meta info message itself. Java exception/stack output reaching stderr does not establish android.util.Log's sink. Collect both existing child stderr and bounded same-PID hilog rather than searching only stderr. A missing log can mean unexecuted path, Java filter, sink/priority filtering, collection timing, or loss; this review selects no root cause among those.

## Minimum next observation (no new gate)

1. In the already authorized window bind boot, parent/child birth, engine/content attempt, actual tap time, and the existing screenshot sequence. Capture same-child stderr plus hilog from before tap through the bounded interval, preserving raw rc and timestamps.
2. Prefer one **actual final player data-source choice**: scheme/type (direct http(s), local proxy, mdl, file) plus redacted/hash identity and engine association; retain its corresponding prepare/ready/error callback. The Meta prepare-context URL is only an upstream candidate. Do not publish tokens/query strings or infer decoder start from a URL alone.
3. Positive helper-output/null-return evidence can distinguish branches only after CC closes the actual production caller and its fallback handling. If absent, record unknown; do not rerun a window solely expecting the native property to reveal Java logs. Native property true, READY, maps and a static cover remain insufficient for playback.

No code/build/device/REA invocation or private log modification was performed. Public material contains metadata and minimal method facts, not full decompiler bodies or commercial logs.
