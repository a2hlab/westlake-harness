# Build and dependency boundary

`BUILD_OUT=/new/output ./build.sh` compiles the exact Java API unit with a JDK8-compatible javac. This is an API-unit build, not a claim that the multi-fix J1-final runtime JAR was reproduced. The original full-JAR build.py and J1-final result are preserved; `integration/B7BindFixes.java` shows the real bind-time call. Every listed source and binary build input SHA remains in the original result. Recover those exact inputs before using the full-JAR producer; the API unit and callsite are in this repository rather than requiring a branch lookup.
