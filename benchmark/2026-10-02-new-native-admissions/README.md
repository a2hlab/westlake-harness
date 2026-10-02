# Exact new-native admissions without relaxing the static criterion

The U12 native draft was correctly refused because `/system/android/lib64/libmediandk.so` has no deployed root baseline. Reusing ZigZag's private library as that baseline would change the object being judged. This change preserves the strict refusal and adds a separate, outer-owned exact-identity table. The production table contains **zero rows**; no mediandk approval has been registered.

## Decision and identity

`knowledge/gates/new-native-admissions.json` has schema `westlake-new-native-admissions/v1` and an `admissions` list. Each row contains:

- `target`: exact board path, no wildcard or prefix matching;
- `sha256`: full lowercase64 artifact SHA;
- `package_manifest_sha256`: full lowercase64 native package manifest SHA, not bundle SHA;
- `reason`: nonempty review rationale;
- `evidence`: nonempty repository-relative paths to actual files, with no absolute/traversing/escaping path;
- `added`: ISO date/timestamp of outer registration.

Only a new **ELF** whose path, artifact SHA and actual validated native manifest SHA equal one row passes this exception branch. The row is returned in the gate report with the raw table SHA. Missing/unreadable/invalid JSON, malformed schema/row, shortened SHA, duplicate JSON keys or identities, invalid timestamp, and missing or unsafe evidence invalidate the entire table and keep the new member REJECT. An unrelated invalid row cannot be silently skipped to admit the requested member.

The existing no-baseline reason remains the default. New JARs remain REJECT. Existing JAR frozen-class comparisons, existing ELF open-site/namespace comparisons and their existing policies are unchanged. Exact new-member admission does not waive N1/N2, frozen, G1/G2, build receipts or package member integrity.

`u7_executor.policy_binding()` additionally hashes the new registry. A row added, revoked or changed after production preflight invalidates the prepared policy identity, just like the other existing policy files. No new runtime behavior or device operation is introduced.

## Known answers and real production PATH

Both Mac and `orb -m a2hlab` used real production tool resolution and an actual classes.dex read. The actual reviewed mediandk bytes are SHA `8fc0752dd561a62992268981164c5e75c87ceb802f93d6d0b958c23b54ddaa58`; the unchanged offline U12 draft is manifest `6d908fd953defe9ee9f1032573ba4aa1279254cd0aa0ca13c6ff1708944a65a1`, bundle `b249c08b1afa986e2e26e4a38fbd0d8ee543a20fec5d3d90f5aa26ffaaf1c038`.

| Case | Mac | VM |
|---|---|---|
| Production empty table, actual static CLI | rc2 / REJECT | rc2 / REJECT |
| Exact row in isolated temporary test table, actual four-member comparison | PASS | PASS |
| Same target, different SHA in fixture row | REJECT | REJECT |
| Different manifest | REJECT | REJECT |
| Different/unreviewed target | REJECT | REJECT |
| Empty table | REJECT | REJECT |
| Table file absent | REJECT | REJECT |
| Eight focused unit tests |8 OK|8 OK|

The positive real-package test uses a temporary fixture table via a test-only module patch. It is not an outer approval and never modifies the production registry. Unit metadata fixtures isolate the admission branch from the already-existing member validator; the actual final ELF and manifest are separately exercised by `run_checks.py`. Unit cases also create a different new native file identity, malformed/invalid tables and evidence, an invalid unrelated row, a new JAR, and an existing ELF open delta. The latter remains REVIEW_REQUIRED; neither the new-member row nor a temporary fixture can bless it. The first Mac unit run exposed the fixture's `/var`→`/private/var` canonical-path mistake; its raw failed result is retained, then all eight passed after canonicalizing the fixture root.

`gates/{mac,vm}/` contains exact actual-package reports and stdout. The production table's SHA is checked before and after every run, and remains empty. Three agent-spec scenarios PASS through their Rust selectors; the pre-existing executor transaction suite is run as a separate regression check. Raw original logs remain outside git; `raw-evidence.json` binds them to public copies with only workspace/home prefix normalization.

## Proposed mediandk row: not registered

`mediandk-row-draft.json` is a proposal only, with deliberately invalid placeholders for the **final U12 manifest** and outer registration timestamp. It must not be copied into the table until the outer loop supplies those final values and approves registration. The final U12 now includes private-zlib and Java/images, so this draft's manifest is not a permanent approval target. N11h-r2 and compat-relocation are explicitly deferred to U13.

The donor calls its artifact report `validation.json` rather than `artifact-checks.json`. The proposal references the real existing `validation.json`, `evidence/abi-mediandk.json`, `evidence/candidate-dynamic.txt`, `strings-review.json`, and `namespace-gates.json` under `benchmark/2026-10-02-u12-mediandk/`; no nonexistent evidence path is invented. Root mediandk only is in scope; ZigZag private `110d02fc` stays untouched. Typed unsupported codec APIs are not advertised as real codec support.

## Reproduction

```sh
source "$WORKSPACES/westlake-inputs/env-mac.sh"
export PATH="$HOME/Library/Android/sdk/build-tools/37.0.0:$PATH"
export CARGO_TARGET_AARCH64_APPLE_DARWIN_LINKER=/usr/bin/cc
python3 benchmark/2026-10-02-new-native-admissions/test_admissions.py -v
python3 benchmark/2026-10-02-new-native-admissions/run_checks.py --surface mac
agent-spec lifecycle specs/new-native-admissions/t1-registry.spec.md \
  --code tools/spec-checks --layers lint,test
```

The VM run prepends the existing shared production `.vm-tools`, uses writable `.vm-tmp`, then runs the same `run_checks.py --surface vm`. Neither path invokes HDC, takes a board lock or deploys. Actual U12 production admission remains refused until the outer registers the exact final manifest row; adding an empty table alone is not readiness.
