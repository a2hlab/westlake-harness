# Initial-closure / TP prepare certificate

Status: host-static fail-closed gate. A PASS is still only `build_pass`; it is
never `device_verified`.

## Boundary and claim

This gate covers the appspawn-x / Musl / Bionic TLS boundary. It binds:

- the exact final appspawn-x SHA and Build-ID;
- its same-Build-ID unstripped sidecar;
- the exact observed Musl loader SHA and Build-ID;
- an immutable project-local snapshot manifest;
- recursive `DT_NEEDED` resolution through an explicit sealed order;
- a conservative raw-AArch64 scan of every resolved executable segment.

Provider absence, multiple provider paths, a mutable/symlinked input, an
unclassified TP-derived flow, missing prepare symbol, or missing binary phase
proof all fail closed.

The certificate has three separate phase buckets: `pre_prepare`,
`post_prepare`, and `unordered_relative_to_prepare`. Module membership, source
order, and comments are never used to move a site out of `unordered`. Only a
`verified_binary_callgraph_v1` artifact bound to the exact main and exact
scanner site set can establish `prepare_order_proven=true` and the required
integer `pre_prepare_slot5_access_count=0`.

## Current CardWords run

The immutable run is:

`adapter/research/atoms/L03/A15/evidence/runs/20260712-initial-closure-cert-r1`

Reproduce its deterministic reports from the project root:

```sh
python3 adapter/framework/appspawn-x/tests/initial_closure_certificate/initial_closure_gate.py certify \
  --config adapter/research/atoms/L03/A15/evidence/runs/20260712-initial-closure-cert-r1/gate-config.json \
  --output adapter/research/atoms/L03/A15/evidence/runs/20260712-initial-closure-cert-r1/reports/initial-closure.certificate.json \
  --inventory-report adapter/research/atoms/L03/A15/evidence/runs/20260712-initial-closure-cert-r1/reports/initial-closure.inventory.json \
  --tp-report adapter/research/atoms/L03/A15/evidence/runs/20260712-initial-closure-cert-r1/reports/initial-closure.tp-scan.json
```

Exit 1 is the expected result for the current generation: the reports are
written first and state exactly why deployment is not authorized.

Run regressions:

```sh
adapter/framework/appspawn-x/tests/initial_closure_certificate/run_tests.sh
```

## What a static PASS still does not prove

It does not prove the child executes the certified path, that stock `setcon`
succeeds under SELinux Enforcing, that new threads receive a real Bionic guard,
or that ActivityThread, Unity, EGL/Surface, RenderService, or a visible frame
works. Those require production-init, truly-cold device evidence.
