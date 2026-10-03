# U15 outer review packet: thirteen classes, strict rebinding and Jitsi observers

The earlier **204 auto-identical** preview was too broad for a strict review: its normalizer discards numeric source `line` and `sequence`. Fresh exact comparisons show **198 equal + 6 source-line shifts**, not 204 field-identical findings. All six are listed for explicit outer review; no risk field is erased here. The ANL observer gap is also real: its Jitsi routing change has no ANL-specific marker and fd-meet is outside the current U16 signed population, not proven lit.

| Item | Fresh result | Review material |
|---|---|---|
| NSD8 + trampoline5 | 13 exact additions / 0 identical in added set / 0 unexpected; source blobs 13/13 | `class-review.md`, `classes.json`, original per-class DEX dumps/diffs |
| Registry | 198 equal / 6 line-only differences / 0 new, IDs independently recomputed | `registry-review.md`, `registry-mapping.csv`, `registry-comparison.json`, `changed-findings.json` |
| G2 entry | Four exact outer commands, not executed | `g2-replay-commands.md` / `.json` |
| ANL dual aliases | Jitsi list addition, not mechanical relink; current covered moves 0, historical conditional 1 | `anl-review.md` / `.json`, fresh strings/disassembly/dynamic/open outputs |

Fresh raw class checks return 1 because exact additions are not approved here. U14 native check returns 0; U15 returns 1 because the active registry is deliberately untouched. ANL strings returns 1 for its one addition; disassembly/dynamic/open each return 0. These are evidence exits, **not complete production PASS**. `gate-exits.md` lists every command. Original raw bytes are retained in persistent `.artifacts/raw/` with SHA256; public logs only replace workspace/home prefixes with tokens and have separate SHA256 receipts.

## Ground-truth inputs

- Candidate U15 common `29c8a62c…`, 61b `8a260cec…`; planned U14 BASE common `12d30eb0…`, 61b `b0f74132…`. Full hashes and exact paths are in the G2 JSON and original composition receipts. They are candidate content, not proof that U14 has promoted.
- U14 native manifest `3460435a…` / inputs `11001e6e…` → U15 `4d3b6568…` / `4e25b830…`.
- Stubs `87cf65cc…`→`94a94905…`: 268→276 classes, eight additions. Runtime JAR `0349eb83…`→`20e748e5…`: 219→224 classes, five additions. Full hashes, all-DEX extraction receipts, source commits and raw method signatures are retained.
- Frozen scan-manifest source SHA and exact old/new source lines are verified for every changed finding. Complete trace and sequence comparisons stay in JSON; absent N2 function/evidence fields are not fabricated.

## Reproduce

```sh
python3 benchmark/2026-10-03-u15-outer-review-packet/collect.py
python3 benchmark/2026-10-03-u15-outer-review-packet/collect_anl.py
python3 benchmark/2026-10-03-u15-outer-review-packet/report.py
python3 benchmark/2026-10-03-u15-outer-review-packet/test_packet.py
CARGO_TARGET_AARCH64_APPLE_DARWIN_LINKER=/usr/bin/cc cargo test --manifest-path tools/spec-checks/Cargo.toml --test u15_outer_review_packet
```

The cold test uses only landed evidence/source snapshots, never `.artifacts` executables or sibling APKs. Collectors read exact persistent packages; missing/mismatched sources, SHA, descriptors or mappings refuse. No board access, VM, remote oatdump, build, registry apply, gate edits or replay-entry edits occur. Outer must review additions and all six strict differences, apply its own rebindings after windows, rebind to actual promoted per-board U14 BASEs, then execute fresh Mac/VM/G2 commands. Everything remains disabled.
