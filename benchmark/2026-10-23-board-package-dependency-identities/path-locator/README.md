# T119 two dependency paths from tracked metadata

Both requested hashes have explicit historical 5cd device-path mappings. No device read was performed by this lane, and current file identity remains unknown until CC compares actual stat/SHA.

| Dependency | Exact device path | Tracked source |
|---|---|---|
| JIT_SHA `b42a28e7…` | `/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/prepare_jit50.sh` | `seal-final-20261013/appendix-5cd/appendix.json:478`; `selfcheck-5cd-r5.json:3518–3521` |
| REQUEST_SHA `011a1625…` | `/data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d/request.bin` | `seal-final-20261013/appendix-5cd/appendix.json:489`; `selfcheck-5cd-r5.json:3584–3587` |

Full repository-relative source paths, exact file SHA256, Git blobs and quoted metadata lines are in source-index.json. Both files equal their tracked HEAD blobs. The historical selfcheck records matching expected/actual hashes, stronger than a path guess but not a present-day device observation. No source implementation was investigated, no raw-log tree was scanned, and no stopped workflow was executed. Search stopped after the two explicit mappings and historical selfcheck corroboration were found.
