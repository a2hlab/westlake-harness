# candidate-r2 — REJECTED (kept as evidence)

r2 (`run.sh` `79275cf9`) was rejected on static evidence by the outer (`video-1919-r2-review`) and cx-seal (`video-1919-r2-loader-review`): moving `libttmplayer` into the android namespace makes its `DT_NEEDED libmffmpeg.so` resolve by musl's by-name path, which does not run `SanitizeInitArray`; the original `libmffmpeg` (`fecf91e1`) has a single null `INIT_ARRAY` slot with no relocation, so musl `do_init_fini` (no null guard) would jump to address 0 — a **predicted** fatal (static); the observed r2 failure was the libvcbasekit ns0 relocation that masks it. See `../static/selected-change-r2.json` (`rejected`) and `../static/evidence/r2-review/`.

**Successor: `../candidate-r3/`** — same `run.sh` `79275cf9` plus a byte-exact pre-sanitized `libmffmpeg.so` (`d2882303`, `DT_INIT_ARRAYSZ 8→0`) so the by-name load no longer hits the null slot. The `run.sh` here is reused verbatim by r3.
