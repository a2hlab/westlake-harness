# G01 guardian-only independent evidence review

The early gray host frame was not a final feed failure: the same ordinary icon launch subsequently showed a populated Toutiao feed. This review accepts the observed guardian-only deployment and startup, not video sealing or natural-exit reentry.

The new boot is `40dcce48-da92-497b-a412-697392062b6d`. Actual receipts identify guardian `3996/b3997`, parent `5762/b16535`, host `5522/b16253`, and child `7762/b18314`, sequence 1. All 20 placed payload hashes match the apply plan; four per-boot controls match the published r3 sources. Original runtime file hashes and physical/private inodes match. The run hash is reproduced by changing only the known baseline WID to 30.

The initial compat check used the private data/app path. The later `y07` receipt explicitly checks the actual private `asx` paths with both `-e` and `-L`, bracketed by the same boot and parent birth. Both are absent. This closes that specific evidence gap without replacing the earlier receipt.

Images were directly inspected: t30 gray; t45 feed with promotion overlay; t60 populated feed, matching t75/t90 hashes; final image populated feed. The final identity and original power `30000/86400000` remain unchanged. Debug output reports absent parameter error 106 while the command itself returns 0. Root reported actual unlock at 09:41:00, 731 seconds after lock; that statement is distinguished from directly read file receipts in `results.json`.

The outer retain decision explicitly limits retention to guardian r3. Natural-exit reentry was not observed; no forced exit was performed. No video or audio result is claimed. The private raw root is represented by `T34_GUARDIAN_WINDOW_01`; source filenames, sizes and hashes are preserved in `source-index.json`. This peer used no device commands.
