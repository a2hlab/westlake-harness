# Recover the fixed T14 interaction log range

The T14 64 KiB read was a complete transport of an insufficient prefix. The known source grew from byte 26,377,929 to 57,241,402 (30,863,473 bytes). No player match in that prefix does not establish that the play interaction was not attempted. TOUCH timestamps inside that prefix span 13.787 seconds, with gaps; the prefix is not proven to represent 0.25 seconds. Host command completion differences from log-start were 14.647 seconds for tab, 99.408 seconds for play and 122.976 seconds for the after-stat. Completion timestamps are not exact UI event times.

This host-only candidate recovers the already existing interval without UI, signals, power changes, deployment, restart or a new application instance. The exact old T14 profile pins child 1601/birth 7706984 and the original boot/parent/host/UID/executable/private namespace. Both sides of the read freshly recheck those identities, fd2 target, regular-file type, device 66352/inode 178230 and size at least the fixed end. The outer operator owns a new lock window of at most 300 seconds; the script does not acquire or release that lock.

`read_range.py` uses 4 KiB aligned dd followed by a tail of at most 4095 bytes. The frame declares **aligned raw payload length**, checks both dd return codes and the final identity guard marker, then trims the leading alignment bytes on the host. The requested raw payload cannot exceed 64 MiB. Transport stdout/stderr go directly to persistent files, including on timeout. Short reads (including dd rc 0), missing markers, failed guards or timeout remain PARTIAL_UNVERIFIED. No retries are made for the range. BMS's existing narrowly scoped read-only readiness retry remains unchanged.

Preview (no profile or device required):

```sh
python3 benchmark/2026-10-20-t14-fixed-range-read/read_range.py
```

After independent review, the outer operator supplies the exact historical T14 profile bytes and a freshly held lock whose full holder text contains its ISO timestamp as the third whitespace-separated field:

```sh
python3 benchmark/2026-10-20-t14-fixed-range-read/read_range.py \
  --execute --repo "$PWD" --profile "$T14_PROFILE" --out "$T15_OUT" \
  --hdc "$HDC" --holder "$EXACT_HOLDER" --start "$WINDOW_START_EPOCH" --timeout 180
```

`T15_OUT` must be a new persistent absolute directory. A new exclusive `/data/local/tmp/t15-range-<uuid>` directory holds only two small dd diagnostic files. Original app data and the original log are never written. Successful output includes `selected.raw`, complete `stdout.raw`, `stderr.raw`, the exact `recipe.sh`, transport receipt, command receipts and `result.json` with source offset, size and SHA. On failure, inspect retained original bytes; do not rerun automatically. Release the outer lock within the window even when collection fails. Host timeout stops the host transport; it does not signal the app. A disconnected remote read may finish its already bounded request.

The historical profile SHA is `eb2887fbdbdaf23d6fc1cd2840b0d8d80ea5854962753e7d4d13ce311346a077`. Its evidence alias is `$BASE20/t14-5cd-window-01/profile.json`. Original delta receipt alias is `$BASE20/t14-5cd-window-01/window/1792454599975144000-log-read/delta-result.json`, SHA `5434fd48688811f6a49ab52bd567b4651b8ea216fa68e759e7572913eeae4da1`; old 65536-byte `selected.raw` SHA `a9788774600d0865eb890b7fd7a78d1700c39e23109b76cbe30a412805944736`.

Seven real host tests exercise binary data including NULs, a file extending past the fixed end, short reads with rc 0, dd errors, missing markers, failing pre/post guards, preview/cap rejection and timeout byte retention. The Rust wrapper actually invokes these tests. Parse and lint pass (100% with advisory warnings). These results establish host behavior only; actual transport and log interpretation remain human pending review.

Same inode and size guards do **not** prove immutability or exclude in-place overwrite/truncate-regrow. This is a later retrieval of a historical byte range, not a contemporaneous immutable snapshot and not complete whole-window coverage. No conclusion about playback, namespace winner or first fatal error follows until the recovered bytes are reviewed.
