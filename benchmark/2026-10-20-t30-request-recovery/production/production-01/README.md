# T30 actual two-unit production

The first one-unit preparation did not cover R15's independent retained request record. The admitted successor compiles only R14 `f02a8094…` and R15 `cffeb51b…`, after the independent clean-recovery and concurrent flush/abort preservation fixtures passed. This is offline build evidence; the first RequestBuffer error and device switch recovery remain unknown.

Seven real commands exited 0, with original argv/stdout/stderr/rc retained. Baseline relinking reproduced shim `9f3cecde…` exactly. The new shim is `7f8d75bbf09e28e2b57a4621f1181ff944e79e462b78707c620dd67aef0b0bcb` (107,544 bytes). Bridge `b0e5602a…` was copied unchanged, not recompiled. Both measured compiler dependency files fit the 82 pinned inputs plus their exact copied sources. All 38 indexed output hashes were independently read back after building.

The candidate retains 78 nonempty dynamic definitions, the baseline `libc.so` dependency and no TEXTREL. Actual exported offsets: lock `0x72c8`, unlock/post `0x72dc`, geometry `0xf8bc`. Geometry moved; never reuse the T29 geometry offset. The bridge and its owner resolver addresses remain unchanged.

Reproduction uses [the checked recipe and entry](../README.md), with both candidate source hashes and the actual review file in [source-freeze.json](source-freeze.json). [Results](results.json) pins the actual receipt and candidate. [Raw index](private-raw-index.json) includes the frozen sources, original peer review, exact builder/recipe snapshot, original build output, and both ELF artifacts. All large originals remain in persistent storage pending remote archival. Build success grants no device authorization or runtime success claim.
