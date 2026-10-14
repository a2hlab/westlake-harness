# j7b source-complete overlay sidecar

All original 51 Java inputs are present and SHA-pinned in `sources.lock.json`. Source bytes are unchanged. `producer.original.py` preserves the preceding producer exactly; `producer-deterministic.patch` only adds final smali `--jobs 1`. All original baseline, injection and postflight guards remain.

The fresh producer returned 0, but its JAR did not match the unchanged historical SHA and the wrapper returned 2. Read [the source-closeout report](../../../../benchmark/2026-10-14-verified-source-closeout/jar/README.md). This is implementation-source and executable-recipe delivery, **not historical exact binary reproduction**. Inherited baseline classes remain an explicit pinned binary dependency; original production logs were not recovered.

Use the parent `run_pair.py` for the pinned JDK17 image, or `build.py --inputs INPUTS --out NEW_OUTPUT --run` under JDK17. `fetch-dependencies.py --out NEW_INPUTS` fetches the existing SHA-locked 14-input archive; `--archive-file` enables offline verification. No device calls. Historical path diff text is normalized as `${HISTORICAL_HOME}`, not an executable host path. Copyright and existing license headers are retained.
