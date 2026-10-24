# Native host window record reader (t1)

`0660` with the expected UID/GID is accepted. Group write is not a rejection condition. The API returns a **candidate**, never an authenticated window or an attached session. This is an independent native source candidate; it does not recover a window or establish that the deployed child can read the host file.

## Implementation and replay

`host_window_record_reader.h/.cpp` exposes `ReadWindowRecord(path, expected_uid, expected_gid)` and typed statuses. Successful results contain the positive int32 window ID and file device/inode/size/nanosecond timestamps/owner/mode. Non-candidates carry no candidate value. The reader retains no prior binding and sends no IPC.

The t1 addendum also returns `SourceEvent::WindowReady` or `SourceEvent::StageEvent`, plus optional signed-integer `stage_event` from `details.event`. Missing stage event remains unknown; malformed or unrepresentable values are rejected. HIDDEN=4 remains a candidate with value 4, never a visible-window signal. SHOWN=1 and ACTIVE=2 are preserved without executing actions. Definitions: local SDK `@ohos.window.d.ts:8897-8997`; the baseline EntryAbility publishes this value at lines 21-23. A ready event itself does not authenticate a currently visible parent.

The original nlohmann JSON 3.11.3 single header from the local OH source mirror is vendored byte-for-byte; `dependency-lock.json` records its full SHA and source alias. Parsing consumes one complete object, rejects duplicate decoded keys at every object level, literal NULs, invalid UTF-8, trailing data, malformed JSON, floating-point/string/bool IDs and container depth above 16 (root counts as one). Only `window-ready/details.id` and `stage-event/details.window.id` yield candidates. Other events and missing IDs are unavailable.

The file is opened read-only with `O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC`. It must be regular, at most 8192 bytes, owned by the expected UID/GID and not world writable. At most 16 reads and an 8193-byte buffer bound the work. FD metadata before/after and final `lstat` of the current path must agree; short reads, observed replacement and timestamp/owner/mode drift cannot yield a candidate. The additional byte detects growth. Input contents are never written.

From the repository root:

```sh
CARD=benchmark/2026-10-24-native-host-window-recovery/record-reader
python3 "$CARD/run_tests.py"
CARGO_TARGET_DIR="$PWD/$CARD/.private/cargo-replay" cargo test --offline \
  --manifest-path tools/spec-checks/Cargo.toml --test host_window_record_reader \
  host_window_record_reader_fixtures -- --exact --nocapture
```

The Python entry compiles the **production C++ reader** and the file fixture executable using C++17 and warnings-as-errors, then runs it. Each run gets a fresh private directory; an existing explicit `--out` is refused. Dependency SHA is checked before compilation; all input SHA values are rechecked afterward. Actual argv/start/end/rc/stdout/stderr, compiler version/hash, executable hash and source pins are persisted from execution time. `CXX` may name an explicitly selected local compiler; no downloads or remote builds occur.

## Evidence and test limits

See `results.json`, `evidence/` and `raw-index.json` for actual runs. The updated fixture executable has 81 passing assertions, including three raw stage values and invalid stage type, the two `0660` records and identities, unchanged input bytes, unavailable events, duplicate/escaped keys, malformed input, ID bounds, depth and size boundaries, wrong UID/GID, world write, missing file, symlink, directory and real FIFO rejection under one second. It also invokes the production metadata predicate for each changed field, path replacement identity and short-read rejection. Those deterministic predicate cases are **not** a claim of an observed live concurrent file race. Rust invokes this same build/test entry, not a mirror implementation. Five contract scenarios share that selector. The original 77-assertion logs and pre-addendum source snapshot remain private and unchanged.

The first lifecycle invocation intentionally selected only lint/boundary: it returned rc1 with five skips because the test layer was absent. Its original receipt is preserved, separately from the subsequent test-layer result; it is not a test pass.

The subsequent lifecycle test-layer invocation timed out at 120 seconds, and explain-history timed out at 15 seconds. Both empty-output receipts are preserved. No further meta-workflow retries were made; direct production tests and the actual Rust selector pass are reported separately from the incomplete full lifecycle.

No metadata bracket can prove the absence of changes completely restored between samples or changes after the final observation. `O_NOFOLLOW` protects the final component; callers must supply a trusted parent path. Bounded bytes/syscalls are not a hard wall-clock guarantee for a filesystem operation. File reads can update filesystem access-time metadata; “read-only” means no content, permission or configuration writes by the reader.

Compilation here is for the local Mac host, not the OH bridge/ABI. Actual child access, SSM ownership authentication, polling, lifecycle/ID mapping and rendering recovery are deferred to subsequent tasks. No frozen implementation, Java/JAR/HAP or control component was modified; device/SSH/REA operations and runtime bridge builds are zero. Existing unrelated worktree edits remain untouched. Shared Git writes are not retried: `author_commit=null`, with a path-only landing list for the outer lane.
