# B6: caller identified; candidate rejected; signal dispatch order established

**Blocked, R2 partially, +0 LIT.** The earlier assumption that any same-version
boot rebuild could carry a one-method Context fix was wrong. Although every
candidate OAT was version 230 and the child loaded the expected hashes, rebuilding
all 27 files changed core AOT behavior: Wikipedia crashed in
`InflaterInputStream.read`, and HelloWorld regressed in `Proxy.getMethods`.
Neither proves execution of the new Context guard. Both B6 bind mounts were
removed. The original framework/boot cohort and accepted B5 runtime remain active.
Do not count the earlier crash as `advanced`, or deploy the rejected candidate.

## Evidence and outcome

| Experiment | Evidence | Result |
| --- | --- | --- |
| Original APK on Android reference | [welcome screenshot](android-reference/final.png), [receipt](android-reference/record.json) | Desktop click, 15 s, PID 18995, Wikipedia own UI |
| B6 whole-cohort Wikipedia | [final](evidence/rejected-full-cohort/wikipedia/final.jpeg), child SHA and fault excerpts alongside | Exited to OH desktop, PID 6826, earlier core crash |
| B6 whole-cohort HelloWorld | [final](evidence/rejected-full-cohort/helloworld/final.jpeg), fault excerpt alongside | Regression, PID 7902, `Proxy.getMethods` SIGSEGV |
| Rollback HelloWorld | [final](evidence/rollback-baseline/helloworld/final.jpeg) | Desktop click +15 s, PID 16537, Hello World own UI |
| Rollback ZigZag | [final](evidence/rollback-baseline/zigzag/final.jpeg) | Desktop click +15 s, PID 17566, ZIGZAG own UI |

These visual descriptions are developer observations, not outer acceptance.
The rollback checks are desktop observations, not the contract's final-fix
`quick` gate. The derived HelloWorld quick wrapper refused the mandated VM→Mac
transport before doing board work (`SSH/mac-server execution is forbidden`).
ZigZag quick was not run: no surviving B6 candidate existed. The failed quick
attempt and exact-pin wrapper provenance are retained; no upstream check was removed.

## Java caller and attempted fix

[Original APK smali](caller/AppCompatActivity-attachBaseContext.smali.txt) identifies
`androidx.appcompat.app.AppCompatActivity.attachBaseContext(Context)`:
line 1655 calls `Context.getTheme`, line 1662 catches NPE, and only line 1688 calls
`super.attachBaseContext`. The delegate logic is R8-inlined. MainActivity,
SingleFragmentActivity and BaseActivity do not override this method; see
[inheritance and source hashes](caller/inheritance.json).

The unattached Activity's `ContextWrapper.mBase` is null. ContextImpl's theme
initialization reads the outer Activity's ApplicationInfo. Stock ART should
turn that compiled null access into an NPE caught by AppCompat. This runtime
instead produced the B5 native fault at `ContextWrapper.getApplicationInfo+44`.
The original APK SHA remains `eba82a0f…fc77101f`; no APK was modified.

Searches of the local adapter, 00.Workspace main/worktrees and hanbin found no
specific Context/Theme fix. Instrumentation.newActivity lacks the new base
Context, while callActivityOnCreate is too late; no narrow runtime-JAR-only
seam was established. The experimental source patch explicitly throws NPE when
`mBase` is null, preserving the Java contract. The tested JAR was assembled by
transcribing this one-method guard into the baseline DEX; it was not javac-built
from the full framework. Re-disassembly found one semantic class change; 17
other classes only changed omitted default static-field encodings. The source
patch's hunk counts were subsequently corrected without changing Java/smali;
[source dry-run receipt](source-patch-check.json) records both hashes.
**The guard's device execution remains unverified.**

## Build, identity and rollback

[identity.json](identity.json) pins the real child namespace: framework OAT 230,
route-a libart SHA `59e1bb45…d0fe5f`, containing `oat\n230\0`, not 247. The
Westlake host dex2oat247 was therefore not used. Recovered hanbin dex2oat64 SHA
`7382bb5a…6f82` emits 230; Rosetta still requires `LD_PRELOAD=libmap32bit.so`.
The first no-preload probe crashed; its raw VM location/hash is indexed.

