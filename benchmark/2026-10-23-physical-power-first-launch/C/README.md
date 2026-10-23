# T75 C — first launch after a real power cycle (61b)

User confirmed a whole-device power cycle on site ("重新上电", relayed by the outer loop; exact off/on times not independently measured). Enumeration: old boot 33f35797 present, absent from 14:36:56, back at 14:37:57 as new boot e9d0a715 (uptime 16.8 s); ready at uptime 39.5 s.

After a normal wake/unlock (14:41:03) the network auto-connected within 12 s, with no manual action. One UITest tap (not a human finger) on the layout-located Toutiao icon at 14:41:32: t10/t30/t60/t120 screenshots all white; the guardian spawned child 8105, which exited ~43 s after the tap (AWAITING_REENTRY). The device clock read 1970-01-01 08:04 during the run (recorded only).

Result: FAIL, no feed after the first tap following a real power cycle. No retry, no diagnosis. Power restored to the new-boot baseline 30000/10000; lock herdr-t75c released 14:43:54.

The transition log is an exact evidence copy and intentionally preserves original trailing spaces; `git diff --check` reports only those evidence lines, not source or documentation defects.
