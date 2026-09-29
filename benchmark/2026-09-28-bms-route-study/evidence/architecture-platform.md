# BMS architecture, platform identity, and historical light-up evidence

Read-only study dated 2026-09-28; updated for board item 15 preparation. No device command, build, deployment, or flash was executed. Paths below are relative to `00.Workspace` unless prefixed `t006:` (the local `~/t006` snapshot) or `merged48:` (the sibling `westlake-harness-merged48` worktree). Historical receipts are evidence of their recorded run, never evidence of the current campaign boards.

## Decision-relevant results

- The strongest locally inspectable OH 7 light-up is **`org.a2hlab.baseline.helloworld` on OpenHarmony-7.0.0.38, aarch64**: the receipt binds the runtime/BMS library hashes, installation UID/token, and child identity; I inspected both original screenshots and saw the blue JNI self-check screen change to orange `Color changes: 1`. This is a historical visual observation, not a new run. Sources: `vault/tasks/task_e3bb7b54/evidence/device-r8-baseline/device-ready-receipt.json:9-23,60-68`; `vault/tasks/task_e3bb7b54/evidence/device-r8-baseline/external-hello/receipt.json:12-85`; `vault/tasks/task_e3bb7b54/evidence/device-r8-baseline/external-hello/pixel-review.json:2-18`. Images inspected in place: `vault/tasks/task_e3bb7b54/evidence/device-r8-baseline/touch-r1/screen/{before-touch,after-touch}.jpeg`; no image copied into the public repository.
- **T006's own two bringup reports do not prove a successful HelloWorld launch.** Both record successful installation, but `run2` has no child and `run-new` aborts on screen-override drift. Sources: `t006:run2/evidence/bringup-report.json:92-122`; `t006:run-new/evidence/bringup-report.json:92-118`. Do not replace these failures with the distinct dedicated-Hello evidence above.
- **No historical BMS-lit app identified here intersects the 09-27 unlit app keys.** The inspected historical names are legacy HelloWorld, dedicated HelloWorld, ZigZag, and a weaker Capybara report; none occurs in the pre-tail blocked list or final eight unlit tail keys. This is a name/package-level intersection of the inspected evidence, not proof that BMS fixes any current unlit app. Sources for the unlit set: `merged48:benchmark/2026-09-27-app-breadth-sweep/RESULTS.md:51-66`; `merged48:benchmark/2026-09-27-app-breadth-sweep/README.md:56-69`. Historical-app evidence is individually graded below.
- **The available T006 baseline requires OH 7.0.0.38 Release before deployment** and does not contain the firmware image. Its README records boot hangs with a same-number Beta build because the patched BMS libraries cannot load; treat this as the payload's historical compatibility claim, not an independently reproduced root cause. Sources: `t006:run-new/README.txt:31-34,63-66`. Its read-only doctor records both fullname and `Release`: `t006:run-new/doctor.json:29-36,61-75`.

## Historical application matrix

