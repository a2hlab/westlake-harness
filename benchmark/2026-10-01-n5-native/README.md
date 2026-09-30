# N5: bounded Flutter runtime lookup and native preflight integration

The previous diagnosis conflated an observed dependency failure with the claim
that OH musl never consults inheritance for `DT_NEEDED`. The OH 6.1 source
contradicts that claim: `preload_direct_deps` creates tasks with inherited lookup
enabled (line 5486); `load_library_header` checks loaded inherited DSOs (5227)
and then direct inherited owners (5275). Inheritance is one hop. This source
snapshot is evidence about those functions, not a byte-for-byte provenance claim
for the device libc.

The N4-order FluffyChat trace additionally contains `Xpm check failed for
liboh_android_runtime.so, errno for mmap is: 22`, header-map failure and FDSAN,
following the successful resident-runtime publication. A missing-path-only story
is incomplete. The archived source also gives a narrower mechanism to test:
absolute-path loading leaves `shortname` unset; name lookup can therefore miss,
while opening the actual file lets `find_library_by_fstat` reuse an inherited
matching device/inode/offset. The extracted, unchanged lookup functions pass
host tests including no-inherit, different-inode and LOCAL_NS_PREFERED cases.
This is **not a whole-loader test or proof that it fixes the observed XPM path**.

## Candidate and provenance

- Base: N4-order `7bc02de79f989d48cedb1e5020df1be3b5cd58f6d2229df8f1a3f08cc4f5ffbe`.
- Candidate: `<WORKSPACES>/westlake-generation-n5-6d001bb8`, manifest
  `b446d8db35e30a9180760f8dc8a4837b93e23c5187217e30b9901f94d66b68f7`.
- ANL: `6d001bb8c5f2dbc91ac7cd6dda9e14a974bbcf2864cadde010e79fcc882b9580`.
  Exactly its two android/route aliases change. Host, runtime, ABI library,
  provider, ART, boot image, JAR and installer remain byte-identical to the base.
- Production source baseline: `../2026-09-30-n3-native/flutter/`, the source of
  the existing `eebd62f2` ANL. Only `flutter_domain.inc` changes.
- Approved option 2: add `/system/android/lib64` after the private root in search
  and permitted paths **only for the existing six Flutter packages**. Native
  non-Flutter domains, lookalikes and ZigZag retain their previous paths. This
  broadens that directory's visibility for six packages; it does not add a new
  runtime copy to the payload. Device checks must still detect duplicate DSOs
  and constructors, including the pre-existing two-mapping ambiguity.
- Reference proposal: cc-t3 `westlake-harness-t3/benchmark/2026-09-30-u4-sweep/FLUTTER-NEEDED.md`.
  Existing owner publication comes from real-work `be16148da`,
  `src/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/src/sealed_child_provider_loader.c:366`.
- Source search was local workspaces/vm-copies, then VM, then hw248. The two
  losslessly gzip-archived read-only source copies came from the OH 6.1 tree's
  `third_party/musl/porting/linux/user/ldso/{dynlink,namespace}.c`, commit
  `02dd8d82887b040b85a4294e9a5039f016fd607a`; no remote tree was changed.
- `build-anl.sh` uses the existing frozen OH toolchain in the authorized VM.
  Sources, headers, script and tool hashes are retained; ELF outputs remain
  in `bms/src/.work/n5-native/flutter/` and the candidate package.

## Gate result: not deployable

The source-bound N2 view now resolves
`westlake_flutter/libandroid.so -> /system/android/lib64/liboh_android_runtime.so`.
The complete offline preflight remains **REJECT**, not a dry-run success:

- N1: 28 rejections (22 unresolved calls, 6 unknowns).
- N2: 78 rejections (67 missing dependencies, 6 uninstantiated dynamic paths,
  5 uncovered library directories). Traversing the now-visible runtime exposes
  more dependencies to this conservative checker; this is not 52 proven new
  device regressions. Missing system snapshots and inherited-owner semantics
  are not silently assumed away.
- No native exceptions were added. Candidate `rollout_ready` remains false.
- No N5 device deployment was performed. Runtime-instance, Flutter rendering
  and control regression outcomes are unverified.

N1/N2 came unchanged from cx-bms `942fcbd22` (also landed on master). Its N2
model is deliberately path-only and conservative; it is not a full musl model.
The archived `native-checks/` binds the actual candidate manifest, unchanged
source/DEX inputs and changed ANL. Unknown app paths remain unknown.
`prepare.py` now emits this sidecar and runs N1 after assembly; rejection exits
nonzero and prevents claiming a deployable build.

## Deployment integration

The repository `deploy_generation.py` checks SHA and frozen policy, then calls
repository-controlled N1/N2 **before dry-run success, orb or Board construction**.
It refuses missing sidecars/readelf, input drift, and any unwaived finding.
Package/input/checker/registry bindings survive Mac-to-VM forwarding, and payload
hashes are rechecked. `NATIVE_READELF` selects a trusted host tool; package-supplied
checkers are never imported. Copied tools require `WESTLAKE_DEPLOY_REPO` if no
trusted checkout can be found.

Replace/add still operate on complete effective candidate packages and retain
existing alias/mount/SHA checks. Before mutating, the current package also must
have valid native provenance for automatic rollback. Explicit rollback requires
`--rollback-state <owned-state.json>` and gates the actual restored package,
then matches the receipt to the live boot/state before mutation. Initial
new-boot deployment supports `--recovery-package <audited-underlay-package>`;
its native checks run before dispatch and its live hashes must match the board
before staging. Raw legacy underlay recovery without provenance is refused with
an outer-reviewed recovery message. There is no bypass switch or SHA-only
fallback. Existing published tools and active boards are not rewritten here.

Example offline check (expected nonzero while the disclosed findings remain):

```sh
python3 scripts/lab/deploy_generation.py "$SERIAL" \
  "$WORKSPACES/westlake-generation-n5-6d001bb8" --dry-run
```

Do not deploy this candidate until the strict findings are resolved or precisely
registered by the authorized outer reviewer. The next device gate would be
HW/ZZ, FluffyChat dependency/init progression and exact runtime instance and
constructor checks, followed by the externally scheduled batch.

## Validation record

Two same-path ANL builds produced the same SHA. Production ANL scope tests,
original musl lookup-function tests, 10 CLI hook tests, 19 delivered gate tests
and 6 frozen-policy tests pass. Contract lint is 100%; lifecycle is 3 pass +
1 pendingreview, zero skips. The first lifecycle invocation used the repository
root instead of `tools/spec-checks` and skipped all four scenarios; that failed
record is retained, not reported as success. Candidate build N1 and actual
deployment dry-run both reject as intended. No native exceptions were added.

The imported gate corpus retains exact original readelf/log bytes in adjacent
`.raw.gz` files; `.txt`/`.log` views trim trailing whitespace only for repository
checks. Gate source code itself is unchanged from the handoff.
