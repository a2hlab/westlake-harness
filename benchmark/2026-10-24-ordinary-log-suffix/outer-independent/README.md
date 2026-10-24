# Outer-independent collection addendum

Both existing ordinary stderr files are bound to the saved T109 file identities and exact 131072-byte prefixes. PID 7011 has 368251 bytes (237179 additional bytes); PID 9860 has 314796 bytes (183724 additional bytes). Both remain below 512 KiB. This establishes evidence identity only, not the cause of a blank screen or a repair.

The unchanged `check_identity.py` returned rc 0 with both files bound. `review_outer.py` additionally parsed the original STAT lines and T109 marker framing, compared the actual payloads, verified exact allowlisted argv and eight successful HDC command receipts, and checked the 60-second window / 10-second command budgets. The recorded lock check returned 1 with empty output. Atime is excluded from identity. Current observed boot and historical capture boot are recorded separately; neither is inferred to be file birth boot.

Aliases in the SHA index:
- `$OUTER_PARENT`: `$HOME/.local/share/westlake/t122-hdc-outer-check-20261024`
- `$OUTER`: `$OUTER_PARENT/collection-01`
- `$T109`: `$HOME/.local/share/westlake/spare-board-reboot-repeat-20261023/raw/06`
- `$CARD`: this card in the inner worktree.

Only SHA/size/identity receipts are public. The payloads, prefixes, source argv and raw stderr remain private. `review-result.json` pins every collection file, both original T109 captures and the outer collector. `private-run-index.json` pins this offline review's actual execution receipts. No device command was issued by this review.

```sh
python3 benchmark/2026-10-24-ordinary-log-suffix/check_identity.py "$HOME/.local/share/westlake/t122-hdc-outer-check-20261024/collection-01"
python3 benchmark/2026-10-24-ordinary-log-suffix/review_outer.py --raw "$HOME/.local/share/westlake/t122-hdc-outer-check-20261024/collection-01" --old "$HOME/.local/share/westlake/spare-board-reboot-repeat-20261023/raw/06"
```

The original inner timeout, `results.json`, collection summary and raw index are retained unchanged. This is a subsequent independent collection, not a relabeling of the failed invocation. Six Python cases passed again; the previously recorded Rust thin test remains applicable because its checker and tests are unchanged. No diagnosis, deployment or UI success is claimed.
