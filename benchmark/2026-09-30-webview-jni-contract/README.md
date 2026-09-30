# N3b / J5b exact JNI artifact contract

J5 compiled successfully and declared both native entrypoints, but it did not
define `adapter.core.WebViewUpdateServiceAdapter`. N3b uses that exact FindClass
name and exact GetStaticMethodID descriptors. A service proxy, a reference in a
DEX string table, or a method returning IBinder cannot replace the missing class
and its self-typed `getInstance` descriptor.

The host gate is `scripts/lab/check_webview_jni.py`, integrated through
`tools/spec-checks` selectors `webview_jni_exact_definitions` and
`webview_jni_real_pair`. It performs **zero device IO** and never loads the ARM
runtime on the host.

| Direction | Exact DEX owner and member | Required flags |
|---|---|---|
| Native → Java | `Ladapter/core/WebViewUpdateServiceAdapter; isAvailable()Z` | static, concrete implementation |
| Native → Java | `Ladapter/core/WebViewUpdateServiceAdapter; getInstance()Ladapter/core/WebViewUpdateServiceAdapter;` | static, concrete implementation |
| Java → native | `Ladapter/core/WestlakeWebViewInstall; nativePrime()Z` | static + native |
| Java → native | `Ladapter/core/WestlakeWebViewInstall; nativePublishAfterBind()Z` | static + native |

Private native methods are allowed: visibility is not a JNI static-lookup error.
The first two can resolve inherited implementations if their real class
definitions are supplied. Native declarations must belong to their exported JNI
owner. Duplicate candidate definitions fail instead of silently choosing a JAR.

## Provenance and implementation

- Native bytes are fixed to **7c9c6240c7bbaa529460d7acb8e12629e3c9f9151b390a071f1d10a0bd727042**.
- Its source TU is the existing N3b `src/webview_publication.cpp`, SHA
  **ba5a3fe23d4a72f0406427e38b51259cc7c8fd0d04a7c78237d9f6d3fccac210**,
  from accepted commit `7fbfc54d`. The N3b build/source receipt establishes the
  pair; this gate refuses a new native/source SHA rather than silently adapting.
- A bounded extractor takes the actual FindClass/GetStaticMethodID literals from
  that TU, confirms their NUL-terminated presence in the fixed ELF, and verifies
  both defined/global/default-visible JNI functions in `.dynsym`. Wrapper
  `jboolean (JNIEnv*, jclass)` determines the Java static `()Z` declarations.
- Androguard **4.1.4**, already used by `n3-native/offline-followup/inspect_webview.py`,
  reads class definitions and encoded method definitions in **every** classes*.dex;
  method references/string matches are never implementations. pyelftools reads
  the ELF. No new packages are fetched, no upstream/runtime source is changed.
- Receipts include full JAR/native/source and individual DEX SHA, method flags,
  resolved owner, DEX member, observed wrong overloads and failure reasons.

## Run

From this worktree, with WORKSPACES resolved by `scripts/lab/lab_paths.py`:

```sh
"$WORKSPACES/westlake-inputs/venv/bin/python" scripts/lab/check_webview_jni.py \
  --jar "$JAR" --out /tmp/webview-jni.json
python3 benchmark/2026-09-30-webview-jni-contract/verify.py exact
python3 benchmark/2026-09-30-webview-jni-contract/verify.py pair
```

`--jar` is repeatable for a supplied classpath. Default native is the immutable
N3b package; `--native` / `--source` permit relocated copies **with the same SHA**.
Exit **0** = this static contract satisfied, **1** = mismatch, **2** = bad/missing
input or parser dependency. JSON is emitted on stdout and optionally `--out`.
Do not invert the production gate to accept old J5: only the *regression test*
expects that real negative to fail. J5b's positive requires its real pinned JAR,
not a fixture or skip when the file is absent. `pair-inputs.json` records the pair.

## Negative controls

Eight tiny **test-only** JARs contain genuine assembled DEX, built with the
existing B7 smali 2.5.2 recipe through `a2hlab-b5-java:24.04`. Their source is
`build_fixtures.py`, inputs/SHA/size in `fixture-receipt.json`; they are not Android
implementations or deployable providers. Correct signatures, reference-only,
wrong return type, nonstatic method, nonnative Java entry, multidex supplier,
duplicate class, and inherited implementation cover the lookup boundaries.
CLI exit/report equality, changed-native SHA and missing-DEX ZIP are tested too.

Rebuild in a fresh fixture output directory using dockbuild and:
`python3 build_fixtures.py --inputs <existing-B7-inputs-directory>`.
Generated fixture JARs total only a few KB and are checked in so the gate does
not need Docker merely to run. No production JAR is added to git.

## What a pass does not establish

This is the **adapter ABI** gate. Platform JNI fields/methods and methods on
dynamic Map/Throwable instances are not resolved here. A DEX pass proves neither
ART ClassLoader visibility nor JNI execution, Binder/cache identity, provider
APK/native dependencies, post-bind timing, nor Chromium rendering. In particular,
the existing native cache/public-readback and boolean-return requirements remain.
The real provider payload is still a separate prerequisite. All board behavior,
screenshots and process survival remain **unknown**; this task does not authorize
U4 rollout or rewrite its frozen prediction table.

## Actual pair result

| Real artifact | SHA prefix | CLI | Exact checks | Verdict |
|---|---|---:|---:|---|
| Original J5 | dbce2eee | 1 | 2/4 | FAIL as expected: supplier class absent; both native declarations present |
| J5b | ce2c3baf | 0 | 4/4 | PASS for this static contract |

J5b full SHA: **ce2c3baf7586b3a6f50202fc4b8a75740cbf5beb7e953ab97693566f1d2c3652**.
The Mac vm-copies handoff was not yet posted, so the actual completed VM
`build-j5b/oh-adapter-runtime.jar` was copied **read-only**, after matching the
producer's `build-result-j5b.json` full SHA. The reader-owned copy lives at
`vm-copies/cx-t0-j5b-contract-ce2c3baf/`; producer files were untouched.
`producer-j5b.json` preserves the original build receipt. This is real output,
not the good test fixture, and this test does not substitute for producer signoff.

`j5.json`, `j5b.json`, `cli-exits.json` contain the raw parsed results. Eleven
exact-lookup/CLI/fixture tests plus the real-pair test pass; 82 known-answer tests
ran with 3 skips and no failures. No production artifact or frozen source was
modified. Lifecycle covers the exact-definition and real-pair selectors.
R2: static identities/DEX/ELF checks verified; runtime and UI unverified.
Screenshots and alive counts: **unknown** (no board run).
