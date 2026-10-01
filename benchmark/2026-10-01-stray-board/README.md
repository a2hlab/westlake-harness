# cc-t3 board entries that never reached the canonical board (2026-09-30 07:39 .. 2026-10-01 11:54)

Found by `scripts/lab/stray_board_check.sh` at 2026-10-01 13:37. cc-t3 appended its hand-offs to an untracked file
`westlake-harness-t3/app-lighting` (a relative board path resolved inside its worktree) instead of
`westlake-harness/.octos/boards/app-lighting.md`. 50 entries (LOCK/UNLOCK, PROGRESS, ACK) — none of them is on the
canonical board; the outer loop only saw cc-t3's work through commits and pane reads and recorded "did not post"
several times (board ACK(95) 09:11:04, 10:16:22 …; R2 #97 EVO-0060).

`cc-t3-worktree-app-lighting.txt` is a byte copy (sha256 equal to the original). The original was renamed, not
deleted, to `app-lighting.archived-20261001` in the cc-t3 worktree so a later relative write shows up again as a
fresh stray file. The entries are not re-appended to the board: their timestamps would interleave out of order.
