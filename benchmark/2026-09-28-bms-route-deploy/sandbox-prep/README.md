# B1: exact restore sandbox preparation; Wikipedia remains blocked by alias loading

**The missing sandbox preparation is fixed and verified. Wikipedia now reaches Android runtime initialization, then fails because the launcher alias `org.wikipedia.DefaultIcon` is instantiated as a Java Activity class.** The B1 contract therefore remains blocked: 3 scenarios pass and the Wikipedia survival/UI scenario fails. The 62-key rerun has not started.

Campaign #26 was superseded by #27 during execution. The authoritative [B1 contract](../../../specs/bms-copy/b1-sandbox-prep.spec.md) is copied unchanged from the campaign tree; [lifecycle-b1.json](lifecycle-b1.json) records its actual verdicts. B4 is a later dispatch, not an implicit continuation past this failed gate.

## Exact recipe and integration

[prepare_sandbox.sh](../batch/prepare_sandbox.sh) wraps the original HelloWorld restore lines **291–294** unchanged, introducing only the function boundary and local `PACKAGE` / `APP_UID` parameters. [Copied source body](source-lines-291-294.sh.txt) and [full source SHA/path](source.json) make byte comparison possible. The original wrapper `.agents/skills/reproduce-helloworld/scripts/reproduce.sh` delegates to `src/tools/devices/restore-pr03-helloworld-5min.sh`; ZigZag's equivalent `prepare_sandbox` is at `src/tools/devices/zigzag-apk-lightup.sh:2336–2340`. The HelloWorld version supplies the additional per-path `find ... -exec chcon` workaround, so both original command lines are retained.

The recipe creates nine base/database/sharefiles roots plus el2/log, creates the nine el2/base subdirectories, applies UID/GID ownership, 0700/0770 modes and the original SELinux labels, then runs per-path chcon. It does not change APK or runtime bytes.

The batch installer calls it after successful install/BMS readback and cold-stop confirmation, before the desktop click. The existing-install capture path does the same after verifying the installed original APK SHA. A failed command records `sandbox_prep_failed`, its return code, full submitted command path/hash and output; no desktop click follows. Package and UID validation occurs before device writes.

## Wikipedia critical experiment

Only board `5ea34a4500000000000000001123012c` was used. Boot remained `56e521b3-858f-4fbf-8e35-daec29525c93`; the four recorded runtime hashes match before/after. The installed Wikipedia APK remained `eba82a0f77940d8a6be5bd2e53723675a59859a6c8a51be5e50bd034fc77101f`. No reinstall, runtime patch or reboot occurred. 61b was not touched; 5cd belongs to the other lane and was not touched.

| Observation | Before preparation (#24) | After preparation (#27) |
|---|---|---|
| Required sandbox mount | ENOENT at el1/database, hook 31 result `0xd000008` | Preparation returns 0; spawn reply result 0 |
| Child | PID 26163, about 22 ms | PID 4789, visible in UID polling |
| Runtime admission | No RAC/LSP or Android entry | RAC/LSP/provider passes; `ActivityThread.main()` entered |
| New failure | Missing sandbox directories | `Unable to instantiate activity ... org.wikipedia.DefaultIcon`: `ClassNotFoundException` |
| End | Early initialization exit 0 | Parent records exit code 1 at 18:41:26.873 |
| At final capture | No UID process; desktop | No UID process; desktop |

The new trace records successful spawn at 18:41:24.953, Android main entry at 18:41:26.405, alias class failure at .804 and exit at .873. BMS exposes `org.wikipedia.DefaultIcon` with `targetAbility: ""`; the clicked ID is the exact registered desktop alias. The trace establishes that this alias reaches class loading unresolved. It does not identify the precise source layer that must translate the alias to its target; no BMS/shared-runtime repair was attempted under B1's forbidden boundary.

- [t+3 screenshot](evidence/wikipedia/t3.jpeg) and [t+15 screenshot](evidence/wikipedia/final.jpeg), for outer review. cx-t0 read the final image: it is the OH desktop.
- [Relevant original-line hilog excerpt](wikipedia-hilog-excerpt.txt), [full archived hilog](evidence/wikipedia/hilog.txt), [UID timeline](evidence/wikipedia/timeline.txt), [BMS dump](evidence/wikipedia/bundle.txt).
- [results.json](results.json): 91 samples across 16.09 seconds, sampled PID 4789, no surviving PID at the end, no new fault files. Nominal snapshot times include command overhead.

The full archived hilog redacts only unrelated SSID/BSSID fields; [original VM path and hashes](evidence/redactions.json) preserve raw provenance. Process snapshots alone are not used to infer whether fork occurred.

## B1 directory and repeat checks

[HelloWorld attributes](evidence/roots/helloworld.txt) and [Wikipedia attributes](evidence/roots/wikipedia-before-repeat.txt) contain all ten roots. Corresponding modes and labels match exactly. Owners are the respective BMS UIDs (20010055/20010057); app directories use their UID as GID, while el2/log uses GID 1007 (`log`).

The same preparation function was executed a second time on Wikipedia. It returned 0 and the [after-repeat attributes](evidence/roots/wikipedia-after-repeat.txt) are identical to the before-repeat attributes. [Repeat receipt](evidence/roots/result.json) records this explicitly.

| Authoritative B1 scenario | Verdict |
|---|---|
| Wikipedia survives and shows its own UI | **fail** — child exits after alias ClassNotFoundException |
| Ten root attributes match HelloWorld | pass |
| Preparation failure records status/command/return and skips click | pass |
| Preparation can be repeated without attribute change | pass |

Offline batch regression: **28 passed**, including exact recipe body, unsafe parameters, preparation failure and install→prepare→click ordering. Repository known-answer tests: **69 run, 67 passed, 2 skipped**. The deliberate failed B1 scenario is preserved; the contract was not weakened to make the lifecycle green.

R2: **partially**. Exact recipe integration, directory equivalence, idempotence and the new launch divergence are verified. Wikipedia visual acceptance is unmet, and no broad compatibility result follows. [Two planned 31-key shards](planned-shards.json) are offline planning only; no 62-key rerun was executed. Local commit only, no push.
