# ACK G06-PS-FORMAT-FIX

Actual window-outer-01 command-00104 rows 152/153/240 contain kernel NAME fields with spaces. The sole production logic change is `split(maxsplit=3)`; PID/PPID/UID, holder, boot, package and restore gates are unchanged.

- Hook SHA256: `6c6d7bd05c97c2872d2cd598467f2f35594d06b9efe0af3b1f373bcc837de17b`.
- Real fixture red rc1 before the fix; 16 tests green rc0 after it. The complete real stdout parses 348 process rows offline. Only three kernel rows are public.
- No device call, no fabricated missing context, no original-window rewrite. Retain the failed after_lock and before_unlock receipts. Regenerate the next approved config to bind this new hook SHA; do not overwrite the failed window's config.
- Exact delta list: `landing-ps-format-paths.txt`. Manifest includes the prior payload plus this revision; original test receipts remain unchanged except public red traceback paths are sanitized, with exact raw retained privately.
