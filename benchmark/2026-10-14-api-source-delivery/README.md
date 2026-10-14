# API source delivery renderer checkpoint

The first completeness predicate accepted a nonempty, hash-matching build entry without proving that the script was tracked on MAIN/master. The corrected predicate requires an independently read build-entry Git blob to match the recorded master tree, using a repository source path. A real, identical master script copied into T0 fails; `$WORKSPACES` cross-tree and absolute-path forms also fail. This is a renderer checkpoint, not complete source delivery or API functionality acceptance.

Ten independent checks and the `api_source_delivery` Rust wrapper passed. The unchanged task contract has 0 failed, 0 skipped and 2 pending_review scenarios (lint 100%). Final views have **not** been frozen. Preview tables were actually generated, but later mapping pins refer to mutable Java review data and were rejected. The failures remain in `evidence/pin-drift-failures.json`; no alias hides them. Generation will resume once ROOT reports `ALL_SOURCE_LANDED` and supplies a stable mapping/recipe snapshot.

The renderer reuses the signed315 JSON and original atlas, adding source/build fields without changing any original315 semantic field. Source and build entry navigation is enabled only for exact MAIN/master-tracked entries. Unpublished candidates have no user source entry. Unknown/stub/incomplete build evidence remains incomplete. The generator never executes recipes or device commands. The source/build mapping in `inputs` is a preview test input only; its mutable evidence pins are not accepted for final generation.

## Commands

```sh
WORKSPACES=/path/to/workspaces PYTHONDONTWRITEBYTECODE=1 python3 benchmark/2026-10-14-api-source-delivery/verify.py
WORKSPACES=/path/to/workspaces cargo test --manifest-path tools/spec-checks/Cargo.toml --test api_source_delivery -- --nocapture
```

After stable source delivery, copy the exact mapping and its pinned `recipes/recipes.json` into `inputs`, update `inputs/request.json`, and run `generate.py build --mapping inputs/mapping.json --mapping-sha256 <ROOT fullSHA>` from this packet. Outputs land directly at `MAIN/benchmark/2026-10-14-api-source-delivery/views`; no flattening layer is required. The checker validates the generating master commit as an ancestor of current master, so unrelated later commits do not cause a false rejection.

`publication_check.py simulate` copies the new view at this exact physical directory depth inside T0, reusing existing MAIN source files read-only, then resolves the rendered links and checks their SHA. After ROOT lands final views, `publication_check.py actual --views <actual MAIN views> --receipt <T0 receipt>` uses the real supplied MAIN directory as origin. It never writes MAIN. Only this latter receipt may be called an actual MAIN physical-link audit.

The historical alias is solely the immutable original315 registration evidence (`knowledge/gates/unlanded-ack.json`), independently recovered from its exact old Git blob. It cannot supply live source or mutable delivery review bytes. No old signed packet, runtime, active round, or device was changed.
