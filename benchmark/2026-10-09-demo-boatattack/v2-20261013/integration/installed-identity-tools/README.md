# Final actual5ea collection and request assembly

The saved root Pain/nine tools reuse the original batch_adapter installer. Their
original per-command logs already contain exact serial, raw stdout/stderr,
return codes and numeric times. This tool binds those files without rewriting
any receipt. No standalone install-preflight collector was found among outer's
saved Python/shell scripts; this adds only the required11 batch reads, using the
same native HDC and raw receipt shape. No driver, guard or reviewed compiler changes.

`collect_actual.py` defaults to **preview**. Explicit `--execute` reads boot,
fresh BMS list, eight batches of16 base.apk hashes, then boot. Every actual command
persists its exact argv, raw stdout/stderr, start/end numeric time and remote rc.
Missing/error bytes are UNKNOWN, never absence. No writes, launches, lock changes,
installation or UI actions occur on the device. Collection alone is not admission.

`assemble_request.py` defaults to **preview**. It automatically finds successful
install-only records in root's Pain/nine directories and an explicit future Noice
root. It requires one key-addressed original bm install command, matching original
install.txt, and real sameboot commands before/after installation. Duplicates,
missing receipts or foreign identity reject. No synthetic log/time is generated.
`--write` requires all11 and final fresh evidence, validates through the unchanged
compiler in a temporary local directory, then writes only the request. Publication
of the final index remains the compiler's explicit CLI operation.

Actual Pain+nine10/10 are bound in `actual-install-preview.json`; Noice was pending
at capture. All10 have before <= install <= after <= record.finished_at. Pain's
original054/055/058 command triplet is used. Initial BMS time is the original float
1791866190.266471. An ISO probe metadata timestamp cannot replace a command receipt.

## Root commands

Set WORKSPACES to the real shared root. After landing:

```sh
export PYTHONDONTWRITEBYTECODE=1
V2="$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013"
TOOLS="$V2/integration/installed-identity-tools"
FINAL="$V2/outer/actual-install-final-5ea"
BOOT=35da6f13-e7b1-4472-a36a-5c4a69d5f191
python3 "$TOOLS/collect_actual.py" --boot-id "$BOOT" --out "$FINAL"
```

Only root, after the actual Noice install completes and during its authorized
window, runs the same command with `--execute`. A fresh output directory is required:

```sh
python3 "$TOOLS/collect_actual.py" --boot-id "$BOOT" --out "$FINAL" --execute
```

Point NOICE_ROOT at the actual completed installation run; never a probe-only or
invented directory. Preview is useful before Noice completes:

```sh
: "${NOICE_ROOT:?set actual Noice installation evidence root}"
python3 "$TOOLS/assemble_request.py" --boot-id "$BOOT" \
  --install-root "$NOICE_ROOT" --final "$FINAL/final.json"
python3 "$TOOLS/assemble_request.py" --boot-id "$BOOT" \
  --install-root "$NOICE_ROOT" --final "$FINAL/final.json" \
  --out "$FINAL/request.json" --write
python3 "$V2/integration/installed-identity-5ea/compile_index.py" \
  --request "$FINAL/request.json" --out "$FINAL/verified-installed-identity"
```

The output `$FINAL/verified-installed-identity/install-index.json` becomes the
existing full128 driver's `--install-index` input for a new round. All ordinary
128 members, original bindings and special-slot rules remain unchanged. A sameboot
capture mismatch or missing/drifted APK refuses admission; do not recycle an old
PASS or modify the already prepared round.

## Checks

6/6 focused tests PASS, zero board calls. Actual10 original log binding, original
float timestamps and missing-Noice refusal are checked. Fake native HDC runs all11
reads, persists the real output shape, and that shape passes the unchanged compiler
with explicitly synthetic installation fixtures. Preview makes no subprocess call;
rc0/Connect server failed stays incomplete. First fake-runner parsing test failed
because shell punctuation remained in its parsed token; only the test parser was
corrected. The collector was unchanged by that correction. No real final128 PASS
or index is claimed. `tests.txt` contains the actual final test output.
