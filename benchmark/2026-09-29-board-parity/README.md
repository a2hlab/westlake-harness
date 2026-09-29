# Item 64: three-board runtime parity at 14:46 CST

**158 paths per board: 153 identical, 5 different, 0 unreadable.** The active `6cb40cd6` native generation is consistent on disk across all three boards. The material active differences are **5cd's Java JAR and its two installer copies**. Two additional differences are in 61b's old `74e6…` generation directory, which is not used by the captured HelloWorld processes.

Two assumptions were wrong. First, the collection did contain HelloWorld on **5ea PID 29584 and 61b PID 14337**: `ps NAME` reported the inherited executable name `appspawn-x`, while `/proc/PID/stat`, exact APK mappings and parent PIDs identify the actual children. Second, **5cd's JAR is r8b `d5000c4e`, not the reported r7b `c432d987`**. The full hash matches the r8b build receipt. Rules established: derive process roles from combined identity evidence; use sampled full hashes, not deployment labels or a previous check result.

## Capture and completeness

The outer loop ran the reviewed read-only collector at **2026-09-29 14:46:18–14:47:03 CST**. All three boot IDs and critical hashes remained unchanged during their respective reads. The raw [collection.json](evidence/collection-20260929T1446/collection.json) and 105 companion JSON receipts are preserved unchanged; the summarizer corrects roles only in derived output. The earlier local transport failure is retained separately and is not used as current evidence.

| Scope | Paths per board | Equal | Different |
|---|---:|---:|---:|
| `/system/android/lib64` | 50 | 50 | 0 |
| `/system/android/framework` including nested boot files | 41 | 40 | 1 |
| route-a `6cb40cd6…` | 29 | 29 | 0 |
| route-a `74e6f759…` | 28 | 26 | 2 |
| `/system/lib64/appspawn` | 7 | 7 | 0 |
| appspawn-x + two installer copies | 3 | 1 | 2 |
| **Total** | **158** | **153** | **5** |

Raw tree receipts: each board's `tree-0.json` through `tree-3.json`, plus `single-files.json`; full hashes in [file-parity.csv](file-parity.csv). This is a timestamped snapshot, not a claim about later B9 deployment. Same boot alone cannot establish unchanged generation: bind overlays can change without reboot.

## All five differences and their significance

Full paths/hashes are in [DIFFERENCES.md](DIFFERENCES.md), [results.json](results.json) and the CSV. Prefixes here are display abbreviations.

| File | 5ea | 5cd | 61b | Behavior / accepted scope / recommendation |
|---|---|---|---|---|
| `framework/oh-adapter-runtime.jar` | `250958dc` | **`d5000c4e`** | `250958dc` | B5 versus r8b. r8b adds manifest JSON fallback and other Java projections; it changes binding/application behavior. Its build receipt proves identity, not acceptance. Do not merge B5/r8b shards into one B4 baseline. |
| `/system/lib64/libapk_installer.so` | `675536e8` | **`1ebf78ab`** | `675536e8` | B2/B3 labels versus B7's missing-icon fallback extension. Both are functional variants; newer is not a byte-only rebuild. Choose one accepted installer for all shards. |
| `/system/lib64/platformsdk/libapk_installer.so` | `675536e8` | **`1ebf78ab`** | `675536e8` | Same difference; both copies agree within each board. Foundation's mapped object confirms the active variant (below). |
| old `74e6…/libnativeloader.so` | `fde6f31c` | `fde6f31c` | **`eddeb87e`** | Old-generation discrepancy, absent from captured appspawn/HelloWorld mappings. No observed effect on the active `6cb` children; relevant if that old directory becomes a rollback target. Do not copy it into the active generation. |
| old `74e6…/libwestlake_android_runtime_provider.so` | `80c9aee0` | `80c9aee0` | **`6787ea7d`** | 61b retains the PR03 provider rather than the historical R155 provider under this old directory. **Current captured children use `6cb…/3aa5d169`, not either old provider.** Restore a coherent old generation only if intentionally selecting that rollback profile. |

JAR identity evidence: raw 5cd `tree-1.json` and `critical-after.json`; [r8b-build-reference.json:5](evidence/r8b-build-reference.json) records the exact output SHA; its lines 6–31 list changed/added classes, including `ManifestJsonFallback`. Historical r7b identity is retained separately in [r7b-report-reference.txt](evidence/r7b-report-reference.txt), original README line 28. Installer behavior/provenance comes from accepted #52/#54 work and [reference-installer.txt](evidence/reference-installer.txt); a desktop label installed before the new installer does not update merely because a library changed.

## Actual mapped objects

Maps were read using `cat`, not `hdc file recv /proc/PID/maps`. The collector hashes `/proc/PID/map_files/<range>` and checks its device/inode against maps; `/proc/PID/root/<path>` is a fallback only with matching device/inode. It brackets reads with process start times and relevant maps. The captured listed objects pass this check; these hashes identify backing files at sampling time, not relocated in-memory pages.

