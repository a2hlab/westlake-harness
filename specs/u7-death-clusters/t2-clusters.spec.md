spec: task
name: "Rank cause clusters with implementation source and N8 scope"
inherits: project
depends: [t1-evidence]
---

## 意图

Produce a ranked wall table for U8 JAR and native selection with precise evidence and reusable implementation provenance.

## 已定决策

- Partition all thirty-two apps once into named walls with layer count and evidence; sort by descending blocked-app count.
- Class A Wikipedia and AppManager belong to the outer-assigned window race; B-class app shatteredpixeldungeon and termux form a separate unresolved white cluster.
- Record source path commit and file hash for implementations found in Westlake 00.Workspace or real-work; distinguish inspected implementation from verified same-wall repair, and use none when no verified repair exists.
- Explicitly mark N8 in-flight native membership and blockers that N8 does not yet prove fixed, including private zlib versus root zlib visibility.

## 边界

### 允许修改
- benchmark/2026-10-01-u7-death-clusters/**
- specs/u7-death-clusters/**
- tools/spec-checks/tests/u7_death_clusters.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Clusters partition rank and provenance without inventing fixes
  测试: u7_death_clusters
  假设 Bound thirty-two evidence rows and source audit with outer classification
  当 The machine-readable clusters and report are generated
  那么 Counts sum to thirty-two each app appears once layers and evidence exist ordering is descending and every implementation has a path commit hash or explicit none

## 排除范围

- Applying source fixes, claiming all N8 targets will light and modifying earlier scoring results.
