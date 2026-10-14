# Recoverable worktree retirement

A completed source/API delivery did not establish that every historical worktree was disposable. The initial inventory contained 75 registered worktrees, including seven stale registrations. Twelve valid worktrees had tracked edits and fourteen had non-ignored untracked files. Even a clean, merged candidate contained 223,461,960 bytes of ignored APK, SO and screenshot data. Consequently, a clean Git status alone is not a deletion criterion.

This bounded operation retires only `westlake-harness-label` and `agent-a2ef2d12ea17a76fc`, after verifying both HEADs are ancestors of master, no local edits or non-ignored untracked files exist, no processes hold their paths, and every file (including ignored content) is in a complete private archive. All branches, the main checkout, remaining worktrees, stale residual directories, remote build-source trees and demo artifacts are retained.

The private archive includes Git administrative data, both complete candidate directories and staged/unstaged binary patches from all 68 valid worktrees. It does **not** back up all untracked/ignored content of retained worktrees; those directories stay in place. Archive contents are checked member by member, both candidates are actually extracted and compared, and the independent hw248 copy must have the same SHA256 before normal `git worktree remove`. No force removal, branch deletion, object garbage collection or device operation is used.

An initial extraction refused absolute toolchain symlinks. That failure is preserved privately. The successful recovery extracts ordinary files first, then recreates the exact symlink targets without following them or writing to their destinations.

Actual outcome: both normal removals returned zero, seven stale registrations were pruned, and the registered count changed from 75 to 66. All branch refs were identical before and after cleanup. The 1,361,149,188-byte archive contains 14,104 members; 9,282 candidate regular files were restored and verified. The [post-cleanup API publication check](api-links-after.json) still resolves all 460 links per language, 1,993 Markdown links and 470 source/build publisher URLs.

See [inventory](inventory.json), [independent review](independent-review.json) and [actual results](results.json). The results record the private local and remote archive locations, SHA256, restoration count, actual removal return codes and branch-reference comparison. Private archives, raw patches, Git configuration and commercial APKs are deliberately absent from this public repository.

## Recovery

Keep the current main repository. Recreate each removed worktree with `git worktree add` using its preserved original branch; restore that candidate's archived files on top, excluding the old `.git` pointer, and compare against the private archive manifest. `RESTORE.md` in the private backup gives details. Never overwrite a live `.git` directory with the administrative snapshot; use a separate private recovery directory if disaster recovery is needed.

## Checks

```sh
python3 benchmark/2026-10-14-worktree-retirement/test_verify.py
python3 benchmark/2026-10-14-worktree-retirement/verify.py
cargo test --manifest-path tools/spec-checks/Cargo.toml --test worktree_retirement
```

The refusal tests cover an unmerged HEAD, tracked/untracked changes, content drift, missing restore proof, active files, archive verification failure, missing or mismatched archive hashes, and paths outside the two-directory allowlist. The operational gate is called again immediately before each removal. Remote build directories remain protected; this report is not authorization to remove all build outputs or all remote branches.