| Board | Boot ID | appspawn parent | HelloWorld | Foundation / mapped installer |
|---|---|---:|---:|---|
| 5ea | `e36781a9-2ba1-4804-b8e5-2a1125c39a47` | 28947 | **29584** | 881 / `675536e8` |
| 5cd | `64a531ef-ae65-443a-af63-089255340a8e` | 18501 | **supplement requested** | 919 / `1ebf78ab` |
| 61b | `b5994fff-ce37-4bbc-89d8-c99662bf8b4b` | 13708 | **14337** | 885 / `675536e8` |

5ea/61b HelloWorld `stat` comm is `com.example.hel`, PPID is the corresponding parent, and maps contain exactly `/data/app/el1/bundle/public/com.example.helloworld/android/base.apk`. Their original files remain named `appspawn-<pid>-*`; derived records include `original_role` and the evidence supporting reclassification. 61b PID 17209 is another application child (ZigZag), not a second appspawn parent. See numbered [5ea](evidence/5ea34a45-key-lines.txt), [5cd](evidence/5cd1e3dd-key-lines.txt) and [61b](evidence/61b06572-key-lines.txt) excerpts; each line points back to a raw receipt and original stdout line.

| Active component | Full-hash prefix | Established scope |
|---|---|---|
| appspawn-x | `b7205719` | disk + all three parent mappings |
| child plugin | `03aa6216` | disk + all three parent mappings |
| `6cb…/runtime_provider` | `3aa5d169` | disk on three; 5ea/61b HelloWorld mappings |
| `liboh_adapter_bridge` | `84695d62` | disk on three; 5ea/61b HelloWorld mappings |
| `6cb…/libart` | `59e1bb45` | disk on three; one offset-zero ART mapping in each captured HelloWorld |
| `6cb…/libopenjdkjvm` | `8b462862` | disk on three; route-path mapping in each captured HelloWorld |
| boot ART / OAT / VDEX | `2e4f8049` / `25d92cf7` / `23c1f5b0` | disk on three; matching files mapped in both captured HelloWorld processes |

The runtime JAR is not a named JAR mapping in these two HelloWorld maps; ART can consume dex into anonymous mappings. Its disk hash is verified, but this capture alone cannot prove the exact Java bytecode already loaded by those children. Do not manufacture a JAR mapping to close that gap.

## Three-board alignment recommendation

**Keep the signed #66 native `6cb40cd6` group as this snapshot's common control; do not restore old R155 host/child/provider merely to match the preparatory pin file.** Its 29 route files, 50 Android libraries, appspawn directory and executable already agree. The B9/v3 experiment was starting after this snapshot; it must be assessed with a new timestamped manifest, not inferred from unchanged boot IDs.

For an immediate reproducible **control** replay, [alignment-profile.json](alignment-profile.json) pins **130 paths**: accepted #66 native + **B5 JAR `250958dc` + installer `675536e8` in both locations**. Those components have historical control evidence; this inventory adds no new visual success claim. The old 28-file `74e6` directory is deliberately outside the active profile. The preparation-only `reference-pins.json` describes older R155, and is not the current deployment target.

For the forward B4 rerun, finish the r8b/B9 controls, then publish one updated common profile before splitting the keys. Promote the accepted Java JAR and installer `1ebf78ab` together where appropriate, recording full hashes and their validation scope; **do not mix 5cd r8b with 5ea/61b B5 or call all three “r7b.”** This is a recommendation to freeze the rerun's inputs, not an instruction to interrupt the currently authorized experiments. Any old-directory cleanup/alignment is separate from the active runtime and was not performed here.

The latest user-authorized B9 direction moves identity checking to the deployment tool and permits single-file replacement after the new native generation is accepted. This report does not impose a superseded runtime sealing policy. The relevant check remains the deployed manifest plus child mappings, regardless of where enforcement lives.

## Reproduction and verification

```sh
python3 benchmark/2026-09-29-board-parity/summarize.py \
  benchmark/2026-09-29-board-parity/evidence/collection-20260929T1446/collection.json
python3 -m unittest discover -s benchmark/2026-09-29-board-parity -p 'test_*.py' -v
```

The complete raw tree collection and the full CSV are reviewable offline. Only 5cd HelloWorld needs a supplemental capture. The outer loop confirmed that cc-t3 currently owns 5cd for B8, so it will collect after release; this lane will not launch or interrupt an app. The supplement requires the same boot and matching mapped hashes; `collect_process.py` has been supplied to the outer loop. The summarizer's `--supplement` option preserves its separate provenance/time interval and rejects changed boot or mismatched mapped files.

Validation: **7/7 offline tests** (including replay of all raw hash receipts and mapped-object classifications) and the Rust wrapper pass; known-answer suite **69 tests / 2 skips / 0 failures**. The lifecycle remains **1 pass / 2 fail** because both live scenarios share the complete-inventory selector, which still requires 5cd HelloWorld. These failures are preserved in [lifecycle-1446.json](evidence/lifecycle-1446.json); they do not mean the successfully read disk trees are missing.

R2: all disk hashes, five differences, parent/foundation mappings and 5ea/61b HelloWorld identities **verified**. Complete three-board HelloWorld mapping coverage **partially**, pending 5cd. Exact loaded JAR bytecode and post-alignment app/UI behavior **unverified**. No device write, launch, lock, deployment, commit or push by this lane. Outer loop owns the commit.
