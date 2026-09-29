# B4 v4 three-board rerun — task 59 (offline preparation)

Earlier one-off probes and mixed/resumed runs cannot serve as a fresh 66-key round. This plan fixes one explicit round identity and gives each key exactly one board. **66 keys = 22 + 22 + 22; zero device commands were executed.** Historical v3 labels balance the shards; they are never copied into v4 outcomes.

Master `57d0dafa` supplies the accepted #57 runner. The initial `git merge master` was denied at ORIG_HEAD.lock by this sandbox; the outer loop subsequently fast-forwarded this worktree to **57d0dafa**, confirmed by HEAD/reflog. Runner, apps.json and history SHA-256 pins are in [b4-rerun-shards.json](b4-rerun-shards.json). This task changes no runner behavior.

## Start conditions and fixed round identity

- Execution starts only after the outer loop accepts the B6 generation on all three boards and assigns their locks. This plan does not claim B6 is ready. Preserve the same accepted runtime/installer generation for comparisons; the runner records boot/hash observations but does not deploy or independently certify B6.
- Proposed execution lanes are cx-t0 (5ea), cc-t3 (5cd), oc-t4 (61b), matching their current board lanes. Each command verifies its lane owns the exact full serial; no lock is acquired by this plan. If dispatch changes, update lane and command together in the JSON and rerun offline validation.
- Round ID is `b4-v4-after-b6-r1`. Use each command once with a fresh output directory. If already used, allocate a new round and change all three run IDs, command arguments and artifact directories in the JSON before starting. Never delete evidence to reuse an ID.
- Run the master-path commands below **after outer-loop commit/merge of task 59**. `b4_rerun.py plan` prints commands and checks pins without executing them. On a later master runner change, review and repin its SHA rather than silently using a different tool.

## Shard distribution

