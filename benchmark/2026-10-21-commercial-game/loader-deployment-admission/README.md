# G19 existing loader deployment and restoration admission

The unsafe assumption was that the old U13 package or an old `active_verified` state directly described the current boot. They do not. **The existing U7 transaction entry is reusable for G20; deployment is not yet signed ready.** A new U7 transaction needs an exact effective baseline and creates its own real journal. It does not require a fabricated historical owned state. This closes G19 entry discovery; G20 owns bundle assembly and the outer lane owns the device window.

The final outer receipt reports **285/285 effective U13 targets + prerequisites + bundle boot/JAR targets**, nine batches with remote rc=0, unchanged boot `a1d869b4`, and exactly the four public Boat r4 differences. Its persistent root is `$HOME/.local/share/westlake/commercial-game-20261021/loader-deployment-admission/outer-full-baseline-01`. This is explicitly an outer observation relayed by the user, already handed to G20; G19 did not reread it. The former full-baseline evidence gap is therefore closed at handoff.

## Exact reusable inputs

`$WORKSPACES` means the existing workspace parent resolved by `scripts/lab/lab_paths.py`.

The complete historical U13 bundle is:

`$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u13-effective-rebind/.artifacts/bundle-v4`

| Member | Original SHA256 |
|---|---|
| `bundle.json` | `91272eaf4cdda30b0c079575cd269959c6f6dab9f23a09a0fed567c20478bd28` |
| `native/package.json` | `85aef68eafbde98e6ac885264fe36f2f1e357618abf1d455de6ca15c0996cee6` |
| `native/native-checks/native-gates.json` | `c40faa79d197f023dbe47a62ae186d5eb5671f9b8f4a448924098fdd5f02f185` |
| `reference/runtime.txt` | `7ec4fef27cc61feb55522bf2c7e827a881a1defc10943150d7a60a5c954820a8` |
| `reference/boot-image.txt` | `fcb68d6155e4b4abcc064511969072617c8799375fb8bda2de42e40c0a16b010` |

Both `native/payload/android/lib64/libnativeloader.so` and `native/payload/route/libnativeloader.so` exist and hash to `b8be63d2f617ba202373e4a60b34cc4eadba84bcfe31e42b64cfe4f01bfa62f7` (773,928 bytes each). This is a reusable artifact/source package, **not an unchanged current-baseline or current-gate approval**. See `package-inventory.json`, `objects.json` and `u13-original/`.

G18 candidate is `$WORKSPACES/westlake-harness-g10-env/benchmark/2026-10-21-commercial-game/gles-loader-candidate/.private/build-01/candidate/libnativeloader-candidate.so`: 774,000 bytes, SHA256 `878c7019b1b78c8affbf9808d69fdc8478554273fe5d06d499b6775b7d004f23`. The corresponding `baseline/` file is the original b8be artifact. G18 main-tree landing `0dac7115db` is supplied by outer. Its ELF/build receipt is not itself a deployment bundle or updated native gate ticket.

## Actual boot and paired targets

The independently collected outer readonly receipt has before/after boot `a1d869b4-69a2-40a4-937e-4860f5b54239`, mountinfo 34,534 bytes, process table 11,465 bytes, and both alias hashes b8be. The visible parent is root `appspawn-x` PID 6274, PPID 1. This is a snapshot, not a fresh parent-birth/no-live-child window admission. Mountinfo is from `/proc/self/mountinfo`, not a claim of separately measured init namespace equivalence.

| Target | Current observed source | New candidate | Restore |
|---|---|---|---|
| `/system/android/lib64/libnativeloader.so` | `/data/westlake-demo/u13/sources/seq16` | 878c7019… | Unbind only the new owned layer, reveal saved original stack, verify b8be |
| `/system/lib64/westlake/route-a/74d1d6d48210ec5bf66ae43598655c3486b8873513821f13c2ffe15f0de552ac/libnativeloader.so` | `/data/westlake-demo/u13/sources/seq51` | 878c7019… | Same journal-controlled restoration, verify b8be |

Actual child 10946 historically mapped both aliases with distinct inodes. G16 peer established the paired publication rule (`namespace_gates.py:14–16`, `report.py:81–82`). Unique winner remains unknown and is **not** a new prerequisite for preserving the pair. Historical child observations are not current process admission. The G19 local HDC attempt failed with `Connect server failed` despite rc=0; `readonly-01/` preserves that failure separately and no retry was made.

## Existing entry and recovery boundary

All line references below address the archived, SHA-pinned originals in `sources/`, from main `scripts/lab/`.

