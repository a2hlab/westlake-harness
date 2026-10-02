# Corrected effective T8 with U10.1/U11i — unarmed promotion proposal

The first T8 used the native underlay stubs and removed frozen APIs. This candidate uses the signed U9 **effective** stubs (`f3bcc9d7`) as its source/reference and preserves those APIs. It is deliberately unarmed: exact native open-delta review and the 26/27 rerun provenance discrepancy remain pending. No board or lock has been accessed.

## Final artifacts and evidence

The immutable candidate is `$WORKSPACES/westlake-inputs/generations/u10.1-t8-effective-j5ae3dd29-s2f365a75-v2/bundle`. `composition.json` binds its native manifest and bundle SHA. The previous rejected `a2172f18/3df46844` candidate was not changed.

U10.1 changes runtime JAR/host/compat/policy (six effective paths). T8 changes 27 images plus stubs/framework (29 targets). `evidence/disjoint-members.json` demonstrates no intersection. T8 uses `2f365a75/2257b835`, images `d5b43805/4ba08485/23c1f5b0`; U11i remains `5ae3dd29`. Every unchanged provider remains byte-identical. Installation service libraries are unchanged, so the existing 61b service difference remains visible in the per-board runtime fingerprint.

- Three final JARs pass `deployed_class_diff --deployed <effective U9> --frozen`. The runtime policy drops **only** `Ladapter/activity/J10eWebView$DelegateForward;` and `Ladapter/activity/J10eWebView$WlCookieManager;`, bound to full candidate/deployed hashes and ACK(90) 11:34:15 / commit `8214ec53b4`. A prefix, missing evidence, or either SHA drift refuses before class comparison.
- `final-artifacts/` audits final native ABI/calls, 102 payload ELF copies/86 unique artifacts and 12 pinned app consumers, normalized readonly data and exact previously reviewed strings. Raw strings exit1 is preserved.
- `approved-native-gate.json`: all 156 findings are semantically identical to approved U10.1; automatic rows are in `registry-delta.json`. New findings: zero. These grants do **not** authorize new static open deltas.
- `image-gates.txt`: production G1/G2 PASS against actual signed U9 images + effective BCP (36/36 String instructions identical), exactly two jointly swapped segments. `image_gate_reference` binds all 36 reference members.
- `static-checks.json`: three JARs and both policy paths pass, host plus both compat aliases require review. `open-delta-review.json` binds each physical target, candidate/deployed SHA and complete delta digest. No approval was invented.
- `paired-receipt-pending.json` records all nine input and 27 output hashes with status **unknown**. There was no archived original bake stdout. The same-path independent logged rerun finished with **26/27** identical outputs. `boot.art` differs by three bytes at offsets254905–254907 (`d5b43805` original vs `ab88cf38` rerun); both sizes4644864. Original 27 outputs were preserved. `evidence/t8-rerun-compare.json` and real rc0 logs preserve the observation. Cause is unclassified; no provenance exception has been approved. The outer stop-on-difference rule applies. The logged rerun is not presented as this original image’s verified receipt. A retrospective inventory is not a build log.

Source: donor cc-wiki `feat/wikipedia-line@fd25c9814a`, corrected `build_t8_effective.sh`; persistent inputs/outputs in `$WORKSPACES/westlake-inputs/generations/t8-rebake-effective/`. Raw donor gate receipts are copied in `evidence/`. Host/policy/compat sources are the already audited U10.1 recipes in `benchmark/2026-10-01-u10-native-shims/` (bms worktree), not newly compiled sources.

## Plans and admission

`window/plan-{5ea,5cd,61b}.json` and `promotion_dispatch.py` are **review-only**. Admission requires exact approved static deltas, verified paired provenance, all production gates, coherent armed composition/bundle hashes, and an outer-approved plan before infra preflight or LOCK. The pre-lock check then tests OrbStack, the VM workspace bind SHA and HDC serial. Apply first verifies signed same-board U9; parent remains stopped through all image/JAR/native binds. Existing rollback cold-stops receipt-owned OrganicMaps residues and restores U9 layers, 318 assertions, smoke and final verification.

The full166 partition is 55/55/56; 5ea also gets an early Toutiao probe. Window limit 45 minutes; no new key after minute35. Promotion is conditional on full outer screenshot signoff: Toutiao t20 bright, HW/ZZ bright, no regression among the 115 U9-lit keys, no unknown/inconclusive keys, exact final identities. Otherwise finish rolls U9. This strict full-signoff condition may not be satisfied in a single 45-minute window at observed throughput; an explicit continuation/retention schedule must be reviewed, rather than silently retaining partial results. Missing full signature is never inferred from facts or process survival.

Current runtime fingerprints: 5ea/5cd `f3b604c94df4`, 61b `d6848fa2c989`; boot all `fd4ce75b7eb3`. Static assertions318/unique316. These are expected offline identities, not live verification.

## Tests and status

15 tool tests, 8 promotion admission/rollback tests, 82 harness tests (3 skipped) pass. SHA/prefix-drift drop grants reject before checker invocation. Pending gates reject before DeviceIO/LOCK. Real production dry-run refuses the unapproved host/compat open deltas. R2: final offline artifact checks verified; deployability and board outcome unverified. No promotion, build-log substitution, or board access is claimed.
