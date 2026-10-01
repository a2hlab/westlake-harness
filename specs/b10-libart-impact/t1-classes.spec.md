spec: task
name: "Index exact U8 jars and scan whole DEX missing-class sites"
inherits: project
---

## 意图

Index U8 boot classes and all app definitions, then retain executable and declaration references with staged startup and later reachability.

## 已定决策

- SHA-check all 166 APKs and every DEX; compare all app DEX definitions together before marking a type absent.
- Include invoke owners and signature types, field owners/types, type operations, superclass/interface and declaration sites.
- Reuse staged RTA for Application, providers, launcher and later components; non-reached sites stay unanchored rather than becoming proved later-only.
- Keep runtime-jar-only providers separately from truly absent classes; do not add classes or infer a repair from absence alone.

## 边界

### 允许修改
- benchmark/2026-10-01-b10-libart-impact/**
- specs/b10-libart-impact/**
- tools/spec-checks/tests/b10_libart_impact.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Deployment and complete class membership bind the inventory
  测试: b10_libart_identity
  假设 Exact U8 jars and a class defined only in a second app DEX
  当 Missing-class membership is computed
  那么 Artifact drift is refused and the cross-DEX class is not reported absent

场景: Signature gaps and startup roots stay visible without false later proofs
  测试: b10_libart_classes
  假设 A missing invocation parameter an Application onCreate and an unanchored library method
  当 Whole-DEX references and stages are analyzed
  那么 The parameter and Application witness are retained while the unanchored method is not labeled proved later-only

## 排除范围

- Adding hidden classes to make references resolve or changing verifier/class linker semantics.
