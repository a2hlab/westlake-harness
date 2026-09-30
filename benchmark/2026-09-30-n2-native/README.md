# N2: native batch after N1 device results

N1's file-level closure passed, but its live loader failed on runtime visibility,
property imports and JNA errno. Package identity was checked in different places
by ANL and the host. Also, marking an ELF `DF_1_GLOBAL` did not make a LOCAL load
persistent global supply in this OH musl implementation. N2 selects the private
domain lazily from admitted search/permitted/load paths and preloads the ABI
through the existing default-owner callback using `RTLD_GLOBAL`. Unselected
packages retain the original path. Physical closure is still not a live-domain
proof: this candidate has **no device validation**.

## Artifact and evidence

- Package: `/Users/zhaoyue/orca/workspaces/westlake-generation-n2-51a78bde`.
- Manifest SHA: `51a78bde7075305758bd40b0af3169753dc4be343509e8a8e3d8909fb5d9df09`.
- Parent: accepted N1 `aa57845c`, unchanged; 7 declared paths change, 288 files.
- `results.json`, `package-changes.json`, `elf-audit.json`: exact artifact identities,
  NEEDED and exports. No removed dynamic exports in the changed artifacts.
- `load-path-tests.txt`: production ANL compiled with mocked OH callbacks; load-only
  package identity, Flutter/native lazy creation, reuse, unrelated/lookalike and
  admission negatives. The old N1 source fails the same test.
- `namespace-tests.txt`: actual host callback compiled with mocked namespace calls;
  search/permitted identity, direct owners, foreign namespace and lookup failure.
- `abi-audit.json`: 7 exact LIBC-versioned exports, 6 actual consumers; removing errno
  or abort-message from the provider set rejects the negative.
- `closure/`: all 6 engines have zero absent strong symbol names and NEEDED names.
  Each still has 292 or 293 non-exact version matches against unversioned OH
  exports; these are **not** certified exact-version compatibility. New target
  imports have separate exact checks. Broad platform owner reachability is not
  inferred from this file scan.
- `jni-signatures.json`: all 250 GLImpl entries plus 2 Camera entries match the
  SHA-verified N1 framework DEX inventory. This checks signatures, not execution.
- `frozen.txt`: FZ-002 aliases and FZ-003 source unchanged. Installer FZ-001 is not
  in this package and is never replaced. `dry-run.json`: offline deployment plan.

## Source and behavior

| Cluster | N1 first wall / apps | N2 implementation and prediction | Limit |
|---|---|---|---|
| Flutter visibility | private libandroid cannot find runtime; LocalSend, FluffyChat, KitchenOwl | host recognizes permitted/load identity and adds direct default/sealed edges for the selected private domain; expect facade preload to advance | Only the six authorized Flutter packages; actual owner lookup still needs device logs/maps |
| Flutter properties | `__system_property_get`; Immich, Libre, Saber | copy Westlake property reader/fallback; LIBC-versioned private ABI | property fallback is compatibility data, not proof of device capabilities |
| JNA | `__errno@LIBC`; Firefox, Fennec | admitted absolute load identifies native domain lazily; host explicitly preloads ABI globally in that domain | generic runtime ClassLoader must reach this actual path; log `[ANL-N2]` and `[N2-OWNER]` |
| GLImpl | SPD `_nativeClassInit` | full 250-method AOSP14 table and verified Westlake GLES1 forwarding recipe | driver may not supply every GLES1 extension; missing upstream forwarders log/return defaults, no rendering claim |
| Camera | OpenCamera `_getCameraInfo` | new OH Camera NDK list/orientation bridge; two Camera1 JNI entries | no synthetic camera, no capture implementation; backend errors and portrait override throw |
| VLC libc++ | `android_set_abort_message@LIBC` | Westlake ABI implementation with exact LIBC export | app-owned libc++ remains private; this does not implement later media capabilities |

Provenance is in `source-origins.json`, `source-sha256.json`, and
`toolchain-identities.json`:

- ABI functions: local `vm-copies/westlake-current/framework/webview-shim/webview_bionic_shim.c`,
  Westlake `532633da63b770d3d459c74683db6d7a1f82a022`. The property buffer is capped
  at Android's 92-byte ABI size; the executable canary test checks it.
- GL recipe: VM `/home/zhaoyue/a2hlab/ws/westlake/framework/opengl-jni/` plus
  `tools/build_opengl_jni.sh` and `tools/gen_gl_forwarders.py`, commit
  `22b945321929987c86b35cd99f9f2d2f4283e82e`. Local snapshot `westlake-gl/`.
  Full GLImpl source is AOSP14 restored `frameworks/base/core/jni/` (SHA recorded).
  Existing N1 EGL/GLES2/3 registration stays; only GLImpl and its missing GLES1
  forwarders/bounds join this runtime, not a second registration of all GL APIs.
- Camera: local Westlake/00.Workspace/real-work search, VM framework/stubs search
  (`vm-jni-search.txt`), then bounded hw248 search found AOSP Camera source, not
  a verified OH implementation. `camera_info.cpp` is explicitly new code, using
  frozen OH6.1 SDK headers and the five real libohcamera exports in `camera-exports.txt`.
- Domain changes build on N1's real-work host callback. OH musl source evidence
  is `oh-musl-global-evidence.txt`; the ABI's DF flag alone was insufficient.
- Asset-fd source stays exactly FZ-003 blob `e47ede07`; N1 SurfaceControl/BLAST,
  VelocityTracker, CommonEvent, AudioSystem and other unchanged cache objects stay.

## Reproduction and environment exception

The outer authorized direct a2hlab VM compilation at 12:36 because Docker was
stuck stopping before container creation. No OrbStack restart and no board writes.
Use the same frozen compiler/sysroot hashes (recorded), not VM distro compilers:

```sh
orb -m a2hlab bash -lc 'cd /Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy && bash benchmark/2026-09-30-n2-native/build-all.sh'
python3 benchmark/2026-09-30-n2-native/prepare.py /Users/zhaoyue/orca/workspaces/westlake-generation-n1-aa57845c /Users/zhaoyue/orca/workspaces/westlake-generation-n2-candidate
```

`build-host.py` compiled twice and compared every byte. Docker-vs-VM N2 byte
comparison is **unavailable**, because Docker produced no N2 artifact. Do not
substitute a different source revision for that comparison. Build logs are included.
Incremental runtime inputs use authenticated B91 objects and explicitly invalidate
changed TUs; `restore_cache.py` records this, with frozen asset source compiled again.

Skia is **not merged**: cc-wiki's 12:26 layout probe falsified the header-layout
hypothesis. Dynamic root-cause work is separate; no valid patch was delivered.

See `HANDOFF.md` for the <=45 minute device window, controls, predictions and rollback.
Offline results are verified; namespace behavior, JNI execution and UI are unverified.

Source-preservation note: the copied OH camera header retains three upstream whitespace-only lines; generated CLI transcripts also retain their raw trailing blank lines. No source bytes were normalized to silence whitespace diagnostics.
