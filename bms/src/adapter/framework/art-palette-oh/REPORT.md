# ART Palette OpenHarmony boundary

## Result

The target boundary replaces AOSP's host-only priority cache with real Linux
thread-priority operations. `PaletteSchedSetPriority` calls `setpriority` using
the exact Android managed-priority mapping; `PaletteSchedGetPriority` reads the
kernel value with `getpriority` and maps it back. A fake-success mutant is
rejected.

The AArch64 DSO builds twice with identical bytes, SHA256
`76f11378883d5501485f7f269e3049c3c616582b43522c99227fb6490f6dccbc`.
It needs exactly `libc.so` and the real `liblog.so`, imports both priority
syscalls, and has no RPATH/RUNPATH/TEXTREL. This is
`ARTIFACT_VERIFIED_NOT_PRODUCT_ACTIVATED`. Its source and exact export map are
now inputs to the Route-A v13 candidate, replacing the frozen v12 host fake;
neither generation has run on a device.

## Boundary

- Boundary: ART Palette C ABI to the OpenHarmony/Linux thread scheduler and
  diagnostic services.
- Android behavior: managed priorities 1..10 map to nice values
  `19,16,13,10,0,-2,-4,-5,-6,-8`, exactly as frozen AOSP target Palette.
- OpenHarmony mapping: real per-thread `setpriority/getpriority`; crash stack
  diagnostics use the existing real liblog-to-hilog boundary.
- Fix layer: adapter-owned platform Palette provider. ART and the APK are not
  modified.

## Evidence target

- What this proves: priority changes are no longer an in-memory fake, error
  results reflect the actual kernel syscall, unsupported capabilities do not
  claim functional success, and the ARM64 artifact is deterministic.
- What this does not prove: OH QoS/cgroup policy, final namespace load order,
  Route-A activation, Unity startup or first frame.

## Environment

- Host: native host test plus network-disabled target container.
- Device: not used.
- Tool path: `adapter/framework/art-palette-oh/tests/`.
- Artifact path: `.work/art-palette-oh/{host,target}/`.
- App: common ART platform boundary used by CardWords bring-up.

## Status

- Label: `host_tested / target_artifact_verified`.
- Product activation: false. The Route-A v13 candidate consumes this source
  and must still pass its complete provider/namespace gate and true-cold test.
- Why: host kernel readback, mutation rejection and deterministic ARM64 ELF
  structure are proven, while final generation/device behavior is not.

## Proven

- Invalid managed priorities and null outputs fail with typed Palette errors.
- A child process is really moved to nice 19 and read back as managed priority
  1; a build that returns success without the syscall fails the test.
- The exact target symbols contain non-empty scheduler implementations and
  unresolved `setpriority/getpriority` imports owned by Musl libc.
- Target DSO membership is two exact dependencies: libc and liblog.
- All source and semantic references are copied below this project and hashed
  in `var/evidence/PROVENANCE.json`.

## Not proven

- Per-thread OH QoS/cgroup translation beyond Linux nice values.
- Device permissions for favorable negative nice values after stock DAC.
- Device lazy-load order and runtime scheduling receipts for
  `libartpalette-system.so`.
- Any product or first-frame claim.

## Failed

- The prior AOSP host fake kept priorities in a private map and returned OK
  without affecting a real thread. It is forbidden from future target provider
  generations.
- The fake-success scheduling mutant is rejected by real child readback.

## Next evidence

- Command: `adapter/framework/art-palette-oh/tests/run_all.sh`.
- Expected output: host real-priority PASS, one mutant rejected, target DSO
  deterministic twice with two real scheduler imports.
- If it fails: reject the Palette provider; do not fall back to the host fake
  or report a successful scheduling operation.

## Shim/stub/bypass inventory

| Capability | Current behavior | First-frame disposition | Removal condition |
|---|---|---|---|
| Thread priority | Real `setpriority/getpriority` | Functional, not stubbed | Add OH QoS only when its typed provider is frozen |
| Trace | Explicitly disabled; enabled=false, begin/end no-op | Diagnostic only; may be called but does not feed runtime state | Map to HiTrace when required |
| Crash stacks | Real liblog/hilog write | Crash-only | Add typed DFX sink if required |
| JIT zygote ashmem | `NOT_SUPPORTED` | Compiled out by this non-Bionic ART build | Implement if a Bionic zygote-JIT build is admitted |
| odrefresh/dex2oat reporting | Disabled/`NOT_SUPPORTED` | Server/tooling, not app child first frame | Map when on-device compilation is admitted |
| Dex/OAT/JNI/lock reporting | Disabled/`NOT_SUPPORTED` | Diagnostics; callers do not consume state | Map when telemetry is required |
| Task profiles | `NOT_SUPPORTED` | Current provider `libart.so` has no import | Map to frozen OH QoS provider before admitting a consumer |

No security operation, process lifecycle bypass, global pthread/signal broker,
APK patch or fake scheduler success is introduced.

- Item: explicit disabled diagnostic/unsupported Palette capabilities listed
  in the table; scheduling itself is real and is not a stub.
- Owner: `adapter/framework/art-palette-oh`, with libc owning priority syscalls
  and liblog owning crash diagnostic transport.
- Why it exists: ART loads one typed platform Palette provider even where OH
  does not yet expose every Android diagnostic/tooling service.
- Removal condition: replace each unsupported row only with a frozen typed OH
  provider when an admitted consumer requires that capability.
- Test coverage: real child priority readback, invalid/error cases, explicit
  capability results, fake-success mutant, two deterministic ARM64 builds and
  dynamic-symbol/NEEDED verification.
- App-specific or common: common ART-on-OH boundary; current evidence uses the
  CardWords provider generation.

## Memory/skill/CI/review updates

- Memory: replaces the v12 audit's dormant fake-Platform warning for the only
  startup-functional Palette surface, thread priority.
- Skill: boundary-first, explicit capability ledger and no-overclaim rules were
  applied.
- CI: `tests/run_all.sh` is ready for the unified Bionic/Musl lane after the
  final provider generation is frozen.
- Review checklist: exact mapping, real syscall imports, error propagation,
  unsupported capability honesty, two-run target identity and no product claim.
