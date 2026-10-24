# t1 host window record reader: independent review of the visibility increment

Reviewed files (read-only, in `$WORKSPACES/westlake-harness-g10-env/benchmark/2026-10-24-native-host-window-recovery/record-reader/`):

| File | SHA-256 |
|---|---|
| `host_window_record_reader.cpp` | `29eb5ba7519f7b0ed74a28f5ccbe05457c7d7028d9fdbb1dee8956fe2eda47b2` |
| `host_window_record_reader.h` | `2427a498acd03ecbfb466e16048c7e42d3e4a4b4b62b5a99a889fbdecf47931d` |
| `tests/reader_test.cpp` | `618e3aebd7790e4043e4947fdfc982fcebb17da151de135571e8db91b1a94562` |
| `vendor/nlohmann/json.hpp` | `9bea4c8066ef4a1c206b2be5a36302f8926f7fdc6087af5d20b417d0cf103ea6` |
| SDK `ets/api/@ohos.window.d.ts` (DevEco SDK 6.1.1.125, apiVersion 24) | `34cf97f1ab75223ee33ef6ee5681b403a151c2c6379183128dceb18336404bed` |

The test count of 81 passed / 0 failed is quoted from that card's `results.json`; I did not rerun it. The earlier 77-assertion review covered `.cpp` `d286eab7…` and does not stand in for this version. **OH toolchain compilation was not done.**

## SDK enum
`WindowStageEventType` (`@ohos.window.d.ts:8897-9018`): `SHOWN = 1` (8922), `ACTIVE = 2` (8947), `INACTIVE = 3` (8972), `HIDDEN = 4` (8997), `RESUMED = 5` (9007), `PAUSED = 6` (9017). The host writes this number as `details.event` in its `stage-event` records (`EntryAbility.js:21-23`).

## Findings
- **`event` / `stage_event` typing** (`.cpp:68-89`, `.h:14, 26-28`):
  - `window-ready` gives `SourceEvent::WindowReady` with `stage_event` empty.
  - `stage-event` gives `SourceEvent::StageEvent`. `details.event` is optional; when present it must be a JSON integer that fits `int64`, otherwise the result is `InvalidRecord` (74-77). The value is passed through raw.
- **HIDDEN is not presented as visible:**
  - The result has no visibility field. `stage_event` is the raw integer, and when it is missing it stays empty (comment `.h:27`: "missing is unknown, never inferred as visible").
  - A `stage-event` with `event = 4` (HIDDEN) still returns `Status::Candidate` with id 62 (test `:51-57`).
  - That is correct for a reader, but it means **the visibility gate belongs to the consumer (t2)**. `Candidate` must not be read as "visible" or "foreground".
- **0660 is accepted:** only `S_IWOTH` is rejected (`.cpp:111-114`). The fixtures write mode 0660 by default (`test:22-25`) and assert `(mode & 0777) == 0660` on the candidate's file identity (`:44-47`).
- **No blocking defect found.** The file-boundary logic, read bounds and JSON rules are unchanged from the earlier review.

## Non-blocking notes (no change requested)
- `stage_event` is not range-checked against the SDK values 1-6. Negative or unknown integers pass through raw. The consumer must treat any value other than an explicitly allowed one as "not visible".
- Test coverage of the new field:
  - stage values: only 1, 2 and 4 are covered; 3, 5 and 6 are not;
  - non-integer stage values: only `true` is covered; float, string and an unsigned value above `int64` max are not;
  - the code paths for these cases exist (`is_number_integer`, the unsigned bound at 75-76).
- **Carried over and still open:**
  - the reader depends on C++ exceptions (it must not be built with `-fno-exceptions` or `JSON_NOEXCEPTION`), and its behaviour under the recorded bridge recipe (`-fno-rtti`, `-nostdinc++` libcxx-ohos, `aarch64-linux-ohos`) is **unknown until the original toolchain compiles it**;
  - the host writes its record non-atomically (`TRUNC` then `write`), so a transient `InvalidRecord`/`Drift` must be treated as retryable by the caller.
