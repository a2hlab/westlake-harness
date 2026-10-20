# T29 independent consumer error-budget correction

The method-ready logger assigned independent reference/unreference failures to its success quota. An actual four-call fixture against `ddd684fb` emitted two successful destroy records and a limit marker, dropping both later `unref=-31` records. The original 14-mode suite even asserted this incorrect classification in `refunref`; its historical PASS does not establish the required independent error budget.

R29-C04 is closed by adding only called, valid, nonzero ref/unref results to the diagnostic failure classification. It does not change method control flow, public/provider return values, JNI calls, reference counts, or lifecycle. The two method translation units and logger header remain unchanged. The final logger SHA is `8d8ff860f659379cbb5d6f493fbb169ed36b94c8c1a7390200b890570ae212fb`.

The corrected suite passes all 14 modes (13 unchanged; one wrong assertion corrected), plus separate actual-logger ref and unref tests. Each new test proves two success records followed by two independent failure records, then exactly one limit notice and no further formatting/time/write work. Original failing assertions and the pre-fix missing-error counterexample are preserved. This is host-only evidence; production integration and device observation remain pending.

Run from any directory:

```sh
python3 benchmark/2026-10-20-t29-consumer-budget-fix/replay.py --out "$HOME/.local/share/westlake/t29-consumer-budget-replay-new"
```

Use a new output directory. The runner preserves actual stdout/stderr and command return codes; a deliberate assertion failure demonstrates that the original wrong test rejects the corrected behavior. The earlier 01 failure is the same wrong test; 02 accidentally included the baseline logger through the fixture's source directory and is preserved as an invalid corrected-build attempt. 03 and 04 pass; 04 uses relative compile paths for shareable raw diagnostics.

Integration replacements are already present at `../2026-10-20-t29-window-observation/consumer/logger/observe29c.c` and `../2026-10-20-t29-window-observation/consumer/test/test_observe29c.c`. `logger.patch` and `test.patch` show the exact delta. `source/` contains the exact corrected logger and unchanged header for standalone reproduction. `counterexample/` retains the original test and missing-error evidence. `evidence/` contains small original outputs; the complete raw logs and all failed attempts are SHA-indexed in `private-raw-index.json` for durable archival. Methods' separate 40 behavior plus 40 observation checks belong to the independent consumer test peer and were not repeated here.

Source review also confirms that published SurfaceTexture state keeps image/window pointer fields unchanged through release/finalize; copying their opaque values does not assert that a released provider object is usable. Producer-destroy `self` identifies the extracted helper, not the public JNI entry; the new production ELF must locate that helper. Named PLT provider identity remains unknown.
