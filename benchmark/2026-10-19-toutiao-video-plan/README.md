# Toutiao video contract and source evidence inventory

Historical feed and cover screenshots did not establish dynamic video playback. The 2026-09-28 report named `ReliableSurface` and `SetMetadata -5`, but its counts alone do not bind a player's producer to the failing buffer. This plan requires current object, namespace and time correlation before choosing a repair. It does not revise the historical observation or declare a new root cause.

## Evidence and scope

- 10 source/report entries have exact file hashes in [source-index.json](source-index.json).
- 4 contracts parse; the 3 task contracts score 1.0 at the required 0.7 lint threshold. Non-fatal coverage/metadata warnings remain in the recorded lint reports.
- 3 real Rust test selectors compile and are listed. All 3 intentionally fail when execution receipts are absent; this is a fail-closed check, **not a playback pass**.
- 0 runtime files changed; 0 board operations; 0 pushes.

The current APK/player path, board identity, content availability, sound and current runtime provider are unknown to this planning lane. The outer collects read-only identity and owns any device window. The existing icon-reentry task has priority on 61b.

## Sources worth reusing, with limits

| Evidence | What it establishes | What it does not establish |
|---|---|---|
| [Historical video observation](../2026-09-28-toutiao-video-playback/README.md) | Two identical cover frames 5 seconds apart; 37,265 ReliableSurface messages and 280 SetMetadata failures were reported on 5cd | Current-generation root cause, decoded frames, player-buffer ownership |
| [MediaCodec crash correction](../2026-09-26-toutiao-crash-knowledge/README.md) | Historical d4fae8e5 fail-loud setup and getOwnCodecInfo registration avoided one crash path | A playable video decoder |
| [ReliableSurface source](../../bms/src/adapter/aosp_patches/libs/hwui/renderthread/ReliableSurface.cpp) | HWUI reliability wrapper has no interceptors; underlying windows must be traced | That every video player consumes this wrapper or that its no-op alone causes frozen video |
| [MediaPlayer source](../../sources/api-implementations/shared-native-production/related-source/framework/android-runtime/src/android_media_MediaPlayer.cpp) | Explicit lifecycle/JNI stub; no real decode, pixels or nonzero position | Playback implementation or current provider ownership |
| [AudioTrack source](../../bms/src/adapter/framework/android-runtime/src/android_media_AudioTrack.cpp) | PCM16 stereo ring buffer backed by OH AudioRenderer exists in source | Toutiao uses that path, accepted formats beyond its scope, or audible output on the current board |
| [SurfaceView split](../2026-10-13-runtime-surfaceview-split/README.md) | Prior scoped SurfaceView geometry work and build entry are available | Video-specific producer/consumer and timing correctness |
| [Media NDK evidence](../2026-10-02-u12-mediandk/README.md) | API/ABI coverage with unsupported status semantics and small real containers | Codec/Stagefright or OH video decode |
| [API source delivery](../2026-10-14-api-source-delivery/README.md) | Current v4 source/build correspondence; relevant historical NATIVE-066/067/068, NATIVE-123/134 | Current board media capability; preserve each row's historical grade |

## Execution order

1. [t1 static evidence](../../specs/toutiao-video-playback/t1-static-evidence.spec.md): source/provider investigation and prediction, immediately dispatchable after outer review. If current identity or first blocker is missing, deliver a precise minimal observation request instead of guessing code.
2. [t2 candidate](../../specs/toutiao-video-playback/t2-minimal-repair.spec.md): depends on confirmed t1. Bind exact allowed source files and input hashes before coding; copy only those into an independent candidate directory. The broader implementation tree must not become blanket permission to alter frozen/runtime files.
3. [t3 playback and API delivery](../../specs/toutiao-video-playback/t3-playback-seal.spec.md): depends on t2; validate on an outer-assigned spare board, then join the icon-reentry release on 61b. Two timed playback/pause/resume/exit cycles, real video-content regions and audible corresponding audio are required. Local probe success cannot replace real Toutiao success.

REQ-TTVIDEO is newly scaffolded with proposed governance. The user requested this behavior; the outer reviews the requirement and task card before dispatch. No prior REQ corpus existed in this checkout.

## Evidence checker contract

The Rust selectors `ttvideo_static_receipt`, `ttvideo_build_receipt`, and `ttvideo_playback_receipt` invoke [verify_receipt.py](verify_receipt.py). Set `TTVIDEO_RECEIPT_STATIC`, `TTVIDEO_RECEIPT_BUILD`, or `TTVIDEO_RECEIPT_PLAYBACK` to the matching JSON receipt. No variable/default output means failure, never a skip. The code defines the exact receipt fields. Evidence paths are relative to their receipt, cannot escape that directory, and must match SHA256. Private recordings remain in durable private storage; only redacted permitted evidence is committed.

The checker validates bindings and required fields, not image/audio meaning or causal proof. Every scenario remains `审核: human`; use `agent-spec lifecycle --review-mode strict`. Keep pending review until the outer reviews the actual screenshots, audio and logs. Do not create empty or fabricated receipts to make these gates pass.

```sh
agent-spec parse specs/toutiao-video-playback/t1-static-evidence.spec.md
agent-spec lint specs/toutiao-video-playback/t*.spec.md --min-score 0.7
cargo test --manifest-path tools/spec-checks/Cargo.toml --test toutiao_video_playback -- --list
# Requires actual stage receipt; absent receipts are expected to fail:
cargo test --manifest-path tools/spec-checks/Cargo.toml --test toutiao_video_playback ttvideo_static_receipt
```

See [results.json](results.json), [estimate](ESTIMATE.zh.md), and [dispatch card](DISPATCH.zh.md). Static source facts are an investigation head start, not evidence of a completed bridge repair.
