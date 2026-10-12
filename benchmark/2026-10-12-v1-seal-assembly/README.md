# V1 seal assembly (t6-sealpack)

Offline material assembler for the v1 seal (no Boat; 61b 20-key Plan-2 +
5cd signed-128 cross-reference). Live on-site results enter ONLY as
parameters — anything missing refuses the seal. Zero board/VM/remote; every
digest is computed locally over pinned files.

## Sources (all pinned by SHA in assembly-inputs.json)

- Plan-2 reference: westlake-harness-wiki commit `d6e16a5ffd` (user-approved
  2026-10-11: 61b runs a 20-key representative set cross-validated against the
  5cd v1-Permissive full-128 prerun).
- 61b 20-key: `demo-manifest-20.json` (00140d6d…), driver `demo_seal_61b.py`
  (a7add551…), PLACE-ONLY installer + recover-v3 cfg/script, t5 compiler +
  v1 draft overlays (Route B slot pending).
- 5cd 128: full128-readout facts / comparison / readout driver.
- Restore providers (planned objects, not yet live): u13-base (order 1) then
  toutiao-route-b (order 2, pending acceptance); Boat is v2 and absent.

## Usage

```sh
# inventory preview: verify all pinned digests, list providers/order, BOARD_COMMANDS=0
python3 benchmark/2026-10-12-v1-seal-assembly/assemble.py inventory

# final seal — delegates to the PINNED t5 compiler build_seal.build(snapshot,
# overlays, manifest); refuses otherwise (exit 2), writes nothing. The live
# file must carry: live_snapshot_json (demo-seal-snapshot/v1), overlays,
# manifest, interaction_signoff_json {accepted_by, steps}, non-empty
# archive_sha256_map, provider_admissions incl. toutiao-route-b with
# admitted_by + rollback pin. Forged inputs (nonexistent paths, empty
# strings/dicts, lying synthetic:false, missing rollback) are rejected.
python3 benchmark/2026-10-12-v1-seal-assembly/assemble.py compile \
  --live LIVE.json            # live_snapshot_json, interaction_signoff_json,
                              # archive_sha256_map, provider_admissions
                              # (+ toutiao-route-b admission while the draft slot is pending)
```

`--inputs` / `--out` support isolated synthetic fixtures (fixture outputs stay
marked `synthetic:true` and are never admitted to a real device).

## Assembly receipt (bound to the seal)

On a successful compile the assembler also writes `<seal-stem>-assembly-receipt.json`
(schema `v1-seal-assembly-receipt/1`) next to the seal: seal_path + seal
digest, synthetic flag, the pinned Plan-2 manifest reference, the validated
interaction signoff, the archive SHA map, and BOTH providers (u13-base order 1,
toutiao-route-b order 2) with admitted_by and their verified rollback
{path, sha256} pins. The receipt is the restore-plan input; it never replaces
the t5 restore-deployment JSON (which the outer loop still authors).

## Strict live validation

- `interaction_signoff_json`: non-empty `accepted_by` + non-empty list of
  non-empty step strings ([False] and [""] are refused).
- `archive_sha256_map`: non-empty, every value 64-hex sha256.
- `provider_admissions`: BOTH u13-base and toutiao-route-b required; each with
  non-empty `admitted_by` and `rollback{path, sha256}` where the path EXISTS
  and its digest matches ({"x":"y"} and wrong SHAs refused).
- Non-synthetic `live.manifest` must equal the pinned demo-manifest-20.json.
- Synthetic material must stay `synthetic:true` (claiming false is refused);
  synthetic t5 fixtures keep their own manifest in the isolated branch only.

## Restore-deployment assembly (real t5 validate)

```sh
python3 benchmark/2026-10-12-v1-seal-assembly/assemble.py assemble-deployment \
  --seal SEAL.json --deployment CANDIDATE.json --out OUT_DIR
```

The candidate is a real `demo-restore-deployment/v1` (files with
`source{path,sha256}` covering EXACTLY the sealed files+APKs; providers in
order `u13` then `toutiao-route-b`, each with interpreter/program/rollback
real pins and disjoint targets). Validation is delegated to the main-tree
`t5 restore.validate(seal, deployment, base)` — the assembler invents no
rules of its own. The validated deployment is staged verbatim with
`execution_enabled=false` (a candidate arriving enabled is refused; enabling
is outer-only) plus a `v1-restore-assembly-receipt/1` binding seal+deployment
digests. Pending/empty files or providers refuse with the pending list.
Interaction signoff uses the legacy acceptance shape: each of
launch/feed/refresh/article must be `{name, passed: true, evidence {path,
sha256}}` with the evidence file readable and digest-matching — plain string
steps no longer pass.

## Tests


`tools/spec-checks/tests/v1_seal_assembly.rs` — inventory / reject / fixture:
3 passed, 0 failed (reject runs the outer attack replay plus a 7-mutation
matrix: sign-steps-false, sign-steps-empty-str, archive-bad-sha,
provider-missing-u13, rollback-arbitrary-pair, rollback-wrong-sha,
lying-synthetic-false; fixture compiles through the real t5 compiler with both
providers and asserts the receipt binds the seal digest).

### Outer correction: preserve relative source identity

After landing c06f7a1177, the outer review replaced relative-file copying with reference rebasing against the new output directory. Copying a ../ pin could escape the output or collide with its original; copying only a provider also detached its relative imports. Sources and providers now remain in their persistent original location, referenced relatively from the output, and the unchanged real validator rechecks every resolved SHA. No source file is copied or overwritten, and generated references do not add a user-home absolute path.
