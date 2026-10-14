# Final supplement v2 — fixed handoff

- Mapping: `benchmark/2026-10-14-api-source-delivery/release-v2/source-build-mapping.json`
- Mapping SHA-256: `c78e9e61f79b958f22e5f69a9309287d383c3824b74e38a16c4413e619c1d6b0`
- Recipes: `benchmark/2026-10-14-api-source-delivery/release-v2/recipes/recipes.json`
- Recipes SHA-256: `c6ad2f46e5b27578d4c1cda90ea7c973018f2ed49bcbb868c7c77cd6fd909261`
- Master: `b7d63270327c3ec4f97fb9ecaab820d981fca614`
- Base v1 mapping: `6e65f6fdcd06efb7a8cc8630b2cdd9f0b9de49631d9f5f0b2894e20589d4458e` (unchanged).

## Extra stable metadata: land first or with this packet

- `benchmark/2026-10-14-api-source-delivery/frozen-inputs-v2/remaining-api-resolutions.json` — `e8aa0f647a3248a5f5eea18b5bc194657c39dce8f5fc5ca27fa11cd4f4a25a71`
- `benchmark/2026-10-14-api-source-delivery/frozen-inputs-v2/native155-resolution.json` — `d721247c1dc4cf6465b41bfb43ea060454beeae05c2cbd8da6d3261655b88bc1`

Exact two-file listing: `landing-metadata-v2.txt`. Full producer listing: `landing-mapping-v2.txt`. These are frozen copies of the committed resolutions; no mutable final-delivery-review pin is consumed. All code and all direct build entries resolve from MAIN, never a producer code fallback.

## T0: run once after metadata landing

```sh
python3 benchmark/2026-10-14-api-source-delivery/generate.py build \
  --mapping "$WORKSPACES/westlake-harness-t4/benchmark/2026-10-14-api-source-delivery/release-v2/source-build-mapping.json" \
  --mapping-sha256 c78e9e61f79b958f22e5f69a9309287d383c3824b74e38a16c4413e619c1d6b0 \
  --out benchmark/2026-10-14-api-source-delivery/views-final-v2
python3 benchmark/2026-10-14-api-source-delivery/generate.py check \
  --mapping "$WORKSPACES/westlake-harness-t4/benchmark/2026-10-14-api-source-delivery/release-v2/source-build-mapping.json" \
  --mapping-sha256 c78e9e61f79b958f22e5f69a9309287d383c3824b74e38a16c4413e619c1d6b0 \
  --out benchmark/2026-10-14-api-source-delivery/views-final-v2
```

The original315 semantic grades are unchanged. This supplement updates10 reviewed member rows, NATIVE155 producer/consumer, and six J7b member recipes. Do not pass --require-complete: missing APIs, stubs, historical producing-source gaps and external toolchain dependencies remain explicit. Native155 original test imports failed before tests, so no PASS is invented. Bitmap owner reference and proposal are not claimed as the historical deployed repair. The J7b full overlay build still records producer0 / strict wrapper2 and unequal historical DEX/JAR.
