# B93: declared TLS and HTML additions

The previous prototype wrote a new file outside the deployment manifest and
was not suitable for the resident payload. This package adds both original
libraries to `files` and `live_hashes`; each addition is checked by the same
board-lock, boot, SHA, mount-ownership and child smoke gates as replacements.
No provider rebuild is needed for this package. The old f6068470/12115cea
handoff and `stage_tls.py` are superseded and must not be used.

## Artifacts and loading agreement

| Target under `/system/android/lib64/` | SHA256 |
|---|---|
| `liboh_tls_boundary.so` | `8ecf62507e997bb31941135200aae3f9eac2efb38beef68d098eed16b1808919` |
| `libwestlake_html_compat.so` | `26ac847bdec6552dc26def1215dc9d2e8ac6847705461626160a0d72499baa6b` |

TLS source/build: oc-t4 `bms/src/adapter/framework/native-compat/westlake-tls/`;
artifact copied unchanged from `vm-copies/tls-boundary-8ecf6250/`.
HTML source/build: oc-t4 commit `fe153eb8`, actual worktree
`westlake-harness-b4/benchmark/2026-09-29-westlake-port/html-compat/`
(the advertised `westlake-harness-t4` path does not exist).
Both libraries export `JNI_OnLoad`; neither was rebuilt or binary-patched here.

cc-t3 owns the r17b/r17c Java call sites. In **child init only**, from a class
loaded by the runtime PathClassLoader, load TLS and then HTML using their
absolute paths above. Configure `WESTLAKE_NET_HELPER_PATH` to the TLS path if
using the existing OhTrustBridge environment-driven load. Before loading HTML,
set `WESTLAKE_HTML_COMPAT=1` and
`WESTLAKE_HTML_COMPAT_CLASS=adapter.compat.HtmlCompatFallback` in the child
(e.g. the existing Java `android.system.Os.setenv` mechanism). Never enable the
HTML helper in the appspawn parent. Class loading/registration may initialize
Java code; do not prewarm JCA providers in the parent.

`System.load` from a **null/boot class loader** uses native-loader-oh's fixed
four-library system list and rejects these new names. The runtime
PathClassLoader route is the intended route; device load success is still
unverified. Preserve the complete exception if namespace registration/search
rejects it. TLS JNI_OnLoad returns success even when its FindClass registration
fails: require `[WESTLAKE-441] RegisterNatives(WestlakeSSLSocket) rc=0`, not
merely a loaded-library map. TLS also requires the Java SSLContextSpi /
SSLSocketFactory route; the earlier r17 class explicitly remained dormant.
Actual trusted HTTPS and content remain separate device acceptance.

## Deploy on 5ea (cc-wiki owns the lock)

Bundle: `/Users/zhaoyue/orca/workspaces/westlake-b93-tls-html-8ecf6250-26ac847b`.
It contains two declared package snapshots plus pinned deployer code. Step 1
adds TLS to the current B92 package; step 2 adds HTML. A second-step failure
rolls back that step and then the first. The old libraries, provider 0509fe23,
ANL a9c9187d, bridge 84695d62, ART and installer are unchanged.

Before deploy, stop any non-control Android app and temporarily remove the
experimental Java overlay to expose package r8b d5000c4e. Preserve its receipt;
the deployer must verify all resident hashes rather than ignore the JAR.
Then run:

```sh
python3 /Users/zhaoyue/orca/workspaces/westlake-b93-tls-html-8ecf6250-26ac847b/deploy_bundle.py 5ea34a4500000000000000001123012c --lane cc-wiki --dry-run
python3 /Users/zhaoyue/orca/workspaces/westlake-b93-tls-html-8ecf6250-26ac847b/deploy_bundle.py 5ea34a4500000000000000001123012c --lane cc-wiki
```

Reapply the Java candidate containing the load sites, then use master batch
with 16 MiB/private-off/clock preflight and shots 5,20. Check both libraries'
SHA through `/proc/<child>/root`, their maps, TLS registration and HTML logs;
retain facts.txt verbatim and screenshots for outer review. HelloWorld and
ZigZag are controls. Do not equate dry-run/registration/process survival with
TLS content or visual acceptance.

## Rollback / interruption

Expose package r8b before rollback checks, then:

```sh
python3 /Users/zhaoyue/orca/workspaces/westlake-b93-tls-html-8ecf6250-26ac847b/deploy_bundle.py 5ea34a4500000000000000001123012c --lane cc-wiki --rollback
```

It rolls back HTML then TLS. Each removal requires the last recorded owned
bind and the empty mountpoint created for it; changed files/mounts are refused.
Prior B92 stays active. Reapply the preceding Java overlay after rollback.
If interrupted after TLS only, inspect the deployment receipt and roll back
only that last step with the bundle's `tools/deploy_generation.py`, package
`1-tls`, and `--add /system/android/lib64/liboh_tls_boundary.so --rollback`.
Do not force through an ownership/boot mismatch. After a reboot restore the
approved base first; these two snapshots are incremental experiments, not the
complete v3c replay package.

## Host evidence

- 8 addition transaction tests: absent-only creation, manifest SHA/one-file
  scope, smoke failure recovery, preexisting target and foreign mount refusal,
  safe rollback, changed underlying file preservation.
- 2 bundle orchestration tests: all-stage preflight before writes and
  rollback of the first addition after a second-stage failure.
- 26 existing deployer tests remain passing.
- Both complete package snapshots pass dry-run with zero device I/O.

R2: host packaging/rollback logic verified; new-library runtime loading and
app behavior unverified until cc-wiki's device evidence arrives.

Known-answer suite: 69 tests, 2 skipped, OK. Related B9 lifecycle: 5 pass,
1 pendingreview, 1 fail (manifest JNI export requirement conflicts with the
outer-approved v3a 84695d62 bridge + Java fallback, #68). The bridge is
unchanged here; do not report full B9 pass or new device acceptance.
