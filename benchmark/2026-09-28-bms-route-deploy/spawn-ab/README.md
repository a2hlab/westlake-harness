# Same-boot HelloWorld / Wikipedia launch divergence

**Wikipedia forks, then fails stock sandbox setup before entering the Android runtime.** The earlier inference from `observed_pids: []` was too strong: it meant no target-UID process remained at the late observation, not that no child was created. The missing preparation is the app sandbox directory tree that the accepted restore scripts explicitly create after `bm install`.

The outer reviewer classified the preceding #23 sweep as **0/62 LIT**: white starting windows followed by the OH desktop. This A/B establishes the cause for Wikipedia only; it does not assign that cause to all 62 apps or claim that preparing directories alone will make Wikipedia render.

## Direct evidence

Board `5ea34a4500000000000000001123012c`, boot `56e521b3-858f-4fbf-8e35-daec29525c93`, parent AppSpawnX PID 13161. The four runtime hashes (appspawn-x, child library, adapter JAR and Android runtime) match before/after. Both trials used the same boot and runtime, sequential cold starts and exact SceneBoard icon IDs. No install, reboot, runtime replacement or directory repair occurred.

| Stage | HelloWorld | Wikipedia |
|---|---|---|
| BMS | bundleType 10, UID 20010055, MainActivity | bundleType 10, UID 20010057, DefaultIcon alias |
| AMS / AppMS | Routes to AppSpawnX | Routes to AppSpawnX at 18:30:07.840 |
| Request received | Parent 13161 receives request 26 | Parent 13161 receives request 27 at .841 |
| Child | PID 25183 at 18:29:34.115 | PID 26163 at 18:30:07.844 |
| Sandbox | Completes mandatory mounts; optional missing directories produce nonfatal warnings | ENOENT for el2/base and el2/log; **fatal required el1/database mount** at .856 |
| Reply | result 0; RAC/LSP/provider admission passes | `Execute hook [31] result 218103816`; reply `0xd000008` at .858 |
| Runtime | Provider load and `ActivityThread.main()` observed | No WLCGATE admission or Android runtime entry observed in this window |
| Termination | Still alive after capture | SIGCHLD at .866; parent reports exit code 0, not a fatal-signal crash |
| UI | Actual HelloWorld UI, CREATED/RESUMED | Returns to OH desktop |
| Target UID samples | 87 samples across 15.93 s, PID 25183 seen | 89 samples across 15.88 s, no target-UID PID sampled |
| New fault files | 0 | 0 |

The Wikipedia child is visible in hilog for approximately 22 ms (.844–.866). Sampling had maximum gaps of 220/210 ms and filtered by BMS UID; either short duration or failure before UID transition can explain why polling missed it. The logs establish child creation and controlled initialization failure. They do not establish a separate child `exec` syscall, nor is a native crash backtrace present.

Read [HelloWorld raw-line excerpt](helloworld-hilog-excerpt.txt) and [Wikipedia raw-line excerpt](wikipedia-hilog-excerpt.txt); line numbers refer to [full HelloWorld hilog](evidence/helloworld/hilog.txt) and [full Wikipedia hilog](evidence/wikipedia/hilog.txt). `Child process:... success pid:...` is misleading when followed by nonzero `result`; the subsequent AMS `NotifyStartProcessFailed` and exit record resolve the outcome.

| Trial | Early screenshot | Final screenshot | Raw process samples |
|---|---|---|---|
| HelloWorld | [t+1](evidence/helloworld/t1.jpeg) | [final](evidence/helloworld/final.jpeg) | [timeline](evidence/helloworld/timeline.txt) |
| Wikipedia | [t+1](evidence/wikipedia/t1.jpeg) | [final](evidence/wikipedia/final.jpeg) | [timeline](evidence/wikipedia/timeline.txt) |

cx-t0 read both final images: HelloWorld renders its buttons and lifecycle text; Wikipedia shows the desktop. Independent review remains pending. The archived full hilogs redact only unrelated SSID/BSSID fields; [raw hashes and VM locations](evidence/redactions.json) retain original provenance and line numbering is unchanged. Raw `hilog -r` output, fault inventories before/after, BMS dumps, process maps and mountinfo are retained under [evidence](evidence/). Snapshots follow a one-second and fourteen-second wait with capture overhead; they are not exact millisecond-aligned frames.

## Installed payload versus sandbox

`/data/app/android/<pkg>` is absent for **both** apps and is not the differentiator. BMS reports the real APK path as `/data/app/el1/bundle/public/<pkg>/android/base.apk`. Both have that APK and a generated `entry.hap`, with original APK hashes intact.

