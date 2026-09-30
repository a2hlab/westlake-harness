# v3 execution revision: actual profile strata

Treating the next sweep as the frozen v3 profile would be wrong: the outer loop reports that 5ea's diagnostic `libhwui a578b949` was rolled back to `be59260f` at 05:20 on September 30. That reported time precedes the final v3 freeze at **05:22:23.255216 +08:00**, although this notice arrived after acceptance commit `57525634`. A later click does not resolve a component mismatch.

`execution-revision.json` records that notice separately. **All 104 frozen artifacts and the original scoring code remain unchanged.** The original receipt SHA-256 is `f9d4881a121b8bd36603835604e42bca7ab3c59a68f1735c04721ac82ebd143b`.

The reported execution target is v3c `668e4f7c`, hwui `be59260f93b3debe1ad64cc8e7b6b0575e5be04794b46f8eb876436d1ebc9b74`, installer `6aadb8b4/7048c7c5`, and either r17o or a future r17q. The full hwui hash comes from the frozen base-package file table; this is not a new device readback. The outer loop reports a ZigZag regression with r17p on 61b and has withheld it as the unified JAR. No r17q artifact/hash was supplied; its forecast attribution remains unknown.

## Run the companion audit

```sh
python3 benchmark/2026-09-30-r17op-execution-revision/profile_audit.py \
  --run /ABSOLUTE/COMPLETED/RUN/5ea34a4500000000000000001123012c \
  --installer-readback /ABSOLUTE/installer-readback.txt \
  --out /ABSOLUTE/new-profile-strata.json
```

Repeat `--run` for continuation segments. Omit `--installer-readback` to use each run's own file. The output must not already exist. This reads facts.txt, runtime-fingerprint.txt, baseline.json and installer readback only; it does not consume app outcomes.

| Actual evidence | Classification | v3 same-profile treatment |
| --- | --- | --- |
| Full original native projection, exact frozen JAR and installer, accepted board | `exact_frozen_projection` | Eligible only after the existing installer/boot audit; original per-app scoring gates still apply |
| Exact r17o/r17p JAR with changed native component, including be59260f | `known_jar_profile_drift` | Separate descriptive stratum; excluded from same-profile accuracy |
| JAR hash absent from both frozen columns, including a distinct r17q | `unfrozen_or_missing_jar` | No frozen forecast column; excluded |
| Missing/inconsistent facts, fingerprint or baseline | `invalid_evidence` | No trusted profile identity; excluded |

Strata use board plus the complete measured path/hash map. Each comparison lists changed, missing and unexpected Android components. Component names and claimed version labels never substitute for SHA identity. An exact projection without installer readback is still unverified. The preserved scorer already rejects native/JAR deviations; this companion makes their actual profile explicit without relaxing that scorer or rewriting a forecast.

The audit emits no accuracy. Once outcomes exist, retain descriptive outcome counts separately for each drift stratum; do not combine them with the frozen denominator or select the better-scoring JAR column. For any genuinely matching run, use the original score.py with its matching variant and APK, clicked_at, installer feature, capture and outcome evidence gates. Run-start fingerprints do not prove all resident mappings or exclude changes later in the run.

## Offline checks

```sh
python3 benchmark/2026-09-30-r17op-execution-revision/test_revision.py
agent-spec lifecycle specs/bms-background-start/t4-execution-revision.spec.md --code tools/spec-checks
```

Six synthetic tests cover exact versus rolled-back profiles, unknown JARs, board/component strata, missing installer evidence, malformed/missing facts and frozen integrity. No test fixture is board evidence. Actual next-sweep profile verification and outcomes remain pending; no screenshot or survival count is claimed.

R2: offline gates and immutable artifacts verified; rollback/JAR selection recorded from the outer-loop notice; actual execution pending. No device I/O. Git metadata is read-only here; outer loop handles submission.
