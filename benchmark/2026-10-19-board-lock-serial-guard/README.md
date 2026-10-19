# Reject truncated board keys on every lock operation

Previously only `lock` validated the length of a hexadecimal OH connect-key. A truncated `unlock` could return 0 and append an UNLOCK record while leaving the real board locked. The 2026-10-19 video observation window exposed this; the exact 32-character key was then unlocked and independently checked.

`lock`, `unlock`, and `held` now share the same existing hexadecimal-key length rule. Three real CLI negative checks returned 2 without changing the campaign board. The valid, unheld key returned 1 with no holder, preserving read semantics. See `results.json`. No device commands were issued by these checks.
