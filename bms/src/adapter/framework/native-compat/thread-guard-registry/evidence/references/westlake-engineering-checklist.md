# WestLake Engineering Checklist

## Boundary

- Which boundary is touched?
- What Android behavior is being preserved?
- What OpenHarmony behavior is mapped?
- What layer owns the fix: Java, JNI, native runtime, OS boundary, build/image, or device config?

## Evidence

- What exact command was run?
- What device or host was used?
- Where are hilog/tombstone/screenshot/test outputs?
- Is this host-only, QEMU-only, or true-device?

## Status

Allowed status labels:

- `build_pass`: build/link only.
- `stub`: skeleton, fake, default value, bypass, or partial shim.
- `real_impl`: behavior implemented with tests.
- `device_verified`: real implementation verified on target device.

## Shim / Stub / Bypass

Every shim/stub/bypass must state:

- Owner.
- Why it exists.
- Removal condition.
- Test coverage.
- Whether it is app-specific or common adapter capability.

## Trial Discipline

- Same error 3 times: stop guessing.
- Same file rewritten more than 2 times: merge constraints into a plan.
- Every trial records effective actions, ineffective actions, and next evidence.

## Required Handoff Sections

- Boundary.
- Evidence target.
- Environment.
- Status.
- Proven.
- Not proven.
- Failed.
- Next evidence.
- Shim/stub/bypass inventory.
- Memory/skill/CI/review updates.
