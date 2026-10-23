# Scoped Toutiao demonstration handoff — 2026-10-23

The earlier mistake would be to equate a retained READY state with a currently visible feed, or to turn one successful launch into a repeatability guarantee. T72 still fails its original stable-use criterion: its 30/120-second screenshots are blank and the new child later exits.

The user explicitly changed the demonstration scope: crashes need not be repaired; an ordinary desktop-icon click after exit reaching the feed is sufficient. Under that scope, **61b has one accepted observation**, independently reviewed by outer and peer. This is a new scoped acceptance, not a rewrite of T72 or a guarantee for future clicks.

## Evidence

- T72: previous child 8088 exited naturally; one ordinary desktop UI click at 13:09:18 started child 10877. Existing guardian capture at 13:10:21 shows the real recommendation feed, approximately 63 seconds later. Host/device clock precision was not independently measured.
- [Actual feed screenshot](../2026-10-23-ordinary-desktop-recovery-check/04-guardian-feed-2-1310.jpeg), SHA256 `699946010bfda20158432039c901ca2acb650ae1101e7781d8d5291d25cd9a26`.
- [Original results](../2026-10-23-ordinary-desktop-recovery-check/results.json) retain the subsequent exit and blank t120 view. Three original card captures plus one received existing guardian capture; this handoff adds zero captures.
- [Independent peer review](peer-review.json) binds exit, click, new child, and visual evidence. Private raw receipts remain in the persistent location recorded in the signoff; hashes and the public screenshot are tracked here.
- [T73 5cd fallback](../2026-10-23-5cd-demo-fallback-check/results.json) stayed white at 30/60/120 seconds and is not accepted as a fallback.

## Delivery rule

Use **61b** for the user's limited demonstration scope. See [Chinese operating instructions](OPERATIONS.zh-CN.md) and [signed scope](final-signoff.json), approved by `outer(codex)`. No runtime changes or new API freeze were made in this handoff. Both board windows ended at desktop, with original power settings restored and locks released.

Historical source/build references remain at [T34 source-build refs](../2026-10-21-t34-demo61b-video/archive-05-preparation/source-build-refs.json); this handoff does not claim a fresh complete runtime rehash or a new build. Historical 115/128 APK results are startup-only, not current full-function or cold-boot acceptance.

Physical power-cycle launch, repeated recovery reliability, article navigation, video playback in this observation, and crash ownership remain unverified. The user's anti-virtualization explanation is not established by these artifacts.