The [Wikipedia path readback](evidence/readback/org.wikipedia-paths.txt) shows all ten restore-created sandbox roots absent. The [HelloWorld readback](evidence/readback/com.example.helloworld-paths.txt) shows them present:

- `el1/100/{base,database}/<pkg>`
- `el2/100/{base,database,sharefiles,log}/<pkg>`
- `el3/100/{base,database}/<pkg>`
- `el4/100/{base,database}/<pkg>`

HelloWorld base/share roots have mode 0700; database/log roots have 0770. App roots belong to its BMS UID/GID and `appdat` label; log belongs to UID:log with `data_app_el2_file`. Restore also creates cache, code_cache, databases, files, haps, no_backup, preferences, shared_prefs and temp under el2/base. The original restore explicitly uses `find ... -exec chcon` after documenting unreliable recursive `chcon` behavior.

The [live sandbox configuration](evidence/readback/parent-runtime-and-sandbox.txt) sets `check-action-status: true` for el1/database, whereas el2/base and el2/log are optional checks. This explains the first fatal divergence precisely: not every ENOENT is fatal, and HelloWorld itself has unrelated optional-directory warnings. Its [child mountinfo](evidence/helloworld/child-25183-mountinfo.txt) confirms the successful private namespace. Wikipedia dies during namespace construction; no surviving child mountinfo was available.

## What restore does beyond bm install

[Source hashes and excerpt ranges](source-provenance.json) pin the actual cloned recipes. They are read-only evidence, not a new deployment performed during A/B.

| Preparation | HelloWorld restore | ZigZag accepted recipe | Batch #23 |
|---|---|---|---|
| Global host/runtime | Deploys the fixed PR03 Android payload, route provider, child, AppSpawnX, sandbox config and host libraries; sets file modes/labels, init recovery, platform parameters and socket readiness | Activates the accepted candidate with global library/JAR overlays | Reuses that accepted baseline |
| APK | Checks fixed original SHA; uninstall/install; reads bundleType and UID back | Checks fixed candidate APK SHA; install/readback | Installs original input and reads BMS back |
| Per-app sandbox | Explicit ten-root creation, subdirectories, ownership, permissions and labels | Calls `prepare_sandbox(bundle, uid)` after install, and for HelloWorld validation | **Missing** |
| Per-app native payload | No extra app-native overlay shown in this HelloWorld restore | Overlays accepted ZigZag native libraries plus media/signal support | None |
| PNF / per-app runtime descriptor | No explicit PNF build or per-app descriptor generation step in the inspected restore | No explicit PNF build in the inspected device recipe; uses pinned candidate manifest/runtime paths | Not demonstrated as the first blocker |
| Signing | Uses the fixed hashed APK; the restore does not call a re-signing step | Uses its already accepted fixed APK | Preserves original APK bytes |

The live failure precedes provider admission. Consequently, this experiment supplies no evidence that a missing PNF package, signing step, or runtime path descriptor caused Wikipedia's current failure. Global runtime provisioning is already shared and HelloWorld passes it. Fixing the sandbox preparation would be the smallest next intervention, followed by a fresh launch trace; it is not performed or claimed successful here.

## Template desktop labels

The [installed HAP resource audit](evidence/resource-labels.json) finds identical `resources.index` SHA `3e9702180cbb930ba39c9e21ca82ee3af7e48d9a884e3ae8f445ff6a54504c79` in HelloWorld and Wikipedia, with `Hello World` at offsets 218 and 359 and no `Wikipedia` string. Their module JSON hashes also match. The screenshot confirms the Wikipedia W icon labeled Hello World. This is a template-resource defect separate from the earlier fatal sandbox setup.

## Validation and scope

[results.json](results.json) contains timing and outcome facts; [manifest.json](manifest.json) pins all small archived evidence. The evidence checker validates exact board/boot, unchanged runtime hashes, both 15-second sample windows, fault inventories, launch records and hashes. [lifecycle.json](lifecycle.json): evidence scenario `pass`, interpretation scenario `pendingreview` (1 pass, 0 fail, 1 pending review). Repository tests: 69 run, 67 passed, 2 skipped. Causal/visual interpretation stays under human review.

R2: **partially** overall. The Wikipedia sandbox failure, short-lived child and missing restore preparation are directly evidenced. The exact 62-app generalization, post-repair Wikipedia UI, long-term stability and syscall-level `exec` behavior remain unverified. Only 5ea was written, solely for cold launch and observation; 61b and 5cd were untouched. No push.
