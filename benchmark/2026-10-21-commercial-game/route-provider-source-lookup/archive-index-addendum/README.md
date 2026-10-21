# Archive-index addendum: are the deployed-generation source snapshots in the two airdrop archives?

Independent-review follow-up to the route-provider source lookup. RUNBOOK-102 names the deployed route-A
generation's source at `$WORKSPACES/01.OH61AOSP16/real-work/.state/zigzag-*` (identities.txt,
r138h-sealed-generation-source, r148-source, r150-sealed-generation-thin.bundle, final-r155). The outer loop
reports those are no longer at the original paths, but the two migration archives
`_airdrop-20260930-delta` and `_airdrop-20260930-delta2` still exist. This checks only whether the targeted
source is an **extractable member** of those archives.

## Method

Read-only Python `pathlib.read_bytes` of the four literal member-list files; separator auto-detected from the
bytes (NUL in all four); member counts exclude the trailing empty item from the final separator. No
decompression, no `ls`-rendered paths, no script run, no network/device/REA/debugger. Authoritative receipt
is read 10; reads 08/09 used correct NUL splitting and agree.

| Member list | SHA256 | Separator | Members |
|---|---|---|---|
| `_airdrop-20260930-delta/delta.tar.zst.files` | `ee22e36d…` | NUL | 77329 |
| `_airdrop-20260930-delta2/delta.tar.zst.files` | `cd66a23e…` | NUL | 363 |
| `_airdrop-20260930-delta/octos-state.tar.zst.files` | `0d3cc88d…` | NUL | 6 |
| `_airdrop-20260930-delta2/octos-state.tar.zst.files` | `0d3cc88d…` | NUL | 6 |

## Result

- **Target source snapshots: none present.** No member contains `zigzag-final-r155`,
  `zigzag-r138h-sealed-generation-source`, `zigzag-r148-source`, `zigzag-r150-sealed-generation-thin.bundle`,
  `post-rollback-redeploy/identities.txt`, or `01.OH61AOSP16` / `real-work`.
- **No 6d5 sigchain source record**, and the deployed SHA `6d5d5538…` does not appear in any member path.
- **Only payload copies exist.** The sole route sigchain/unwindstack members are payload `.so` files in two
  generations:
  - `westlake-generation-n3-8a7880fa/payload/{route,android/lib64}/{libsigchain,libunwindstack}.so`
  - `westlake-generation-n3b-53bb18d1/payload/{route,android/lib64}/{libsigchain,libunwindstack}.so`
  The member list carries **no SHA**, so it is not established that any equals the G34-deployed `6d5…`/`d2c1…`
  bytes, and a payload `.so` member is **not** source or a reproducible build.

## Conclusion

Within these two migration archives' four member lists, the original deployed-generation **source is not
extractable**: the RUNBOOK-102 snapshots, identities.txt and the r150 thin.bundle are absent, and no 6d5
sigchain source record appears. The only matches are payload `.so` copies in two generations, listed without
SHA. An archive member is not source and not a reproducible build; a payload copy is not proof of the
deployed bytes.

This is bounded to the four literal member lists; the archives were not decompressed and the search was not
widened.

## Honesty note on receipts

- `06-airdrop-lists` and `07-airdrop-detail` recorded **outer rc0** (their `.rc` files are `0\n`). An earlier
  note mis-read the 2-byte file size as "rc2"; that is **withdrawn**. They are still unusable: they used an
  `ls`-rendered entry path carrying OSC8 hyperlink escapes and produced **empty/invalid counts** from a wrong
  separator assumption, and their **stderr was not separately saved** (merged into stdout via `2>&1`).
- The `.argv` files for reads 06-10 are **description sentences, not exact argv**. `10-pathlib-index.argv.txt`
  contains a `/tmp/<pid>` placeholder; the original temporary Python script was deleted after the run and is
  **gone**, so it cannot be copied to a persistent location. This is recorded as missing, not reconstructed.
- None of 06/07 is a complete original execution receipt. The usable stdout/rc are from reads 08, 09 and 10
  (10 stdout/stderr/rc are real, rc0, and agree with 08/09); treat their argv as descriptions, not
  reproducible commands.

No device, ADB, REA, debugger, build, decompression or network. No claim of a game fix or crash cause.
