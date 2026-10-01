spec: task
name: "Cross installer-selected icon formats with signed U8 and observed tiles"
inherits: project
depends: [t1-selection]
---

## 意图

Emit one JSON and CSV row per key, intersect selected WebP icons with own-tile witnesses and retain the separately signed U8 rerun without overwriting the initial full-sweep result.

## 已定决策

- Bind selected original sequential directories and exact APK/package to record.json; exclude invalid concurrent runs.
- Own tile requires the exact package and desktop Activity under sceneboard; another package or alias is not a match.
- Distinguish observed tile, searched-no-match, cold desktop, and missing snapshots; none imply app UI.
- Preserve full-sweep and supplemental rerun columns and format counts in machine outputs.

## 边界

### 允许修改
- benchmark/2026-10-01-icon-format-scan/**
- specs/icon-format-scan/**
- tools/spec-checks/tests/icon_format_scan.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Exact tiles and missing evidence remain distinct
  测试: icon_format_tiles
  假设 An exact app tile, another package tile, hidden tile, cold desktop and missing snapshots
  当 Snapshot witnesses are classified
  那么 Only the exact tile is positive and cold or missing evidence has unknown status rather than an absence verdict

场景: JSON and CSV retain the complete cohort and separate rerun
  测试: icon_format_outputs
  假设 A complete key cohort and a supplemental signed rerun
  当 Machine tables are emitted
  那么 Every key occurs once and original outcomes remain alongside supplemental observations

## 排除范围

- Reading screenshots as a new signoff or claiming WebP alone explains every missing tile.
