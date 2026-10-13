# 61b postinstall readonly collector

The earlier61b preinstall collector deliberately leaves UID null and complete=false; it cannot supply a postinstall provider capture. This successor reuses the validated5cd collector byte-for-byte except for three strings: CLI description, serial and schema. `collector.diff` shows the entire executable delta. The497-file request, three RouteB directories and two declared new directories are copied byte-for-byte from the actual61b request, not from5cd. Source paths and SHA256 are in `source.json`; old frozen files are unchanged.

Default execution is a disabled preview with zero transport calls. No real61b capture was made in this delivery. User unseal approval and outer execution authority remain pending.

```sh
cd "$WORKSPACES/westlake-harness"
P=benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/capture61b-postinstall
: "${EXPECTED_61B_BOOT:?outer must supply the actual current61b boot}"
: "${CAPTURE_OUT:?fresh output directory beneath WORKSPACES required}"
python3 "$P/capture_readonly.py" \
  --expected-boot "$EXPECTED_61B_BOOT" --out "$CAPTURE_OUT"
```

After explicit user unseal, original missing-only preinstall completion, and root authorization, outer may append `--execute` to that same command to perform readonly collection. The collector is not an authorization manager; the caller retains the existing lock/window responsibility. Never add `--execute` just to inspect the interface. No UID, WID, old boot or complete flag is filled by this package.

The inherited collection keeps expected-boot and boot bookends; BMS package/UID/version plus sameboot timestamp-ordered raw receipt/stdout/stderr triplets; all497 file hashes and mode/UID/GID/label; full319 baseline equality; exact cfg bytes; explicit remote rc and stderr checks; three directory metadata observations; and Boat root absence. An existing root produces rc2 with complete=false and pending, without deletion. New output must not exist. No install, launch, reboot, bind or write-device command exists in this collector.

Feed the resulting complete capture to existing `final-v2-f28/board61b/provider/prepare.py --capture "$CAPTURE_OUT/capture.json" --out NEW`, then the existing `selfcheck/bind_request.py` and `compile_selfcheck.py`. Their outputs remain disabled; capture success is not placement or seal acceptance. The previous command card in `routeb-fresh-restore/closeout-and-61b-preparation/README.md` remains immutable historical evidence; this package resolves its stated collector gap.

Validation:9 Python tests,5 Rust selectors, and all5 lifecycle scenarios pass. The full-shape synthetic fixture runs the actual collector through61 mocked readonly transport calls, writes and verifies the original triplets, and never runs HDC. Negatives cover wrong request serial, wrong initial boot, changed final boot, stripped cfg, missing UID, remote rc/stderr failures and existing root. Synthetic fixture identities are not actual61b observations. A real CLI default preview separately returned rc0 and created no output directory.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 "$P/test_capture.py"
cargo test --offline --manifest-path tools/spec-checks/Cargo.toml --test capture61b_postinstall
agent-spec lint specs/demo-recovery-followup/t13-61b-postinstall-capture.spec.md --min-score 0.7
```

`evidence/lifecycle.json` preserves the initial lint/boundary-only invocation with5 skipped scenarios (not PASS). `evidence/lifecycle-tests.json` records the subsequent correct Rust-crate invocation with5 PASS. This delivery does not alter unrelated root Cargo setup or other worktree changes.
