# BMS execution preparation — board item 15

> **Superseded deployment choice:** the user subsequently selected OH 6.1 R130 + R155 from `01.OH61AOSP16` (#19), without flashing. The T006/OH7 audit below is retained as historical #15 work; do not execute its first-hour sheet for this campaign. Batch tooling continues under #20.

**Select the `~/t006/pack/` v3 archive, not the same-named archive one directory above.** The selected archive matches the published contract: **274,575,597 bytes**, SHA-256 `e30a91993f06fc50ce401655837d9cfdec5a177aca65a311a5810ce14ae71145`. The local PAC is **3,514,798,293 bytes**, SHA-256 `4046781bfcd033ea62dc339892b671d71a34bad3fa53b6c44d914d79281cb0b8`. Host readiness finds the six tools, module index, payload inputs and CTS module; the target board's BCP copy remains missing. No board was queried or changed. Evidence: [payload audit](evidence/payload-audit.md), [PAC measurement](evidence/pac-audit.json), [readiness receipt](evidence/cts-ready-materials.json).

The earlier assumption that filenames identify interchangeable artifacts was wrong: two `v3` archives have different runner behavior, and this machine's correct OH7 PAC lacks the documented `-oh-7` suffix. The rule is **size + hash + post-flash fullname/release readback**, never a filename alone. Sources: `00.Workspace/CTS_ENVIRONMENT.md:32-50,220-233`, `firmware/README.md:5-20`; measurements above.

Scope changed from six-question route assessment (#13) to execution preparation (#15). The BMS route is selected; the stock-OH6.1 projection-HAP alternative is no longer a deliverable. `00.Workspace` was inspected at commit `cd5b3293596cc9d9f324743d6d904c5135954076`; the archive is an older, separately pinned runtime generation. Current source findings do not describe every byte of that release. R2: **verified** host checks/archive measurements; **partially** historical application evidence (strength differs by row); **unverified** new deployment, current-board compatibility, and first-hour execution. Human review remains pending.

Citation roots: `00.Workspace/` = the read-only source checkout; `t006/` = `~/t006`; `firmware/` = `~/orca/firmware/OpenHarmony-7.0-Release`; `merged48/` = sibling `westlake-harness-merged48` at `bc90c65e73a8a9eb9650466dac142a9eaafbd497`. All commands below and in the run sheet are **future execution instructions**, except the explicitly recorded host checks.

## 1. Execution materials and remaining host prerequisites

| Material | Actual host result | Decision |
|---|---|---|
| `~/orca/firmware/OpenHarmony-7.0-Release/wukong100_nosec_userdebug.pac` | 3,514,798,293 bytes; full SHA above matches local SHA256SUMS | Correct candidate despite missing `-oh-7` suffix; post-flash identity still mandatory |
| Old `~/t006/t006-baseline-v3.tar.gz` | 274,574,386 bytes; SHA `b4d77dc00a2bb164fdefc648131cd9441f42c2bca104cf652187c805f23f3c4c` | Do not select for this run |
| Selected `~/t006/pack/t006-baseline-v3.tar.gz` | 274,575,597 bytes; published SHA above | Select and preserve pin |
| Selected `~/t006/pack/t006_baseline.py` | 59,606 bytes; SHA `6693d60a7cf95db816d653032c4298561e57765132a1b1346a03a5937f79a6a8` | Use this companion driver |
| CTS PMS APK already local | 112,615,886 bytes; SHA `0856402e69f4b67e6bf77a9c84859cdacfff85f96be90beb9181769bb8152a41` | Matches contract; no full CTS download |
| CTS PMS config already local | 26,119 bytes; SHA `38285696c47199d0c4ad8ff11c23164e47bd1960ac6ec0537ed56dacc0ad7f39` | Pass explicitly with APK |

Evidence: `00.Workspace/CTS_ENVIRONMENT.md:75-80,220-233`; [member diff](evidence/payload-member-diff.json), [manifest validation](evidence/payload-manifest-validation.json), [CTS measurements](evidence/cts-module-audit.json), [PAC measurement](evidence/pac-audit.json). The PAC hash was recomputed over all bytes; its match is to the retained local provenance record, not an independently redownloaded official release.

Each archive has **20 regular files**, of which **17 are identical and 3 differ**: `PAYLOAD.json`, `runner.tar.gz`, `t006_baseline.py`. Each manifest's **18 entries** passes size/hash validation. Device payload bytes are identical. The newer runner protects the HelloWorld baseline from CTS teardown, warms up `uitest` before the screen hold, and resolves work paths. The nested runner has 44 files, with only three changed. See [exact differences and source lines](evidence/payload-audit.md); archive integrity does not prove device success.

The requested `PYTHONDONTWRITEBYTECODE=1 ./cts-ready` was run from the source checkout with **no serial**. Exit 1, six host tools FOUND, suite index FOUND, dex2oat FOUND, BCP MISSING, board/payload/module unspecified = UNKNOWN ([raw output](evidence/cts-ready.txt)). A second check used a fresh selected-archive extraction in a host temporary directory and symlinks arranging the existing two CTS files into the expected module layout. It found payload, three standard test jars, candidate runtime jar and CTS module; only BCP remains MISSING and the three board checks remain UNKNOWN ([JSON](evidence/cts-ready-materials.json)). Temporary extraction did not modify `00.Workspace` or `~/t006`.

Missing or deferred:

- Target-specific BCP snapshot: collect **after** assigned-board deployment using `hdc -t "$BMS_SERIAL" file recv /system/android/framework "$BMS_WORK/bcp"`. An old board's BCP is not a replacement. Sources: `00.Workspace/CTS_QUICKSTART.md:54-60,93-113`.
- Board assignment, reachability, fullname, release type and flash execution are unverified by design; do not reinterpret UNKNOWN as absent hardware. Sources: `00.Workspace/CTS_QUICKSTART.md:11-18,38-47`.
- UpgradeDownload R27 and `PAC_uis7885_2h10` are the recorded flash procedure, but the flashing workstation/tool was not verified here. Preserve required crash evidence before its ERASEUBOOTLOG/ERASESYSDUMPDB actions. Source: `00.Workspace/CTS_ENVIRONMENT.md:32-51`.
- No additional host tool download is indicated by the readiness result. `d8`/`apksigner` found here are 37.0.0; the doctor reports presence, not a candidate rebuild compatibility test. No candidate was built.

The full documented `all` invocation includes **both CTS inputs**, which the shorter environment example omits (`00.Workspace/CTS_QUICKSTART.md:224-243`):

```sh
python3 "$HOME/t006/pack/t006_baseline.py" all \
  --payload "$HOME/t006/pack/t006-baseline-v3.tar.gz" \
  --work "$BMS_WORK/payload" \
  --hdc "$BMS_HDC" --serial "$BMS_SERIAL" \
  --apk "$HOME/orca/00.Workspace/.work/t001-uninstall-inputs/CtsPackageManagerTestCases.apk" \
  --original-config "$HOME/orca/00.Workspace/.work/t001-uninstall-inputs/CtsPackageManagerTestCases.config"
```

This is **not run**. It combines doctor/bringup/CTS; do not invoke it after a successful separate bringup just to collect a screenshot, or claim its CTS results establish visual success. The first-hour run sheet uses `bringup` to stop at the installation/UI gates. Before a later CTS slice, follow BCP/reachability/profile gates; Android14 ART/OAT230 plus CTS16_r4 can yield zero-method ENV_BLOCKED. Sources: `00.Workspace/CTS_QUICKSTART.md:20-22,93-113,224-246`.

## 2. First hour after flashing

Use [the full command-by-command run sheet](evidence/first-hour.md), including exact environment variables, board lock, per-step pass criteria, stop conditions and release of the lock. This sequence is an ordering guide, not a time guarantee.

| Window | Required observation | Stop / fallback |
|---|---|---|
| 00–10 | Assigned serial; exact `OpenHarmony-7.0.0.38`; `Release`; Enforcing; doctor and read-only preflight; pinned payload/driver | Wrong version/Beta: stop and return to flash owner. No automatic board substitution |
| 10–35 | One pinned `bringup`: 598 bridge files, 26 gap files, 4 links, jar/ANCO, reboot and socket readbacks | Preserve first failure; bridge rollback alone is not proof of full-stack rollback |
| 35–45 | foundation PID/boot identity, mapped BMS paths and **process-root** library hashes against selected gap files | Wrong hash/deleted mapping/missing foundation: patched BMS unverified; no further APK expansion |
| 45–50 | `bm install -p /data/local/tmp/HelloWorld.apk -u 100`, BMS record, pinned APK readback and UID/directories | Missing record/wrong hash/UID drift: stop; the helper assumes UID 20010052 |
| 50–60 | SceneBoard launch and actual `snapshot_display` image reviewed by human | Desktop/black/blank/wrong app is not lit, regardless of script PASS |

The one-key helper already installs and attempts to launch HelloWorld; its embedded install command is shown for review, not an instruction to reinstall twice. `aa start` is not the prescribed path: the baseline records shell-caller rejection and uses SceneBoard. Sources: `t006/run-new/README.txt:36-61`; `t006/t006_baseline.py:594-625,645-738`.

A specific false-positive trap is now explicit: **`bms_alive` is not proof of patched BMS**. Historical foundation kept an old mount namespace while shell-side new-library loading succeeded. Compare the live process view under `/proc/<foundation-pid>/root/system/lib64/...`, capture mappings and require positive raw-APK readback. Sources: `00.Workspace/evidence/runs/cts-getpackageinfo-20260915.md:133-149`; `t006/t006_baseline.py:583-591`. Screenshot existence/process maps are similarly weaker than visual light-up (`t006/t006_baseline.py:716-738`).

## 3. Historically installed/lit apps and campaign priorities

**There is no evidenced ready-made “previously unlit in our 66 launches, already BMS-lit there” first batch in the inspected records.** The intersection is empty for the identified historical apps, not proof that the entire archive contains no other success. The campaign final total is 66 launches / 15 lit launches / 13 distinct lit apps, so launch count is not package count. Sources: `merged48/benchmark/2026-09-27-app-breadth-sweep/README.md:30-69`, `merged48/benchmark/2026-09-27-app-breadth-sweep/RESULTS.md:51-66`; detailed per-app evidence in [historical matrix](evidence/architecture-platform.md).

| App | What is actually evidenced | Relation to 09-27 sweep / execution priority |
|---|---|---|
| `com.example.helloworld` | Pinned T006 first APK; historical OH6.1 display claim. Local OH7 `run2` installed but had no child; `run-new` installed but launch stopped on screen override | Outside sweep. **First canary because the pinned bringup owns it**, not because these T006 runs passed |
| `org.a2hlab.baseline.helloworld` | OH7.0.0.38, board `61ae0be500000000000000000324012c`; BMS/UID/token receipt and two original screenshots re-reviewed here: blue self-check → orange Color changes:1 | Outside sweep. Strong historical comparator; a different APK/package than T006, not a silent substitution |
| `com.a2hlab.bridge.zigzag` | Older report records BMS bundleType10; later OH6.1 board `5583f5be00000000000000000323012c` report records 3 interactive ~17s runs. Later artifact differs and screenshots were not re-reviewed here | Outside sweep. Later runtime-port test; do not join different-generation install/display records into a single verified OH7 result |
| `com.Revenko.org.CapybaraAdventure` | Usecase claims real game content with app-private library changes; raw BMS receipt/screenshot not re-reviewed | Outside sweep. Lower-confidence research candidate, not a confirmed BMS canary |
| `android.content.cts` | OH7 BMS installation/token evidence; that record says runner not started, 0 tests | Test harness, not a lit consumer app |

Sources: `t006/run2/evidence/bringup-report.json:92-122`; `t006/run-new/evidence/bringup-report.json:92-118`; `00.Workspace/vault/tasks/task_e3bb7b54/evidence/device-r8-baseline/device-ready-receipt.json:9-23,60-68`; `00.Workspace/evidence/runs/ab-compare/AB-REPORT-20260808.md:34-49`; `00.Workspace/evidence/current-apk-lightup.md:7-22,30-38,90-102`; `00.Workspace/domaindb/usecase/13-部署持久化与可回滚工程.md:181-224,259-262`; `00.Workspace/evidence/runs/cts-getpackageinfo-20260915.md:143-149`.

Proposed next batch **after** the canary is accepted: `markor`, `newpipe`, `anki`, in that order, as new measurements of campaign failures—not historically proven BMS successes. All three occur in the blocked list (`merged48/.../RESULTS.md:55-56`); markor also provides a campaign failure sentinel. Fix one runtime generation for all comparisons and keep an existing lit control such as Aegis. The route does not by itself implement missing download/account/bluetooth services or guarantee a first frame; source-only limitations remain in [blocker appendix](evidence/blockers.md).

The interrupted #13 source findings are retained as appendices: [architecture](evidence/architecture-platform.md) and [PMS semantics](evidence/semantics.md). In particular, current `resolveService` uses the canonical component-state catalog chain, not merely the older direct BMS query. This corrects the earlier DIGEST shorthand without claiming that the selected older payload contains the new path.

## Verification and handoff

`results.json` carries the selected artifacts, exact host readiness status, unexecuted first-hour steps and historical app list. Small evidence files contain measurements and source references; no firmware, APK, runtime binaries, credentials or source-machine logs were copied into git. User-home prefixes in copied small audit diffs are redacted.

Host verification checks the delivered receipts, hashes and referenced file spans. Human source/visual acceptance is separate and remains pending; current-board deployment is unverified. Local commit only, no push. Completion ACK belongs to **15**, because 13 was superseded.

Validation receipt: `cargo test --manifest-path tools/spec-checks/Cargo.toml bms_route_study_evidence` passed (including two negative controls). `agent-spec lifecycle ... --review-mode strict` returned exit 1 with **0 failed, 0 skipped, 0 uncertain, 2 pending_review**; both bound tests passed. See [lifecycle receipt](evidence/lifecycle.json). This is the intended human-review boundary, not a claim of full lifecycle acceptance.

Known-answer suite: 69 tests ran, 2 skipped, 0 failures. **Local commit blocked by the filesystem sandbox**: Git could not create the main-tree `.git/worktrees/westlake-harness-bms/index.lock`. No files were staged, no commit was created, and nothing was pushed. The complete work remains in `analysis/bms-route-study` for the outer reviewer to inspect and commit; ACK(15) records this concrete blocker.
