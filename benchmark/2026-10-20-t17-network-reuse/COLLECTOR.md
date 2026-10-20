# Fresh T17 profile collector

`collect_reader_profile.py` derives the paired-reader profile from explicit new
identities; it does not discover/reselect a child. Its read-only recipe derives
from the historical outer T16 collector, with every old PID/boot removed. It
requires parent/child/host PID **and birth**, boot, exact holder/start, and source
pins. It records two process snapshots, init namespace, maps, physical/private
module SHA/dev:inode, current run bytes/hash/private inode, raw ps and WMS.
Whole-line host cmdline and four UIDs/TracerPid/state/birth are checked. It then
calls the accepted `read_binding.guard` on the derived profile before publishing.
No module means UNKNOWN and no profile, not a substitute candidate identity.

```sh
python3 "$REPO/benchmark/2026-10-20-t17-network-reuse/collect_reader_profile.py" --execute \
  --repo "$REPO" --hdc "$HDC" --boot "$FRESH_BOOT" \
  --parent "$PARENT" --parent-birth "$PARENT_BIRTH" \
  --child "$CHILD" --child-birth "$CHILD_BIRTH" \
  --host "$HOST" --host-birth "$HOST_BIRTH" \
  --holder "$EXACT_T17_HOLDER" --start "$T17_START_EPOCH" \
  --out "$BASE20/t17-fresh-reader-profile"
```

Default invocation without `--execute` is zero-device preview. The new output
contains `profile.json`, `receipt.raw` (exact HDC stdout, including remote rc
framing), `run.sh`, `result.json` and original Board command receipts. Pass those
first three files to reader `--profile`, `--receipt`, `--run-file` respectively.
The collector allows at most 90 seconds and starts only before window second
1080, leaving the reader's 120 seconds and 600-second recovery reserve. Successful
profile collection is not paired-binding proof or playback acceptance.

Eight collector host tests cover real shell syntax, fixture parsing/identity,
status line order, missing/duplicate/trimmed-final markers, wrong UID/birth/tracer,
run/inode drift, missing mapping, and zero-device preview. No HDC was invoked by
the author; actual transport collection remains outer execution.
