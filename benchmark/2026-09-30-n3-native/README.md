# N3: U2 native wall batch, offline candidate

The old diagnoses mixed a loader's first failure with later resource fallbacks.
Firefox/Fennec first fail `__sF@LIBC`, then report JNA resource absence. Noice's
first uncaught error is a null MediaRouter service, and fd-noice lacks SSLSockets;
these are J4 inputs, not evidence of an audio JNI fault. VLC's selected
`Theme.VLC.Transparent` really lacks `background_default` in its APK parent chain.
We must identify the incorrect inflater context before changing resource semantics.
Evidence is in `evidence/`, with original U2 file paths and line numbers.

The single candidate is `/Users/zhaoyue/orca/workspaces/westlake-generation-n3-8a7880fa`.
Manifest SHA: `8a7880fa207a4e13e6d0cb86140d0345dcd1f377a0eebcab8d633a323e9b9a24`.
Base: accepted U2 native N2 `51a78bde`; 11 declared path changes, 292 package files.
No board was assigned or touched. Device facts and screenshots are **unknown**.
`rollout_ready=false` remains until external device review. `results.json` contains
all SHA identities; `dispositions.json` handles every cx-bms N3 cluster.

## What is built

| Change | Evidence and expected checkpoint | Provenance |
|---|---|---|
| Runtime EGLImpl registration | 28 JNI entries match current framework DEX; Unciv/SPD `_eglGetDisplay(Object)J` | Complete unchanged `framework/opengl-jni/oh_egl_impl.cpp`, VM Westlake `22b945321929987c86b35cd99f9f2d2f4283e82e` |
| Resident runtime publication | LocalSend log first has Xpm header mmap EINVAL; after direct inheritance use exact-path `RTLD_NOLOAD|GLOBAL`, fail if absent | real-work `be16148da9ae7bb89c62e81e144ed0bceb5c4669`, `stock_child_plugin/src/sealed_child_provider_loader.c:WLSCPL_InheritAndroidRuntimeV1`; NOLOAD and package scope are N3 adaptations |
| Native private facades | Reuse N2 libandroid/GLES2/jnigraphics, plus existing empty stdc++ SONAME alias; gdx strong imports supplied independently | Westlake `532633da63b770d3d459c74683db6d7a1f82a022`, `framework/webview-shim`; exact existing N2 artifact bytes |
| Property find/read callback | Actual three Flutter engine versioned imports; retain N2 92-byte get bound | Whole cache/find/callback bodies from `framework/webview-shim/webview_bionic_shim.c`, Westlake `532633da` |
| JNA stdio sentinels | `__sF@LIBC` from both real jnidispatch files; real FILE I/O test | Whole `framework/appspawn-x/bionic_compat/src/bionic_stdio_compat.c`, Westlake `532633da` |
| OpenSLES | Mindustry + PPSSPP actual imports matched to OH slCreateEngine and Android extension IIDs | Whole `opensles_android_compat.c`, Westlake `532633da`; existing OH platform OpenSLES opened in default owner |

Host and ANL paths are restricted to six exact Flutter package names and thirteen
native package names. SPD and PPSSPP are the only new native selections relative
to N2. HW/ZZ/lookalike names do not select the branch. The runtime is published
only for packages using the libandroid facade; JNA/SPD do not gain that operation.
Mindustry/PPSSPP alone preload platform OpenSLES. No broad system search root,
new ART, provider, child, JAR, boot image, installer, or frozen-source change.
The host retains INET and the unchanged big-stack provider.

The stdc++ file is a SONAME placeholder, not a C++ implementation. Both actual
gdx consumers' strong symbol names resolve without it. Existing process-global
musl and canonical system libc are untouched. The stdio adapter handles bionic
stdin/stdout/stderr sentinels and forwards other FILE pointers unchanged; its
namespace visibility and interaction with loaded apps still require device tests.

## Sources and build

Sources were searched on Mac first (`vm-copies/westlake-current`, real-work,
00.Workspace). EGL source already vendored in N2 was byte-checked against the VM
Westlake copy. All new native source snapshots are here; `source-origins.json`
records original paths/commits/hashes. Unchanged N2 helper snapshots and build
inputs remain pinned by N2's committed source list. `source-sha256.json` covers this
batch; `toolchain-identities.json` records the frozen OH compiler/sysroot inputs.

Docker remained stuck stopping. The user explicitly authorized the same frozen
compiler and scripts directly in a2hlab; no OrbStack-wide restart was performed.
No Docker-vs-VM bitwise claim is made. Host was built twice with identical bytes.
Initial EGL build failed on missing SDK C++ include search; adding that include
fixed it. Build failures and final logs are retained.

```sh
orb -m a2hlab bash -lc 'cd /Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy && bash benchmark/2026-09-30-n3-native/build-egl.sh && bash benchmark/2026-09-30-n3-native/build-runtime.sh && bash benchmark/2026-09-30-n3-native/build-flutter.sh --anl-only && python3 benchmark/2026-09-30-n3-native/build-host.py'
python3 benchmark/2026-09-30-n3-native/prepare.py /Users/zhaoyue/orca/workspaces/westlake-generation-n2-51a78bde /Users/zhaoyue/orca/workspaces/westlake-generation-n3-candidate
```

Only the unexported candidate path may be regenerated. Preserve the hash-named
export; any changed package must get a new manifest hash and path.

## Gates and limits

- ELF audit: 11 declarations, no removed exports, runtime retains newAudioSessionId.
- EGL table: 28 exact DEX signatures; missing registration and malformed signature
  negatives rejected. Real AndroidRuntime registration code is compiled.
- Native ABI: 10 exact GNU-version exports and 6 real consumer checks; missing
  export negatives rejected. Property bound and stdio real I/O host tests pass.
- Six Flutter engines: no missing strong symbol **names** or NEEDED **names** in the
  offline graph. Existing OH unversioned/version-mismatch counts are retained in
  `closure/summary.json`; this is not exact version closure or runtime owner proof.
- Two gdx + two OpenSLES consumers: static supply verified, missing audio/IID
  negatives rejected. Audio behavior remains unverified.
- Actual host/ANL functions run with mocked OH boundary: selected/default/sealed
  owners, NOLOAD, missing owner, missing runtime, non-target and lookalike cases.
  N2 host fails the new runtime-publication assertion as the negative control.
- Package SHA, frozen provider aliases and asset-fd source pass. FZ-001 installer
  is outside this package and unchanged. Corrupted package/source negatives reject.
- Deployment dry-run: no device I/O. Human lifecycle scenario remains pending review.

Not implemented: VLC inflater context selection, Termux finishActivity trigger,
WebView Java/provider integration, Noice Java services, AppManager mDNS/NSD wait,
Skia writer cause. The loopback slow-refusal hypothesis was disproved by cc-wiki's
OH probe (ECONNREFUSED 0.1–0.4 ms). Four FDSAN faultlogs are debug signal 42 with
later loader failure, not proof of FDSAN abort; no FDSAN suppression was added.
These are explicit scope/results limits, not claims that N3 fixes every white screen.

Verification: `agent-spec lifecycle specs/native-n3/t1-native-batch.spec.md --code tools/spec-checks` yields three pass and one pendingreview, lint 100%. The initial run inherited env-mac’s Android `cc` shim and could not link Mach-O test objects; the rerun used a clean host PATH and `CARGO_TARGET_AARCH64_APPLE_DARWIN_LINKER=/usr/bin/cc`. This was a host test-environment failure, not a passing attempt; `lifecycle-env-failure.json` is retained. Repository known answers: 82 run, 3 skipped, zero failures (`known-answers.txt`).
