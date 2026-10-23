# T115 — launch-policy provenance, metadata-only first slice

**Historical control generations differ; current policy values remain incompletely bound.** T106's 18 core backing files and HAP comparison does not cover this control chain. Event state names and three observed sequences do not establish a configured retry limit.

| Evidence level | 61b | 5cd |
|---|---|---|
| Actual historical identity | T55 boot350d374d, root `icon-manual-20261021-r3`; root and boot-copy SHA listing includes watchdog8bf74a08, entryad76c656 | T52 R4 boot89388a7b restored watchdog2b635ef1, entry81dd0557; `actual-review.json#/boot_phases/3/key_copies`, independently accepted restoration |
| Publication meaning | T34 manual-icon r3 generation. T34 final signoff retains r3 as recovery baseline | T52 candidate was withdrawn; original baseline restored, no full contract PASS |
| Explicit config record | Startup serial61b, TAP_WAIT_POLICY=`until-human-or-stop-or-boot-change` | Startup serial5cd, same TAP_WAIT_POLICY; other SHA bindings differ |
| Retry-mode documentation | Published manual-reentry family; current numeric limit unknown | Historical base README explicitly describes TT_MAX_ATTEMPTS=3, automatic retry and 5/10-second backoff; **not a verified current parameter** |
| Later actual observation | T61 cfg7b9f2c0e unchanged; T85/T87 boot61aa5791, ordinary T87 tap followed by child6291 and t90 feed | T109/T112 bootecb84d86: recorded seq1/2/3 and RETRY_LIMIT, subsequent single tap no new child; T114 foreground/stage receipt is outer-supplied context |
| Remaining identity gap | Selected T85/T87 receipts do not supply a complete same-boot control SHA/parameter binding | Selected T109/T112 reports do not supply current root+boot-copy control hashes; shared root pathname does not prove unchanged bytes |

## Precise metadata sources

All 17 input files are SHA/size pinned in `results.json#/source_pins`, with line-numbered excerpts where useful. No referenced implementation is opened by the reproducer.

- T34 `reentry-retirement-01/deploy-package-r3-root/generation.json:4–13`: root, serial and expected identities. This generation file alone is preparation, not deployment proof.
- Its `CHAIN.json:82–87,122`: actual init target `/system/etc/init/01_westlake_u13_toutiao.cfg`, r3 SHA7b9f2c0e; **generated payload/recovery.cfg must not replace the live init cfg**, which uses a different service/binding.
- T55 private `raw/02-fresh/rootsha_all.stdout:7,10,22–24`: entry, members, startup, expected and watchdog hashes, followed by boot-copy hashes. T55 `static-r3.json` supplies the boot/root binding.
- T34 `window-05-public/final-signoff.json#/recovery`, `/source_build_map`, `/archive`, `/root_independent_archive_recheck`: signed recovery reference and source/build/archive chain. Original archive 5,982,325 bytes, SHA23d2f7fb…; 10,479 members recorded verified. This card pins that signed metadata, not a fresh archive or implementation-byte verification. Signoff's ordinary return was warm; natural-exit reentry was not observed there. Later T87 is separate observation evidence.
- T47 `baseline/startup.env:2–14`, `baseline/members.tsv:1–4`: historical 5cd configuration and member identities. Its enabled/approved fields are historical only.
- T52 `review/actual-review.json#/boot_phases/3`, `execution-review.json#/remaining`: exact restored baseline identities and candidate-not-retained acceptance; recovered baseline final feed was visually accepted, without a full contract PASS.
- `2026-10-19-toutiao-icon-reentry/README.md:8–11` and `2026-10-12-toutiao-recovery-candidate/README.md:94`: explicitly documented historical base retry behavior. No source implementation was read to expand it.
- T61 results:6,34,37,40–41; T85/T87 README; video-tree T109/T112 results: actual observation context, not parameter declarations.

## Minimal remaining evidence

Prefer existing receipts, without new device work by this lane: same-boot board/boot + live init cfg SHA; exact-root startup.env/startup.expected/members/entry/config-common/boot-entry SHA list; existing boot-copy deployment hash manifest. For implementation generation use existing approved hash provenance only—do not read prohibited watchdog or aliases. If unavailable, leave unknown. Numeric retry/mode requires an explicitly bound parameter/schema record; event counts are insufficient.

The reviewed historical roots are board-specific. Serial, ROOT, entry, members, startup and init bindings differ. No current cross-board recovery package or blind-copy recommendation is justified. No new activation permission is supplied.

## Reproduce

```sh
python3 benchmark/2026-10-23-launch-policy-provenance/collect.py --main "$WORKSPACES/westlake-harness" --video "$WORKSPACES/westlake-harness-video" > "$HOME/.local/share/westlake/t115-outer-review-20261023/replayed.json"
cmp "$HOME/.local/share/westlake/t115-outer-review-20261023/replayed.json" benchmark/2026-10-23-launch-policy-provenance/results.json
```

The collector has an explicit metadata-only input list and never follows source references. Private original execution receipts remain in `.private/`. Zero device/remote/REA/build actions; no stopped source or renamed watchdog read, no patch, commit or push. author_commit=null.
