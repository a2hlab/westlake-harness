# Generation v2: SQLite JNI and Flutter permitted paths (#67)

The accepted 6cb40cd6 runtime `9ccf64f8` exported four SQLite registrars as weak
zero-return functions. Its app loader admitted absolute loads only below the
search path, although the same class-loader domain already declared permitted
paths. The build now links the existing SQLite JNI implementation and tests both
search and permitted roots with `realpath` and a directory-component boundary.

## Build evidence

- Final runtime: `7e1fd94e`, two complete builds byte-identical. SQLiteConnection,
  SQLiteGlobal, SQLiteDebug and CursorWindow registrations are strong functions.
  The existing SQLite 3.39.2 amalgamation, local CursorWindow engine and memfd
  adapter are compiled in; no new provider library is added for SQLite.
- App loader: `ae848463`, two builds byte-identical. Its existing host suite plus
  permitted-root/symlink tests passes 136 checks. Running the new test against
  the original source fails exactly the permitted-root positive check.
- Generation: `15728be5`; host `42804330`, child `ecb3ebf6`, provider `af0c661f`.
  Host/provider/child each have two identical builds. Sealed verification and
  host ABI checks pass; SHA admission remains enabled.
- Host NEEDED closure: 319 libraries, 2830 edges. Missing-file, missing-platform,
  wrong-SHA and wrong-SONAME negative controls pass. All five changed ELF roles
  retain the original ordered dynamic dependencies; the child's `b dlopen`
  tail call is preserved. ART `59e1bb45`, sigchain `6d5d5538`, bridge `84695d62`
  and the B5 JAR are unchanged. 25 of the 28 original R155 provider files remain
  byte-identical; relative to 6cb only loader/provider change in that pool.

The first offline runtime build accidentally included later AudioTrack and
TLS/ICU extensions from the current source cohort. It added `libohaudio` and
registration strings absent from `9ccf64f8`; **it was never deployed**. The
existing pre-extension source copy restores six files before adding SQLite.
`baseline-runtime-source-restoration.json` records exact source hashes, and
`source/android-runtime/` preserves those selected files. This restores the
baseline registry rather than skipping an existing registration after failure.

Inherited limitations remain explicit: the existing SQLite Android shim uses
byte/code-unit localized collations, lacks Android telephony SQL extensions,
and rejects cross-process CursorWindow Parcel marshaling. The existing memfd
adapter's `ashmem_set_prot_region` is a no-op. This task restores real local SQL
operations and JNI registration; it does not claim complete Android database
or ashmem compatibility.

## Deployment

Package: `/Users/zhaoyue/orca/workspaces/westlake-generation-v2-15728be5`.
The v1 package remains intact for rollback/reference. Use the updated repository
entry point or this package's `tools/deploy_generation.sh`:

```sh
scripts/lab/deploy_generation.sh <full-serial> <v2-package> --dry-run
# First hold board_note.sh lock as your assigned lane.
scripts/lab/deploy_generation.sh <full-serial> <v2-package> --lane <lane>
# Explicit rollback, if required:
scripts/lab/deploy_generation.sh <full-serial> <v2-package> --lane <lane> --rollback
```

There are 15 mounts. Compared with v1, the app-loader system alias is bound to
the same sealed route file too. The package changes six payload files (counting
the two loader copies). Installer bytes and APK originals are untouched by
runtime deployment. The B5 JAR `250958dc` is restored by the package, so agents
using newer Java overlays must reapply them after the generation switch.
State now includes generation as well as serial/boot; v2 rollback restores the
previous 6cb generation. The deployer can read legacy v1 state, and re-entry
finds the live parent by identity rather than assuming the saved PID survived a
service restart. Reboot replay remains the same one-command procedure.

## Board evidence and review