[build-framework.json](build-framework.json), [build-boot.json](build-boot.json)
and [deployment.json](deployment.json) record inputs, commands and all 27 output
hashes. Only 5ea was touched. The parent had no ART mapping, so each fresh child
loaded the overlay; PID 6826's `/proc/<pid>/root` SHA evidence matches framework
`3ec6e1b5…e14fae`, boot-framework OAT `76b03de3…46db6a`, B5 runtime
`250958dc…d3146`. Matching versions and hashes did not establish compatibility.

The extension-only attempt first had an extra `arm64` path component. With that
corrected, ART rejected the original image with **“received 9, expected non-zero
and <= 7”**. It is one nine-component image, not a reusable seven-component
prefix. Both offline failures are retained. No malformed extension was deployed.

[rollback-first.json](rollback-first.json) verifies restored framework
`3e106350…dde9af` and boot-framework OAT `0ff275fa…2d7c0`, retaining B5 runtime.
No reboot, installer change, or signal-handler change was made. Raw logs remain
under VM `/home/zhaoyue/a2hlab/board/`; [evidence-index.json](evidence-index.json)
records 98 files and hashes. Large binaries, raw logs and unrelated Android
launcher inventories are not committed.

## Read-only signal investigation (7 minutes, limit 30)

`results.json.null_check_root` separates observations from inference:

1. Captured child hilog contains no explicit FaultManager initialization line.
   This is not evidence that FaultManager was never initialized.
2. At **19:07:35.276**, PID 27515 dispatches musl **special slot 3** to address
   `0x7f95347e78`, inside OH `libdfx_signalhandler.z.so`. DFX dumps the crash.
   At **19:07:35.946**, the same PID dispatches its **user action** to
   `0x7f11f826a0`. Maps plus matching-library symbols identify this exactly as
   AOSP `art::SignalChain::Handler`: load bias `0x7f11f80000` + symbol `0x26a0`.
   Thus DFX gets this fault **670 ms before** the ART chain.
3. OH 6.1 source installs DFX in a constructor with
   `add_special_handler_at_last`; musl always executes special actions before
   user actions. Source therefore suggests DFX is installed first and ART later
   occupies the user action, but exact installation timestamps were not traced.
   The demonstrated issue is **dispatch priority between two signal registries**,
   not proof of a last-installer-wins overwrite.
4. bms and 00.Workspace retain a comment saying `-Xno-sig-chain` was removed.
   A legacy dedicated-worker SIG_DFL reclaimer exists, but its main.cpp fallback
   is labeled unreachable; no evidence ties it to the route-a child.
5. Existing reuse leads: repository
   `bms/src/adapter/aosp_patches/art/sigchainlib/sigchain_muslcompat.cc`, plus
   hanbin `doc/design/compat/retired/art_sigchain_oh_musl_bridge_design.html`.
   The former forwards ART handlers into OH musl's special registry; the latter
   reports an older ARM32 bridge experiment and a libc-name rebuild hazard.
   Neither is proof of current ARM64 success. Current loaded libsigchain SHA
   `ea7becd0…3865ba2` exports AOSP Handler and has no OH bridge imports.

Evidence: [signal log](null-check-root/b5-wikipedia-signal-hilog.txt),
[maps](null-check-root/b5-handler-maps.txt), [symbols](null-check-root/sigchain-symbols.txt),
[live hash](null-check-root/signal-identity.json), OH source excerpts and source
hashes in the same folder. The OH source snapshot is supporting evidence,
not a claimed byte-exact source build of the board's logging variant.
**No signal code was modified or deployed; no policy refusal occurred.**

## Contract gates

[lifecycle.json](lifecycle.json): 3 passed / 3 failed, no skipped or pending review.
Caller, artifact-mismatch negative and null-check-mode pass. Wikipedia LIT,
final-fix regressions and advancement fail. [Negative results](negative-results.json)
reject three individual SHA substitutions, a real rollback proof, and a dead
child; all rejected cases add zero LIT. Known-answer suite: 69 tests, 2 skipped.

The next assigned owner can evaluate the existing signal bridge against this
exact route-a generation without requiring a framework boot rebuild. This
report does not authorize or claim that deployment.
