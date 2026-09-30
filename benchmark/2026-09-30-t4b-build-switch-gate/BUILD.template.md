# T4b builder receipt template — not evidence

Replace both placeholders with full hashes of the actual inputs. Do not use
this template to claim a missing historical build. Keep source/toolchain and
host dex2oat/dependency hashes, compiler commands, build logs, and all relevant
environment settings in the completed BUILD.md. The runtime library may be the
unchanged board R155 artifact; it need not be the newly built target library.

```t4b-build-json
{
  "schema": 1,
  "evidence_kind": "build_receipt",
  "artifacts": {
    "libart_sha256": "<actual runtime libart full SHA256>",
    "boot_oat_sha256": "<actual generated primary boot.oat full SHA256>"
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

Values above illustrate the requested T3b configuration, not a measured build.
Record actual values even when they disagree; the gate must then fail.
