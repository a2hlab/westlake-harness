# B6 #33: musl bridge builds; sealed native identity rejects a one-file swap

**Blocked, R2 partially, +0 LIT. No policy refusal occurred.** The assumption that
route-a libsigchain could be replaced like the B5 runtime JAR was false. Native
artifacts are identity-checked before ART starts. A one-file overlay made both
Wikipedia and HelloWorld exit with code 123 at `FAIL_SEALED_PROVIDER`; it did not
reach the signal bridge. The overlay was removed, and the original B5 baseline
again renders HelloWorld and ZigZag. Framework, boot images, APKs, installer and
identity validators were unchanged.

## Build and symbol gate

The original `bms/src/adapter/build/inner/compile_sigchain_muslcompat.sh` compiled
production `sigchain_muslcompat.cc` without `--probe`, using `dockbuild.sh`,
`a2hlab-build:24.04`, and the locked OH SDK clang++/sysroot under
`/home/dspfac/a2hlab/source-closure/verify/toolchains/ohos-sdk/native`.
Source commit: `a115654434001a1575c70daa46086a46d3150005`. Source SHA and binary
hashes are recorded in [symbol-gate.json](symbol-gate.json); the binary is not
committed. Build output is at `bms/src/adapter/out/aosp_lib_arm64/libsigchain.so`.
New SHA: `0084775af8a47de3272170599726686b696ccd8b6c3efd0ea81854494d98f8f4`.
The only compiler warning was an unused constant. No diagnostic/probe exports
were present.

The source comments and production implementation were read. The referenced
`_codex_handoff/yue_refs/oh_musl_faulthandler_investigation.md` was not found under
the searched 00.Workspace/main and six worktree handoff directories. The related
hanbin historical bridge report and provenance were already retained in #31.

The old export/libart-import intersection contains **five** names. A static
intersection alone would incorrectly require new libsigchain to export
`sigaction`. Read-only inspection of live PID 17566's five relocated slots proved:

| Symbol | Actual binding owner | New bridge export |
| --- | --- | --- |
| AddSpecialSignalHandlerFn | route-a libsigchain | yes |
| RemoveSpecialSignalHandlerFn | route-a libsigchain | yes |
| EnsureFrontOfChain | route-a libsigchain | yes |
| SkipAddSignalHandler | route-a libsigchain | yes |
| sigaction | OH `/system/lib/ld-musl-aarch64.so.1` | supplied by musl, not a libsigchain dependency |

[bindings.json](bindings.json) includes raw slot values, owner maps and exact
libart/old-libsigchain hashes. The reader does not write process memory. Its
initial attempt selected a full-file read-only mmap, yielding invalid zeros;
the corrected attempt derives load bias from the executable PT_LOAD and all
five slots resolve into executable DSOs. Earlier failed attempts remain in VM
`b6-sigchain-binding-5ea` and `...-v2`; accepted evidence is `...-v3`.

All **4/4 actual libsigchain-owned imports** are covered. Removing each one from
the parsed export manifest makes the same deployment predicate reject it; see
[negative-symbols.json](negative-symbols.json). This is an offline symbol-manifest
negative, not a deployment of a defective binary. The source's intentional musl
`add_special_signal_handler` / `remove_special_signal_handler` imports are present.

## Device result and root cause

5ea was locked; before deployment the original library, libart, framework, boot
OAT and B5 runtime hashes were verified. Parent 13161 mapped neither libart nor
libsigchain, so no restart was required. One reversible bind mount over the
route-a libsigchain path was staged and its global SHA verified. See
[deployment.json](deployment.json), [deploy.py](deploy.py), [rollback.py](rollback.py).

Both apps were cold-stopped and launched from their desktop icons with 15-second
screenshots:

| Attempt | Child | Raw result | Screenshot |
| --- | --- | --- | --- |
| Wikipedia candidate | 7493 | LOAD_ERROR:8, VALIDATED_COUNT:8, FAIL_SEALED_PROVIDER, exit 123 | [OH desktop](evidence/rejected/wikipedia/final.jpeg) |
| HelloWorld candidate | 8524 | same loader rejection, exit 123 | [OH desktop](evidence/rejected/helloworld/final.jpeg) |
| HelloWorld after rollback | 11548 | alive at 15 s | [Hello World own UI](evidence/rollback/helloworld/final.jpeg) |
| ZigZag after rollback | 12554 | alive at 15 s | [ZIGZAG own UI](evidence/rollback/zigzag/final.jpeg) |

These visual classifications are developer observations, not outer acceptance.
The new child exits before the sampler can capture maps/SHA; **new library
execution is not proven**. No new cppcrash was generated. The main failure
receipts are [Wikipedia loader log](evidence/rejected/wikipedia/loader-hilog.txt)
and [HelloWorld loader log](evidence/rejected/helloworld/loader-hilog.txt).

`sealed_child_provider_loader.h` defines error 8 as
`WLSCPL_ERROR_ARTIFACT_IDENTITY`. The loader passes manifest SHA/build-id into
`WLEI_OpenVerifiedFileHex` before mapping. `westlake_android_child_plugin.c:672`
obtains `WLSCPL_GetBuildGeneratedManifest()`, not a runtime JSON manifest.
The current child plugin SHA `0976dee8…bf12e40` embeds the old libsigchain SHA
`ea7becd0…3865ba2` at file offset **0x8798**.

The existing `build_target_in_container.sh` generates `sealed_provider_manifest.c`
(lines 389–450), compiles it (489), then pins the resulting plugin SHA into the
appspawn host (`WLASC_PLUGIN_ELF_SHA256_HEX`, line 551). Exact source excerpts and
hashes are in [source-evidence/](source-evidence/index.json).
A consistent native generation therefore needs the new artifact admitted into
this generated manifest and the associated plugin/host identities rebuilt by
the existing workflow. That exceeds #33's explicit **only libsigchain** scope.
No validator was disabled, no digest patched in place, and no extra native
artifact was changed.

## Rollback and honest verification

[rollback.json](rollback.json) proves the overlay was removed and original
`ea7becd0…3865ba2` restored. Child namespace proofs after rollback confirm it.
Framework `3e106350…dde9af`, boot-framework OAT `0ff275fa…2d7c0` and B5 runtime
`250958dc…d3146` remain unchanged. Only 5ea received commands.

`results.json.null_check_mode=sigsegv` is explicitly scoped to the last observed
original-generation #31 fault. The requested new NPE retest was attempted but
blocked **before ART**; it is not evidence of either new signal behavior or
advancement. `null_check_retest.npe_proven=false`; `next_blocker=null`.
HelloWorld regression is recorded. Final-fix HelloWorld/ZigZag quick was not
run because the candidate could not be admitted; rollback desktop observations
are not substituted for quick acceptance.

[Lifecycle](lifecycle.json): caller, artifact-mismatch negative and symbol coverage
pass; Wikipedia LIT, final-fix regression, advancement and NPE retest fail:
**3 pass / 4 fail, no pending review**. The merged contract has seven scenarios;
its NPE retest is a new clause in the existing null-mode scenario, not an eighth
selector. [Artifact negatives](negative-artifact.json) reject old SHA, absent
child proof and dead child; the real loader rejected both candidate launches.
Known-answer suite: **69 tests, 2 skipped**, passing.

[Evidence index](evidence-index.json) retains hashes/paths of 87 VM evidence files.
Large binaries and unfiltered hilog remain outside git. This is a technical
blocker requiring revised deployment scope, not a content-policy restriction.