| Application / exact identity | Installation evidence | Visible result and strength | Platform and limitation | 09-27 unlit intersection |
|---|---|---|---|---|
| Dedicated HelloWorld `org.a2hlab.baseline.helloworld`; APK SHA `526a92a767f308e7f2298f8dc0a3fc1060db724b58cf876b25d49cf7c72cfb5a` | Installation receipt UID `20010053`, token `537825521`; exact BMS/installs/common/installer hashes | Two actual screenshots personally inspected: JNI self-check blue screen, then orange `Color changes: 1`; historical pixel pass, original review was not independent | OH 7.0.0.38 / aarch64 / Enforcing; one recorded boot | None |
| Legacy HelloWorld `com.example.helloworld`; APK SHA prefix `2d122a7973ffd68c` | T006 run2 and run-new explicitly record successful install and package APK hardlink | T006 run2 launch fails `10107101` then no PID; run-new blocked on screen override; **not a T006 light-up pass**. Older OH6.1 AB report says it previously displayed | OH7 T006 deployment results must remain separate from OH6.1 historical display | None |
| ZigZag `com.a2hlab.bridge.zigzag`; APK SHA `aaa7c9cce4886eef1280e917fd25bf434c53065cf0bf8b5704b83738137275bc` | Historical AB report records `bundleType=10`; later accepted report describes original APK and exact runtime generation | Later report records real track/ball and GAME OVER, five touches, three roughly 17-second runs including rollback/redeploy; **report-backed**, its cited `.state` screenshots were not used as locally re-reviewed evidence here | OH6.1.0.31, historical PR03/AOSP14-derived artifact; current AOSP16 rebuild equivalence explicitly UNKNOWN | None |
| Capybara `com.Revenko.org.CapybaraAdventure`; APK SHA `552b731aa6b6c50871ac218c65665669c089ddb09ec780f414c18e3d685b5730` | Usecase describes original installed APK and app-private library mount paths; **no raw BMS receipt inspected** | Usecase quotes final real game content in top 1200×750, but original working log/screens are not in the inspected material; **historical documentation candidate, weaker than receipt+image** | App-private modified library views; cannot generalize to all Unity apps or current OH7 | None |
| CTS `android.content.cts` | OH7 installation report: `bundleType=10`, arm64-v8a, token `537429530` | Installation only; report explicitly says runner had not started and 0 tests passed; **not a light-up app** | OH7 migration experiment with service-view library SHA validation and recovery | Not applicable |
| G3 Minimal CardWords | Fixture source/README only in this survey | **Not admitted as BMS-lit evidence** from fixture existence | README only documents build/output | Not applicable |

Matrix sources, by row:

1. `vault/tasks/task_e3bb7b54/evidence/device-r8-baseline/device-ready-receipt.json:9-23,60-68`; `vault/tasks/task_e3bb7b54/evidence/device-r8-baseline/external-hello/receipt.json:12-85`; `vault/tasks/task_e3bb7b54/evidence/device-r8-baseline/external-hello/pixel-review.json:2-18`.
2. `t006:run2/evidence/bringup-report.json:92-122`; `t006:run-new/evidence/bringup-report.json:92-118`; `evidence/runs/ab-compare/AB-REPORT-20260808.md:34-39`.
3. `evidence/runs/ab-compare/AB-REPORT-20260808.md:44-49`; `evidence/current-apk-lightup.md:7-22,30-38,90-102`.
4. `domaindb/usecase/13-部署持久化与可回滚工程.md:181-209,217-224,259-262`.
5. `evidence/runs/cts-getpackageinfo-20260915.md:143-149`.
6. `APKS/G3-Minimal-CardWords/README.md:1-8`.

The sweep total itself needs care: its authoritative final report says **66 launches, 15 lit launches, 13 distinct lit apps**; `noice` repeats `fd-noice`, and `burgerking` has a McDonald's-label anomaly and is not counted as a separate victory. Thus 51 is the count of non-lit launch outcomes, not automatically 51 distinct packages. Sources: `merged48:benchmark/2026-09-27-app-breadth-sweep/README.md:30-59`. The report's interpretation that label text proves APK identity is not independently established here; package and APK hashes must decide identity during the future experiment.

## OH7 preparation and BMS verification facts

The preparation sequence supported by T006 is: verify payload SHA; independently verify OS fullname and release type, SELinux, root mount state and capacity; deploy 598 bridge files plus 26 gap files and four symlinks; configure runtime jar, ANDROID_DATA and ANCO parameter; controlled reboot; verify AppSpawnX socket and BMS; install HelloWorld, hardlink and sandbox directories; launch by its desktop icon and capture evidence. Source: `t006:run-new/README.txt:36-61`. This is a recorded method only, not a recommendation to execute it on an unspecified campaign board.

