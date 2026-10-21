# G20 independent native-admission evidence review

The old exception conditions cannot authorize this experiment. In the unsigned
proposal, 46 rows (23 per package) still limit approval to the historical N10b
window, and four rows (two per package) cite U10.1 and compat `015aa3a6`.
Those restrictions and identities are reference material, not G20 approval.

The actual offline replay returned **rc0**, verified **27 original evidence
pins**, recomputed **318 issue IDs** (baseline and candidate each have 55 N1
and 104 N2 findings), and checked their historical approval references. All
318 original proposals remain unsigned. No registry, candidate, board or git
state was changed by this review.

## Decision supported by the evidence

The evidence is sufficient for the outer reviewer to make a **new, bounded
exception decision** for the 5ea GLES single-variable experiment. It is not a
claim that the findings are resolved, a signed exception registry, deployment
admission, a runtime winner determination, or game success.

The previously independently checked current baseline covers the original
285 package targets and a 319-target fingerprint union. The candidate has two
logical byte changes: the system and route `libnativeloader.so` aliases both
change from `b8be63d2` to `878c7019`. U7 plans **32 writes, including 30 same-SHA
writes**. This replay retains that earlier result rather than repeating the
entire package check. Four Boat public changes belong to the observed baseline;
they are not additional changes introduced by G20. This is not a claim that
three private Boat mounts were part of the original 319-target coverage.

| Review item | Independent finding | Permitted interpretation |
|---|---|---|
| N1 `resolve_oh_wm_funcs` | Line 415 becomes 416; the same `liboh_adapter_bridge.so` NOLOAD call remains. | Rebind the current source/artifact; retain the namespace uncertainty. |
| N1 `eglCreateWindowSurface` | Line 1408 becomes 1404; the same `libEGL.so` NOLOAD call remains. | Same bounded review; not a new namespace-resolution proof. |
| Two N2 runtime dependency findings | Consumers and finding text are unchanged; the outside-domain candidate changes from runtime `1876` to current `9471`. | Review the actual current provider candidate; do not mark either dependency resolved. |
| N2 system directory | Current Boat public bytes plus the G18 loader change are enumerated separately. | Review those objects; the directory remains uncovered by the scanner. |
| N2 route directory | Candidate changes its loader alias to `878c`; baseline retains `b8be`. | Preserve paired publication and rollback without inventing a unique winner. |
| Remaining 100 N2 rows per package | Historical findings and inspected package/system-snapshot objects match. | Reuse evidence under new manifest/input pins; this is not a fresh scan of every board provider. |

The two unmatched N1 keys are identical to their historical findings after
removing only evidence line numbers. This does **not** mean the whole compat
source is unchanged: the Boat geometry edits are present. The current
`94718e0d` artifact is linked to the original fresh-build rc0 receipts and
compiled compat source `280a36f2`. `n1-current-source-attestation.json` correctly
limits its claim to the bounded scanner, rather than whole-binary semantic
equivalence.

## Per-row handoff, not signatures

`evidence/replay-01/recommendations.json` contains one suggestion per unsigned
proposal, keyed by package, gate, exact issue ID, package manifest and input SHA.
Each row retains the old condition as reference, identifies changed objects,
and supplies proposed `reason`/`removal_condition` text and evidence paths.
It deliberately has no `approved_by` or `approved_at` fields and cannot be
loaded as an approved registry.

The outer reviewer must make the actual decision and bind its real window
authorization. The suggested scope expires at the bounded G20 window close;
any object, source, input, baseline, namespace-policy or finding drift requires
new review. Neither the old N10b window nor the old U10.1 identity is inherited.
The historical libc-inheritance/libshared_libz re-review triggers are retained
without claiming runtime inheritance has now been proven. The current board
identity, lock, baseline and journal restoration checks remain the existing
execution gates; this review introduces no replacement deployment tool.

## Exact sources and raw evidence

- Main G20 input: `../gles-transaction-package/exception-comparison.json`,
  SHA `99dba69e53fcca6cca8be75df31b6228aae3d39d3069e3259bcd4597fa62e0dc`.
- Unsigned proposal: `../gles-transaction-package/exceptions.unsigned.json`,
  SHA `4f22913b6500f1ebd08ffcbc86e94c0e416579807a82f02eda10cac54cd5fc33`.
- Source attestation: `../gles-transaction-package/n1-current-source-attestation.json`,
  SHA `3a47b4a85917a67fabd50517c51dc19918eb199e1be657af66ceb39bacfc858d`.
- Historical report: `benchmark/2026-10-03-u13-final-assembly/evidence/native-v3.json`;
  the exact SHA and registry SHA used by this replay are recorded in `results.json`.
- Current runtime build evidence is bound by
  `benchmark/2026-10-10-boat-runtime-port-spec/evidence/linkfix-verification.json`.
  Its original `receipt.json`, `image.stdout.txt`/`image.stderr.txt`, and
  `container-build.stdout.txt`/`container-build.stderr.txt` are under
  `$WORKSPACES/westlake-harness-bms/benchmark/2026-10-10-boat-runtime-port-spec/.artifacts/fresh-link-zpsaydde/`.
  `evidence/replay-01/attestation-pin-checks.json` records all 27 checked aliases
  and hashes without copying large private logs.
- Current loader build evidence is the unchanged G18
  `gles-loader-candidate/build-01-receipt.json` and `source-pins.json`.

## Reproduce without devices or rebuilding

From the repository root, select a **new** output directory:

```sh
python3 -B benchmark/2026-10-21-commercial-game/gles-native-admission-review/replay.py \
  --repo . --out /tmp/g20-peer-replay-new
```

The script requires the referenced persistent workspace originals and fails on
missing files or pin drift. It does not run subprocesses, sign anything, modify
the registry, invoke devices or rebuild artifacts. The original execution is
recorded in `replay-command.json`, `replay.stdout.txt`, `replay.stderr.txt` and
`replay.rc.txt`. Its durable output is `evidence/replay-01/`.
