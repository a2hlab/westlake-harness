# v2 backtest on 5ea: v3c + authorized installer + r17j

The forecast overestimated app-domain dependency repairs: **2/27 progress predictions were confirmed, 16 failed their named checkpoint, and 9 remain unknown**. Merely installing the expected SONAMEs did not make them visible to each app. [Per-key results](backtest.csv), [machine-readable score](results.json), [review decisions](reviewed.tsv), [quoted evidence with original paths/line numbers](adjudication-evidence.json).

## Identities and execution changes

The unchanged forecast CSV is `be1879a15267f3c208236fce946644ea0580319b9cf8c9395218091182058bed`, frozen at **03:22:58.395659 CST**. All 63 clicked keys were launched later, from **03:29:23.052383 to 04:25:44.753140 CST**. The user authorized 5ea after the original profile named 5cd/61b; [execution amendment](../../execution-amendment-5ea.json) changes no prediction or component identity.

Both runs match all **87 sampled runtime paths** of package `668e4f7c` plus JAR `20dcb71b`. The first `RUNTIME` line in each facts file matches the hash of its readback. The first fingerprint is `b094154c95f5` (115 rows); the continuation is `3829b2d68cbb` (117 rows). Their only differences are the newly included installer rows, `libbms=6aadb8b4` and `libapk_installer=7048c7c5`. The **03:34:55** independent readback also matches in shell and foundation PID **979** roots, on the same boot `51812b02-ec64-4d36-821c-ffd94531fb45`. [Run identity evidence](run-identity/).

This is a run-start component snapshot plus the outer `active_verified` package attestation, **not a rehash of all package files or continuous per-process maps proof**. The audit lists 183 unsampled projected package paths. Per-key eligibility additionally checks record APK, boot, actual launcher, installed grant, sidecar verification and post-freeze click time.

The first run stopped after FileManager cleanup at **27/66**. The outer resumed 40 keys with cold-stop fix `e98d00c9`. This is an execution change: **the combined result is not an unchanged-batch-protocol experiment**, since v2 explicitly excluded additional batch behavioral patches. Original-batch and continuation results are separated below. [Continuation policy](../../continuation-policy.json).

We retain each key's first terminal record, including FileManager's original two captures. Its later repeat is excluded, without choosing a better result. Run `-b` has no terminal summary/capture and contributes nothing. HW/ZZ controls are outside the frozen 66-key corpus.

## Score and coverage

| Protocol stratum | Eligible | Exact scored | Exact hits | Minimum promise scored | Minimum hits |
| --- | ---: | ---: | ---: | ---: | ---: |
| Original batch | 27 | 17 | **12/17 (70.6%)** | 19 | **12/19 (63.2%)** |
| Cold-stop continuation, excluding repeated FileManager | 36 | 28 | **18/28 (64.3%)** | 30 | **18/30 (60.0%)** |
| Execution-amended combined sweep | 63 | 45 | **30/45 (66.7%)** | 49 | **30/49 (61.2%)** |

Among 63 eligible keys, **47 have a known four-class outcome**, including two frozen abstentions (Thunderbird/K9 database-update pages); 16 outcomes remain unknown. Exact scored coverage is **45/63 (71.4%)**, not 100%. The minimum-promise metric additionally judges the two lost lit predictions and two different unresolved native dependencies; it does not silently replace the exact metric.

On the same 45 exactly scored rows, a descriptive “always unchanged” comparator would get **32/45 (71.1%)**, above this forecast's 66.7%. This comparator was not preregistered; it illustrates how the large unchanged class and overoptimistic progress predictions limit the aggregate rate.

| Prior exposure stratum | Exact | Minimum promise |
| --- | ---: | ---: |
| Earlier sweep only | 24/36 (66.7%) | 24/40 (60.0%) |
| Earlier background-grant calibration | 3/5 (60.0%) | 3/5 (60.0%) |
| Earlier v3c targeted run | 2/3 (66.7%) | 2/3 (66.7%) |
| Earlier r17j targeted run | 1/1 | 1/1 |

These are profile-specific prospective predictions with disclosed historical exposure, not an unseen-app study. Seal/Toutiao match their predicted host validation failures, but have no click/capture and are excluded from post-click accuracy. Subway was rejected for changed APK identity. All three remain in the 66-row diagnostic table.

## What missed, and what advanced

