# B9: unlocked v3a deployment and Java manifest fallback

**Current acceptance route (outer #68 override, 2026-09-29):** v3a retains
bridge `84695d62` and uses r8b `d5000c4e` Java manifest fallback. The complete
package is `/Users/zhaoyue/orca/workspaces/westlake-generation-v3a-74d1d6d4-r8b`.
The rebuilt-bridge regression below is a separate unresolved experiment and
does not block this explicitly approved combination. The original native-export
scenario is reported separately; the retained bridge does not gain those exports.

The original bridge `84695d62` omitted both AppSchedulerBridge manifest/property JNI
exports. File identities were enforced independently by the host, child provider
loader and bridge admission, so even an ABI-compatible replacement required a
new host/child generation. This report separates removal of those checks from
application compatibility and screenshot acceptance.

## Evidence so far

Generation `74d1d6d4` uses the #67 SQLite runtime `7e1fd94e` and app-domain loader
`ae848463`. The original R155 ART remains `59e1bb45`; 25 of its 28 provider files
remain byte-identical. The host, child and runtime provider reproduce byte for
byte in two builds. The host dependency audit covers 319 libraries.

- HelloWorld displays its own controls with bridge `22df3988`.
- A single-file change `22df3988 -> 84695d62` passes SHA/maps/single-ART checks;
  HelloWorld PID 31905 displays its own UI and reads bridge SHA `84695d62` through
  its process root. Its hilog contains zero occurrences of the three identity
  rejection strings. Single-file rollback restores `22df3988`.
- With the package's B5 Java JAR `250958dc`, fd-android reports 9 providers and
  OONI Probe reports 4. The previous Koin-not-started/Application-cast errors are
  absent. fd-android reaches an AlarmManager dependency failure; OONI reaches a
  WorkManager initialization failure. Both return to the desktop.
- The authorized r8b Java overlay `d5000c4e` also reports 9/4 providers, but those
  later failures remain. The JAR is the explicit independent variable; child
  process-root hashes and the overlay restoration receipt are retained.
- SQLite `nativeOpen` is registered in the rebuilt runtime. Neither Java cohort
  provides evidence of a **successful invocation**. Do not promote registration
  into an execution claim.
- Initial ZigZag with `22df3988` is white. The same unlocked generation with only
  the bridge changed back to `84695d62` renders ZigZag. This isolates the regression to the replacement bridge; it does not
  identify the responsible source change.

Screens and exact line-numbered log excerpts are under `screens/` and
`evidence/`. `results.json` records each JAR cohort separately. Full continuous
logs, command receipts and process timelines remain at their recorded Mac/VM
paths; full-log SHA values bind the excerpts to those captures. Screenshot
acceptance belongs to the outer reviewer.

## Source implementation

The actual build uses the real-work V1 host/child cohort under
`bms/src/.work/b68-generation`, copied from #67. The tracked generic loader is
V2 and is **not** silently treated as this cohort. The changed V1 files, patches
against #67, and the actual build recipes are in `source/`.

1. Host resolves the child path and checks actual `dlopen`/symbol failures. It
   no longer hashes the child or checks its file build ID. Corresponding child
   service ABI slots remain, but no longer require nonzero SHA/build-ID values.
2. Provider loading preserves paths, load order and ordinary loader errors; its
   file SHA/build-ID callback is removed. Generation/protocol IDs remain as
   interface metadata; they do not reject a different file SHA.
3. Bridge/runtime admission checks ordinary loading and required ABI symbols.
   It neither compares file identities nor emits a `WLUNLOCK` mismatch log.
4. The existing P2-B manifest parser, AXML parser and ARSC resolver are linked
   with the existing minizip/zlib sources. Both JNI symbols are exported. Missing
   required source/zip objects now fail the build with their exact paths.

The old target verifier demanded the now-removed `WLEI_VerifyFileHex` call.
Its topology rule was explicitly updated to reject remaining runtime identity
calls instead. Other ABI/import/export/TLS and strict-link checks remain.
The missing historical tuple receipt exemption remains the previously approved
one; no new missing prerequisite was silently converted to PASS.

The first rebuilt bridge came from the older buildable source snapshot, not a
byte-identical reconstruction of `84695d62`. A same-generation A/B exposed the
ZigZag regression. `window-source-restore.json` identifies the verbatim
real-work `be16148da` OH6.1 window source/header cohort, including the root BLAST/focus path that is
present in the accepted binary. Their patch/source provenance is retained;
there is no additional host/child rebuild for this correction.

## Deployment and one-file replacement

The package manifest is authoritative for deployment identities. The original
Route-A input receipt documents the initial build, not a runtime file seal.
A replacement package must be a separate directory and differ in exactly one
`.so` payload and its live SHA entry. Never edit the active package in place.

```sh
python3 scripts/lab/prepare_generation_replacement.py \
  CURRENT_PACKAGE /system/android/lib64/liboh_adapter_bridge.so NEW_BRIDGE \
  --sha256 EXPECTED_SHA --out NEW_PACKAGE
scripts/lab/deploy_generation.sh SERIAL NEW_PACKAGE \
  --replace /system/android/lib64/liboh_adapter_bridge.so
scripts/lab/deploy_generation.sh SERIAL NEW_PACKAGE \
  --replace /system/android/lib64/liboh_adapter_bridge.so --rollback
```

The deployer validates package SHA before device I/O, preserves the previous
package, records mount intent before binding, checks active/child SHA and maps,
and rolls back only the new file if verification fails. A full rollback unwinds
single-file overlays before removing the generation's owned mounts. Boot and
lock checks remain active. Installer and APK bytes are not changed by this tool.
OONI was absent on 5ea; its original pinned APK was installed for this acceptance
run using the existing installer and the established sandbox preparation.

A real wrong-SHA package was rejected before device I/O; board bridge and host
hashes stayed unchanged. Host tests inject a duplicate-ART maps failure after
binding and prove restoration of only the replaced file. That simulated failure
is distinguished from device observations in `negative-package.json` and
`host-gate-tests.txt`.

## Persistence

Actual build inputs, source and frozen tools are preserved at:

- Mac: `/Users/zhaoyue/orca/workspaces/westlake-b9-v3-source-74d1d6d4/`
- hw248: `/home/alvin/westlake-oh6.1-b9-v3-74d1d6d4-source/`

`source-preservation.json`, `source-link-inputs.json` and the remote SHA receipts
record both archives. The external link archive dereferences the platform
symlinks. The documented SDK aliases map to the same archived compiler/sysroot;
compiler bytes were checked before declaring them interchangeable. Restore the
recorded paths or relocate them consistently in the saved build scripts. The
small window correction and all subsequent report scripts are committed here.

The ARM64 recipe selects `sources/oh61-v7-b2133b5b/framework/window/jni`, not
the generic `framework/window/jni`. Its `.d` files are the evidence for actual
consumed input. Changing only the latter produced an unchanged SHA and was never
deployed. Moving three files alone then failed compilation because adjacent
headers/consumers differed; the selected window cohort is restored as a unit.

## Regression controls and candidate status

Neither `22df3988` nor the window-cohort replacement `bc1d2f77` passes
ZigZag screenshot regression. Copying the complete 27-file real-work window
cohort restored missing exports but did not restore rendering. The earlier
root-BLAST attribution was premature. A further single-file negative control,
`d0f2fda4`, uses the same bridge recipe without `apk_manifest_jni.cpp`; ZigZag
still shows a white window with its process present at both actual t+5/t+20
samples. Thus enabling manifest JNI is not necessary for the regression.
This deliberately incomplete control is never a deployment candidate.

A separate build from the entire canonical real-work framework linked but
failed the existing `FN03_A10_TYPED_RECEIPT_V1` check. The accepted `84695d62`
binary contains that marker. The check was not relaxed, and that build was
not deployed. Current canonical and selected OH6.1 sources are not a verified
reconstruction of the original stage-ack bridge. The original binary was
mounted from `/data/local/tmp/zigzag-research-20260820-stage-ack/`; its complete
matching source recipe has not been recovered. Source-cohort comparison and
post-link evidence are retained in this directory.

The new master batch driver is used directly for the final B5/r8b application
repeats. Its preflight records 16M hilog buffers, privacy off, screen timeout
and clock skew. Early runs used a 256K/private log configuration; absence of
an invocation in those logs is not evidence that it never happened. All
capture/liveness counts are taken verbatim from `facts.txt` or `run_facts.py`.
The dedicated ZigZag control observer imports the same master driver for its
preflight and records actual t+5/t+20 process tables.

## Final 16M application comparison

Both original APKs were reinstalled by the master batch driver using the
unchanged installer. B5 records providers 9/4; r8b also records 9/4 and proves
its Java changes execute: `alarm answered in process (LocalServiceBinders)`,
`bind providers=9 metaData filled=7`, and projected InitializationProvider
metadata. r8b moves OONI's provider failure from NameNotFoundException to an NPE
inside WorkManagerInitializer. Thunderbird still throws an NPE inside
`AndroidAlarmManager.<init>` even after the alarm stub answers. These later
failures are not the original Koin-not-started/Application-cast wall.
Neither cohort proves a successful SQLite nativeOpen invocation. Full logs
contain registration and are retained with hashes; that is a weaker claim.

For **each** B5 and r8b run, the master `facts.txt` says exactly:

```text
fd-android           shots 0/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
ooniprobe            shots 0/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
TOTAL keys=2 screenshots_captured=0/4 alive_t5=0 alive_t20=0
```

`child_hilog=0` here counts PIDs present in the t+5/t+20 process tables; both
apps already exited at those samples. It does not mean their startup logs are
absent: complete 16M startup dumps and hash-bound excerpts record the exceptions.
The JAR overlay was removed in `finally`; shell and parent process-root SHA
readback both returned to B5 `250958dc`. See `final-r8b-overlay-receipt.json`.

B9 lifecycle: six pass, one fail (HelloWorld/ZigZag regression). The initial
swap evidence selector missed the final child maps file and failed; retaining
that actual maps capture corrected the evidence plumbing, not the criterion.
The ZigZag screenshot failure remains unchanged. Known-answer tests: 69 run,
2 skipped, no failures. Host transaction/input gate tests: 6 pass.

## Approved v3a exception

| Object | Strict requirement | Approved disposition | Evidence |
| --- | --- | --- | --- |
| Manifest/property bridge JNI exports | Native symbols present | Retain original 846 bridge; use r8b Java manifest fallback | Explicit outer #68 override in the board and user message, 2026-09-29; final v3a app logs |

No loader/deployment gate is disabled for this exception. The same full package
fixes the unlocked host/child/provider, SQLite runtime, Flutter native loader,
846 bridge and r8b JAR across boards. Its initial 846 replacement package was
created with `prepare_generation_replacement.py`; the final independent copy
contains r8b and updates both payload and live SHA entries. Previous packages
remain intact. `v3a-package-manifest.json` is the delivered file manifest.

## Final v3a acceptance evidence

5ea is resident on the complete v3a package; do not roll it back as part of
this handoff. `v3a/helloworld/final.jpeg` shows HelloWorld controls and
`v3a/zigzag/final.jpeg` shows the ZigZag menu. Inner visual result is own UI;
outer approval remains pending. The child gate proves one route ART and one
route openjdkjvm, bridge 846 and JAR d5000c4e by process-root SHA.

The two target APKs again populate providers 9/4 and remove the original
Koin-not-started/Application-cast walls. Later AlarmManager/WorkManager NPEs
remain, and successful SQLite execution remains unverified. Exact v3a facts:

```text
fd-android           shots 0/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
ooniprobe            shots 0/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
TOTAL keys=2 screenshots_captured=0/4 alive_t5=0 alive_t20=0
```

The original, unchanged B9 contract yields five pass, one pendingreview
(HW/ZigZag), and one fail (native manifest/property exports). This last result
is intentional and retained honestly: the final v3a uses 846, which lacks those
exports. The explicit user/outer #68 override accepts Java fallback instead;
see the exception table above. `lifecycle-v3a.json` is the final raw lifecycle
receipt, while `lifecycle-rebuilt-bridge.json` records the rejected native
bridge route. No spec criteria were edited to manufacture a pass.

Use the same complete package on the other authorized boards after outer
acceptance; no per-board bridge/JAR patching is needed. Package manifest SHA:
`aef124075df8f5caaf9cdcf094d523ea7d806cfd1e2e4fbe3eedfc183c78f525`.
The independent unresolved source/link experiment is in `bridge-regression/`.
