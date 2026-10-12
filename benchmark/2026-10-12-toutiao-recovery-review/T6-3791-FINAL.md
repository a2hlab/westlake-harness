# T6 immutable freeze delta review

## Verdict and evidence

**OFFLINE RELEASE ACCEPT; execution still requires outer admission.** No new
blocker was found in the requested delta/closure checks. Independent command:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/2026-10-12-toutiao-recovery-review/check_t6_freeze.py
```

Exit **0**. Raw output is `evidence/base-placement/t6-freeze-final.json`.
No behavior matrix, device, VM or remote command was run.

| Object | SHA256 |
|---|---|
| freeze.json | `3791b700da9f5d139fc40bdfc81396a0b22e50aef9ecf38e080f8db605a84e27` |
| Producer landing, 52 paths | `20683049afc522769a14fdcd9185a27340c129bd533095d04e44dd9fe6a5811d` |
| Realization proof | `7d5c024b4cabc6a95b307e87ae464345f87960a8c548972eb04a57da41afb173` |
| Prospective enabled manifest | `7c698a86e63d331f1cc0559405ec218f78c7d8122082f96dc715bd34cd235ff0` |
| Prospective enabled plan | `088dd4cdf67438426dae214671375a5001aedc86ea8ed807ea354f3c536d1592` |
| Unchanged original executor | `496fa979f4af71b8c01c44a474aed4074b64544d5d1eb500709c649679831d0d` |

## Exact checks

- **8/8 pre-reviewed files byte-identical** to the narrow pre-review, including
  realization, restore, sameboard, observations, selfcheck, seal_checks, CLI and
  observation tests. No new code delta therefore no repeated behavior tests.
- **50/50 freeze rows** match physical SHA and size; the producer's **52** unique
  landing paths are exactly those rows plus freeze and landing themselves.
  Every generated artifact pin also matches its actual byte object.
- Disabled and prospective enabled packages each contain **487 unique plan
  targets**. Every physical manifest member and every actual plan source SHA
  was read and checked (1,542,595,650 manifest-member bytes across both packages).
  Both executor objects are exact `496fa979…`.
- The disabled package retains the accepted v6 manifest `f2d0ae47…` and plan
  `35276f1e…`. Activation changes only startup.env and its expected-SHA file;
  all member metadata, sources, preimages, prerequisites, directories and other
  transaction fields remain unchanged. The plan's prospective enable flag is
  not an admission or a signed execution ticket.
- Source identity/proof remain **806** unique targets and `candidate/not_sealed`;
  original seal is explicitly null, signature null. No original seal is forged.
- Independent recorded parameter evidence `a7d9ae13…` is physically SHA-pinned
  and revalidated: serial **5cd1e3dd00000000000000000923012c**, boot
  **43bc3915-04bd-42ca-895e-26e8292911fa**, UID/GID **20011300**, installed HAP
  `df385638…`, WID/PID/birth **null** for placement. Raw boot bookends, ownership
  and HAP readings have transport/remote rc0; synthetic=false. This is not a
  claim of a fresh live host window or of this reviewer accessing the board.
- Producer clean-copy receipt rc0 and its copied source hashes match the frozen
  rows. Its 39 tests are producer evidence, not a repeated independent run.
  Earlier independent eight observation tests remain valid for identical bytes.

## Execution boundary

Outer must pin the exact proof, preview manifest/plan, lock tool/holder and both
independent admission/authorization records, retaining their existing required
role strings. Recheck current boot and actual preimages before invoking the
unchanged transaction. Default preview remains non-executing; this report does
not sign admission, reboot, start applications or issue a seal/UI verdict.

If landing/recompilation changes absolute request/proof provenance paths, the
resulting proof or manifest SHA can change: use the newly generated exact pins,
never carry an old ticket across that change. Placement has no asserted WID;
later running selfcheck requires independently collected current WMS/proc/boot
evidence, not the run.sh assignment. The user-approved whitelist is unchanged.

Original review evidence and the original 52-file R2 handoff remain untouched.
