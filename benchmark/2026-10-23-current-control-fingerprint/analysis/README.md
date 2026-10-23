# T116 — current control identity, metadata-only peer review

A control-file hash match establishes file identity, not runtime behavior or a failure cause. The current root and boot-copy hashes match the respective T115 historical generations; the two boards retain different generations.

The collector index already had an `ended` field on the first read. It was consumed again after the completed collector README was available: both reads are SHA `b4779795074855621295768e33fc7334f0e0a7ef4620da31fcd18e0362c40a59` (41,543 bytes), ended `2026-10-23T23:11:18+0800`. `first.json` is retained; `final.json` contains the completed per-path comparison.

| Board | Current boot | Init-selected root | Historical identity match |
|---|---|---|---|
| 61b | `61aa5791-fd69-4bbb-a7b5-333b5d913c81` | `/data/westlake-demo/toutiao/recovery-attempts/icon-manual-20261021-r3` | 37 rows match; no observed historical SHA mismatch |
| 5cd | `ecb84d86-f22f-4622-9501-143a26f39cf1` | `/data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012` | 28 rows match; no observed historical SHA mismatch |

Counts include init/config/member rows at distinct root and boot paths; they are not unique-code counts. **61b:** 41 genuine rows = 37 matches + 4 unavailable boot copies. **5cd:** 35 genuine rows = 28 matches + 4 unavailable boot copies + 3 historical unknowns (init cfg, root startup.expected.sha256, root boot-entry.sh). The four unavailable boot copies on each board are startup.env, startup.expected.sha256, members.tsv and boot-entry.sh; their root files exist.

**Parser-artifact exclusion:** 16 rows on 61b and 8 on 5cd have a 64-hex basename. Each was checked against the digest column of that board’s members.tsv and mapped back to the actual member filename. All 24 are excluded from missing-file and mismatch counts. Every actual member uses the filename column, never the digest column. Exact excluded paths and corresponding filenames are in `final.json`.

Current root/boot pairs match for **16** existing members on 61b and **13** on 5cd. All observed member hashes also match their own current members.tsv entries. This is not proof that a process has loaded those exact bytes.

| Key metadata | 61b SHA prefix | 5cd SHA prefix |
|---|---|---|
| `watchdog.sh` | `8bf74a08b71474e3` | `2b635ef1ea9e0054` |
| `entry.sh` | `ad76c65653e860ce` | `81dd055764b0737f` |
| `config-common.sh` | `f7c8e077dc11d9d7` | `638f47a6e40e4fdc` |
| `real-start-parent.sh` | `8e1d214e7e74b8b0` | `22ca89574f022322` |
| `real-start-parent-bounded.sh` | `f77f0f70dd1b64c3` | `fc0444a42b9b9ab9` |
| `startup.env` | `5a8f555e1af68da4` | `44993dbc61116a4e` |
| `members.tsv` | `b5fd108c2af5a077` | `328f0af2e95f6d0e` |

61b control identity matches T115’s T34 r3 family; 5cd matches T115’s accepted restored baseline. Historical boot IDs are retained separately in each board record. Same-name files are compared using full current paths and historical metadata mappings; no implementation file was opened. The second review additionally recognizes the accepted T115 hash of 5cd members.tsv itself, resolving one first-pass historical unknown without changing inputs.

Retry count and current manual/automatic mode remain **unknown**. No state-name inference, behavior claim, cross-board copy, policy change or root-cause conclusion is made. Extra 61b members absent from the 5cd inventory remain unqueried/unknown, not declared absent on disk.

Reproduce final review: `python3 benchmark/2026-10-23-current-control-fingerprint/analysis/compare.py final`. Inputs are only the CC index, accepted T115 JSON, its pinned historical SHA list and members.tsv. Full path/SHA/history-source references and input hashes are in `final.json`; no device, REA, implementation-content or stopped-flow access occurred.
