# Historical Boat V2 layer composition source

The API table previously referenced a handoff document instead of actual executable composition source. This directory preserves the five original source scripts/config from source commit `a8bb2dac4a612069695ee532f9e9d3fc2d4656cf`. Every byte matches the six-input handoff inventory where applicable; `source.lock.json` pins all five delivered files.

```sh
python3 sources/api-implementations/NATIVE-138-boat-overlay/build.py
python3 sources/api-implementations/NATIVE-138-boat-overlay/build.py --out "$NEW_PAYLOAD"
```

These interpreted shell scripts and init configuration require no compilation. The new offline entry verifies and optionally stages source bytes; it never invokes the device-side scripts. Those scripts implement the historical shared adapter/JAR plus three private library bindings, SHA checks and rollback. Their device-side execution is **not** this build entry.

The five referenced binaries are external pinned inputs, not rebuilt by this source package. This does not deliver Unity's proprietary library source or prove the adapter/JAR source-to-binary equivalence; follow each binary's separate provenance. The historical scripts are retained for API implementation traceability, not advertised as the current sealed board's deployment command. No standalone license was present in the original source directory; licensing scope remains unspecified rather than invented. No board operation or new runtime verification was performed.