T006 `bringup-report` contains successful readbacks for 598 files, 26 files, four links, baseline jar, ANCO, return from reboot, AppSpawnX socket, and BMS; the later launch gate fails. Source: `t006:run-new/evidence/bringup-report.json:38-118`. The layout replaces platform libraries: appmgr, appspawn client, BMS, installd, bundle-common and installer are explicitly present in the gap attributes. Source: `t006:run-new/gap-attrs.txt:14-26`. This is not merely copying a new user-space subsystem while preserving stock services.

For BMS migration, the September report gives a useful genuine failure→correction chain: the initial OH7 system rejected raw APK (`9568269`); no-cache compilation rebuilt 242 CFI BMS objects and 38 AppMgr objects, then strict linking and device `dlopen` succeeded; but foundation's boot-time system namespace still saw factory libraries. Only validation inside `/proc/<foundation>/root/system/lib64/...` established which libraries actually serviced the request. Adding OH7 `ExtractParam.bundleName` then produced real APK installation, bundle type 10 and AccessToken; recovery was separately checked. Sources: `evidence/runs/cts-getpackageinfo-20260915.md:88-90,125-149`.

The original APK may be installed while shell `aa start` remains rejected. T006 specifically documents shell-caller permission rejection and desktop/SceneBoard launch as its working admission path, not a missing permission that can be granted to the app. Source: `t006:run-new/README.txt:50-61`. Earlier OH6.1 bridge deployment also changed native HAP shell launch behavior after replacing `libabilityms.z.so`/`libappms.z.so`; it must not be called a stock-preserving route without regression evidence. Source: `evidence/runs/ab-compare/AB-REPORT-20260808.md:384-400`.

This historical/source sub-study did not validate firmware or flashing; the parent PAC byte/hash audit is separate. No board flashing success or source-to-image build was validated. T006 explicitly excludes firmware (`t006:run-new/README.txt:63-66`); current AOSP16-to-final-ZigZag artifact equivalence is explicitly UNKNOWN (`evidence/current-apk-lightup.md:15-22`).

## Architecture and ownership retained from item 13

The historical raw-APK route is:

`APK -> bm/BMS Android install branch -> manifest verification/projection -> installd file deployment + InnerBundleInfo + HAP token -> BundleType::APP_ANDROID -> AMS/AppMgr AndroidSpawnClient -> AppSpawnX -> ART preload/fork -> Android ActivityThread and adapter lifecycle/window seams`.

This chain is documented at `domaindb/usecase/01-包安装与包信息投影.md:48-74` and `domaindb/usecase/02-进程孵化与运行时启动.md:40-65`. The install metadata entry is directly present: pathname-only legacy install returns rejection; the manifest API validates a sealed snapshot before parsing and leaves filesystem mutation to BMS/installd (`src/adapter/framework/package-manager/jni/oh_adapter_install_apk_c_entry.cpp:216-266`). It serializes activities, launch modes, orientation, exported state, actions/categories and launcher designation (`src/adapter/framework/package-manager/jni/oh_adapter_install_apk_c_entry.cpp:295-342`).

UID claims require distinguishing two generations. The minimal manifest bridge actually computes `10000 + hash(package)%10000` and serializes that UID/GID (`src/adapter/framework/package-manager/jni/oh_adapter_install_apk_c_entry.cpp:268-276,311-312`); this is not proof that this value is the final BMS-assigned host UID. The accepted OH7 Hello receipt independently records UID 20010053/token 537825521 (`vault/tasks/task_e3bb7b54/evidence/device-r8-baseline/external-hello/receipt.json:81-91`). The real BMS/AccessToken allocation is described by the historical patch account (`domaindb/usecase/01-包安装与包信息投影.md:50,65-74`).

