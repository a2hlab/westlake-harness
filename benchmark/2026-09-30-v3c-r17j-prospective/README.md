# v2 prospective forecast: v3c + authorized installer + r17j

The previous permission-only forecast overpredicted visible pages: dispatch advanced in 4/5 calibrated apps, but only 1/5 showed the predicted UI. **This version does not promote a removed dependency/permission wall directly to a page prediction.** It preserves known successor walls and treats app-domain visibility separately from libraries existing on disk.

**66 keys: 12 expected lit, 27 expected to advance, 23 expected unchanged-blocked, 4 unknown.** [CSV](freezes/v2/predictions.csv), [JSON](freezes/v2/predictions.json), [frozen policy](freezes/v2/policy.json), [receipt](freezes/v2/freeze.json).

Frozen **2026-09-30 03:22:58.395659 +08:00** and announced on board item 91 before reading any upcoming full-sweep outcomes:

```text
be1879a15267f3c208236fce946644ea0580319b9cf8c9395218091182058bed  predictions.csv
```

The start time of the upcoming sweep was not supplied. Only launches **after this freeze** qualify for prospective scoring; do not claim every eventual run necessarily qualifies. v0/v1 were not modified.

## Exact profile and scope

| Component | SHA-256 / requirement |
| --- | --- |
| v3c package manifest | `668e4f7c74bfe635c57ca7133e1373acb0c675959d5953a20708e70293d27107` |
| r17j JAR | `20dcb71bf9a91b21b660174ad3730f4fa62fbb59ed9f662d7be7808611b3591f` |
| libbms | `6aadb8b4ca9ad7d1dbaf6d99ca70f4603e3e7a2ec152fb60aee49137751afbf9` |
| libapk_installer | `7048c7c50a828fc744b5f06e4e9ec50ac317a2272f33789249fc63e43a655a18` |
| Installer behavior | Reinstall/grant actually effective; SelectLauncher active |
| Batch behavior | Existing native-sidecar assembly enabled; no undeclared new validation exceptions |
| Boards | 5cd first, 61b separately; never select each key's best board result |

[Profile](freezes/v2/profile.json) pins full identities. All 27 Java source files were read from `d50325c6` and checked against the r17j build receipt; the actual Mac JAR hash also matches. [Build receipt](freezes/v2/evidence/build-result-r17j.json). Native file hashes and ELF exports are preserved under [native inputs](freezes/v2/evidence/native-inputs.json). Export presence is static evidence, not proof of a live app's link graph or JNI binding.

No pending MediaStore, CameraX, EGL/HWUI or AudioSystem repairs are silently added. In particular, r17j attempts to load HTML compatibility at [B7BindFixes.java:166](freezes/v2/evidence/B7BindFixes.java), but v3c excludes that library. A declaration does not make the feature active. Package activation alone does not prove the JAR overlay, installer or each app's grant.

## Forecast meanings

| Label | Meaning |
| --- | --- |
| `亮` | Expect own UI, including previously accepted UI surviving a regression test; screenshot required |
| `推进` | Expect the **named** prior wall/checkpoint to be crossed; destination page may still fail |
| `不变` | Expect the named unresolved wall to remain blocking; not a generic prediction that any current behavior stays the same |
| `unknown` | Abstain because identity, current blocking stage or profile-specific evidence is insufficient |

Expected lit: `aegis`, `fd-AppManager`, `fd-auxio`, `fd-com-kunzisoft-keepass-libre`, `fd-droidify`, `fd-fitness`, `fd-netguard`, `fd-mpv`, `fd-notes`, `fd-stk`, `fd-minetest`, `fd-filemanager`. These are regression/transfer predictions from **earlier** UI acceptance, not 12 new successes. Auxio/NetGuard's latest native proof uses different JARs; FileManager comes from the earlier authorized-installer run. Minetest's prior acceptance was its own loading page, not complete gameplay.

The four unknowns are `fd-android`, `fd-k9`, `fd-feeder`, and `subwaysurfers`. Thunderbird/K9 already returned StartAbility=0 in the prior run; assigning new authorization benefit from that alone would repeat the v0 error. Subway's bytes do not match the pinned APK identity.

Examples deliberately left blocked:

