# Original d4fa bridge sources

The earlier input inventory was insufficient source delivery: 37 of the 50 original bridge translation units had no identical tracked copy in the audited MAIN tree. This package preserves all 50 as a coherent original snapshot, including the 13 already present elsewhere; `snapshot.json` maps each to its original SHA and existing MAIN paths. It also preserves the actual later source layers, project dependencies, licenses and original recipes. No source text was modernized or path-rewritten.

| Layer | Identity evidence | Location |
|---|---|---|
| Original 50 translation units | All 50 match original bridge15 artifacts source SHA | `base/` |
| Generated adapter source | Exact recorded transform output `87fc9f39…` | `generated/` |
| Final nine focus34 object inputs | All nine original command+dependency `.key` stamps independently reproduced | `focus34/`, manifest key records |
| Ability38 policy and input source | Both source SHA match original producer artifacts | `ability38/` |
| Final mc46 MediaCodec replacement | Exact source `d6e470ec…`, original recipe retained | `mc46/` |
| Author/upstream licenses | Unchanged LICENSE/NOTICE files; individual source headers retained | Each source subtree |

`base/` is an earlier layer, not a replacement for the later layers. The final link uses 52 original objects with the mc46 replacement; the 50-base count must not be described as the final object's complete fresh rebuild. The focus stamp checks use original command strings and full recorded compiler dependencies, not filenames or code similarity. All 138 payload files (2,588,795 bytes) have original-source aliases and SHA in the manifest. Role counts overlap because original header inventories also list translation units.

## Build and recovery

`build-entry.json` pins the existing MAIN production entry, recipe and input set. That entry already reproduced baseline d4fa and builds the single-owner AudioTrack candidate; this collection task did not rebuild anything. From the repository root:

```sh
python3 benchmark/2026-10-20-t18-audiotrack-production/build.py \
  --inputs "$T18_INPUTS" --sdk "$OH_SDK_NATIVE" --out "$T18_NEW_OUTPUT"
```

The default is a pin-check preview. A separately authorized build adds `--execute` and requires a fresh output directory. This is an incremental recipe, not a claim of rebuilding every historical object. `T18_INPUTS` must contain the exact archived relative input tree; `OH_SDK_NATIVE` must match the existing production SDK pins. The large SDK, upstream headers and object/library dependencies belong in the outer durable archive. The original 50-source/900-header/object/record supplement has been requested from cx-seal; no remote receipt is invented here. The original 900-header SHA map is retained in `snapshot.json`.

Original producer scripts in `original-recipes/*.original.txt` are unmodified historical evidence, not portable executable entry points. Some preserve original author paths. Their original execution logs and artifact records are hash-indexed in `snapshot.json` and requested for separate archival. The original final mc46 stdout/stderr/rc was not located. New exact baseline relink receipts must not be relabeled as those missing historical logs.

Two original header comments contain an author path. Their exact file exceptions are proposed separately and approved by outer; neither source byte is changed. No personal application data, screenshots, device logs or credentials are included.
