# T35 whitescreen-01 — 61b white screen after closing Toutiao and tapping the icon (read-only)

Frames (`61b-white-1.jpeg`, ×3 byte-identical, ~3 s apart): uniform white with the gesture bar. Same boot
`be4badc3`; guardian 4016/b3869 and private parent `appspawn-x` 5089/b5573 are still the W05 instances; the old
child 7140 and old host 4834 are gone; the host was recreated (imehost 22069 as `imehost0` WID 66, later focus 72).

Guardian `state = AWAITING_REENTRY`; events end with child 7140 `process_exit` → `child_retired strict_exited` →
`AWAITING_REENTRY child_exited_wait_manual_icon` at uptime 23350, then nothing.

Mechanism (static, deployed sources; `watchdog.sh` 8bf74a08): a host focus counts only if `verify_parent_window_soft`
(`watchdog.sh:235`) finds the parent's `WL_PARENT_ID` equal to the focused WID; otherwise `rc_focus_state`
(`watchdog.sh:304`) returns `other`, the arm is cleared and no spawn or event happens (`reentry-common.sh:78`).
The parent's WID is written only when the parent is launched (`real-start-parent-bounded.sh:9` rewrites
`WL_PARENT_ID` in `run.sh`); `start-parent.sh:9` refuses an existing socket (bootstrap-only parent); `real-spawn.sh`
only sends a spawn request to the old socket with no rebind. After the close the host was recreated (WID 66, later
72), so a parent still carrying its bootstrap WID would make every host focus `other` — consistent with
`AWAITING_REENTRY`, no new child and a white host. **Inferred, not observed.**

Missing evidence: the live `WL_PARENT_ID` of parent 5089. Why board reading stopped: (1) tool failure — the board has
no `tr`, so the `w07` `cat | tr | grep` pipeline returned `env_rc=1`, which proves nothing; (2) my following step that
reported environment-derived content was stopped by a safety classifier, so I did not retry any environment read.
Historical W-02 `run.sh` copies are not used as live evidence. Not claimed: crash, guardian death, or that the
user's close killed the child. Raw: `$HOME/.local/share/westlake/manual-video-regression-20261021/whitescreen-01/`.