Only 5ea is assigned to this task. Baseline fd-libre PID 6377 reproduced
`path is outside app domain` for its own `app_lib/libflutter.so` (hilog lines
12548 onward). Thunderbird was absent and was installed from the unchanged
pinned fd-android APK; BMS readback UID is 20010079. Its first batch capture did
not retain early exception lines, so it is not claimed as a SQLite A/B proof.
Fresh post-deployment observations, screenshots and the exact remaining wall
are recorded in `results.json`. Screenshots require outer visual sign-off.

### Fresh 5ea outcome

HelloWorld (PID 9487) and ZigZag (PID 13553) show their own UI. Both target
apps return to the desktop, with no new native fault files. Screens are in
`screens/`; inner visual readings are not outer sign-off.

- **Flutter path wall crossed:** fd-libre PID 12442 no longer reports `path is
  outside app domain`; it now reaches the next gate and throws `current thread
  is not READY for guest dlopen` (hilog 12794, 12841). The same-board 6cb baseline
  PID 6377 reports the original path rejection. This proves the permitted-path
  change is effective, not successful Flutter loading or rendering. The thread
  READY gate is retained.
- **SQLite target-app execution remains unverified:** PID 11325 binds the exact
  `SQLiteConnection::nativeOpen(Ljava/lang/String;ILjava/lang/String;ZZII)J`
  method to runtime 7e1fd94e (hilog 1854), then returns from bindApplication and
  fails activity launch with `KoinApplication has not been started` (14834).
  No observed nativeOpen execution is claimed. B5's `nativeParseManifestJson`
  is unresolved (4076), so application metadata/bootstrap is an earlier
  prerequisite. The separate cc-t3 r7b / 6cb result on 5cd has the same Koin
  exception. Following the outer instruction, the exact r7b c432d987 is also
  tested temporarily on both 5ea generations; each overlay is removed and
  the B5 hash reread immediately afterward. See the same-JAR comparison below.

The generation passes host and regression gates, but #67 requires a target app
past SQLite, not merely a strong registrar. Keep that gate **unverified** until
the existing Java/application prerequisite is resolved. The v2 transaction was
rolled back as a whole to resident 6cb40cd6; the v2 package is a built candidate,
not the new accepted three-board baseline. No APK was modified and no installer
was replaced. `rollback-console.txt` and the restored baseline evidence record
this explicitly.

`lifecycle-b6.json` reports 5 pass / 1 pending review / 2 fail;
`lifecycle-b7.json` reports 3 pass / 2 fail. These unmodified selectors read the
previous B6/B7 reports. They are kept as requested and do not certify this new
candidate. The first invocation inherited a Linux `cc` wrapper from env-mac;
setting `CARGO_TARGET_AARCH64_APPLE_DARWIN_LINKER=/usr/bin/cc` fixed that local
link-tool selection, after which every selector ran.

### Same-JAR comparison requested by the outer loop

The exact r7b JAR `c432d987` (built on B5 `250958dc`, not the older r4) was
bound temporarily on 5ea twice. 6cb PID **22789** and v2 PID **27196** both throw
`KoinApplication has not been started`; neither run proves SQLite nativeOpen
execution. Both runs have continuous logs, process-root JAR hashes and screenshots.
Each overlay was cold-stopped and unmounted immediately, with B5 `250958dc`
verified in shell and parent process root. The package still contains B5.

`evidence/b67-v{1,2}-r7b-sqlite-5ea/` retains the receipts and numbered excerpts;
`results.json.sqlite_same_jar_comparison` pins both full raw log hashes. This
is an earlier Java/Application prerequisite shared by both generations, not a
new v2 regression. Inspection also finds that bridge `84695d62` has no dynamic
export named `Java_adapter_activity_AppSchedulerBridge_nativeParseManifestJson`
(`bridge-exports.txt`); the source implementation is in
`bms/src/adapter/framework/package-manager/jni/apk_manifest_jni.cpp`. Connecting
that metadata/bootstrap prerequisite is a follow-up, not a claimed SQLite pass.
