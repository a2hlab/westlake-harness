# B10 v2 feedback: conditional requirements, not a revised forecast

The old rules missed typed `ActivityResultLauncher.launch(Intent)` and static-field-triggered class initialization. They also mixed API availability, actual entry selection and visual success. This increment retains the old v2 forecast and its **30/45 exact score (66.7%, below the 32/45 always-unchanged baseline)**. It adds two DEX detectors and one runtime-only requirement, with a separate post-hoc calibration. No board operation was performed.

## Run

From the repository root:

```sh
python3 benchmark/2026-09-29-static-wall-prediction/scan_feedback_v2.py
python3 benchmark/2026-09-30-v2-scanner-feedback/profile.py
python3 benchmark/2026-09-30-v2-scanner-feedback/calibrate.py
python3 benchmark/2026-09-29-static-wall-prediction/test_feedback_v2.py
agent-spec lifecycle specs/bms-static-v3/t8-v2-feedback.spec.md --code tools/spec-checks
```

The first command consumes the pinned v2 APK identities and previous same-APK manifest roots, then decodes all base-APK DEX again. APKs and source runs are read-only. The dexdump tool, input paths and hashes are recorded in `provenance.json`. `--keys`/`--out` on the scanner are for isolated development runs; the delivery uses the full cohort. `publish.py` seals the delivery after checks. Preserve this delivery before deliberately rerunning these commands, because the new post-hoc outputs are regenerated; the older prospective directories are never written.

- `matrix.csv`: 66 keys × 3 families, with explicit scope/unknown states.
- `predictions.csv`: new conditional requirement candidates alongside each unchanged v2 forecast. Candidate order is bounded startup reachability, not a proven first-wall order; no new lighting prediction is asserted.
- `calibration.csv`: static witnesses, exact observed target names, installer-selected entry, provider failure/main-fatal distinction, and EGL evidence.
- `evidence/<key>.json.gz`: DEX methods/offsets/lines, exact call paths, candidate destinations, and complete witness method instructions. `evidence/observed/<key>.json`: selected-run, target-PID log lines and source SHA.
- `profile.json` + `evidence/boot-provider-dex.txt`: actual 668e4f7c package and 20dcb71b JAR definition inventory and fallback DEX, separate from app-level references.
- `EGL-EXPERIMENT.md`: native-window lifetime experiment; no static EGL hit is fabricated.

## Known answers and limits

**Secondary Activity.** Aegis `MainActivity.onStart` explicitly constructs `IntroActivity` and calls a typed ActivityResultLauncher; the new rule follows that bridge and verifies the owner hierarchy. Thunderbird/K9 have a conditional `DefaultDatabaseUpgradeInterceptor → UpgradeDatabaseActivity` call. AppManager has explicit Splash paths to KeyStore/Main. FileManager's Splash contains a MainActivity class hint next to the call/finish; its unresolved callback/branch remains a candidate, not a proven Intent target. `finish` order is lexical, not dominance or execution proof. Inherited generic/merged callbacks can overapproximate startup.

The observed Thunderbird/K9 `B5-ALIAS` directly selects `UpgradeDatabaseActivity` (original run line 30356; continuation line 31983). Their accepted upgrade screenshots do not prove a permission-enabled secondary launch. `calibration.csv` separates this installer effect. AppManager's accepted observed StartAbility target is KeyStoreActivity; a static MainActivity path does not by itself prove that target executed in this run.

**Boot provider fallback.** All five requested examples (Droidify/NewPipe/Catima/Amaze/AntennaPod) have DEX ServiceLoader/JAR-verification requirements. `sget/sput` now add conditional declaring-class initialization edges, alongside static calls and construction. This names the r17j runtime profile, not an isolated proof that the JAR alone caused the regression. This is not restricted to bind: Droidify fails through `MainActivity.onCreate → MainDispatcherLoader → ServiceLoader`, and other paths can run in Application initialization or workers. The bounded APK graph records the root; lazy iterator/resource execution is a conditional framework requirement, not a claim that every ServiceLoader call reaches a verified JAR.

The actual pinned `core-oj.jar` defines `Providers.getSunProvider` at dexdump `classes.dex:283996`: it reads `jarVerificationProviders[0]`, calls single-argument `Class.forName` (284000), then tries `sun.security.provider.VerificationProvider` on failure (284007–284008). Its initializer names OpenSSLProvider (283520), and SunProviderHolder calls getSunProvider (307776). Both provider definitions are absent from the supplied boot-JAR union. An app/runtime-JAR copy is not evidence of boot visibility. The union absence is decisive for those inputs; future profiles must be rescanned. Source availability or the older v3a graph is not a substitute for this pinned DEX.

Catima's provider initialization failure appears before its later resume error. A detected family or a caught initialization failure is not automatically the main-thread fatal wall. No-log cases remain unknown; the calibration reports positive-witness recall and alert burden rather than inventing precision/specificity from silence.

**EGL.** Every scanned key remains `runtime-only`, including Noice/Wikipedia. Their v2 failures and the later colorspace/BAD_ALLOC experiment are distinct evidence sets. Same-pointer surface creation is insufficient without native-window generation, create/destroy ownership and frame presentation evidence. A successfully created surface can still leave a blank frame (AppManager).

## Calibration

The final scan covers **65 exact-identity base APKs; 1 input remains unknown**, and emits **198 key-family cells**. The 66-key post-hoc results are:

| Family | Static alerts | Observed positives | Exact/strong witness recall | With weaker candidates | Startup witness recall |
|---|---:|---:|---:|---:|---:|
| Secondary Activity | 33 | 16 accepted target transitions | 12/16 (75.0%) exact destinations | 15/16 (93.8%); hints included | 10/16 (62.5%) matching destination |
| Boot provider fallback | 45 | 13 initialization failures | 12/13 (92.3%) ServiceLoader/JAR requirements | 13/13 (100%); generic resource candidate included | 10/13 (76.9%) |
| EGL same-window lifetime | 0 static claims | 3 v2 EGL_NO_SURFACE keys | runtime-only | runtime-only | runtime-only |

These are app-level recalls (at least one matching destination per observed-positive app), not transition-edge recall. Provider initialization enters the main-fatal chain in 8/13 cases. The five requested provider examples are all startup candidates. There are 18 provider startup-alert apps and 27 secondary-Activity startup-alert apps; `wall-ranking.csv` also keeps full-reference counts separate. The provider rule has 45 strong alerts against 13 observed positive logs: this alert burden must not be hidden behind recall. Precision is unknown because silence is not a negative and a conditional requirement is not a promised fatal wall.

The remaining strong misses are **Tusky** (only `Class.getResourceAsStream` in `org.conscrypt.Conscrypt.<clinit>`, resource/JAR provenance unresolved) and **Anki** (IntentHandler forwards an input Intent; DeckPicker destination/branch unresolved). Tusky's v2 stack at continuation hilog lines 44545–44565 proves the resource-to-verifier chain at runtime, but that outcome does not upgrade its static classification. FileManager/Calendar/Notes count only as destination hints where the Intent target was lost at a branch. See `results.json` and `calibration.csv`. This is training-set/post-hoc coverage learned from v2, with known-answer selection bias, not a second prospective accuracy score. Unknown inputs/observations and unproven causal attribution remain explicit. The accepted frozen v2 score and every preserved forecast/backtest file are rechecked by SHA. No new screenshot or survival count is claimed by this offline task.

R2: **verified** static artifacts/tests/hash preservation; **partially** calibrated family coverage with explicit unknowns; **unverified** new board behavior, grant-only causal effect, or prospective accuracy improvement.
