# Task 58 follow-up: preserve R155 dlopen caller namespace

The previous static review treated the wrapper local-array/code-shape difference as harmless. That was wrong: R155 ends `WLSCPL_OpenPreparedNamespace` with **b dlopen**, while task58 used **bl dlopen**. OH musl passes its caller return address to `dlopen_impl`; a real call presents the default-namespace child plugin, while the tail call preserves the sealed NativeLoader caller. The 26 original providers and ordered NEEDED lists were already correct; changing a library filename would not restore this call boundary.

The only functional source edit changes the prefix from an automatic array to a static constant, restoring R155's emitted tail call. All canonical/prefix/flag checks remain. The locked build regenerates manifest, child and host identities normally. `loader-tail-call.patch` and the final loader source retain the edit; the remaining source snapshot and recipe provenance are in `../task58/`. No namespace access or artifact verification is relaxed.

## Offline gates

The final instruction gate requires **b dlopen** and rejects the previous **bl dlopen** artifact as a negative control. Host/child/provider dynamic tags match the previous R155-aligned lists. All three reproduce twice; 26 R155 providers retain original bytes; the explicit closure has 319 libraries / 2830 NEEDED edges. Six closure controls (one positive, five negative), four missing-sigchain-export controls and the V1 host tests pass. `static-dispositions.json` records this focused correction to the prior full static inventory.

## Device gate and recovery

The hub lost power after generation **6cb40cd6** was activated, before any app launch. The user restored power; the board returned on boot **e36781a9-2ba1-4804-b8e5-2a1125c39a47**. The fixed HelloWorld `check` passed the auto-restored PR03 profile. Exact saved R155/B5 system mounts, JAR **250958dc** and five ZigZag native mounts were restored and read back. Installer **675536e8** remained intact in both paths and the foundation process root. B5 HelloWorld PID **7660** showed its own UI before candidate reactivation. Board epoch was near 1970 after power loss; it was synchronized and read back before candidate tests (`clock-sync.json`).

Candidate host **b7205719**, child **03aa6216**, runtime-provider **3aa5d169** passed live identity in HelloWorld PID **11055**. [Its final maps](trial-hello/helloworld/child-11055-maps.txt) have exactly **one ART instance** and **one libopenjdkjvm**, both in the new route-a directory. `libjavacore.so` and `libopenjdk.so` retain the system paths seen in R155. The [mapping gate](live-mapping-gate.json) counts offset-zero mappings, not just unique filenames; original R155 maps pass and the prior double-ART fault maps fail its controls.

[Candidate HelloWorld](trial-hello/helloworld/final.jpeg) and [candidate ZigZag](trial-zigzag/zigzag/final.jpeg) display their own UI (PIDs **11055**, **18672**), with no new fault records. This is a desktop cold-start/screenshot regression probe; the fixed-hash upstream `quick` wrapper was not run against the custom generation. Outer visual sign-off remains pending.

## Wikipedia: advanced, not lit

Wikipedia ran twice (PIDs **13213**, **16802**). Both times the SIGSEGV handler in **slot 0** resolved to original ART **+0x417210** and **returned directly**, with no DFX dispatch or new faultlog. Execution passed the old attach boundary and completed **performCreate**, then called **finishActivity → TerminateAbility(rc=0) → System.exit(0)**. The [final screenshot](trial-wikipedia-debug/wikipedia/final.jpeg) is the desktop. See [original numbered log lines](wikipedia-next-wall.txt).

BMS `QueryAbilityInfos/readParcelableInfo` errors precede the finish, but their causal role and the caller that decides to exit are not established. The expected caught NPE is supported indirectly by ART consuming SIGSEGV and the activity reaching creation; the capture contains neither the typed caught exception nor its fault PC. Consequently **null_check_mode remains unverified**, rather than promoting this inference to direct NPE proof. SIGBUS registration/dispatch is also unverified.

The second Wikipedia run temporarily disabled hilog's privacy formatter to read diagnostic messages and restored it to **true** in `finally` (`debug-log-settings.json`). One pre-launch attempt stopped on a transient empty target listing; no app was clicked, boot/lock were rechecked, and the new run ID preserves that stop. Public excerpts omit repetitive class-linker diagnostics; full raw files and SHA manifests remain in the recorded VM directories.

## Final state and validation

All seven candidate mounts have been rolled back and their original hashes read back. [B5 HelloWorld](rollback/helloworld/final.jpeg), PID **22270**, and [B5 ZigZag](rollback/zigzag/final.jpeg), PID **23450**, both display their own UI with no new fault records. Installer **675536e8** remains unchanged. The 5ea lock is released. No provider or native-root bytes were changed in place.

Known-answer suite: **69 tests, 2 skipped, 0 failures**. Lifecycle: **5 pass / 1 pendingreview / 2 fail**. Caller, next-wall recording, artifact rejection, identity and symbol coverage pass; HelloWorld/ZigZag visual regression awaits review; Wikipedia lighting and directly demonstrated NPE fail. Status is **advanced**, lighting delta **0**, with the next exit behavior recorded for a separate task.
