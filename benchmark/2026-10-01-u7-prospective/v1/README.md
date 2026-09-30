# U7 T7d/J7b/N4-order prospective freeze

## Evidence first: what changed

The historical skeleton planned N6 and an incomplete T7d API set. **That composition is not this candidate.** Outer ACK95 04:57:34 selects **U6 + accepted full-tagsoup T7d**, with **U5 N4-order native unchanged**. N7 failed its control window; N8 is deferred to U8. The new freeze lives in `v1/` so the earlier skeleton and source priors remain reproducible without being mistaken for final predictions.

- **CSV SHA256:** `fa92c5b964fed2976ba66d82fb703672241435a294c8d9286a7c9192ebab9007`.
- **Expected-run SHA256:** `15fb66a5cab24ca9af2cbf4ef1eb801f6e3bddc2b1b4f2d4515e99c17e77b6c3`.
- Registered on the shared board **2026-10-01 05:15:52 +0800**, before the combined U7 sweep. `FREEZE.json` records the UTC freeze time and all source/evidence hashes. No combined U7 result was consumed.
- `PREDICTIONS.{csv,json,md}` contains **66** input-bound rows. Each has independent first-wall, repaired-operation checkpoint and first-t20 criteria, plus original-line prior references.
- t20 forecast: **28 own UI / 32 unlit / 6 unknown**. Unknowns are four explicitly flaky keys plus fd-reader and fd-seal. Outer's expected aggregate 27+3 includes the already-lit fd-notes/fd-uhabits; their single-attempt forecasts stay unknown, hence 28 rather than 30 predicted stable own-UI rows.

## Exact candidate and handoff

`expected-run.json` has **119 runtime + 36 boot files**. Runtime is byte-for-byte U6, including J7b `381110a675fb543b6ad4102c8fc721fcb5673bc0da8644ececd1bab1ca60bec8`; all native libraries remain U5 N4-order. Boot replaces the authorized 27 image files plus `adapter-mainline-stubs.jar` **d8b2406eb89d2947a8cb313a471d4858ff6be86018ece3bb5c2068a11b42ca2c**. The resulting entire 36-file boot inventory equals the accepted T7d/5cd component run, not merely its aggregate prefix.

Physical artifacts, unchanged and read-only from this lane:

- J7b: `WORKSPACES/_u6-stage/oh-adapter-runtime.jar`.
- T7d stubs: `WORKSPACES/_hw248-t7d/adapter-mainline-stubs.jar`.
- T7d images: `WORKSPACES/_hw248-t7d/arm64/` (27 files).
- Actual input root: **VM `$HOME/a2hlab/app-inputs-u6`**, not the unmerged Mac base input root.
- Use **this directory's `apps-u7.json`**: Firefox has 18 external sidecars, burgerking/mcdonalds/subwaysurfers/x have zero, Seal has six and Toutiao 137. The old U6 synthetic embedded-library counts are not deployment counts.

Outer transferred U7 execution from cc-t3 to cc-wiki while this freeze was being finalized. This report does not authorize a new device window: the runner must follow the latest outer board assignment and existing deployment gates, use first scheduled t20, and roll back U5. Generation-package execution is not implemented here.

## Actual inputs, not synthetic sidecars

`inputs.json` records **66/66 successful `resolve_input` receipts** from original master `bms_batch.py` SHA256 `456dfc6f9cb637a82c357823ebe4395c9d9c16dea7b3ebed93c6580efefe6418`. Reads used the mounted VM view with explicit translation of absolute VM per-key symlinks; no input, metadata or quarantine file was changed. The `orb` shell read did not return promptly, so collection did not depend on it or claim a VM CLI execution receipt.

All selected APKs, external native files and metadata were rehashed. Seven changed/merged keys received fresh full-DEX/native scans; 59 reused static facts only after byte/hash revalidation. The corpus has **214 DEX**. Split-key, non-AArch64-sidecar and APK-pin-mismatch findings are separately represented and all empty in this selected input set. Per-key static evidence is in `evidence/inputs/`.

Some merged metadata retains historical top-level `splits`, so batch `split_hint` can be true. We retain that warning rather than editing metadata: the actual directory has one APK, its selected hash matches, and fresh aapt2 badging has no split attribute. This is not permission to treat a multi-APK directory as installed splits.

