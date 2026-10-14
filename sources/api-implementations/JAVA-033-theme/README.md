# Activity manifest theme: actual source and reproducible J10d overlay

The API atlas previously linked only disassembled evidence although the exact Java source was already tracked. The [actual Java implementation](../../../benchmark/2026-10-01-j10-freeze-draft/sources/J10dTheme.java) is blob `f7429baf140476ffdd37febd2565f78f290deeaa` from commit `1d691f67cc9da4a41f4beb2fae8c139bab44c538`. It restores the activity manifest theme immediately before launch. [caller.patch](caller.patch) preserves the original Java call-site change. Historical app evidence remains in the original J10d benchmark; this delivery does not claim new board testing.

The new [build.py](build.py) compiles that Java, adds only its D8 output to the locked J10 baseline, inserts the exact historical smali call, and assembles the JAR. A compile-only helper declaration matches the existing `ManifestJsonFallback.activityTheme` signature and is never included in DEX; the actual helper source is pinned in [source.lock.json](source.lock.json). JDK 17 reproduces the historical DEX and complete JAR `57d621837eee4d065a49929f0a7f981e811becc4beba988c18b0ab847e67058c`.

```sh
python3 sources/api-implementations/JAVA-033-theme/fetch-inputs.py --out "$INPUTS"
python3 sources/api-implementations/JAVA-033-theme/build.py \
  --inputs "$INPUTS/tools" --baseline "$INPUTS/baseline.jar" \
  --out "$NEW_OUTPUT" --javac "$JAVA_HOME/bin/javac" --java "$JAVA_HOME/bin/java"
```

Use JDK 17 (`17.0.20.1` was executed). The [dependency lock](dependencies.lock.json) records all 11 archive members; fetch supports `--archive-file` for offline use, or `HW248_HOST` and `HW248_HOME` for an authorized archive mirror. Output directories must be new. Every executed command writes raw stdout/stderr and return code; a differing historical JAR returns 2. This is a newly reconstructed and executed recipe, not a recovered original build log.

[New execution](../../../benchmark/2026-10-14-verified-source-closeout/root/verified-j10d-rebuild-04/execution.json). The first attempt exposed an unnecessary transitive compile dependency; the JDK 8 attempt differed only in debug line 38, and the initial JDK 17 package used STORED instead of DEFLATED ZIP members. Failures are retained in the [private raw archive](../../../benchmark/2026-10-14-verified-source-closeout/root/raw-archive.json); none changed frozen expectations.
