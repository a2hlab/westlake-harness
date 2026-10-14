# Source/build table handoff

Input remains the immutable `benchmark/2026-10-14-api-progress-final61b/views/api-progress.json` (315 rows). Output `source-build-mapping.json` is additive and joins **only by `id`**; never replace implementation/UI/version grades.

Top-level: `schema`, `input {path,sha256}`, `master_commit`, `rows`, `recipes`, `summary`.

Each row has exactly the original `id` and the following seven fields (always present):

- `source_entry`: array of `{path,sha256,git_blob,master_tracked,role,license_status}`. Empty means unknown. `role` distinguishes implementation/source_candidate/report/index/stub. Only implementation is an implementation locator; a tracked stub or registry is not complete API delivery.
- `source_revision`: `{master_commit,expected_source_sha256,exact_binding,status}`. Unknown expected SHA array stays empty (per-file expected_sha256 stays null); current bytes alone do not prove a historical/deployed binding.
- `build_recipe`: `{id,path,sha256,status}` pointing to a shared entry in `recipes/recipes.json`; a recipe may serve multiple APIs.
- `build_command`: `{status,argv,working_directory,notes}`. `argv` is null unless an existing actual command is evidenced. Described historical commands are not a new execution receipt.
- `build_dependencies`: `{status,entries,gaps}` with path/SHA or explicit upstream/toolchain identities. Missing closure remains partial/unknown.
- `build_outputs`: `{status,entries}` with exact output hashes where evidence provides them; empty otherwise.
- `build_verification`: `{status,evidence,executed_this_audit:false,gaps}`. Native delivery receipts and historical source build receipts retain their actual scope. No invented build PASS.

Other fields: original `record_kind`, `implementation_status`, `source_location`; `coverage_status`, `gaps`, and `native_delivery` references. Coverage counts do not change capability status. Native FZ-001..008 delivery is owned by the two native lanes; consume their actual source/build/license manifests without duplicating their source search.

Renderer: turn path objects into physical relative clickable links; display null/empty as **unknown**. Keep seven columns in both languages and use the same JSON. Shared recipes are navigation, not new build runners. Do not run any build from the renderer.
