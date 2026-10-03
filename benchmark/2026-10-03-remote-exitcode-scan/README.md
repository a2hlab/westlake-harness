# Remote exit-code / path-grep lint — rescan v2 (2026-10-03, read-only report)

`scripts/lab/check_remote_exitcode.py` v2 (12/12 unit tests). Three fixes over v1 per the outer's
10:22 return: ① **wrapper-function detection** — functions defined in the same file whose body
calls `hdc shell` (e.g. `H() { timeout "${T:-60}" hdc -t "$SERIAL" shell "$@"; }`) make every
later `H "..."` a remote call (the body scan is brace-aware: `${T:-60}` no longer truncates it);
② **run_a0.sh known-answer tests** — the two window-1 line shapes (`H "ls $RT_TARGET"
>/dev/null 2>&1 && {…}` for R1, `H "ls $RT_TARGET" 2>&1 | grep -c "$RT_TARGET"` for R2) each hit
exactly once; ③ **scope** now `scripts/**` + `benchmark/**/*.sh` (recursive, includes board/),
and single-file arguments work (v1's rglob silently scanned nothing — the "0 findings" the outer
saw). R1 also narrowed: the consumer must follow the call (`cond && hdc …` is a precondition
guard, benign) and must sit outside the quoted remote string (a remote `echo rc=$?` sentinel is
correct usage, not a bug).

## Correction to the 10:22 dispatch premise

Master `run_a0.sh` (fb3ccd2b53) contains **no `RT_TARGET`** — the quoted `:51/:67` shapes are
the **window-1** version, already fixed by cc-t3 in `ee8e0b8d18` (commit message: "grep -c
fix"). A live probe of master's current file yields **1 finding**:

| file:line | kind | verdict | why |
|---|---|---|---|
| benchmark/2026-10-03-m2-a0-probe/board/run_a0.sh:55 | R2 | **benign after the ee8e0b8d18 fix** | `dirs=$(H "ls -d $PKG_DIRS … 2>/dev/null" \| grep -c "$PKG" \|| true)` — the `2>/dev/null` sits INSIDE the remote command string, so ls's "No such file" never reaches local stdout; grep then counts only real listing lines. The lint cannot see quote-internal redirections — documented known false-positive mode. |

## Repo-wide scan (scripts/** + benchmark/**/*.sh): 4 findings, all R2, all benign

| file:line | kind | verdict | note |
|---|---|---|---|
| scripts/lab/toutiao_accept.sh:53 | R2 | benign | greps a faultlog *listing* for a pid marker; listing stdout carries no error lines |
| scripts/lab/ttdrive.sh:49 | R2 | benign | same pid-marker pattern inside a case branch |
| scripts/lab/sc17_run.sh:64 | R2 | benign | display-only echo |
| scripts/lab/sc17_run.sh:65 | R2 | benign | `head -1` of the same listing |

**0 R1 findings** in the repo scope (t6_board_test.sh's `cond && hdc …` lines are precondition
guards — excluded by the after-call rule). The two real R1/R2 bugs were run_a0.sh window-1
lines, fixed before this scan ran.

## The pattern to adopt (unchanged)

    out=$(hdc shell "[ -f '$p' ] && echo PRESENT || echo ABSENT")
    [ "$out" = "PRESENT" ] || { echo "missing: $p"; exit 3; }

Never judge `hdc shell` by its local exit code; never grep ls/stat stdout for a variable path
unless the error stream is provably dropped remotely (quote-internal `2>/dev/null`).

## Repro

    python3 scripts/lab/check_remote_exitcode.py scripts benchmark --csv out.csv   # 4 findings (test fixtures excluded)
    python3 scripts/lab/check_remote_exitcode.py <single file>                    # works in v2
    python3 scripts/lab/tests/test_check_remote_exitcode.py                       # 12/12 OK