The quarantined Seal ZIP payloads are still unavailable to its downloader. Passing input validation does not prove complete downloading, extraction or runtime behavior. Toutiao's 32-bit file also remains quarantined. Proposed `kind=payload` support is **not** part of U7; do not restore those inputs until a separate version is frozen.

## Repairs and causal predictions

`repair-catalog.json` lists all seven Android stub methods and the full AOSP tagsoup replacement:

| Repair | APIs / semantics | Target keys |
|---|---|---|
| SSL fallback | SSLSockets.isSupportedSocket=false; setUseSessionTickets no-op | wikipedia, noice, fd-noice |
| Media permission | MediaStore.canManageMedia=false | fd-gallery |
| Media file URI | MediaStore.Files.getContentUri(String) | fd-gallery |
| Saturation stub | ColorMatrix.setSaturation no-op | fd-plus |
| Signal strength | NetworkCapabilities.getSignalStrength=MIN_VALUE | x |
| Network request stub | ConnectivityManager.requestNetwork returns without callback | vlc |
| Full tagsoup | Parser implements XMLReader/ScanHandler/LexicalHandler, real parsing and handler/property APIs; 15 AOSP sources | wikipedia, fd-libretube, fd-reader |

Expected new own-UI targets from the signed component prior are **fd-gallery, fd-libretube, noice**. This is a forecast, not credit for the combined run. fd-reader may move beyond tagsoup but its next wall/UI remains unknown. fd-plus retains the termination-linked MapInfoLayer null prediction; earlier ColorMatrix.set errors remain separate risks. VLC retains its U6 inflation prediction, while its T7d component exit has no adjacent causal block in the strict parser.

Native walls are **not repaired**: Flutter field-ID/private-runtime failures, Realm libz, OpenSL ES and other native requirements remain. Subway's explicit JNI FatalError L58959/L58960 and SIGABRT L58962 in the same PID/TID support the prospective `unity-mediandk-load` wall; this uses a new U7 input identity and does not retroactively score its non-comparable U6 row.

The six changed-sidecar U6 rows remain three-axis unknown in `u6-scoring/SCORING.json`. Their separately retained observations can inform this new prediction without rewriting U6.

## White screens and component timing

Do **not** freeze a Compose-specific root cause: T7d's noice and LibreTube are positive rendering counterexamples. White-screen causality remains unresolved; emitted frames and `alive` do not establish own content.

The captured cc-t3 document's earlier claim that Wikipedia's content was View-based was corrected on the board at **05:14:38** and accepted at **05:15:12**: its t20 foreground was `InitialOnboardingActivity`, with Compose content inside the AppCompat decor. The frozen source snapshot is historical, not a claim that this old inference remains true. This correction does not change any prediction: the independent lit-Compose counterexamples remain valid and the white-screen cause is still not established by logs alone.

In the T7d x component run the bound t20 cutoff is **04:36:53.999**, while main_threw L78898 is **04:36:54.706**, followed by the XLiteActivity NPE chain. The full-log failure is retained separately in `full_log_termination_observation_only`; it is not backdated as the t20 first wall. This is why x's U7 first-wall forecast remains unknown and t20 is unlit. Component runs used **U5 J6**, not U7's J7b, and are always labeled as such.

## Reproduction and validation

```sh
python3 benchmark/2026-10-01-u7-prospective/v1/predict.py --verify
python3 benchmark/2026-10-01-u7-prospective/v1/test_predict.py
```

`collect.py --help` describes read-only input/candidate collection; it refuses collection after a freeze. `collect_priors.py` reproduces the source/causal prior excerpts. `predict.py --freeze-receipt` emits a receipt only before a freeze exists and refuses re-registration. No automatic command overwrites a frozen CSV. A changed candidate/input requires a new version.

`VALIDATION.json` records both isolated-master gates and contract outcomes. `landing-paths.txt` includes the historical skeleton plus the final v1 files; U6 has its own separate landing manifest. Shared root README/DIGEST changes must be extracted by the U7 row/line, never whole-file copied from this lane. Git's shared worktree index lock is permission-blocked; final worktree bytes, not the earlier 12-file staged snapshot, are the delivery.
