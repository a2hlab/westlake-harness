# J1/J7b source-production closeout sidecar

The previous producers compiled successfully but failed their strict historical JAR SHA gates. All implementation class text matched: the mismatch is DEX metadata pool order, not missing implementation code. This sidecar delivers the actual 39/51 Java inputs, their original Git identities, both producers, 14 SHA-locked compile/tool inputs, a durable exact toolchain image and one new execution pair. Historical binary reproduction **remains rejected**, with wrapper rc2 for both outputs.

See [results and original new-execution logs](../../../benchmark/2026-10-14-verified-source-closeout/jar/README.md). Original FZ-004/FZ-006 sources, SHA expectations, baseline choice, injected calls, preflight and postflight assertions were not changed. `producer.original.py` retains the previous producer; the candidate changes only final smali assembly to `--jobs 1`. This freezes insertion scheduling within that stage but does not recover the historic concurrent order.

Run from the repository root with Python 3.11+, Git, SSH and Docker. These commands write to a new persistent repository-local artifact directory, never a board. Existing output is refused.

```sh
D=benchmark/2026-10-14-verified-source-closeout/jar/.artifacts/replay
python3 sources/api-implementations/jar-production-closeout/j1/fetch-dependencies.py --out "$D/inputs"
python3 sources/api-implementations/jar-production-closeout/fetch-artifact.py --kind toolchain --out "$D/java-image.tar.gz"
docker image load --input "$D/java-image.tar.gz"
python3 sources/api-implementations/jar-production-closeout/run_pair.py --inputs "$D/inputs" --out "$D/build"
```

On an older isolated worktree that lacks the original frozen checker/object provenance, explicitly pass `--reference-repo PATH_TO_MASTER_CHECKOUT`. This mounts the reference read-only; it is not a source lookup for the implementation. The driver mounts this repository read-only and only the new output writable; networking is disabled in the build containers. Docker image ID is `sha256:f39400369f20f4ba610693834f148581376d05c2f321e6194d5bd2934fece4c1`. Its archive is SHA-pinned and durably archived on `hw248`, not an unpinned image tag. `DOCKER` may choose the Docker executable. `HW248_HOST` chooses the configured SSH host. No user-specific absolute path is required.

The one new pair took 32.747/35.000 seconds on the executed host; these are recorded elapsed times, not a promised runtime. The strict driver returns 2 when the producer succeeds but a historical output differs. The comparison tool disassembles both actual DEXs with the locked baksmali dependency and compares all class text and raw section hashes. It cannot authorize deployment or make semantic identity satisfy an exact SHA gate.

The pinned b5 baseline is an inherited binary input. This package does not claim a source rebuild of every baseline class or recovery of original production logs. Original source headers are retained. Existing source license attribution is preserved; no new license is assigned to previously unmarked project source.