- **Lit retention: 10/12.** AppManager is blank despite StartAbility=0 and a nonzero frame; Droidify dies on `OpenSSLProvider` class initialization. Conversely OONI shows its own introduction page despite JNA background errors, disproving its predicted first-page block. See original-run hilog: AppManager **41566, 45607**, Droidify **38980, 39079**, OONI **61681** plus its captures.
- **Native dependency predictions failed.** Anki/McDonalds still cannot resolve `liblog`; Unciv cannot resolve `libstdc++`; OrganicMaps/PPSSPP/Immich/Saber cannot resolve `libGLESv2`; Mindustry cannot resolve `libOpenSLES`. FluffyChat/Aves report a different dependency but still fail the complete library-load checkpoint. A changed first linker error is not success. See the individual rows and cited original log lines.
- **Two confirmed advances:** Shattered Pixel Dungeon reaches `EGLImpl.<init>` then fails `GLImpl._nativeClassInit` (continuation hilog **24372–24377**). [Frozen-package DEX](EGLImpl-dex.txt) proves `EGLImpl.<clinit>` unconditionally calls its old native initializer before returning; constructor entry therefore establishes that static checkpoint, not successful instance construction/gameplay. [JAR provenance](EGLImpl-provenance.json). `fd-mobile` reaches a **1200×1920** ViewRoot frame (hilog **58286–58287**) but both captures remain black.
- **Do not convert different errors into progress.** NewPipe/Amaze/Reader/Habits/Element encounter provider class initialization failures; direct proof of their frozen checkpoints is absent. VLC's first PID has the provider failure (**32905, 33020**), while a successor PID fails onboarding theme inflation (**49260**). That later Activity does not establish crypto-provider initialization. These remain unknown where the named checkpoint cannot be adjudicated.
- **TLS installation is not app TLS use.** `fd-noice` logs self-test OK but its actual OkHttp call enters `TlsShimProvider$ShimSocketFactory.createSocket` (**40180–40181**) and fails, then EGL aborts (**40242**). The frozen installer source's self-test only gates the default HTTPS factory; it does not directly prove the app's TrustManagerFactory checkpoint. Both Noice rows remain unknown for that checkpoint.

## Captures and processes

The 66 selected records contain **126 captured=true screenshots**, all 126 files hash-verified. Both scheduled sample stages have **63 measured apps / 3 unknown**, **19 live apps**, and **22 app processes**. Same-UID shell helpers excluded from app-process counts: **2 at t5**, **1 at t20**. These come from the copied [source records and process tables](source-records/), not producer PASS labels or requested shot counts.

There are 128 captures across both raw batches; two belong to the excluded FileManager repeat. Controls are separate. **13 keys have visible own app content in this agent's screenshot review:** OONI, Aegis, Auxio, KeePassDX, Fitness, NetGuard, Thunderbird, FileManager, K9, Minetest, MPV, Notes, STK. The definition includes the frozen loading-page criterion: Thunderbird/K9 show database-update pages, Minetest a loading page, and STK its startup logo. This is not a claim of completed startup, gameplay, network access or full functionality. UI adjudication remains pending outer acceptance.

Contact sheets retain both scheduled captures: [01 t5](review-01-t5.jpg) / [01 t20](review-01.jpg), [02](review-02-t20.jpg), [03](review-03-t20.jpg), [04](review-04-t20.jpg), [05](review-05-t20.jpg), [06](review-06-t20.jpg), [07](review-07-t20.jpg), [08](review-08-t20.jpg), [09](review-09-t20.jpg). Matching `-t5.jpg` files and key manifests accompany sheets 02–09; original capture paths/hashes are in results.json.

## Reproduce and R2

Run `../../finalize_backtest.py` with repeated `--run` arguments for the original and `-c` serial directories, `--installer-readback` pointing at the supplied readback, `--reviewed reviewed.tsv`, and a **fresh** `--out`. It requires all 66 explicit rows and complete continuation evidence. `../../score.py` can independently score `observations.json` using the same two runs/readback. Tests: `python3 -m unittest discover -s benchmark/2026-09-30-v3c-r17j-prospective -p 'test_*.py'`; lifecycle: `agent-spec lifecycle specs/bms-background-start/t3-5ea-backtest.spec.md --code tools/spec-checks --min-score 0.7`.

R2: **verified** local hashes, eligibility gates, record-derived counts and deterministic arithmetic; **agent-reviewed / pending outer acceptance** visual labels and evidence-based checkpoint adjudication; **unknown** unobserved checkpoint successes and end-to-end functionality. No board I/O, locks, runtime modifications or Git commits were performed by this lane. Shared Git metadata is read-only; the outer commits the deliverable.
