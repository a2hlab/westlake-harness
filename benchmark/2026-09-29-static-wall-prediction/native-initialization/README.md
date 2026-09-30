# Native initialization walls — retrospective replay, 2026-10-01

## What the old scan missed

Export/table presence did not establish **namespace mapping** or **initialization order**.
The new source scanner reports both known failures and leaves the two controls unflagged:

| Replay | Artifact SHA prefix | Rule | Findings | Expected |
| --- | --- | --- | ---: | --- |
| N2 | host `42c35453` | NOLOAD before local mapping | 0 | No corresponding wall |
| N3b | host `c8fdfc76` | NOLOAD before local mapping | 1 | Resident runtime unavailable |
| N4 `1617080a` | runtime `71f79c84` | JNI cache before registration | 1 | GLImpl initialization before native registration |
| N4-order | runtime `216b68fb` | JNI cache before registration | 0 | Registration invocation moved before cache |

These are **four retrospective replays, not four new predictions**. No screenshot was accepted,
no device was accessed, and the frozen U4/J6N4 predictions and scores remain unchanged.
`manifest.json` pins full package-manifest hashes, artifact hashes, source hashes and DEX evidence.
`results.json` preserves positive traces, checked prerequisites and unknown coverage separately.

## Rules and witnesses

### `noload-before-namespace-mapping`

The tokenizer removes comments while retaining strings and original line coordinates. It locates
`dlopen`/`dlopen_ns` calls carrying the actual `RTLD_NOLOAD` token, identifies the namespace and
literal/constant target, and checks earlier loads in the same function and fresh namespace.
An earlier same-library load counts only with known loading flags, a null-handle return guard,
compatible lexical blocks, no intervening close, and no namespace recreation.
An inherit edge is not a load. Another namespace, another library, a later load, a conditional
sibling block, an unchecked load, or an opaque flags alias cannot discharge the prerequisite.

N3b `evidence/sources/n3b-host.c:233` creates `app_namespace`; its inheritance edges at 266/269
are followed by the runtime `dlopen_ns` at **281**, with `RTLD_NOLOAD` at **283** and no prior
same-namespace load. N2 has no such call. The ordinary `dlopen(plugin_path, RTLD_NOLOAD)` in the
host entry has an opaque target/external module-install precondition, so both profiles retain
one **unknown**, not an invented mapping or a proven wall. The original explanation is cc-t3's
`westlake-harness-t3/benchmark/2026-09-30-u4-sweep/NAMESPACE-WALL.md` (workspace-relative).

### `jni-cache-before-native-registration`

The native walker follows named functions from the configured startup entry, keeping call order,
JNI class variables and field/method-ID lookups. Registration is matched by **class, method and
descriptor** from actual `JNINativeMethod` tables, not by a function's name alone. DEX superclass,
`<clinit>`, constructor, `new-instance` and invoke edges explain the native initialization prerequisite.
Unreachable cache helpers are not treated as startup calls.

The N4 trace is:

1. `n4-runtime.cpp:666`: `startReg` calls the EGL registration helper.
2. `egl.cpp:549` → `egl.cpp:133` → `egl.cpp:113`: eager cache reaches
   `GetFieldID` on `EGLContextImpl`.
3. DEX superclass initialization reaches `EGLContext.<clinit>`; its constructor path is
   `EGLImpl.<init>` → `EGLContextImpl.<init>` → `new GLImpl` → `GLImpl.<clinit>` → `_nativeClassInit()V`.
   The result includes each method and instruction offset; no runtime log is used by the rule.
4. GL registration is only invoked later at `n4-runtime.cpp:672`, through `gl-wrapper.cpp:6`
   and the real `registerNativeMethods` call at original **GLImpl source line 9294**.

N4-order moves the same GL registration invocation ahead of EGL caching. The detector produces
zero corresponding ordering findings and a checked GL prerequisite. This means **invocation order**
is repaired, not that registration succeeded or a device displayed UI.

## Reproduce

From the repository root, Python standard library is sufficient for the checked-in replay:

```sh
python3 benchmark/2026-09-29-static-wall-prediction/scan_native_initialization.py \
  --manifest benchmark/2026-09-29-static-wall-prediction/native-initialization/manifest.json
python3 benchmark/2026-09-29-static-wall-prediction/test_native_initialization.py -v
cargo test --manifest-path tools/spec-checks/Cargo.toml --test native_initialization
```

The CLI is an inventory: exit 0 means inputs were analyzed, **not no risks**. Invalid, missing,
unbalanced or hash-mismatched input exits 3 with `unknown-invalid-input` rather than an empty result.
New profiles supply source files, hashes, a native entry function and the relevant DEX slice; rule
code has no N2/N3b/N4 labels, app keys, runtime hashes or EGL/GL-specific branch conditions.

To recapture source/DEX inputs from the existing read-only workspace artifacts, use the lab Python
environment with Androguard, set `WORKSPACES`, and write to a separate output directory:

```sh
python3 benchmark/2026-09-29-static-wall-prediction/native-initialization/collect.py \
  --workspaces "$WORKSPACES" --output /tmp/native-initialization-recapture
```

The collector checks N3/N4 build-source hashes, N4-order's old/new source receipt and package
artifact hashes. It records a verbatim contiguous GLImpl registration/table excerpt (original
line 9036 onward) to avoid copying unrelated implementations; all other C/C++ snapshots are full
files. The framework JAR is SHA-pinned, and its DEX entry hashes and decoded initializer offsets
are retained. Binary artifacts and framework JARs are not added to the repository.

## Deliberate limits

- This is a bounded tokenizer/call-order analysis, not a C/C++ preprocessor, CFG dominance proof,
  linker, interpreter or whole-program verifier. Conditional calls produce risk candidates;
  preprocessor choices, function pointers, aliases, external loaders and unmodeled JNI calls require review.
- Namespace checks are intraprocedural and exact-name/exact-path. Cross-function preloads and path
  aliases are not inferred. Missing mapping evidence is a risk on the scanned fresh-namespace path,
  not proof that every execution fails.
- Registration calls are not successful `RegisterNatives` receipts. Branch failure, helper return
  values, runtime class state and partial registration remain outside the proof.
- The pinned DEX slice is intentionally bounded: five lookup records per runtime replay carry
  unknown closure entries (Object/core classes and EGL base-class definitions outside this slice).
  The explicit GL dependency chain is present; missing side branches are not silently filled in.
- `unresolved_calls` remains visible. Zero findings never means full coverage or an app-lighting verdict.

## Validation

Ten unit tests cover the four real snapshots, matching namespace/guard behavior, comments, inheritance,
wrong namespace/library, later loads, opaque flags, all four JNI ID lookup APIs, unreachable helpers,
wrong native-method tables, missing DEX dependencies, source tampering and missing entries.
Three new Rust integration selectors pass; existing selectors are untouched. Contract lifecycle:
3 pass / 0 skip / 0 fail. Known-answer suite: 69 run / 2 skip / 0 fail.