| Shard / lane | Keys | controls / blocked / tail | B6 attach | B6 context | UnsatisfiedLink | Known white startup windows (#51/#60) |
|---|---:|---|---:|---:|---:|---:|
| 5ea / cx-t0 | 22 | 4 / 14 / 4 | 10 | 1 | 2 | 4 |
| 5cd / cc-t3 | 22 | 4 / 15 / 3 | 10 | 2 | 2 | 5 |
| 61b / oc-t4 | 22 | 5 / 14 / 3 | 10 | 2 | 1 | 4 |

Every historical family differs by at most one member between boards. The 30 B6 attach cases split 10/10/10; context 1/2/2; linkage 2/2/1. The later 13 white-startup-window observations also split 4/5/4. Each shard retains original controls → blocked → tail order. Aliases remain separate keys; x/noice identity is resolved from app-input by the accepted runner. Full historical provenance is [b4-rerun-history.json](b4-rerun-history.json); the white-window overlay is explicitly marked historical in the shard JSON.

## Complete execution commands and artifact roots

Invoke each from the Mac. Each is a separate board task and may run concurrently only after its own board is released and locked by the named lane. The explicit `--wait 20` preserves a final process observation at the last screenshot; `--hilog 15` remains the requested diagnostic offset.

### 5ea

Keys in execution order: `wikipedia`, `fd-auxio`, `fd-droidify`, `fd-noice`, `anki`, `opencamera`, `fd-api`, `fd-fennec_fdroid`, `fd-filemanager`, `fd-gallery`, `fd-im-vector-app`, `fd-kitchenowl`, `fd-libre`, `fd-mpv`, `fd-plus`, `fd-uhabits`, `fd-stk`, `toutiao`, `mcdonalds`, `burgerking`, `subwaysurfers`, `noice`.

```sh
orb -m a2hlab bash /Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-28-bms-route-deploy/batch/run-batch.sh --execute --serial 5ea34a4500000000000000001123012c --lane cx-t0 --run-id b4-v4-after-b6-r1-5ea --out /home/zhaoyue/a2hlab/board --manifest /Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-28-bms-route-deploy/batch/apps.json --input-root /home/zhaoyue/a2hlab/app-inputs --keys wikipedia,fd-auxio,fd-droidify,fd-noice,anki,opencamera,fd-api,fd-fennec_fdroid,fd-filemanager,fd-gallery,fd-im-vector-app,fd-kitchenowl,fd-libre,fd-mpv,fd-plus,fd-uhabits,fd-stk,toutiao,mcdonalds,burgerking,subwaysurfers,noice --reinstall --hilog 15 --shots 5,20 --focus-check --wait 20
```

Expected VM directory: `/home/zhaoyue/a2hlab/board/b4-v4-after-b6-r1-5ea/5ea34a4500000000000000001123012c`.

Expected summary: `/home/zhaoyue/a2hlab/board/b4-v4-after-b6-r1-5ea/5ea34a4500000000000000001123012c/summary.json`.

### 5cd

Keys in execution order: `ooniprobe`, `aegis`, `fd-com-amaze-filemanager`, `fd-fitness`, `newpipe`, `fd-android`, `fd-app`, `fd-breezyweather`, `fd-feeder`, `fd-fluffychat`, `fd-libretube`, `fd-minetest`, `fd-musicplayer`, `fd-reader`, `fd-saber`, `fd-shatteredpixeldungeon`, `fd-tutanota`, `fd-wifianalyzer`, `fd-mobile`, `firefox`, `localsend`, `x`.

```sh
orb -m a2hlab bash /Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-28-bms-route-deploy/batch/run-batch.sh --execute --serial 5cd1e3dd00000000000000000923012c --lane cc-t3 --run-id b4-v4-after-b6-r1-5cd --out /home/zhaoyue/a2hlab/board --manifest /Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-28-bms-route-deploy/batch/apps.json --input-root /home/zhaoyue/a2hlab/app-inputs --keys ooniprobe,aegis,fd-com-amaze-filemanager,fd-fitness,newpipe,fd-android,fd-app,fd-breezyweather,fd-feeder,fd-fluffychat,fd-libretube,fd-minetest,fd-musicplayer,fd-reader,fd-saber,fd-shatteredpixeldungeon,fd-tutanota,fd-wifianalyzer,fd-mobile,firefox,localsend,x --reinstall --hilog 15 --shots 5,20 --focus-check --wait 20
```

Expected VM directory: `/home/zhaoyue/a2hlab/board/b4-v4-after-b6-r1-5cd/5cd1e3dd00000000000000000923012c`.

Expected summary: `/home/zhaoyue/a2hlab/board/b4-v4-after-b6-r1-5cd/5cd1e3dd00000000000000000923012c/summary.json`.

### 61b

Keys in execution order: `termux`, `antennapod`, `fd-AppManager`, `fd-com-kunzisoft-keepass-libre`, `fd-netguard`, `markor`, `fd-calendar`, `fd-catima`, `fd-etar`, `fd-immich`, `fd-k9`, `fd-meet`, `fd-notes`, `fd-organicmaps`, `fd-seal`, `fd-tasks`, `fd-tusky`, `fd-client`, `fd-binaryeye`, `vlc`, `ppsspp`, `mindustry`.

```sh
orb -m a2hlab bash /Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-28-bms-route-deploy/batch/run-batch.sh --execute --serial 61b0657200000000000000000324012c --lane oc-t4 --run-id b4-v4-after-b6-r1-61b --out /home/zhaoyue/a2hlab/board --manifest /Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-28-bms-route-deploy/batch/apps.json --input-root /home/zhaoyue/a2hlab/app-inputs --keys termux,antennapod,fd-AppManager,fd-com-kunzisoft-keepass-libre,fd-netguard,markor,fd-calendar,fd-catima,fd-etar,fd-immich,fd-k9,fd-meet,fd-notes,fd-organicmaps,fd-seal,fd-tasks,fd-tusky,fd-client,fd-binaryeye,vlc,ppsspp,mindustry --reinstall --hilog 15 --shots 5,20 --focus-check --wait 20
```

Expected VM directory: `/home/zhaoyue/a2hlab/board/b4-v4-after-b6-r1-61b/61b0657200000000000000000324012c`.

Expected summary: `/home/zhaoyue/a2hlab/board/b4-v4-after-b6-r1-61b/61b0657200000000000000000324012c/summary.json`.

For every key, expected paths relative to its board directory are `<key>/record.json`, `install.txt`, optional `uninstall.{txt,json}`, `bundle.txt`, sandbox receipts, `processes-t5.txt`, `windows-t5.txt`, `processes-t20.txt`, `windows-t20.txt`, `processes-after.txt`, `windows.txt`, `hilog.txt`, `diagnostics.json`, fault listings and `faultlogs/<new-name>`. Successful strict focus probes also produce `<key>/t5.jpeg` and `t20.jpeg`; rejected focus probes intentionally have no image path. Run-level `plan.json`, `summary.json`, `baseline.json`, and `commands/` retain identity and command evidence.

No expected file is claimed to exist on a real board. Input refusal or earlier failure may prevent later-stage artifacts; that remains a per-key result. The known 36627-byte black frame remains rejected; any other byte size still needs visual review.

## Offline plan and FakeBoard checks

```sh
BATCH=/Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-28-bms-route-deploy/batch
python3 "$BATCH/b4_rerun.py" plan --shard 5ea
python3 "$BATCH/b4_rerun.py" plan --shard 5cd
python3 "$BATCH/b4_rerun.py" plan --shard 61b
python3 -m unittest discover -s "$BATCH" -p test_b4_rerun.py -v
```

The test first sends each complete runner argument list (only --execute removed) through master-compatible `bms_batch.main`, checking the actual 22-key corpus selection. It then runs all **66** selected keys through `run_batch` using synthetic APK metadata and FakeBoard, a fake monotonic clock and a subprocess trap. Each shard produces **22 simulated records / 44 simulated captures**. No real APK or device was read. [b4-rerun-fakeboard.json](b4-rerun-fakeboard.json) records the three checks. The synthetic success histogram is deliberately not published as the real v4 result.

Optional reproducible fixture output (fresh local directory only):

```sh
python3 "$BATCH/test_b4_rerun.py" --smoke-out /tmp/b4-task59-fake-smoke-fresh
```

The output is explicitly `synthetic_fixture_only`; its `fixture-v4.json` is test data, not evidence of 66 live apps.

## v4 aggregation entry

Run inside a2hlab after all three shard summaries exist; alternatively copy complete run directories and point --run-root at the copied root. Evidence paths are rebased within their corresponding app directory and verified by recorded SHA, so stale absolute VM paths are never opened.

```sh
orb -m a2hlab python3 /Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-28-bms-route-deploy/batch/b4_rerun.py aggregate \
  --run-root /home/zhaoyue/a2hlab/board \
  --out /home/zhaoyue/a2hlab/board/b4-v4-after-b6-r1-final.json
```

The default rejects incomplete inputs. During an interrupted round use a distinct output filename with `--allow-partial`; missing keys become explicit `not-run`, `complete=false`, exit status 1. Invalid serial/run/options, duplicate or foreign keys, summary/record disagreement, mixed boot IDs, changed APK pins or changed evidence hashes are rejected even in partial mode. Existing histogram output files are never overwritten.

The output retains v3 fields: `total`, `records`, `category_histogram`, `exited_early_first_blocker`, `unknown_keys_remaining`, and each key’s `category`, `category_reason`, `first_blocker`, `blocker_evidence`, process/focus/screenshot data. It adds the round, three serials, source hashes, completeness and missing-key accounting. Counts are recomputed from these current records, never patched over v3.

- Normal v3 categories are preserved: `alive-at-sample`, `exited-early`, `rerun956-install-failed`, `input-refused`. The historical `rerun956-install-failed` spelling is retained for schema compatibility; it now covers any failed install receipt, not only code 9568260.
- `interrupted`, `collection-failed`, and partial-only `not-run` remain separate. A sandbox/launcher failure or missing post-click sample is not silently called an app crash. Screenshot/focus rejection remains visible in `record_status` and each probe even if the process is alive.
- Fatal classification adapts #48’s fault-first/hilog-second approach and family names. New faultlogs must match the target BMS UID; hilog requires exact package or an observed/disclosed target PID. HDC/sigchain/kickdog/hook/PARAM_WATCHER noise and plain method-trace text are excluded. Each selected observation retains original file, line and text. Unattributed or missing evidence stays `unknown`.
- Faults are ordered by filename timestamp suffix within the fault channel; no cross-channel chronological proof is claimed. A live sample plus fatal evidence is recorded separately as `alive_with_fatal_evidence`, without inventing that the crash happened later. Visual review always remains pending.
- Sampling differs from old v3 (mixed historical 15/16-second probes): this round observes through t+20. Requested hilog/fault capture occurs at t+15; a death between t+15 and t+20 can legitimately remain unknown. A focused window may still contain a white startup surface. Neither process survival, focus nor JPEG size is LIT.

## Delivery status

Preparation and offline checks only; no real v4 histogram exists yet. R2: shard identities/coverage, FakeBoard execution and aggregation negative controls **verified**; B6 readiness, real-board results and screenshots **unverified**. Final machine-readable validation is in [b4-rerun-results.json](b4-rerun-results.json), with test log and lifecycle evidence. Outer loop owns commit.