Route A assigns request decoding, contexts, fork, token, sandbox, DAC/capabilities/SELinux and result pipe to the stock OH appspawn host; Android begins after the stock child pipeline. The chosen service is an AppSpawnX-named instance of the stock host with a child plugin, not the original unchanged appspawn binary. Sources: `src/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/ARCHITECTURE_DECISION.md:5-21,26-42,54-85`; `src/adapter/framework/appspawn-x/src/child_main_after_stock.cpp:1-9`. Legacy security-owning child entry is compile-time disabled by default and exits 125 (`src/adapter/framework/appspawn-x/src/child_main.cpp:53-61`).

The stock-host delta is explicit: stage-20 parent prefork must stop on failure before fork; the historical stock call ignored its return. Source: `src/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/ARCHITECTURE_DECISION.md:93-104`. The same document describes six implemented runtime-provider entry points/final link, yet leaves generation-specific activation blocked until remaining admission paths and true-cold evidence pass (`src/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/ARCHITECTURE_DECISION.md:108-176`). The parent README still says the four-symbol provider/final link are missing (`src/adapter/framework/appspawn-x/security_specialization/README.md:9-12`); this is documentation drift, so neither stale README nor a historical light-up should be substituted for current build/deployment proof.

## Exact source-change surface that can be inspected

`src/adapter/bundle.json:2-8,14-32` declares a new `oh_adapter` subsystem/component and bridge target with OH dependencies. That declaration alone does not integrate raw APK installation/launch.

The live `apply_appspawnx_routing.py` makes **five** distinct upstream-file changes, despite its header and terminal message claiming four:

| Upstream file | Mechanism | Source implementation |
|---|---|---|
| `base/startup/appspawn/interfaces/innerkits/include/appspawn.h` | `APPSPAWNX_SERVER_NAME` | `src/adapter/appspawn/apply_appspawnx_routing.py:60-70` |
| `base/startup/appspawn/modules/module_engine/include/appspawn_msg.h` | `APPSPAWNX_SOCKET_NAME` | `src/adapter/appspawn/apply_appspawnx_routing.py:72-82` |
| `base/startup/appspawn/interfaces/innerkits/client/appspawn_client.h` | `CLIENT_FOR_APPSPAWNX` enum | `src/adapter/appspawn/apply_appspawnx_routing.py:92-105` |
| `base/startup/appspawn/interfaces/innerkits/client/appspawn_client.c` | enum→socket and service-name→enum mapping | `src/adapter/appspawn/apply_appspawnx_routing.py:107-142` |
| `foundation/ability/ability_runtime/services/appmgr/src/app_spawn_client.cpp` | accept new service name | `src/adapter/appspawn/apply_appspawnx_routing.py:144-161` |

The separate policy script changes `base/security/selinux_adapter/sepolicy/ohos_policy/startup/appspawn/system/file_contexts` (executable, socket, lib/lib64 labels) and `third_party/musl/config/ld-musl-namespace-arm.ini`. The latter is explicitly legacy ARM32, not an ARM64 prescription. Sources: `src/adapter/appspawn/apply_appspawnx_sepolicy_and_namespace.py:22-36,79-102,128-139`.

Historical documentation additionally describes BMS `base_bundle_installer.cpp` and AMS `app_mgr_service_inner.cpp`, `remote_client_manager.{h,cpp}`, `app_spawn_client.cpp` patches. Their cited `src/adapter/ohos_patches/` directory is absent in the inspected current tree; consequently this note identifies them as historical change surfaces, not ready-to-apply local patches. Sources naming the files: `domaindb/usecase/01-包安装与包信息投影.md:65-74`; `domaindb/usecase/02-进程孵化与运行时启动.md:63-65,365`.

Finally, the frozen directory name `oh-appspawn-security-v7` does **not** mean OpenHarmony 7.0 Release: the repository's explicit disambiguation calls it a 6.x commercial snapshot and gives differing file/stage counts. Source: `domaindb/usecase/00-总览与使用指南.md:154-165`. Artifact provenance must use the actual version/release/hash tuple, not that directory name.
