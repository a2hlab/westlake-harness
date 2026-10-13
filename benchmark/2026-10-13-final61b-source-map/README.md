# Final61b f28 source files — disabled

The signed v1 map contains811 file sources, not940:129 APKs are checked through the original package/nonfile chain. F28 adds13 file targets and one APK, giving824 file sources plus130 APKs =954. Putting APKs into `sameboard.source_files` violates its original subset guard. No source or acceptance condition is excluded here.

`preview-disabled/gaps.json` has zero static source gaps and three explicit unknowns: Boat `binds.tsv` and `worker.sh` require actual61b BMS UID and all seven target mode/UID/GID/label values; RouteB `run.sh` requires the newboot independently bookended host/WMS observation. The original811 local fullSHAs and nine immutable f28/control sources are checked. The historical reference table/worker and old9f WID are stored only in clearly named reference/fixture files. They are never filled into the actual pending map.61b permission, actual postinstall capture/plan, new deployment/boot, full snapshot and overlay admission remain pending.5cd is not assigned another full128.

Prepare the static mapping (local files only):

```sh
export WORKSPACES=/path/to/workspaces
P=benchmark/2026-10-13-final61b-source-map
python3 "$P/prepare_sources.py" --out NEW_SOURCE_PENDING
```

After the actual61b T4 plan/composition exists, rebind using its separately reviewed full SHA:

```sh
python3 "$P/prepare_sources.py" --composition ACTUAL61B/composed/composition.json \
  --composition-sha256 FULL_SHA --out NEW_SOURCE_BOUND_DISABLED
```

This invokes the landed58ee producer's original raw/R5 admission, rejects5cd/5ea composition, maps actual11 member sources and aliases all7 binds. It regenerates run bytes with the unchanged original `running_files` and `exact_numeric` helpers and compares the full map with the producer's824-file candidate. It grants no execution authority. For the final newboot, the T4 request must first include its independently collected `running_parameter_evidence` and actual `current_boot` and be recompiled. A preboot source map is not finalboot evidence.

The existing original CLI sequence remains:

```sh
python3 benchmark/2026-10-12-exact-realization/realization.py window \
  --realization ORIGINAL61B_REALIZATION --observation ACTUAL_NEWBOOT_WMS \
  --observation-sha256 FULL_SHA --boot-id ACTUAL_NEWBOOT --out NEW_RUN_DERIVATION
python3 benchmark/2026-10-09-demo-baseline/t5/build_seal.py \
  --snapshot ACTUAL954_SNAPSHOT --overlays ACTUAL_ADMITTED_V2_OVERLAYS \
  --manifest benchmark/2026-10-09-demo-baseline/demo-manifest.json --out NEW_UNSIGNED_V2_SEAL
python3 benchmark/2026-10-12-exact-realization/realization.py compile \
  --request ACTUAL_FILLED_RUNNING_REQUEST --out NEW_DISABLED_REALIZATION
```

Fill the running request from the actual new seal (same independently pinned `source_identity.kind=seal` and `source_seal`), complete824 `source_files`, actual sameboot observation in both parameter evidence fields, independently verified host UID/GID and control root, actual WID/boot, and the real applicable user approval. The historical approval in the schema fixture is not61b unseal or deployment approval. Actual fingerprint lines,130 APK hashes/versions, complete inventories and admitted RouteB/Boat overlay definitions must come from real collection; old inventories or the pending Boat-absent v1 overlay cannot be relabeled as v2. Original signed v1 and all frozen packages remain unchanged.

Actual original CLI compatibility replay is in `cli-fixture/receipt.json`: `build_seal` and realization compile return0 with explicit synthetic source-only fixtures, preserving824 files/130 packages; actual pending templates return2 and create no trusted output. The original builder tests structural input and does not itself validate admission contents; fixture admission is explicitly `admitted=false` and never actual evidence. Fixture products are unsigned, not deployable, and confer no runtime954 PASS, UI or newboot credit. A new actual snapshot/admission is still required. The compilers do not need a954-specific code patch.
