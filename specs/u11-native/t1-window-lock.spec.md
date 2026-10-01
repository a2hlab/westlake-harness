spec: task
name: "U11 CPU window shim and honest owner-route evidence"
inherits: project
---

## 意图

Replace the obsolete root libandroid owner with a small donor-based CPU lock shim, following outer ACK(90) 21:46:12. Deliver offline behavior and consumer evidence without confusing individual-ELF ABI comparison with dependency-owner union or target namespace acceptance.

## 已定决策

- Copy N10 donor lock:980/post:1145 from SHA c8772d05; current runtime ac59dec0 remains unchanged.
- Export only lock/post, SONAME libandroid.so; dependencies are current liboh_android_runtime.so, libsurface.z.so and libc.so.
- Normalize Android wrapper windows through resident oh_anw_get_oh; SET_USAGE opcode5/usage3, byte stride@8, format@20 and pixels@32.
- Serialize per-window ownership, expand dirty bounds, respect MapWaitFence fence ownership; no positive-fence failure bypass.
- Compare all 268 old-root exports against shim plus runtime; missing exports require explicit outer approval, pending is not passed.
- Run canonical abi_diff --calls on every lock or NEEDED-libandroid consumer, retain differences and failures, and separately report union resolution.

## 边界

### 允许修改
- benchmark/2026-10-01-u11-native/**
- specs/u11-native/**
- tools/spec-checks/tests/u11_native.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Donor-derived CPU pixels preserve known RGBA buffer ABI
  测试: u11_window_pixels
  假设 A SHA-checked donor and mocked OH buffer with padded RGBA byte stride
  当 The generated lock/post implementation operates on its normalized owner
  那么 Pixels, format, stride and reserved words match Android ABI, full dirty bounds are returned and the same OH buffer is posted

场景: Failed and concurrent operations retain ownership discipline
  测试: u11_window_ownership
  假设 Missing owner, usage failure, request failure, fence failure, invalid handle, failed post and concurrent locks
  当 Eleven behavior fixtures execute the donor-derived implementation
  那么 No failed positive fence is bypassed, no successful fence is double closed, abandoned dequeues are cancelled and each window holds only one buffer

场景: Consumer evidence distinguishes partial acceptance from deployment
  测试: u11_window_identity
  假设 Pinned 166 base APKs and matching individually SHA-checked split archives
  当 Reports cover 21 keys/26 lock DSOs and all 37 keys/171 NEEDED-libandroid DSOs
  那么 Union resolution has no consumer breaks, raw individual-ELF failures are preserved and any unapproved missing export plus unmeasured single-owner mapping remains pending

## 排除范围

- Final generation rebinding, namespace visibility, single-owner maps and zero screenshot regression remain separate acceptance gates.
- This task does not claim all OH pixel formats/capacities validated or new YV12 geometry routing implemented.
- libjnigraphics, OpenSLES conversion and native-soname repair are separate ordered clusters.
