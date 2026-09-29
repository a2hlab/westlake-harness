# B6 / task 50: restore the R155 namespace callback

Task 47's library set passed admission but HelloWorld failed while constructing
its app ClassLoader: the real-work host attempted to reopen `libbionic_compat.so`
inside a namespace whose inherited six-SONAME list did not include it. Expanding
that list was not necessary to reproduce R155. The original host does not perform
that extra reopen at all.

## Read-only comparison

[Namespace comparison](namespace-comparison.json) and the
[R155 host disassembly](r155-host-namespace.disassembly.txt) establish the boundary:

- The original runtime-provider's `CreateConfiguredNamespacesFromStock` forwards
  its arguments to the installed host callback. The implementation resides in
  appspawn-x, rather than in runtime-provider.
- Bridge creation uses `CREATE_INHERIT_DEFAULT` (1); app creation uses
  `LOCAL_NS_PREFERED` (4). Both are separated. Search/permitted paths are forwarded
  unchanged. The bridge uses `/system/android/lib64:/system/lib64/platformsdk`.
- The unchanged R155 native loader shares `libandroid.so`, `libEGL.so`, `liblog.so`,
  `libmediandk.so`, `libz.so`, and `libwestlake_bionic_pthread_bridge.so`.
- R155 ends after `dlns_inherit(app, bridge, shared_sonames)`. It does not promote
  or reopen bionic compatibility in these domains, or request a further Android
  runtime inherit step. Real-work's newer callback added those operations.

The historical source function at real-work commit
`044127fce75b36834543bbbd91267ace103ebc00` implements the R155 sequence. The
[patch](recipes/r155-namespace.patch) replaces only
`StockCreateConfiguredNamespaces` with that function. No search/permitted path,
separation flag, shared-library allowlist, or identity check is relaxed.
After rebuilding, the function is 932 bytes / 233 instructions, matching R155.
[Normalized instruction comparison](function-comparison.json) is exact after
address relocation normalization; it is not a claim that whole host bytes or
all referenced constants are identical.

## Rebuild and deployment gates

Starting from task 47's retained-provider generation, apply the patch to the
real-work staging source and run `recipes/build-generation.sh` through dockbuild
with `B6_REPO_ROOT` and the workspace mount. Its existing source-ledger,
retained-SHA, strict-link, two-build comparison and ABI checks remain enabled.
`recipes/finalize_candidate.py` additionally compares all 28 captured original
providers: 26 are byte-identical; only sigchain and runtime-provider differ.
The separate abort bridge remains unchanged. Manifest, child and host pins are
regenerated. The original ART, native roots, Java JARs and boot images remain.

[Generation receipt](generation-verification.json), [closure](closure.json),
[provider comparison](provider-comparison.json), [negative controls](closure-negatives.json)
and [symbol coverage](sigchain-symbols.json) record the host evidence.
Deployment retains task 47's two-alias TGR fix, mapping both paths to the same
R155 original. Only locked 5ea is used; any failed candidate is rolled back as a
complete seven-mount generation and followed by B5 control screenshots.


## Board result: blocked at native VSync initialization

Generation `e59e70fe0ce0` ran with host `02c611c8`, child `587e7a85`,
runtime-provider `8d109259`, original ART `59e1bb45`, and musl sigchain `6d5d5538`.
The [live hash receipt](trial/helloworld/child-proof-5193.late-sha256) and
[map excerpt](trial/helloworld/child-proof-5193.late-maps-excerpt.txt) bind the
observation to child PID 5193, rather than merely to staged files.

[Hilog](trial/helloworld/hilog-excerpt.txt) records `WLCGATE:HSPM:PASS_IDENTITY`,
A06/A02 causes 0, and `MainActivity.onCreate()` at 10:43:57.600. The former
classloader namespace error is absent. At 10:43:57.685 the app requests its first
observed VSync; at 10:43:57.687 it faults with `SIGSEGV(SEGV_ACCERR)` and PC
`0x29dcc`. The [fault stack](trial/helloworld/fault-cppcrash-5193-1790649837687-excerpt.txt)
places the boundary in `do_init_fini`, called by `RsFrameReportExt::Init`, through
`VSyncReceiver::RequestNextVSync`, `OH_NativeVSync_RequestFrame`, and
`DER_nativeScheduleVsync`. The underlying invalid initialization target has not
been attributed to a particular library or source defect.

The [candidate final image](trial/helloworld/final.jpeg) shows the desktop, not
HelloWorld. Therefore this is **blocked**, with zero lighting gain. The ordered
control gate stopped here: Wikipedia, implicit NPE delivery, and candidate
ZigZag were not attempted. This non-null native fault does not establish an
implicit-null-check verdict; `null_check_mode` stays `unverified`.

All seven bind mounts were removed; the deployment rollback asserted all ten
pre-deployment identity hashes. The [readback](rollback/identity-after.txt)
confirms B5 host `1f6cf53b`, child `0976dee8`, and runtime JAR `250958dc`.
[HelloWorld](rollback/helloworld/final.jpeg), PID 9392, and
[ZigZag](rollback/zigzag/final.jpeg), PID 10417, show their own UI after rollback;
both records have zero new faults. These are agent visual observations; outer
image acceptance remains pending. Board 5ea was unlocked after these controls.

Raw VM evidence remains under `$VM_HOME/a2hlab/board/b6-task50-hello-5ea-r1`
and `b6-task50-rollback-5ea-r1`; per-file hashes and local evidence locations are
recorded in each `raw-evidence.json`. Build outputs remain private under
`$REPO/bms/src/.work/b6-task50`; task 47 supplies the retained-source recipe and
this task adds the narrowly scoped namespace source patch. No library binaries
or large raw logs are committed. `generation-verification.json` is the host-stage
receipt (its deployment flag predates the trial); `deployment.json` and
`results.json` record the completed deployment and rollback.

The known-answer suite ran 69 tests with 2 skipped and no failures. Host closure
checks passed 6/6; the four missing-sigchain-symbol controls also rejected their
mutated inputs. R2: build, identity, namespace progress and rollback are verified;
the VSync cause is partial; Wikipedia/NPE and candidate ZigZag remain unverified.

The regenerated [source ledger](SOURCE_CLOSURE.json) and [sealed input manifest](ROUTE_A_INPUTS.json) preserve exact input bytes and hashes. The generation manifest SHA matches `e59e70fe0ce0…`. See [lifecycle](lifecycle.json) and [explain](explain.md): 4 pass / 4 fail. Caller attribution, artifact mismatch rejection, live identity and sigchain symbol coverage pass; Wikipedia UI, candidate regression, Wikipedia next-wall and NPE criteria fail. A HelloWorld next wall does not satisfy the Wikipedia next-wall scenario.
