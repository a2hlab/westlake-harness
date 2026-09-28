# Generation-private Unity identity receipt

This gate consumes exactly two explicitly named private roots. It never searches
`adapter/out`, a device, or a global library directory.

The runtime input must be `GENERATION_ROOT/meta/generation.json` using
`westlake.l03_a12.provider_closure.v3`. The CardWords input uses:

```json
{
  "schema": "westlake.cardwords.native_bundle.v1",
  "generation_id": "the-runtime-generation-id",
  "generation_manifest_sha256": "sha256-of-meta-generation-json",
  "generation_token": "wlgen-ID-MANIFEST_SHA256",
  "artifacts": [
    {"role": "libmain", "path": "lib/arm64-v8a/libmain.so", "sha256": "..."},
    {"role": "libunity", "path": "lib/arm64-v8a/libunity.so", "sha256": "..."},
    {"role": "libil2cpp", "path": "lib/arm64-v8a/libil2cpp.so", "sha256": "..."},
    {"role": "lib_burst_generated", "path": "lib/arm64-v8a/lib_burst_generated.so", "sha256": "..."}
  ]
}
```

Run:

```sh
python3 write_identity_receipt.py \
  --generation-root "$GEN" \
  --generation-manifest "$GEN/meta/generation.json" \
  --cardwords-root "$CARDWORDS" \
  --cardwords-receipt "$CARDWORDS/native-bundle.json" \
  --readelf /absolute/path/to/llvm-readelf \
  --output "$GEN/meta/unity-identity.json"
```

`identity_pass` is host artifact identity evidence only. It is not runtime or
device evidence.
