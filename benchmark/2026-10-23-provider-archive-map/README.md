# G38: frozen-input layout found, persistent archive binding still unknown

**Bounded stop.** The missing775c8ae8 script cannot be recovered by treating a same-named outer source tree as the frozen input. This card establishes the recipe's input-mount and log layout, not the location of the historically executed generation. No exact archive/member mapping was found in the followed references. G37 remains unchanged.

## Evidence progression (at most two reference hops)

1. Main `knowledge/toolchains/art-r155/recipe/SHA256SUMS:285–291` explicitly pins the provider README, REPORT, build_generation and import_inputs records. Their four bytes match the declared hashes (`b3e3f725…`, `8937f1cb…`, `efb2b663…`, `0e4b7577…`). Main recipe README identifies the vendored b6-r155 source and already identifies its inner script as **fd306585**, not775c8ae8.
2. `build_generation.sh:10–29,61–68` defines PROJECT_ROOT as SCRIPT_DIR/../../.., generation/frozen/input-check/work/artifacts/log paths, and mounts FROZEN at `/inputs:ro`. `REPORT.md:47–48` explicitly identifies `provider-inputs-v12-nobroadstub`. These are actual text references, not a guessed generation ID.

The copied mapping source is `evidence/build_generation.sh.txt`; line numbers are unchanged. `results.json` records each hop with source SHA through `input-pins.json` and exact reference text. Numbered provenance/import/upstream excerpts preserve their original source-file hashes and line numbers; they do not claim full closure. The old README's device/Soong historical conclusions are not inherited by G38.

| Required item | Result |
|---|---|
| Frozen archive filename/member | Unknown; no exact archive reference established |
| `/inputs` mapping | Recipe declares `$GENERATION_ROOT/frozen:/inputs:ro`; actual historical host mount remains unbound |
| Exact cross_compile source |775c8ae837306c06a24fc0e2562291f63ee3854bdb5154d82c48a2ee37a6b93a not recovered or analyzed |
| Original compile stdout/stderr/rc0 | Unknown; recipe declares `evidence/build{,-repro}.stdout/stderr`, not actual recovered receipts |
| Target identities | Unwindstack d2c1cbc7 remains manifest-declared; sigchain6d5d5538 remains unbound, never replaced by ea7becd0 |

## Actual bounded absences

- The README's exact local `$WORKSPACES/westlake-harness-bms-deploy/bms/src/.work/b6-r155` root exists. Its v12 `frozen.sha256`, `provenance.tsv`, and frozen inner-script paths do not. Only these three exact paths were checked; no recursive search.
- Outer probe01 checks `adapter/.work` and its two descendants plus `adapter/build/provider_generation/build_generation.sh`: all absent, original SSH rc1. This candidate root is not the build script's PROJECT_ROOT formula.
- Outer probe02 checks the known build-run root's `.work` and its two descendants: all absent, original SSH rc2. This is the formula-derived candidate in that one known root. It still does not establish the original historical execution root.

Both probe argv/stdout/stderr/rc are copied unchanged, with all12 persistent raw receipts indexed in `outer-raw-index.json`. These are outer read operations; this reviewer issued no remote command. Neither probe establishes whole-machine absence or permits another guessed root.

## Next input required, no new path guess

An original archive/member index or executed root/mount record binding **provider-inputs-v12-nobroadstub** is required before asking outer to read another location. Within that established root, the exact relative inputs are `frozen.sha256`, `provenance.tsv`, and `frozen/adapter/build/inner/cross_compile_arm64.sh`; the script must hash to775c8ae8 before analysis. Original build stdout/stderr/rc must be supplied separately. No current concrete remote read request is justified by the available binding, so `remote_paths_to_read_now` is empty.

## Verification

```sh
python3 benchmark/2026-10-23-provider-archive-map/check.py --self-test
# Evidence host only: --private additionally checks the12 outer raw files.
CARGO_TARGET_DIR=benchmark/2026-10-23-provider-archive-map/.private/cargo-target cargo test --offline --manifest-path tools/spec-checks/Cargo.toml --test provider_archive_map -- --nocapture
```

Actual results:19 input pins,4 negative refusals (missing reference, wrong script promoted, missing logs promoted to build completion, sigchain substitution); Rust1 passed/0 failed/0 ignored. Logs are persisted under this card's `.private/{check-01,rust-01}` and indexed in `raw-index.json`. These are host-only evidence tests, not runtime builds. No producer executed, device/remote/Orb/REA/debugger action, main/G37 modification, commit or push. Game first frame remains unknown.
