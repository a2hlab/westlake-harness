# 61b: ordinary Toutiao reentry retained after two software boots

The old early-frame verdict was insufficient: a single capture roughly two seconds after a handled click could still show the preceding feed while a new Activity/window was transitioning. This delivery keeps the native candidate unchanged and requires real changed content from fresh images after one touch, within the existing 60-second observation budget. Earlier unknown frames and failed runs remain unchanged.

**Accepted outcome:** `retained_reentry_validated_av_pending`, signed by `Codex-outer`. Candidate `3291f76db0945f90b402ea61b14c3a912efbeecec9e0422af1a92fec95b8a819` remains on serial `61b0657200000000000000000324012c`. Both software boots used the same published device/inode `66352/590080`. Native sources were not changed during the observation-tool repairs. Read-only queries in the same final boot identify OpenHarmony 6.1.0.31, Linux 5.15.180 aarch64; see `system-version.json`.

| Case | Boot 1: 3755c27b | Boot 2: f10b52cf |
|---|---|---|
| Desktop first open | Feed at s60 sample; actual swipe changes content | Feed at s60; actual swipe changes content |
| Home and same-host desktop reentry | Feed at s5; actual swipe changes content | Feed at s5; actual swipe changes content |
| Remove own Recent card, then desktop reentry | New host 10044, old child 6882; article opens after one click | New host 9878, old child 6845; article opens after one click |
| Final image and release | Actual article, closeout_ok; power restored; released; 332.331 s | Actual article, closeout_ok; power restored; released; 299.404 s |

Both article clicks first produced an unknown early frame and then a new frame with actual article text and an image. No touch was repeated. The two trials use different articles and are not a controlled same-content latency comparison. s60/s5 are observation samples, not guaranteed response times. The final screen is an article detail page.

The original result field `status=running` is preserved; runtime_result, raw unlock/held receipts, restored power and signed actual images establish the completed windows. `final-signoff.json` records that distinction, both boot IDs, the actual candidate object and exact b0e baseline hard-link rollback basis. The baseline was not restored after the successful second boot.

## Sources, build and reproduction

Native source snapshot: `benchmark/2026-10-24-native-host-window-recovery/session-recovery/candidate/` plus `record-reader/`, source commit `46162f45dd`, build commit `97d955b8f9`. The recipe and original build receipt are in `candidate-build-02/`; `compile_candidate.py` and `build-delta.json` describe five recompiled translation units plus 103 reused existing objects. This is not a full clean-source build of the entire bridge. The API observation row added with this delivery links each source/build file and SHA.

The executed observation entry is `demo-seal/reentry/execute_retain.py` (SHA `be8336df180ee124d921a11d3a3f66cf5943c06dd303d2cf798a37cc85ad6e4d`). `executed-steps.json` preserves the exact plan. Original per-phase outer receipts are copied under `boot1/` and `boot2/`. Do not blindly rerun historical plans against the now-retained candidate; a new maintenance window needs fresh identity/object admission and a new receipt. The executable deployment/recovery logic, offline tests and historical validation tools are all in the mainline repository.

Run from the repository root:

```sh
python3 benchmark/2026-10-25-61b-demo-handoff-draft/check_delivery.py --manifest benchmark/2026-10-25-61b-reentry-delivery/manifest.json
```

This checks pinned files and the handoff chain; it does not replace actual image review. All copied JPEGs are original, with original SHA-bound image/layout/review records. Full raw runs, command receipts, stderr and baseline copies are durably archived outside worktrees under `$HOME/.local/share/westlake/t141-retention-evidence-20261025/`, with inventory hashes in the signoff.

## Limits kept explicit

Only this app's opening/reentry/content interaction is accepted. Random application exit was observed in an earlier first-open trial and remains unresolved; no anti-virtualization cause is asserted. Speaker/audio-video acceptance, full T4 sealing and physical removal/restoration of power remain pending. No all-APK success or new multi-app frozen API is claimed. See `OPERATIONS.zh-CN.md` for the short demonstration instructions.
