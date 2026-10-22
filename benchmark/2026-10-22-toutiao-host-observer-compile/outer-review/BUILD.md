# Reproduce the bytecode build

Use the pinned Linux `es2abc` in the existing `a2hlab` OrbStack VM. Source and output paths must be visible unchanged through the Mac filesystem share. The compiler SHA is checked by the driver; a different compiler is refused. `$COMPILER_VM_PATH` is the actual VM-visible tool path, and `$FRESH_BUILD_DIR` must be a new persistent absolute directory.

From repository root:

```sh
python3 benchmark/2026-10-22-toutiao-host-observer-compile/compile_observer.py \
  --compiler "$COMPILER_VM_PATH" --raw "$FRESH_BUILD_DIR"
```

Alternatively use `--compiler-receipt "$HISTORICAL_RECEIPT"` to read the exact compiler path from an original receipt. Do not use both options. The driver reproduces the original baseline before compiling the candidate twice; each command retains raw logs, return code, timestamp and artifacts. The final receipt must report `EXACT_BASELINE_AND_CANDIDATE_COMPILED` and the hashes listed in this card. No signing or installation occurs.

`check_compile.py` verifies this recorded historical build and its indexed raw files; a fresh clone without those external originals cannot pass that evidence check merely by compiling anew. A new build produces its own receipt. Keep that distinction when reproducing on another machine.

Source license: [retained original license](../../2026-10-22-toutiao-host-launch-observation/sources/LICENSE).
