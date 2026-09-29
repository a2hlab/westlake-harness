# B5: resolve launcher activity aliases without changing the APK

The previous launch treated Wikipedia's `org.wikipedia.DefaultIcon` alias as a
Java class. The runtime now sets `ActivityInfo.targetActivity` to
`org.wikipedia.main.MainActivity`, preserving the original OH component identity.
On 5ea, the old alias `ClassNotFoundException` disappeared and execution reached
`Activity.attach`. Wikipedia still did **not** remain alive or show its own UI:
it crashed in `ContextWrapper.getApplicationInfo` called by `ContextImpl.getTheme`.
This is a subsequent wall, outside B5. No claim of Wikipedia LIT is made.

| Trial, same boot and runtime | Evidence | Result |
|---|---|---|
| Wikipedia, UID 20010057 | alias → MainActivity at 19:07:34.492; PID 27515; SIGSEGV at 19:07:35.276; 16.07 s sampler; no PID after | Final image is OH desktop; Wikipedia gate fails |
| HelloWorld, UID 20010055 | ordinary entry, `target=null`; PID 28552 throughout 16.10 s sample and after | Agent read its own UI: Hello World, lifecycle CREATED/RESUMED, action buttons; outer review pending |
| New missing-target fixture, first attempt | alias resolved, but classloader namespace failed on absent nativeLibraryDir; exit 1 | Retained prerequisite failure, not credited as missing-class validation |
| Same fixture, empty fallback library directory prepared | alias → MissingTarget, explicit target ClassNotFoundException; PID 7151 exit 1; 16.00 s sampler | Negative passes; fixture uninstalled and empty directory removed |

Screenshots for outer review: [Wikipedia final](evidence/wikipedia/final.jpeg),
[Wikipedia t3](evidence/wikipedia/t3.jpeg),
[HelloWorld final](evidence/helloworld/final.jpeg).
The agent inspected both final images directly. Visual acceptance remains with the
outer reviewer. R2 is **partially**: alias behavior and negative are verified on
5ea, Wikipedia visual/process success is not achieved, and 61b was not tested.

## Choice and source provenance

The existing 00.Workspace `LaunchActivityAliasProjection` and
`ManifestComponentProjection` already express the intended rule: read the installed
APK manifest, resolve a declared alias target, and write only `targetActivity`.
Their file hashes and upstream commit are in `source-provenance.json`.
The current accepted JAR lacks their `InstalledApkApplicationProjection` dependency
closure. Rather than import that whole package-manager layer, this adaptation
uses the bounded binary manifest reader already present in the copied BMS source.
It checks caller UID/package, APK identity, declaration uniqueness, normalized
names and a declared ordinary target. It preserves application/name/theme/flags.
Resolution errors log and terminate because the enclosing scheduling callback
otherwise catches Throwable and leaves AMS waiting.

Runtime resolution needs one scheduler call and two helper source files. It does
not change the native installer shared with B2/B3, require APK rewriting, or
re-register the desktop ability. A missing dex target is left to the existing
ActivityThread exception/child-exit path; the device negative verifies that path.
The Wikipedia target log plus the subsequent Activity.attach stack supports the
inference that class instantiation passed; the negative gives an explicit
`Unable to instantiate ... MissingTarget` log proving target-class selection.
The stack's later frames are marked unreliable by the fault dumper; this report
records the immediate failure site, not a proven cause for the null context.

## Census: 13 selected aliases out of 66 keys

`census.json` keeps per-key manifest entries and SHA-256. Selection uses the
previously observed BMS desktop entry, falling back to the first enabled
MAIN/LAUNCHER when no registered entry was available. Selected aliases are:
Wikipedia, Termux, AppManager, Anki, calendar, filemanager, gallery, im-vector-app,
LibreTube, musicplayer, notes, OrganicMaps, and uhabits (exact keys in results).
A separate manifest-only metric finds **15 keys with any enabled launcher alias**;
it is not interchangeable with the BMS-selected-entry count. Existing BMS choices
can point to disabled aliases. The earlier Subway Surfers pin mismatch is retained;
its current APK was only read for this census, never deployed by B5.

