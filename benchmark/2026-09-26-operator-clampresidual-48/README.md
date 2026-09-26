# 2026-09-26 operator clamp residual (#48)

After the Layout -79 clamp un-collapsed the window, real render/nav load (360s harder)
revealed residual mallocng heap corruption in clamp-r3/r4. Analysis only (no binary).

## Layout
| Path | What |
|------|------|
| evidence/clamp-r3r4-heap-residual-48.txt | r3=jato free-hook; r4=shadowhook inline-hook machinery via hotfix-opt (only active hooker); (c) pre-existing residual revealed by render load; next = convergent engine (bytehook/shadowhook) hollow + crux experiment; fallback jato+hotfix patches; needs codex-2 arm64 baselines. |

## Verdict
- Same mallocng chunk-header-overwrite class (0xd6e20 / 0xd5e1c detection points).
- r3 jato (unpatched malloc-hooker), r4 shadowhook machinery (hotfix ClassLinker hook).
- Pre-existing, revealed by full-size render + hard nav (hollow's 1px window suppressed it).
- Convergent fix: hollow the engines (kills all hookers); crux experiment resolves engine + load-bearing-hook questions in one run.
