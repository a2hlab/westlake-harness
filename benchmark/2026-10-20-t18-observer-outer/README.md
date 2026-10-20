# T18 outer-owned observer assembly

The historical outer wrapper hardcoded 61b and did not cover staging-to-observer failures with an outer `finally`. This 5cd-only wrapper uses the existing Board transport, fresh T17 collector receipt, and the reviewed T18 bridge-specialized observer. It changes no runtime bytes and performs no UI. This delivery has no device execution evidence.

Preview: `python3 wrapper.py`. Execution is exclusively by the outer operator:

```sh
python3 wrapper.py --execute --repo "$REPO" --plan "$PLAN" --profile-dir "$FRESH_PROFILE" --out "$NEW_PERSISTENT_OUTPUT"
```

Copy `plan.example.json` to a private persistent location. Fill the exact current holder/start/boot, explicit parent/child/host PID/birth, reviewed wrapper and T18 observer SHA, actual local five ELF paths, pinned host/server/HDC paths. Only the outer operator enables and signs `approved_by=outer(codex)`. `profile-dir` must be a successful new `collect_reader_profile.py` output, including `profile.json`, `result.json`, `receipt.raw`, and `run.sh`; freshness is 120 seconds. T18 observer source must already be landed at its named repo-relative path. The new bridge local file is production `candidate.so` dca530, never the old d4fa seal copy.

Before staging, all five actual child-private ELF SHAs and mapped dev/inodes are checked between identity guards; both libandroid mapping instances may share one inode. The module paths come from the historical exact admission template, including `webview-t-lib/libandroid.so`. No server identity is fabricated for admission. The actual owned PID/birth/UID/executable/NUL commandline/listening socket are collected after one launch, followed by the unchanged full T18 gate and SDK15 entry.

All launch attempts, including transport timeout, enter cleanup. Only the uniquely staged server and exact newly-created forward can be stopped/removed. Host waits are bounded; SIGTERM/SIGINT trigger cleanup. If ownership or same-child resume cannot be established, output requires outer recovery. No business process is signalled. Staged server/stdout/stderr remain as evidence. The operator must preserve the output and use the existing candidate-window recovery; this tool does not claim a physical or runtime rollback.

`OBSERVATION_RETURNED_NOT_PLAYBACK` requires observer event-budget completion plus observer detach and outer cleanup. It is not proof of rendering, playback, or audible output. Preview/host checks cannot prove real attachment or cleanup; the final spec scenario remains human pending review.