## Build, deployment and rollback

`build.py` compiles the helpers with Java 8 bytecode through dockbuild, disassembles
the accepted JAR, injects exactly one helper call after buildActivityInfoFromAbility,
and reassembles. Every existing class is compared after the round trip: only
AppSchedulerBridge changed; three helper classes were added. Non-dex JAR entries
are preserved. This is an explicitly recorded minimal overlay of the accepted
artifact, not a rebuild of the entire current source tree. No APK/JAR/keystore is
committed. `build-inputs.json` pins dependency hashes; `build-result.json` records
source hashes and class differences. The isolated Docker Java image setup is in
`Dockerfile`; host SDK aapt2/apksigner package only the new negative fixture.

- Accepted baseline JAR: `9161b50756d3ffdfb2a8908ea7ec13f908214688321b2785365977ac40b28dea`.
- B5 JAR: `250958dc3f133b67fb38c5da3caf81714fd6958e2247556e327d917b1f0d3146`.
- Built artifact: `/home/zhaoyue/a2hlab/build-runs/20260928-oh6.1.0.31-b5/build/oh-adapter-runtime.jar`.
- 5ea staged overlay: `/data/local/tmp/b5-alias-20260928/oh-adapter-runtime.jar`.
- Original backup and command receipts: `/home/zhaoyue/a2hlab/board/b5-alias-deploy-5ea/`.
- Both shell and AppSpawnX PID 13161 root read back the new JAR hash; child alias
  logs prove the added code ran. No native foundation/installer library changed.
- Only 5ea was locked and written. No commands targeted 61b or 5cd. 5ea lock released
  after cleanup; the alias overlay remains active for the next investigation.
- With a fresh 5ea lock and verified same boot/overlay, rollback via the VM is
  `umount /system/android/framework/oh-adapter-runtime.jar`, then verify the
  revealed baseline hash above. Do not blindly repeat umount or reuse PID 13161
  after reboot. This mount is temporary and is not claimed reboot-persistent.

Installed Wikipedia and HelloWorld APK hashes after cleanup match their original
inputs (`eba82a0f…` and `2d122a79…`); the receipts are in `negative/cleanup.json`.
The standalone negative package is `org.a2hlab.b5aliasnegative`, UID 20010079. Its
sources and build recipe are in `negative/`; neither campaign APKs nor their
signatures were modified. The test-only empty directory under `/system/app/` was
removed with rmdir, and BMS no longer lists that fixture.

## Verification and evidence limits

`test_host.sh` exercises 66 original manifests against an independent AXML census,
checks UID/package rejection and preservation of launch fields, and rejects malformed
AXML. All pass. Repository known-answer suite: 69 tests, 67 pass, 2 skipped.
Four Rust selectors invoke `verify.py`; lifecycle results are saved separately.
The Wikipedia selector intentionally fails on the observed dead process. Other
machine passes do not grant outer visual acceptance.

`observe.py` clicks the exact BMS desktop icon, starts hilog before clicking, samples
UID processes on-device for at least 15 seconds, and captures t3/final images.
The Wiki UID sampler also saw crash-dumper processes; they are not app survival.
`raw-evidence-index.json` records original paths/hashes for the full VM logs.
Committed excerpts retain original line numbers, omit unrelated system/network
logging, and do not alter the selected lines. Full command receipts remain in
those VM run directories; no failed attempt was replaced by the retry.

Recorded B5 lifecycle: quality score 1.0, **3 pass / 1 fail**. Selectors
`b5_alias_resolved_to_target`, `b5_non_alias_entry_unchanged`, and
`b5_missing_target_reported` pass. `b5_wikipedia_lit` fails because the Wikipedia
process did not survive. Its human review is not promoted to pendingreview over
that failed prerequisite. See [lifecycle.json](lifecycle.json).