- `deploy_generation.py:132–161` admits exactly one changed package file/live target in replacement mode. Two sequential replacements would expose a mixed pair across parent restarts. `:192–207`, `:317–361`, `:452–480` also require the corresponding owned state for replacement/upgrade. Six locally observed state files belong to older boots; none binds this boot. Do not manufacture a state file or edit its boot field.
- `u7_executor.py:95–124` expands the whole native package and reference hashes. It **always binds the boot group and runtime JAR**, even if bytes match. G20 must inspect that actual plan and preserve current bytes; describing this CLI as a literal two-file transaction would be wrong.
- `u7_executor.py:293–310` verifies actual baseline hashes, snapshots current mount stacks and creates a fresh journal. No historical deploy-generation ownership state is required. `:311–329` holds the parent stopped through all binds, verifies the complete expected set, then starts it once. A live child must fail admission via the existing stop/guard path; the review does not authorize generic process killing.
- `u7_executor.py:336–370` restores only journal-owned layers in reverse order, checks boot and original stacks/full baseline, then restarts the baseline parent. A restore failure leaves it stopped. `:187–265` cross-boot restoration is a different path requiring a real previous journal and persistent source identities; it is not an empty-state escape hatch.
- `u7_executor.py:139–171`, `deployment_native_gate.py:69–120` bind native manifests, gate inputs, static checks, frozen checks, boot-image checks and build provenance. Neither old gate receipts nor old reference files may simply be relabeled current. `deploy_generation.py:110–118` preserves single ART/OpenJDK and bridge checks; paired nativeloader aliases are not a reason to weaken them.
- `u7_executor.py:517–565` supplies the existing CLI and lock. `:380–389` requires actual apply/rollback through the existing OrbStack environment, not direct Mac DeviceIO. No new deployment tool is needed.

The minimal next action is G20's exact baseline/candidate bundle followed by the existing offline entry:

```sh
python3 scripts/lab/u7_executor.py --dry-run \
  --package "$CANDIDATE_BUNDLE" --baseline-native "$EFFECTIVE_BASELINE_BUNDLE/native" \
  --out "$G20_REPORT"
```

This is a command template, not a performed or passed preflight. Subsequent outer apply uses `--apply --serial ... --lane ... --journal ... --out ...`; recovery uses `--rollback` with that same real journal. Outer must bind the fresh lock/boot/parent identity/no-child checks, original power values and signed rollback, with <=30 minutes and restoration beginning by minute 20. G19 supplies no signature or device-ready assertion.

## Boat r4 preservation sources

The exact local captured controls are:

`$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r6-interactive-readonly/control/{binds.tsv,worker.sh,recover-v3-boat.sh,00_westlake_u13_recover-v3.cfg}`

`worker.sh:5–8` identifies `/data/westlake-demo/u13/boat-v2-20261013-r4`, `binds.tsv`, and table SHA256 `a10586a19ca0a812356e6dc65490f3e4a4f236e011021909bb174015c2c66cde`. `recover-v3-boat.sh:224` invokes this worker before READY. `worker.sh:53–80` checks preimages/metadata and logs ownership before and after each bind. These are source references, not scripts to rerun for G18.

All seven original rows, exact source/target paths, hashes and observed mount rows are in `boat-r4/layers.json`. Current public source files are `/data/westlake-demo/u13/boat-v2-20261013-r4/sources/` plus:

| File | Fresh public target SHA256 |
|---|---|
| `liboh_adapter_bridge.so` | `8ab85446f8b386c4a649576326d5f393669b3a22529874fb673eea7c3b1cd71e` |
| `oh-adapter-runtime.jar` | `6333bcab4ca2daad03965712deac6adf028a6ff0dfac04fc8ea91af177828852` |
| `liboh_android_runtime.so` | `94718e0d0b617a0f9a860e0b50b879b0d7d4639f32e8230b1f90f8e26e2c1354` |
| `libandroid.so` | `adc125f4dfb800c25d80e7d73216c8885fd64a31c6b91f064494166c63a59130` |

All four match the captured r4 table. The other three rows are Boat app-private signal-box/Unity/IL2CPP libraries and are outside the fresh fingerprint tool's coverage. No claim of seven-file fresh hash verification or newly located local binary copies is made.

## Evidence scope and landing

`outer-fingerprint-01/` preserves the original-function execution: runtime **124** files `fd464714645b`, boot **36** files `ee927db88a67`, unchanged boot. This is tool coverage, not 321-file coverage. `baseline-comparison.json` is a diagnostic against the **historical bundle's old reference overrides**, not the final outer 285-target effective-baseline method. Its 24 differences/159 uncovered historical expectations must not be promoted to fresh blockers after outer's full effective-target receipt. It illustrates why copying those old references verbatim is incorrect.

`FIRST-SLICE.md` remains the earlier snapshot; this final README and `admission.json` supersede its unknown-current-state conclusions. `source-index.json` records original and portable archived hashes; original private receipts remain persistent. Only user/home prefixes in archived text are normalized. No devices, environ, rejected channels, candidate source, deployment tools, T37/T38 pins or old landing lists were modified. No G18 regression was repeated. Local evidence integrity checks are recorded in `validation.json`; no U7 bundle preflight or game success is claimed.

Use `landing-paths.txt` and `SHA256SUMS` for this incremental G19 package. Outer performs landing; no push or direct collaboration-bus retry was attempted.