- Wikipedia: earlier **single-app r17j** evidence still has EGL_NO_SURFACE → hwui abort after TLS succeeds. This is disclosed prior exposure, not the new sweep.
- Gallery/BinaryEye: the v0 follow-up found a missing MediaStore field and a CameraX resume failure after successful dispatch. Neither is repaired by the pinned source changes.
- OONI: the latest v3c handoff still reports JNA `__errno` relocation failure. Candidate libc exports alone cannot overrule that app-domain observation.
- BurgerKing: selected libc does **not** export `__register_atfork`.
- Seal/Toutiao: the prior batch fails before installation on `libaria2c.zip.so` / `libcvt.so` validation. Installer changes do not bypass that earlier host-side gate.
- LibreTube/Tutanota/Uhabits: respectively tagsoup/HTML, real WebView and asset-file-descriptor behavior need changes outside this package.

Dependency-driven progress predictions are intentionally weaker. Supplying liblog/GLES/stdC++/OpenSLES can remove a named native-load wall, but per-app domain resolution and successor application state may still fail. Anki/McDonalds/Flutter-family rows explicitly retain this uncertainty. A successful load is the scored checkpoint, not the mere absence of the old error text.

## Evidence and exposure

Each row cites a pinned per-key [prior record/log extract](freezes/v2/evidence/prior/), including full raw input hashes, target PID attribution and original hilog line numbers. Main-thread throws are separated from tolerated exceptions; no UI outcome is inferred from these logs. Rows also reference earlier signed UI/backtest tables where used. The CSV's short `prior_log_lines` is a review entry point; complete snippets retain both early errors and later fatal successors.

Inputs read before freeze were the old r16 adjudication, historical r17c sweep, v0 background-launch backtest, and named pre-sweep v3c/r17j targeted handoffs. `prior_exposure` distinguishes prior-sweep-only, prior-grant-calibration, prior-v3c-targeted and prior-r17j-targeted. This is **not** a claim that the app corpus was unseen. It is a prediction of the specified next profile before its full-sweep results.

Useful pinned source anchors: [B7BindFixes.java:145](freezes/v2/evidence/B7BindFixes.java) creates the runtime namespace before gapfill/TLS loads; lines 200–223 add OpenSSL search/permitted paths; [WindowSessionProxy.java:98](freezes/v2/evidence/WindowSessionProxy.java) limits reversePush to degenerate frames; [SystemServiceFetcherStubs.java:23](freezes/v2/evidence/SystemServiceFetcherStubs.java) supplies typed alarm/media-session managers. These changes do not prove all app ClassLoaders see the same libraries.

## Later backtest

Copy [observation-template.json](observation-template.json), which contains 132 board/key slots with unknown outcomes. Fill only observed slots. For each, record exact APK, package/JAR/installer hashes, live-profile evidence, effective grant, actual launcher selection, timezone-qualified click time and the relevant screenshots/logs. Runtime fingerprint evidence must establish the **actual overlay**, not merely the manifest file on Mac. A changed native/JAR/batch behavioral profile requires a new forecast; do not retrofit v2.

```sh
python3 benchmark/2026-09-30-v3c-r17j-prospective/test_forecast.py
python3 benchmark/2026-09-30-v3c-r17j-prospective/score.py \
  --freeze benchmark/2026-09-30-v3c-r17j-prospective/freezes/v2 \
  --observations /path/to/adjudicated-observations.json \
  --out /path/to/new-backtest.json
```

`lit` requires screenshot evidence. `advance` requires evidence crossing the row's exact `progress_checkpoint`. An unchanged outcome requires no UI, no advance and positive evidence of the **same** named wall. Missing evidence stays unknown. The scorer checks immutable hashes, rejects duplicate board/key observations and output overwrite, excludes identity/profile/timing failures, and reports board/exposure strata. Exact four-label accuracy counts “predicted advance, actually lit” as a label mismatch; **minimum-promised-outcome accuracy** separately counts that as exceeding the promise. Coverage and abstentions are always reported, so those two rates cannot be silently substituted.

Current hit rate is **pending**. No new board operations, screenshot captures or process measurements were performed; those counts are **unknown** for the upcoming sweep. [results.json](results.json) and [lifecycle.json](lifecycle.json) cover offline validation only. Shared Git metadata is read-only; outer submits the report.
