# Exact signed Boat C9 input-dispatch JAR

The original C9-only producer remained in the wiki worktree after V2 signing. [producer.sh](producer.sh) is now preserved byte-for-byte from commit `0624b23b86289f6d01416ed5f72e114035e8e424`, SHA `6729b1ba7e9fbeaabc0759925b2738c46a056b951c4c6f38897cb7146453db2e`. The two delivered smali classes are extracted from the original donor JAR `56e4d4733bb6dc4f260981f51184234522df7a67c0eca01bd1b9ef87369221af`, not from the signed result. Their Java counterpart [InputEventDeviceProjection.java](../../../bms/src/adapter/framework/activity/java/InputEventDeviceProjection.java) is already in this repository. The historical producer uses these smali inputs, not a wholesale compilation of the current AppSchedulerBridge.java.

[build.py](build.py) validates the baseline, sources and tool hashes, disassembles the exact `bbc3f530` baseline, prepares fresh input directories, and executes the unchanged original producer. It adds two input-dispatch classes and the small `dispatchOnMainThread` forwarding method; it does not add the C8 letterbox hook. The producer builds twice. Both outputs match signed JAR `6333bcab4ca2daad03965712deac6adf028a6ff0dfac04fc8ea91af177828852` exactly.

```sh
python3 sources/api-implementations/boat-c9-jar/fetch-inputs.py --out "$INPUTS"
python3 sources/api-implementations/boat-c9-jar/build.py \
  --baseline "$INPUTS/baseline.jar" --tools "$INPUTS/tools" \
  --java "$JAVA_HOME/bin/java" --out "$NEW_OUTPUT"
```

The [source lock](source.lock.json) and [dependency lock](dependencies.lock.json) make the original inputs explicit. Use JDK 17 (`17.0.20.1` executed); the new receipt records the actual Java executable hash. The fetcher also accepts `--archive-file` or an authorized `HW248_HOST`/`HW248_HOME` mirror. The baseline JAR remains a pinned binary dependency. This reproduces the historical overlay, not the baseline from upstream source. The raw new [execution receipt](../../../benchmark/2026-10-14-verified-source-closeout/root/verified-c9-rebuild-01/execution.json) is separate from historical logs and board evidence. No device is accessed.
