# U14 frozen compiler and actual image identity

This is an identity rebind, not a new libart/compiler build. The immutable
FZ-005 compiler `ae865ddd6a7e4b25a18b7c07402920c69e5599b329778eff647a08803948322b`
and driver `14b1f709cbeae35c2e606ee923d26a9f59e92dd827da84bdf5126de79a675d46`
were checked in both actual hw248 sessions. The compiler build environment
is inherited unchanged from `knowledge/toolchains/art-r155/BUILD.md` and
`benchmark/2026-10-02-u12-jar-r2-bake/evidence/U12-BUILD-snapshot.md`.
The board libart is unchanged. Only boot.oat identity below is bound to
U14 run1; actual argv, tool and live-log hashes are in `receipts/paired-run1.json`.
This does not approve the paired-byte reproduction difference.

```t4b-build-json
{
  "schema": 1,
  "evidence_kind": "build_receipt",
  "artifacts": {
    "libart_sha256": "59e1bb45294b9dd587dc9b81bad719b60675aa98c9c6cfced426449bcad0fe5f",
    "boot_oat_sha256": "01fbf4810447ba5b2273ae4e7ab288784f7d31703df5d7e45001b3e83415e54c"
  },
  "environment": {
    "ART_USE_READ_BARRIER": "false",
    "ART_DEFAULT_GC_TYPE": "CMS",
    "ART_USE_GENERATIONAL_CC": "false",
    "ART_HEAP_POISONING": "false",
    "ART_TEST_DEBUG_GC": "false",
    "ALLOW_MISSING_DEPENDENCIES": "true"
  },
  "native_debug_build": false
}
```
