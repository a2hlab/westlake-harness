# SDK ABI and actual T26/T27 R23 peer regression

**14/14 original host EGL scenarios pass against the new implementation with the real observer enabled. This is not device or video acceptance.**

The actual OH SDK compiler accepts `sdk_abi.c`: `OH_NativeBuffer_Config` is 20 bytes, with width/height/format/usage/stride offsets 0/4/8/12/16. GetConfig has the void two-argument signature. The distinct SDK `OH_NativeBuffer_FromNativeWindowBuffer` has an int32 return and output pointer; the permitted legacy getter is the exact non-underscored `OH_NativeBufferFromNativeWindowBuffer`, whose pointer-returning one-argument declaration is separately pinned in `results.json`.

`test_egl.c` is byte-for-byte the original T23 fixture. It compiled the **new derived** EGL state machine plus actual `observation.c` and final `observer.c`, using `-DWL_T27_OBSERVER -D_GNU_SOURCE=1`. All 14 existing cases, including duplicate creation and original provider-call assertions, passed. Success, duplicate, and create-failure cases each emitted one actual T27 create record; foreign forwarding emitted none. The original fixture does not bind optional getters, so buffer metadata correctly remains **UNKNOWN**. It does not simulate successful getter-instance admission.

The reviewed glue resolves optional getters from retained owner/HWUI handles and accepts only the already-proven surface instance. Config is read through a typed SDK thunk and copied by field name. Import observation occurs after provider unlock and before table publication while the newly created window remains exclusively owned. The selected create pointer is invoked once; its result is reused.

## Replay

Use the exact source hashes in `results.json`. `T26` and `T27` name the respective implementation directories; output should be in a persistent review directory.

```sh
cc -std=c11 -O2 -Wall -Wextra -Werror -pthread \
  -DR23_SLOTS=2 -DWL_T27_OBSERVER -D_GNU_SOURCE=1 \
  -I "$T26/derived" -I "$T26" -I "$T27" \
  test_egl.c "$T26/observation.c" "$T27/observer.c" -o test_egl
for c in same_image_two_displays success full duplicate wrong_display destroy_retry \
  create_fail display_absent display_multiple foreign fence provider_refused native_fail target_refused; do
  ./test_egl "$c" || exit 1
done
```

A bounded independent check of candidate `fc58cec5…` finds 78 unchanged export/version tuples, unchanged libc-only dependencies, no TEXTREL, both macros in all ten real compile commands, probe strings/local symbols, and real call instructions into the observer. The formal production-02 receipt now completes with explicit GNU output and nonempty export checks. Its candidate bytes exactly match production-01; all 12 declared output hashes/sizes and all 25 raw command return codes were independently checked. The original production-01 incomplete receipt remains preserved. No host scenarios or same-byte disassembly were repeated. This remains an offline candidate result, not deployment or runtime acceptance. Full hashes and exact ELF call locations are in `results.json`; private original commands, source snapshots, stderr and compiler receipts are indexed by hash.
