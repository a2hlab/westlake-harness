# Offline host HAP preflight

The existing live preflight and T33 window operator cannot be imported for an offline check: both can issue device commands. This tool reuses the original strict SHA-record and bundle/runtime assertions in a side-effect-free CLI. It pins T33 reference SHA c2ebf2f4 and accepts only the exact original61b HAP and verified T32 candidate, with the complete nine-member set and only `ets/pages/Index.abc` changed. It checks recorded UID/token, both power fields, all six runtime and18 guardian hashes, explicit compat absence and successful same-serial input receipts.

Actual T33 positive CLI returned0. Six independently mutated copies returned1: missing token, wrong rollback baseline, additional HAP member, wrong runtime path, missing power field and missing compat assertion. Both Rust selectors passed (`cargo test --offline --manifest-path tools/spec-checks/Cargo.toml --test host_hap_preflight -- --nocapture`). This is offline evidence verification, not fresh identity, installation, retention, signature cryptography or API freeze.

Run from the repository:

```sh
python3 scripts/lab/host_hap_preflight.py --intake "$T33_SAMPLE_ROOT/intake-01" --release "$T33_SAMPLE_ROOT/release-01"
```

The default reference is the repository T33 static/reference.json; `--reference` permits a relocated byte-identical copy only. Test samples default to `$HOME/.local/share/westlake/t33-demo-host-61b`; override with HOST_HAP_SAMPLE_ROOT, HOST_HAP_REFERENCE and HOST_HAP_TEST_OUTPUT. Missing actual samples fail rather than skipping or synthesizing a positive. Tests preserve negative input copies and complete raw receipts in the output root. Public per-case receipts retain stdout/stderr/rc, with argument roots aliased; cargo stderr also aliases the checkout root. No retrospective or FLAW record is changed by this package.

The public cargo stdout has only leading/trailing blank lines trimmed; its complete original remains in the private final-receipt directory.
