# T43: desktop observation invalid, original HAP restored

The original report inferred that the host icon was absent across six desktop pages. **That conclusion was wrong.** All six post-swipe layouts are identical lock-screen layouts containing `ScreenLockRootComponent`. Only page 0 was observed as a valid desktop, with Photos and Settings. Historical T32 page 0 has the same two icons; its host icon was on page 8. Neither global icon absence nor lost package registration is established.

No icon click is present in the recorded commands. No callback observation can be attributed to a click. This is **not a white-screen fix, not a successful host launch, and not task acceptance**.

## Evidence and recovery

The outer reviewer and independent peer verified all 385 source-record hashes. Before/after manifests match for 124 runtime files and 36 boot-image files. Directory device/inode/mode/UID/GID, bundle identity and power values match. The recovered device HAP is b189. Host PID was NONE at sampled checkpoints; this does not prove continuous process absence.

Shared board records show the exclusive window from 12:43:08 to 12:51:02. Original lock-command receipts are absent. Of 81 recorded command argv files, only 24 have paired start/end records. No screenshots were taken. These limitations prevent claims of complete execution provenance or visual acceptance.

## Contract deviations retained

- Discovery commands emitted `invalid arg: PowerMgrService` and `settings: inaccessible or not found`, but execution continued despite the card's stop rule.
- Six horizontal swipes followed unresolved icon identification without a prior scope amendment.
- Lock-screen samples were counted as desktop-page coverage.

The failed run is retained; no missing historical evidence was reconstructed. Recovery facts do not erase the deviations.

## Files and provenance

- `results.json` is the authoritative outer review, including raw hashes and limitations.
- `author-report-unaccepted.json` preserves the original report verbatim **for audit only**. Its global-icon-absence, complete-evidence and never-ran claims are superseded above.
- `evidence/` contains small before/after manifests and identity records. The two observed tile names apply only to the sampled valid page.
- Original private layouts and command records remain under `$HOME/.local/share/westlake/t43-outer-20261022/private-raw`. They may contain nearby network names and are not published.
- The author's checker and Rust selector are preserved with hashes in the private author intake, not promoted: they validate the author's assertions and do not establish valid desktop-page coverage.

T44 first establishes the current desktop and exact target on b189 before installing the observer. It checks lock-screen state at each UI step, restores temporary power settings, compares fresh callback records, and records per-command times. See `specs/toutiao-video-playback/t44-verified-desktop-observation.spec.md`.
