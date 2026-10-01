spec: task
name: "Compose U10 policy and native owner visibility"
inherits: project
depends: [t1-shims]
---

## 意图

Add the outer-approved libstdc++ policy edge, expose the resident compat owner without duplicate abort state, and inspect the exact OpenSLES owner before admitting a facade. Bundle verified changes with the GNU shim for cx-t0 integration, without deploying. The discovered Android/OH ABI mismatch moves actual audio forwarding to dependent task t3; this task cannot claim Mindustry repaired.

## 已定决策

- The policy JSON changes only shared_sonames by appending libstdc++.so; mirror that one decision in the compiled header, never add libc++.
- The baked component is libnativeloader.so, not the unchanged ANL backend libapp_native_loader.so.
- Bind compat against its sealed resident reference with NOLOAD checks; prefer an already-mapped default view only when all three symbol addresses match, otherwise use the sealed view and verify app identity. Never load a second default-namespace compat owner.
- Include fd-plus and Meet as abort-visibility beneficiaries, not as already repaired apps.
- Reject direct OpenSLES casts using the SHA-pinned owner's actual IID/output layout. Distinguish public API/IIDs from compiler/runtime internals in the complete dynsym inventory; no always-failure engine stub.
- Preserve the historical full-suite failure and record the fresh master rerun after outer's missing-receipt repair.

## 边界

### 允许修改
- benchmark/2026-10-01-u10-native-shims/**
- specs/u10-native-shims/**
- tools/spec-checks/tests/u10_native_shims.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: One additive policy edge and its compiled consumer
  测试: u10_policy_additive
  假设 Pinned six-entry policy and two payload copies of libstdc++
  当 Policy and native-loader candidate evidence are checked
  那么 Only libstdc++ is added, no exports regress, call differences stay within policy consumption and bridge search selects android/lib64 not westlake_native

场景: Existing compat owner is not duplicated
  测试: u10_abort_visibility
  假设 Resident sealed compat and an app namespace with unresolved abort and GNU imports
  当 The exact-owner visibility helper is replayed
  那么 It inherits only that resident compat, validates symbol identity and refuses missing or wrong owners without a loading fallback

场景: OpenSLES admission rejects an incompatible direct cast
  测试: u10_opensles_abi_evidence
  假设 Verified OH OpenSLES snapshot with a real engine and Android consumer layouts
  当 Its complete exports, IID bytes and GetState store instruction are checked
  那么 Evidence distinguishes 46 public entries from 94 internal symbols, shows the eight-byte output mismatch and holds the unimplemented facade instead of pretending to repair Mindustry

## 排除范围

- Board execution, t20 repair claims, new namespace policy outside exact requested SONAME edges, Boolean stubs, implementing the ABI-converting OpenSLES facade tracked by dependent task t3.
