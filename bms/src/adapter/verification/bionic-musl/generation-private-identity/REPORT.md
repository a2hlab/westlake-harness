# Generation-private Unity identity gate report

Date: 2026-07-15 HKT

Boundary: Bionic/Musl host artifact admission. This report does not prove target
loading, Unity engine startup, JNI entry, constructors, rendering, or device
behavior.

## Command

```sh
verification/bionic-musl/generation-private-identity/tests/run_tests.sh
python3 -m py_compile verification/bionic-musl/generation-private-identity/write_identity_receipt.py
```

## Result

```text
PASS positive
PASS mixed_generation_rejected
PASS sha_rejected
PASS build_id_rejected
UNITY_IDENTITY_SELFTEST_PASS
```

The positive fixture is ELF64/AArch64 and contains exact 40-hex GNU Build-IDs.
The three negative controls each mutate one identity dimension. The gate only
opens files named by the two explicit private roots and receipts; it contains no
filesystem search or shared `out` fallback.

## Status

- Proven: synthetic positive receipt generation; mixed generation, SHA mismatch,
  and missing Build-ID rejection; exact SONAME/NEEDED/PT_INTERP extraction.
- Not proven: admission of the real CardWords APK native bytes and a completed
  AlexPC generation.
- Failed: none in the final self-test.
- Next evidence: produce the real `westlake.cardwords.native_bundle.v1` receipt
  from exact extracted APK bytes, then run this gate against the completed
  AlexPC generation before M07's RTLD_NOW fixture.
