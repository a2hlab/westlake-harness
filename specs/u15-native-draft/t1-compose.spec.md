spec: task
name: "Compose the arrived U15 native members"
inherits: project
---

## 意图

Stage runtime94c3, host9e3a and both ANL b96a aliases on accepted U14 native content while awaiting NSD stubs and the single complete image rebake.

## 已定决策

- Exactly four payload paths change for three objects; no payload addition or deletion.
- Host and ANL native package lists both include org.jitsi.meet; host also publishes its resident runtime path.
- Preserve old BCP and images in staging as historical inventory, without a bundle descriptor or paired-build claim.
- Record full donor SHA, source snapshots and persistent double-build receipts; transaction bases remain explicit unset parameters.

## 边界

### 允许修改
- benchmark/2026-10-03-u15-native-draft/**
- specs/u15-native-draft/**
- tools/spec-checks/tests/u15_native_draft.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Arrived objects and owner aliases move atomically
  测试: u15_native_composition
  假设 Accepted U14 content and three double-built donors have exact SHA256 identities
  当 Native-only composition and both package lists are validated
  那么 Only four declared paths change and no bundle descriptor or execution claim exists

场景: Split alias or partial package routing is rejected
  测试: u15_native_composition
  假设 ANL and host must select the same native-domain packages
  当 An alias hash or one package list is inconsistent
  那么 Validation rejects the draft instead of claiming the Meet relocation wall moved

## 排除范围

- Rebuild donors, replace BCP, bake images, finalize transaction metadata or publish an executable package.
