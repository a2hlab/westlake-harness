# Review: `publish_once` (local JSON receipt publication)

The reviewed function is `publish_once` in `westlake-harness-t37-peer/benchmark/2026-10-24-existing-demo-reentry/recorder-fix/review_wait.py` (file SHA-256 `577de73b…`). Only this function was read. The tests extract it by AST and do not import or run the module.

**Verdict: no blocking defect for the three goals.**

| Goal | Result | Why |
|---|---|---|
| Never overwrite an existing target | yes | `os.link(temp, path)` is create-if-absent. An existing regular file, symlink or dangling symlink raises `FileExistsError` and is left unchanged; the symlink target is not followed. |
| Target visible only when complete | yes | Bytes are written and `fsync`ed into a unique hidden temp file (opened with `'x'`) before the single `link` publishes them. A reader can never open a half-written target. |
| Temp file removed on exceptions | yes | The `finally` unlink removes the temp after success, after a serialization error, after a link failure and after an interrupt raised post-link. |

**Non-blocking notes** (no change proposed, because the task excludes feature expansion):
1. **Durability.** The parent directory is not `fsync`ed after `link`. A power loss right after publication could lose the new name. Visibility and the no-overwrite guarantee are unaffected.
2. **No hard-link support.** On a filesystem without hard links, `os.link` raises. The function then fails closed: nothing is published and the temp file is removed.
3. **Killed process.** A SIGKILL between temp creation and cleanup can leave a hidden `.<name>.<hex>` file behind. It is never visible under the target name.

## Tests
`test_publish_once.py`: 9 tests, all run in a fresh temporary directory, offline, with no device and no existing run touched. Result: **9/9 OK** (`test-run.txt`). They cover:
- a new target, checking the content and that no temp remains;
- an existing regular file, an existing symlink and a dangling symlink, each refused and unchanged;
- a serialization error, which leaves nothing behind;
- `os.link` unsupported, which fails closed and cleans up;
- an interrupt after the link, which leaves a complete target and no temp;
- 16 concurrent processes, of which exactly one wins and 15 get `FileExistsError`;
- a reader polling while a large write runs, which only ever parses a complete JSON.

The last test is weak because its race window is short; the guarantee rests mainly on the publish-after-fsync structure.

Reproduce with `python3 benchmark/2026-10-24-local-json-publication-review/test_publish_once.py`. By default the test reads the sibling benchmark `../2026-10-24-existing-demo-reentry/recorder-fix/review_wait.py` relative to its own location; set `PUBLISH_SRC` to test another copy. In this worktree the sibling file is absent, so `test-run-2.txt` ran with `PUBLISH_SRC` pointing at the t37-peer original (9/9 OK); `test-run.txt` is the first run, kept unchanged.
