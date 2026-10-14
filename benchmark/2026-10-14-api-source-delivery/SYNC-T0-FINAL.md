# Final mapping handoff — frozen

Only this final pair is admitted. The earlier c874d2e1 mapping was pre-freeze and used moving HEAD 65484. It is superseded by this mapping with explicitly pinned, source-equivalent master **42c87ab42b896c68762b88f943ee40b6bd3bfa45**. Recipes are unchanged. No historical-equivalence claim is upgraded.

- Mapping: `benchmark/2026-10-14-api-source-delivery/release/source-build-mapping.json`
- Mapping SHA-256: `6e65f6fdcd06efb7a8cc8630b2cdd9f0b9de49631d9f5f0b2894e20589d4458e`
- Recipes: `benchmark/2026-10-14-api-source-delivery/release/recipes/recipes.json`
- Recipes SHA-256: `59132e2e7291ae4c3adde3311ae68bd8d090aabd163e127c16d133c2703421b1`
- Source/master revision: `42c87ab42b896c68762b88f943ee40b6bd3bfa45` (ancestor of current master).
- Signed315 input SHA-256: `250b6fd1fe90dbc63fd85f6501e98a343eb7b62f8bf997ea9a16d7fbfc5d788c`

## Required stable metadata (land before consumer)

- `benchmark/2026-10-14-api-source-delivery/frozen-inputs/java-source-resolutions.json` — `8c26facba9132ad9362458e94295cc2fa9127bd8cee3482f6658b8e978e9cb15`
- `benchmark/2026-10-14-api-source-delivery/review/native-source-resolutions.json` — `366d8eb2df2edb6d4d44abadfcb143b7c7226312cef6415c3538d93df4fc3573`

These two files are the only additional metadata slices absent from MAIN. Exact listing: `landing-metadata.txt`; pins: `freeze-metadata.json`. Neither references the mutable review/final-delivery-review.json. All 304 actual code/resource references and every non-null build entry resolve to exact MAIN/master blobs.

## T0 invocation after these metadata files land

From T0 worktree, where its already-reviewed generate.py lives; MAPPING points to this frozen producer JSON (data only). Its consumer resolves implementation/build references exclusively from MAIN. Keep recipes/recipes.json adjacent to mapping. Use a fresh output under T0’s delivery directory.

```sh
python3 benchmark/2026-10-14-api-source-delivery/generate.py build \
  --mapping "$WORKSPACES/westlake-harness-t4/benchmark/2026-10-14-api-source-delivery/release/source-build-mapping.json" \
  --mapping-sha256 6e65f6fdcd06efb7a8cc8630b2cdd9f0b9de49631d9f5f0b2894e20589d4458e \
  --out benchmark/2026-10-14-api-source-delivery/views-final
python3 benchmark/2026-10-14-api-source-delivery/generate.py check \
  --mapping "$WORKSPACES/westlake-harness-t4/benchmark/2026-10-14-api-source-delivery/release/source-build-mapping.json" \
  --mapping-sha256 6e65f6fdcd06efb7a8cc8630b2cdd9f0b9de49631d9f5f0b2894e20589d4458e \
  --out benchmark/2026-10-14-api-source-delivery/views-final
```

Do not pass --require-complete: the preserved315 contains missing APIs, stubs, partial source/build links and unknown historical bindings. New later Java javac rc0 is not historical DEX equivalence; J1/J7b producer rc0 still has strict wrapper rc2. One recorded legacy DevEco compiler dependency remains locally unresolved, not a build-entry substitution. No source or recipe command is executed by this mapping or renderer.
